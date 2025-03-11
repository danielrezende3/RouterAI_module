from fastapi import FastAPI

from smartroute.ai_models.chat_model_initializer import (
    FAST_MODELS,
    MID_MODELS,
    REASONING_MODELS,
)
from smartroute.routers import auth, invoke
from smartroute.schemas import MessageResponse
from smartroute.settings import Settings

settings = Settings()  # type: ignore

description = f"""
SmartRoute API is a service that routes text data to the most appropriate model based on the provided tier. If no tier is provided, a classifier is used to determine the best model.

## Models available:

|    type/model | chatgpt                |          Gemini          | Claude                     |
| ------------: | ---------------------: | :----------------------: | :------------------------- |
|      **fast** | {FAST_MODELS["chatgpt-fast"]["name"]} |  {FAST_MODELS["gemini-fast"]["name"]}   | {FAST_MODELS["claude-fast"]["name"]}  |
|       **mid** | {MID_MODELS["chatgpt-mid"]["name"]}            |     {MID_MODELS["gemini-mid"]["name"]}     | {MID_MODELS["claude-mid"]["name"]}   |
| **reasoning** | {REASONING_MODELS["chatgpt-reasoning"]["name"]}     | {REASONING_MODELS["gemini-reasoning"]["name"]} | {REASONING_MODELS["claude-reasoning"]["name"]} |

## Model Selection Options:

### Dynamic Tier Determination:

If the tier is not provided, the API classifies the input text using a classification function and then decides the appropriate tier based on the classification result.

It would be called like this:
```json
{{
  "text": "string",
}}
```

### Tier-Based Selection:

When no fallback is provided, the API uses the tier parameter to select models. The available tiers ("fast", "mid", "reasoning") are mapped to predefined sets of models.

It would be called like this:
```json
{{
  "text": "string",
  "tier": "fast | mid | reasoning",
}}
```

### Fallback Models:

If the request includes a fallback (a list of model keys), the API initializes and uses these models exclusively. This ensures the user can specify a custom set of models. It invokes the models sequentially.

It is choosen using `model-type` style, for example:

```json
{{
  "text": "string",
  "fallback": ["chatgpt-fast", "gemini-mid", "claude-reasoning"],
}}
```

## Response Strategy Configuration:  
The API offers two distinct inference strategies, controlled by a dedicated boolean flag (`latency_mode`):

- **Concurrent (Latency Mode)**: When `latency_mode` is set to `True`, all selected models are invoked concurrently. The API returns the first valid response and cancels any pending tasks—minimizing overall latency.
- **Sequential Processing**: If `latency_mode` is `False`, models are invoked one after another. The API attempts each model sequentially until one produces a valid response.

Note: By default the strategy choosen is sequential.
"""


app = FastAPI(title="SmartRoute API", version="0.1.0", description=description)
app.include_router(invoke.router)
app.include_router(auth.router)


@app.get("/")
async def get_welcome_message() -> MessageResponse:
    return MessageResponse(
        message="Welcome to SmartRoute API! To access the docs, go to /docs or /redoc"
    )
