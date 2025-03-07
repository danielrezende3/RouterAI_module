import asyncio
import logging

from fastapi import APIRouter, HTTPException, status
from langchain_core.language_models import BaseChatModel

from smartroute.classifier import async_classify_prompt, decide_tier
from smartroute.models_config import (
    ALL_MODELS,
    FAST_MODELS,
    MID_MODELS,
    REASONING_MODELS,
    get_chat_instances,
    start_chat_model,
)
from smartroute.schemas import InferencePublic, InferenceRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/invoke", tags=["invoke"])

TIER_MODEL_MAPPING = {
    "fast": (FAST_MODELS, 60),
    "mid": (MID_MODELS, 60),
    "reasoning": (REASONING_MODELS, 600),
}


@router.post("/", response_model=InferencePublic)
async def invoke_ai_response(inference_request: InferenceRequest) -> InferencePublic:
    """
    Endpoint to process the inference request and return an AI model response.

    Depending on the provided tier or fallback configuration, the function
    selects and invokes the appropriate AI model. If no tier is provided, the
    request is classified to determine the best tier.

    :param inference_request: The inference request containing the text, tier,
                              and optional fallback configuration.
    :return: An InferencePublic object with the output and the model used.
    :raises HTTPException: For invalid request combinations or if all models fail.
    """
    logger.info(
        "Received invocation request with tier: %s and fallback: %s",
        inference_request.tier_model,
        inference_request.fallback,
    )
    models, timeout = await get_models(inference_request)
    response = await get_model_response(models, inference_request.text, timeout)
    return response


async def get_models(
    inference_request: InferenceRequest,
) -> tuple[list[BaseChatModel], float]:
    """
    Determines which models to initialize based on the request.

    If both fallback and tier are provided, raises an error. If fallback is provided,
    initializes fallback models; otherwise, if the tier is missing, classifies the request
    to decide the tier before initializing the tier models.

    :param inference_request: The inference request.
    :return: A tuple of the list of model instances and the timeout in seconds.
    :raises HTTPException: If both fallback and tier are provided.
    """
    if inference_request.fallback and inference_request.tier_model:
        logger.error("Both fallback and tier_model were provided in the request.")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Please choose either fallback or tier_model, not both.",
        )
    if inference_request.fallback:
        logger.debug("Initializing fallback models: %s", inference_request.fallback)
        return initialize_fallback_models(inference_request.fallback)

    tier = inference_request.tier_model
    if not tier:
        classification_result = await async_classify_prompt(inference_request.text)
        tier = decide_tier(classification_result)
        logger.debug("Determined tier '%s' from classification result", tier)
    return initialize_tier_models(tier)


def initialize_fallback_models(
    fallback_model_keys: list[str],
) -> tuple[list[BaseChatModel], float]:
    models = []
    for key in fallback_model_keys:
        try:
            model = start_chat_model(ALL_MODELS[key])
            models.append(model)
            logger.debug("Successfully started fallback model: %s", key)
        except (ValueError, ImportError, KeyError) as e:
            logger.error("Error initializing fallback model '%s': %s", key, e)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error initializing model '{key}': {e}",
            )
    # TODO: Dynamically determine the timeout based on the slowest model if needed.
    return models, 600.0


def initialize_tier_models(tier: str) -> tuple[list[BaseChatModel], float]:
    """
    Initializes fallback models based on provided model keys.

    Each model key is used to start a chat model instance. If any model fails to initialize,
    an HTTP exception is raised.

    :param fallback_model_keys: A list of model keys for fallback.
    :return: A tuple of the list of model instances and a fixed timeout of 600 seconds.
    :raises HTTPException: If initialization of any model fails.
    """
    config = TIER_MODEL_MAPPING.get(tier)
    if not config:
        logger.error("Invalid tier model provided: %s", tier)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid tier model. Choose between 'fast', 'mid', or 'reasoning'.",
        )
    models, timeout = get_chat_instances(config[0]), config[1]
    logger.debug(
        "Initialized tier models for '%s' with timeout %s seconds", tier, timeout
    )
    return models, timeout


async def get_model_response(
    models: list[BaseChatModel], text: str, timeout: float
) -> InferencePublic:
    """
    Attempts to generate a response from the provided models.

    Iterates through the list of models and calls their asynchronous invocation method.
    If a model times out or errors, the next model is tried. If all models fail, an exception
    is raised.

    :param models: List of AI model instances.
    :param text: The text prompt for the AI model.
    :param timeout: Maximum allowed time for each model's invocation.
    :return: An InferencePublic object with the model's output and identifier.
    :raises HTTPException: If all models fail to produce a valid response.
    """
    for model in models:
        model_name = extract_model_name(model)
        logger.debug("Invoking model: %s", model_name)
        try:
            result = await asyncio.wait_for(model.ainvoke(text), timeout=timeout)
            output = (
                result.content
                if isinstance(result.content, str)
                else str(result.content)
            )
            return InferencePublic(output=output, model_used=model_name)
        except asyncio.TimeoutError:
            logger.error("Model %s timed out after %s seconds.", model_name, timeout)
        except Exception as e:
            logger.error("Model %s encountered an error: %s", model_name, e)
    logger.error("All models failed to process the request.")
    raise HTTPException(
        status_code=status.HTTP_408_REQUEST_TIMEOUT,
        detail="All models failed to process the request.",
    )


def extract_model_name(model) -> str:
    """
    Extracts a user-friendly name from the model instance.

    The function checks for common attributes that indicate the model's name.
    If the name contains a forward slash, only the part after the last slash is returned.

    :param model: An AI model instance.
    :return: A simplified model name.
    """
    text = ""
    if hasattr(model, "model"):
        text = model.model
    elif hasattr(model, "model_name"):
        text = model.model_name
    else:
        text = "unknown_model"

    if text.find("/") != -1:
        return text.split("/")[-1]
    else:
        return text
