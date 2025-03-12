from datetime import datetime, timezone
import logging
from psycopg import Connection
from sqlalchemy import String, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column, registry

table_registry = registry()


@table_registry.mapped_as_dataclass
class TokenModel:
    __tablename__ = "tokens"
    jti: Mapped[str] = mapped_column(primary_key=True, init=False)
    user: Mapped[str] = mapped_column(String, index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now(timezone.utc)
    )


@table_registry.mapped_as_dataclass
class ChatSessionModel:
    __tablename__ = "chat_sessions"
    context_token: Mapped[str] = mapped_column(primary_key=True)
    owner: Mapped[str] = mapped_column(String, index=True)


def create_tokens_table(session: Connection) -> None:
    create_table_query = """
    CREATE TABLE IF NOT EXISTS tokens (
        jti TEXT PRIMARY KEY,
        "user" TEXT,
        active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );
    """
    with session.cursor() as cur:
        cur.execute(create_table_query)
    session.commit()
    logging.info("Created tokens table")


def create_chat_sessions_table(connection):
    create_table_query = """
    CREATE TABLE IF NOT EXISTS chat_sessions (
        context_token TEXT PRIMARY KEY,
        owner TEXT
    );
    """
    with connection.cursor() as cur:
        cur.execute(create_table_query)
    connection.commit()
    logging.info("Created chat_session table")
