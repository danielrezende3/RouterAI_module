from fastapi import FastAPI

from smartroute.routers import invoke
from smartroute.settings import Settings

settings = Settings()  # type: ignore
app = FastAPI()

app.include_router(invoke.router)


@app.get("/")
async def get_welcome_message():
    return {
        "message": "Welcome to SmartRoute API! To access the docs, go to /docs or /redoc",
    }
