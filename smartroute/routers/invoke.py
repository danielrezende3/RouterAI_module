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
    get_effective_timeout,
    start_chat_model,
)
from smartroute.schemas import InferencePublic, InferenceRequest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/invoke", tags=["invoke"])
TIER_MODEL_MAPPING = {
    "fast": FAST_MODELS,
    "mid": MID_MODELS,
    "reasoning": REASONING_MODELS,
}
ALL_MODELS_FAILED_REQUEST = "All models failed to process the request."


@router.post("/", response_model=InferencePublic)
async def invoke_ai_response(inference_request: InferenceRequest) -> InferencePublic:
    logger.info(
        "Received invocation request with tier: %s, fallback: %s, and latency mode: %s",
        inference_request.tier,
        inference_request.fallback,
        inference_request.latency_mode,
    )
    models, timeout = await get_models(inference_request)
    if inference_request.latency_mode:
        response = await get_model_response_concurrent(
            models, inference_request.text, timeout
        )
    else:
        response = await get_model_response_sequential(
            models, inference_request.text, timeout
        )
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
    if inference_request.fallback and inference_request.tier:
        logger.error("Both fallback and tier were provided in the request.")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Please choose either fallback or tier, not both.",
        )
    if inference_request.fallback:
        logger.debug("Initializing fallback models: %s", inference_request.fallback)
        return initialize_fallback_models(inference_request.fallback)

    tier = inference_request.tier
    if not tier:
        classification_result = await async_classify_prompt(inference_request.text)
        tier = decide_tier(classification_result)
        logger.debug("Determined tier '%s' from classification result", tier)
    return initialize_tier_models(tier)


def initialize_fallback_models(
    fallback_model_keys: list[str],
) -> tuple[list[BaseChatModel], float]:
    """
    Initializes fallback models based on provided model keys.

    Each model key is used to start a chat model instance. The effective timeout is
    determined from the timeout values in the respective model configurations.

    :param fallback_model_keys: A list of model keys for fallback.
    :return: A tuple of the list of model instances and the effective timeout.
    :raises HTTPException: If initialization of any model fails.
    """
    models = []
    timeouts = []
    for key in fallback_model_keys:
        try:
            model_config = ALL_MODELS[key]
            model = start_chat_model(model_config)
            models.append(model)
            timeouts.append(model_config["timeout"])
            logger.debug("Successfully started fallback model: %s", key)
        except (ValueError, ImportError, KeyError) as e:
            logger.error("Error initializing fallback model '%s': %s", key, e)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error initializing model '{key}': {e}",
            )
    effective_timeout = max(timeouts) if timeouts else 600.0
    return models, effective_timeout


def initialize_tier_models(tier: str) -> tuple[list[BaseChatModel], float]:
    """
    Initializes models based on the specified tier.

    Retrieves the model configuration for the given tier, computes the effective timeout,
    and returns the chat instances along with the computed timeout.

    :param tier: The tier name ('fast', 'mid', or 'reasoning').
    :return: A tuple of the list of model instances and the effective timeout in seconds.
    :raises HTTPException: If an invalid tier is provided.
    """
    model_configs = TIER_MODEL_MAPPING.get(tier)
    if not model_configs:
        logger.error("Invalid tier model provided: %s", tier)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid tier model. Choose between 'fast', 'mid', or 'reasoning'.",
        )
    models = get_chat_instances(model_configs)
    timeout = get_effective_timeout(model_configs)
    logger.debug(
        "Initialized tier models for '%s' with effective timeout %s seconds",
        tier,
        timeout,
    )
    return models, timeout


async def invoke_model(
    model: BaseChatModel, text: str, timeout: float
) -> tuple[str, str]:
    """
    Invoke the specified chat model asynchronously with the given text.

    This function extracts the model name from the provided chat model instance and invokes
    its asynchronous method to process the input text. The operation is subject to a timeout, and
    the resulting output is converted to a string if necessary before being returned.

    :param model: An instance of a chat model implementing the asynchronous 'ainvoke' method.
    :type model: BaseChatModel
    :param text: The input text prompt to be processed by the model.
    :type text: str
    :param timeout: The maximum time in seconds to wait for the model's response.
    :type timeout: float
    :return: A tuple where the first element is the model's name and the second element is the output as a string.
    :rtype: tuple[str, str]

    :raises asyncio.TimeoutError: If the model invocation exceeds the specified timeout.
    """
    model_name = extract_model_name(model)
    logger.debug("Invoking model: %s", model_name)
    result = await asyncio.wait_for(model.ainvoke(text), timeout=timeout)
    output = result.content if isinstance(result.content, str) else str(result.content)
    return model_name, output


async def get_model_response_concurrent(
    models: list[BaseChatModel], text: str, timeout: float
) -> InferencePublic:
    """
    Invokes all models concurrently and returns the first valid response.
    Pending tasks are cancelled once a valid response is received.
    """
    tasks = [
        asyncio.create_task(invoke_model(model, text, timeout)) for model in models
    ]
    try:
        for completed_task in asyncio.as_completed(tasks, timeout=timeout):
            try:
                model_name, output = await completed_task
                # Cancel any remaining tasks
                for t in tasks:
                    if not t.done():
                        t.cancel()
                return InferencePublic(output=output, model_used=model_name)
            except Exception as e:
                logger.error("A model invocation failed: %s", e)
                continue
    except asyncio.TimeoutError:
        logger.error("No model responded within the timeout period.")

    logger.error(ALL_MODELS_FAILED_REQUEST)
    raise HTTPException(
        status_code=status.HTTP_408_REQUEST_TIMEOUT,
        detail=ALL_MODELS_FAILED_REQUEST,
    )


async def get_model_response_sequential(
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
    logger.error(ALL_MODELS_FAILED_REQUEST)
    raise HTTPException(
        status_code=status.HTTP_408_REQUEST_TIMEOUT,
        detail=ALL_MODELS_FAILED_REQUEST,
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

    return text.split("/")[-1] if "/" in text else text
