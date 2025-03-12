from typing import Annotated
import uuid
from datetime import datetime, timedelta, timezone
from psycopg import AsyncConnection

from fastapi import Depends, HTTPException, Header, status
import jwt

from smartroute.database import get_session
from smartroute.settings import Settings

settings = Settings()  # type: ignore

SECRET_KEY = settings.jwt_secret_key
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
Session = Annotated[AsyncConnection, Depends(get_session)]


def create_access_token(
    user: str, expires_delta: timedelta | None = None
) -> tuple[str, str]:
    """Generate a JWT access token for a given user.

    Notes:
    - The function creates a unique identifier (jti) for the token.
    - The token payload contains the user information and expiration time.
    - The expiration time is stored as a Unix timestamp in string format.
    - The token is encoded using the SECRET_KEY and ALGORITHM defined elsewhere in the module."""
    jti = str(uuid.uuid4())
    to_encode = {"sub": user, "jti": jti, "exp": 0}
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(weeks=52))
    to_encode["exp"] = int(expire.timestamp())
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return token, jti


def verify_token(token: str):
    """
    Verifies the provided JWT token.

    This function attempts to decode the given JWT token using a predefined secret key and algorithm.
    If the token is valid, it returns the decoded payload. In case the token is invalid,
    it catches the respective exception and returns None.
    """

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.InvalidTokenError:
        return None


async def get_current_user(
    session: Session,
    jwt_token: str = Header(...),
) -> str:
    """Asynchronously retrieves the current user based on the provided authentication token.
    This function validates the given token by verifying its payload and ensuring that it exists
    and remains active in the database. If the token is either invalid or has been revoked,
    an HTTPException with a 401 status code is raised."""
    payload = verify_token(jwt_token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )
    jti = payload.get("jti")
    select_sql = "SELECT * FROM tokens WHERE jti = %s AND active = TRUE"
    async with session.cursor() as cur:
        await cur.execute(select_sql, (jti,))
        token_row = await cur.fetchone()
    if not token_row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token revoked or non existent",
        )
    return payload.get("sub")
