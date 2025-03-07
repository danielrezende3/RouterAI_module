import asyncio
import time

from fastapi import HTTPException
import pytest

from smartroute.classifier import async_classify_prompt
from smartroute.routers.invoke import extract_model_name, get_model_response
from smartroute.schemas import InferencePublic


class DummyResponse:
    def __init__(self, content):
        self.content = content


class DummyModel:
    def __init__(self, model_name):
        self.model_name = model_name

    async def ainvoke(self, text):
        return DummyResponse(content=f"Processed: {text}")


class TimeoutDummyModel:
    def __init__(self, model_name):
        self.model_name = model_name

    async def ainvoke(self, text):
        await asyncio.sleep(0.1)
        raise asyncio.TimeoutError()


class ErrorDummyModel:
    def __init__(self, model_name):
        self.model_name = model_name

    async def ainvoke(self, text):
        raise Exception("Invocation error")


@pytest.fixture(autouse=True)
def patch_dependencies(monkeypatch):
    # Define a dummy ALL_MODELS mapping
    dummy_all_models = {"dummy": "dummy_model_config"}
    monkeypatch.setattr("smartroute.routers.invoke.ALL_MODELS", dummy_all_models)

    # Patch start_chat_model to return a DummyModel instance.
    monkeypatch.setattr(
        "smartroute.routers.invoke.start_chat_model",
        lambda config: DummyModel("dummy_model"),
    )

    # Patch get_chat_instances to return a list containing one DummyModel.
    monkeypatch.setattr(
        "smartroute.routers.invoke.get_chat_instances",
        lambda models: [DummyModel("tier_model")],
    )

    # Patch classifier functions.
    monkeypatch.setattr(
        "smartroute.classifier.classify_prompt",
        lambda text: {"prompt_complexity_score": [0]},
    )
    monkeypatch.setattr("smartroute.classifier.decide_tier", lambda result: "fast")

    # Ensure tier mappings exist (even if empty)
    monkeypatch.setattr("smartroute.routers.invoke.FAST_MODELS", {})
    monkeypatch.setattr("smartroute.routers.invoke.MID_MODELS", {})
    monkeypatch.setattr("smartroute.routers.invoke.REASONING_MODELS", {})


# ----- ENDPOINT TESTS


@pytest.mark.asyncio
async def test_semaphore_limit(monkeypatch):
    # Use a mutable state dict to track current and maximum concurrent calls.
    state = {"current": 0, "max": 0}

    # This dummy synchronous function simulates a blocking operation.
    def dummy_classify(prompt: str) -> dict:
        # Increment the current concurrency counter.
        state["current"] += 1
        # Update max if needed.
        if state["current"] > state["max"]:
            state["max"] = state["current"]
        # Simulate a blocking delay (e.g., model inference)
        time.sleep(0.2)
        # Decrement the counter after work is done.
        state["current"] -= 1
        return {"prompt_complexity_score": [0]}

    # Monkey-patch the original synchronous classify_prompt with our dummy.
    monkeypatch.setattr("smartroute.classifier.classify_prompt", dummy_classify)

    # Spawn several concurrent async calls.
    tasks = [async_classify_prompt(f"Test {i}") for i in range(10)]
    await asyncio.gather(*tasks)

    # Assert that the maximum concurrent calls never exceeded 3.
    assert state["max"] <= 3, (
        f"Semaphore limit exceeded: max concurrent was {state['max']}"
    )


def test_conflicting_request(client):
    """
    When both fallback and tier_model are provided,
    the request should be rejected with HTTP 422.
    """
    request_data = {"text": "Test input", "fallback": ["dummy"], "tier_model": "fast"}
    response = client.post("/v1/invoke", json=request_data)
    assert response.status_code == 422
    assert (
        response.json()["detail"]
        == "Please choose either fallback or tier_model, not both."
    )


