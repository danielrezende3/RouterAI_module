import psycopg
from langchain_postgres import PostgresChatMessageHistory
from smartroute.settings import Settings

settings = Settings()  # type: ignore

DATABASE_URL = settings.database_url
connection = psycopg.connect(DATABASE_URL)
PostgresChatMessageHistory.create_tables(connection, "chat_history")
connection.close()


async def get_session():
    async with await psycopg.AsyncConnection.connect(DATABASE_URL) as conn:
        yield conn
