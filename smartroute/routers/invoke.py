import asyncio
import logging
from fastapi import APIRouter, HTTPException, status
from langchain_core.language_models import BaseChatModel

from smartroute.schemas import InferencePublic, InferenceRequest
from smartroute.models_config import (
    ALL_MODELS,
    MID_MODELS,
    start_chat_model,
    FAST_MODELS,
    REASONING_MODELS,
    get_chat_instances,
)

router = APIRouter(prefix="/v1/invoke", tags=["invoke"])

TIER_MODEL_MAPPING = {
    "fast": (FAST_MODELS, 60),
    "mid": (MID_MODELS, 60),
    "reasoning": (REASONING_MODELS, 600),
}


@router.post("/", response_model=InferencePublic)
async def invoke_ai_response(inference_request: InferenceRequest):
    models, timeout = get_models(inference_request)
    text = inference_request.text
    return await get_model_response(models, text, timeout)


def get_models(
    inference_request: InferenceRequest,
) -> tuple[list[BaseChatModel], float]:
    if inference_request.fallback:
        return initialize_fallback_models(inference_request.fallback)
    else:
        return initialize_tier_models(inference_request.tier_model or "fast")


def initialize_fallback_models(
    fallback_model_keys,
) -> tuple[list[BaseChatModel], float]:
    # TODO: Add a timeout according from the slowest model
    models = []
    for key in fallback_model_keys:
        try:
            model = start_chat_model(ALL_MODELS[key])
            models.append(model)
        except (ValueError, ImportError, KeyError) as e:
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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid tier model. Choose between 'fast', 'mid', or 'reasoning'.",
        )
    return get_chat_instances(models_config[0]), models_config[1]


async def get_model_response(
    models: list[BaseChatModel], text: str, timeout: float
) -> InferencePublic:
    for model in models:
        try:
            result = await asyncio.wait_for(model.ainvoke(text), timeout=timeout)
            model_name = extract_model_name(model)
            output = (
                result.content
                if isinstance(result.content, str)
                else str(result.content)
            )
            return InferencePublic(output=output, model_used=model_name)
        except asyncio.TimeoutError:
            logging.error(f"Model {extract_model_name(model)} timed out.")
            continue  # Try the next model
    raise HTTPException(
        status_code=status.HTTP_408_REQUEST_TIMEOUT,
        detail="All models failed to process the request.",
    )


def extract_model_name(model) -> str:
    if hasattr(model, "model"):
        return model.model.split("/")[1]
    elif hasattr(model, "model_name"):
        return model.model_name
    return "unknown_model"
