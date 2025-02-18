import asyncio
import logging
from fastapi import APIRouter, HTTPException, status
from langchain_core.language_models import BaseChatModel

from smartroute import classifier
from smartroute.schemas import InferencePublic, InferenceRequest
from smartroute.models_config import (
    ALL_MODELS,
    MID_MODELS,
    start_chat_model,
    FAST_MODELS,
    REASONING_MODELS,
    get_chat_instances,
)


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/invoke", tags=["invoke"])

TIER_MODEL_MAPPING = {
    "fast": (FAST_MODELS, 60),
    "mid": (MID_MODELS, 60),
    "reasoning": (REASONING_MODELS, 600),
}


@router.post("/", response_model=InferencePublic)
async def invoke_ai_response(inference_request: InferenceRequest):
    logger.info(
        "Received invocation request with tier: %s and fallback: %s",
        inference_request.tier_model,
        inference_request.fallback,
    )
    models, timeout = get_models(inference_request)
    text = inference_request.text
    logger.debug("Text to process: %s", text)
    response = await get_model_response(models, text, timeout)
    return response


def get_models(
    inference_request: InferenceRequest,
) -> tuple[list[BaseChatModel], float]:
    if inference_request.fallback and inference_request.tier_model:
        logger.error("Both fallback and tier_model were provided in the request.")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Please choose either fallback or tier_model, not both.",
        )
    if inference_request.fallback:
        logger.debug("Initializing fallback models: %s", inference_request.fallback)
        return initialize_fallback_models(inference_request.fallback)
    else:
        tier = inference_request.tier_model
        if not tier:
            classification_result = classifier.classify_prompt(inference_request.text)
            score = classification_result.get("prompt_complexity_score", [0])[0]
            tier = classifier.decide_tier(classification_result)
            logger.debug("Classification result: %s", score)
        return initialize_tier_models(tier)


def initialize_fallback_models(
    fallback_model_keys,
) -> tuple[list[BaseChatModel], float]:
    # TODO: Add a timeout according from the slowest model
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
    return models, 600.0


def initialize_tier_models(
    tier_model: str,
) -> tuple[list[BaseChatModel], float]:
    models_config = TIER_MODEL_MAPPING.get(tier_model)
    if not models_config:
        logger.error("Invalid tier model provided: %s", tier_model)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid tier model. Choose between 'fast', 'mid', or 'reasoning'.",
        )
    logger.debug(
        "Initializing tier models for tier: %s with timeout %s seconds",
        tier_model,
        models_config[1],
    )
    return get_chat_instances(models_config[0]), models_config[1]


async def get_model_response(
    models: list[BaseChatModel], text: str, timeout: float
) -> InferencePublic:
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
            continue  # Try the next model
        except Exception as e:
            logger.error("Model %s encountered an error: %s", model_name, e)
            continue  # Optionally try the next model or handle differently
    logger.error("All models failed to process the request.")
    raise HTTPException(
        status_code=status.HTTP_408_REQUEST_TIMEOUT,
        detail="All models failed to process the request.",
    )


def extract_model_name(model) -> str:
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