def test_fallback_request_success(monkeypatch, client):
    """
    When only fallback is provided, the initialize_fallback_models
    routine should be used and the model response returned.
    """

    def dummy_initialize_fallback_models(fallback_keys):
        models = [DummyModel("fallback_model")]
        return models, 600.0

    monkeypatch.setattr(
        "smartroute.routers.invoke.initialize_fallback_models",
        dummy_initialize_fallback_models,
    )

    request_data = {"text": "Test fallback", "fallback": ["dummy"]}
    response = client.post("/v1/invoke/", json=request_data)
    assert response.status_code == 200
    json_resp = response.json()
    assert "Processed: Test fallback" in json_resp["output"]
    assert json_resp["model_used"] == "fallback_model"


def test_tier_request_success(monkeypatch, client):
    """
    When tier_model is provided (and no fallback),
    the initialize_tier_models function is used.
    """

    def dummy_initialize_tier_models(tier):
        models = [DummyModel("tier_model_test")]
        return models, 60.0

    monkeypatch.setattr(
        "smartroute.routers.invoke.initialize_tier_models", dummy_initialize_tier_models
    )

    request_data = {"text": "Test tier", "tier_model": "fast"}
    response = client.post("/v1/invoke/", json=request_data)
    assert response.status_code == 200
    json_resp = response.json()
    assert "Processed: Test tier" in json_resp["output"]
    assert json_resp["model_used"] == "tier_model_test"


def test_classification_request(monkeypatch, client):
    """
    When neither fallback nor tier_model is provided,
    the classifier is used to decide which tier to use.
    """

    def dummy_initialize_tier_models(tier):
        models = [DummyModel("classified_model")]
        return models, 60.0

    monkeypatch.setattr(
        "smartroute.routers.invoke.initialize_tier_models", dummy_initialize_tier_models
    )

    request_data = {"text": "Test classification"}
    response = client.post("/v1/invoke/", json=request_data)
    assert response.status_code == 200
    json_resp = response.json()
    assert "Processed: Test classification" in json_resp["output"]
    assert json_resp["model_used"] == "classified_model"


# ----- DIRECT UNIT TESTS
@pytest.mark.asyncio
async def test_get_model_response_success():
    """
    Verify that get_model_response returns the expected output
    when at least one model processes the text successfully.
    """
    models = [DummyModel("test_model")]
    result: InferencePublic = await get_model_response(models, "Hello", 60.0)  # type: ignore
    assert result.output == "Processed: Hello"
    assert result.model_used == "test_model"


@pytest.mark.asyncio
async def test_get_model_response_timeout():
    """
    Verify that if all models time out, an HTTPException with
    status 408 is raised.
    """
    models = [TimeoutDummyModel("timeout_model")]
    with pytest.raises(HTTPException) as excinfo:
        await get_model_response(models, "Hello", 0.01)  # type: ignore
    assert excinfo.value.status_code == 408


@pytest.mark.asyncio
async def test_get_model_response_error_then_success():
    """
    Verify that if the first model raises an error and the second model
    returns a valid response, the valid response is used.
    """
    models = [ErrorDummyModel("error_model"), DummyModel("success_model")]
    result: InferencePublic = await get_model_response(models, "Hello", 60.0)
    assert result.output == "Processed: Hello"
    assert result.model_used == "success_model"


def test_extract_model_name():
    """
    Verify that extract_model_name returns the correct model name based
    on available attributes.
    """

    # Case: model attribute exists and contains a slash.
    class ObjA:
        model = "abc/def"

    name = extract_model_name(ObjA())
    assert name == "def"

    # Case: model_name attribute exists.
    class ObjB:
        model_name = "xyz"

    name = extract_model_name(ObjB())
    assert name == "xyz"

    # Case: neither attribute exists.
    class ObjC:
        pass

    name = extract_model_name(ObjC())
    assert name == "unknown_model"

    # Case: model attribute exists without a slash.
    class ObjD:
        model = "simplemodel"

    name = extract_model_name(ObjD())
    assert name == "simplemodel"
