import asyncio
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_postgres import PostgresChatMessageHistory

from smartroute.classifier import async_classify_prompt, decide_tier
from smartroute.database import get_session
from smartroute.models_config import (
    ALL_MODELS,
    FAST_MODELS,
    MID_MODELS,
    REASONING_MODELS,
    get_chat_instances,
    get_effective_timeout,
    start_chat_model,
)
from smartroute.schemas import InvokeResponse, InvokeRequest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/invoke", tags=["invoke"])
TIER_MODEL_MAPPING = {
    "fast": FAST_MODELS,
    "mid": MID_MODELS,
    "reasoning": REASONING_MODELS,
}
ALL_MODELS_FAILED_REQUEST = "All models failed to process the request."


@router.post("/", response_model=InvokeResponse)
async def invoke_ai_response(
    inference_request: InvokeRequest, session=Depends(get_session)
) -> InvokeResponse:
    response, model_used = await process_inference_request(
        inference_request.text,
        inference_request.fallback,
        inference_request.tier,
        inference_request.latency_mode,
        session=session,
    )
    context_token = str(uuid.uuid4())
    # Save the inference request and response to the database
    # save_inference_request(inference_request, response, context_token)
    chat_history = PostgresChatMessageHistory(
        "chat_history", context_token, async_connection=session
    )
    msgs = [
        SystemMessage(content="You're a helpful AI assistant!"),
        HumanMessage(content=inference_request.text),
        AIMessage(content=str(response.content)),
    ]
    await chat_history.aadd_messages(msgs)
    logger.info(await chat_history.aget_messages())
    return InvokeResponse(
        output=str(response.content), model_used=model_used, context_token=context_token
    )


@router.post("/{context_token}", response_model=InvokeResponse)
async def invoke_ai_response_with_history(
    context_token: str, inference_request: InvokeRequest, session=Depends(get_session)
) -> InvokeResponse:
    response, model_used = await process_inference_request(
        inference_request.text,
        inference_request.fallback,
        inference_request.tier,
        inference_request.latency_mode,
        context_token,
        session=session,
    )

    return InvokeResponse(
        output=str(response.content), model_used=model_used, context_token=context_token
    )


async def process_inference_request(
    text: str,
    fallback: list[str] | None = None,
    tier: str | None = None,
    latency_mode: bool = False,
    context_token: str = "",
    session=None,
) -> tuple[BaseMessage, str]:
    logger.info(
        "Received invocation request with tier: %s, fallback: %s, and latency mode: %s",
        tier,
        fallback,
        latency_mode,
    )
    models, timeout = await get_models(text, fallback, tier)
    base_messages = await prepare_text(text, context_token, session=session)
    if latency_mode:
        response, model_used = await get_model_response_concurrent(
            models, base_messages, timeout
        )
    else:
        response, model_used = await get_model_response_sequential(
            models, base_messages, timeout
        )

    return response, model_used


async def prepare_text(
    text: str, context_token: str = "", session=Depends(get_session)
) -> list[BaseMessage]:
    if not context_token:
        return [HumanMessage(content=text)]
    chat_history = PostgresChatMessageHistory(
        "chat_history", context_token, async_connection=session
    )
    history = await chat_history.aget_messages()
    return history + [HumanMessage(content=text)]


async def get_models(
    text: str,
    fallback: list[str] | None = None,
    tier: str | None = None,
) -> tuple[list[BaseChatModel], float]:
    """
    Determines which models to initialize based on the request.

    If both fallback and tier are provided, raises an error. If fallback is provided,
    initializes fallback models; otherwise, if the tier is missing, classifies the request
    to decide the tier before initializing the tier models.
    """
    if fallback and tier:
        logger.error("Both fallback and tier were provided in the request.")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Please choose either fallback or tier, not both.",
        )
    if fallback:
        return initialize_fallback_models(fallback)

    if not tier:
        classification_result = await async_classify_prompt(text)
        tier = decide_tier(classification_result)
    return initialize_models_by_tier(tier)


def initialize_fallback_models(
    fallback_model_keys: list[str],
) -> tuple[list[BaseChatModel], float]:
    """
    Initializes fallback models based on provided model keys.

    Each model key is used to start a chat model instance. The effective timeout is
    determined from the timeout values in the respective model configurations.
    """
    models = []
    timeouts = []
    for key in fallback_model_keys:
        try:
            model_config = ALL_MODELS[key]
            model = start_chat_model(model_config)
            models.append(model)
            timeouts.append(model_config["timeout"])
        except (ValueError, ImportError, KeyError) as e:
            logger.error("Error initializing fallback model '%s': %s", key, e)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error initializing model '{key}': {e}",
            )
    effective_timeout = max(timeouts) if timeouts else 600.0
    return models, effective_timeout


def initialize_models_by_tier(tier: str) -> tuple[list[BaseChatModel], float]:
    """
    Initializes models based on the specified tier.

    Retrieves the model configuration for the given tier, computes the effective timeout,
    and returns the chat instances along with the computed timeout.
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


async def ainvoke_model(
    model: BaseChatModel, text: list[BaseMessage], timeout: float
) -> tuple[BaseMessage, str]:
    """
    Invoke the specified chat model asynchronously with the given text.

    This function extracts the model name from the provided chat model instance and invokes
    its asynchronous method to process the input text. The operation is subject to a timeout, and
    the resulting output is converted to a string if necessary before being returned.
    """
    model_name = get_model_name(model)
    logger.debug("Invoking model: %s", model_name)
    result = await asyncio.wait_for(model.ainvoke(text), timeout=timeout)
    return result, model_name


async def get_model_response_concurrent(
    models: list[BaseChatModel], text: list[BaseMessage], timeout: float
) -> tuple[BaseMessage, str]:
    """
    Invokes all models concurrently and returns the first valid response.
    Pending tasks are cancelled once a valid response is received.
    """
    tasks = [
        asyncio.create_task(ainvoke_model(model, text, timeout)) for model in models
    ]
    try:
        for completed_task in asyncio.as_completed(tasks, timeout=timeout):
            try:
                result, model_name = await completed_task
                # Cancel any remaining tasks
                for t in tasks:
                    if not t.done():
                        t.cancel()
                return (result, model_name)
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
    models: list[BaseChatModel], text: list[BaseMessage], timeout: float
) -> tuple[BaseMessage, str]:
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
        try:
            result, model_name = await ainvoke_model(model, text, timeout)
            return result, model_name
        except asyncio.TimeoutError:
            logger.error(
                f"Model {get_model_name(model)} timed out after {timeout} seconds."
            )
        except Exception as e:
            logger.error(f"Model {get_model_name(model)} encountered an error: {e}")
    logger.error(ALL_MODELS_FAILED_REQUEST)
    raise HTTPException(
        status_code=status.HTTP_408_REQUEST_TIMEOUT,
        detail=ALL_MODELS_FAILED_REQUEST,
    )


def get_model_name(model) -> str:
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
