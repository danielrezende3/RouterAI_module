from datetime import datetime, timezone
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
