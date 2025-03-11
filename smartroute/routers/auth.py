from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from psycopg import AsyncConnection, Connection

from smartroute.database import get_session
from smartroute.schemas import MessageResponse, TokenResponse
from smartroute.security import create_access_token, verify_token
from smartroute.settings import Settings

settings = Settings()  # type: ignore
SECRET_KEY = settings.jwt_secret_key
INVALID_TOKEN = "Invalid token"
router = APIRouter(prefix="/v1/auth", tags=["auth"])
Session = Annotated[AsyncConnection, Depends(get_session)]


@router.post("/token")
async def login(user: str, session: Session) -> TokenResponse:
    """
    Logs in a user by generating an access token and storing it in the database for potential revocation.

    Notes:
    - The access token is generated with an expiration time of 30 minutes.
    - A unique token identifier (jti) is generated and stored along with the token and user information in the database.
    - The token is committed and refreshed in the database session to persist the changes.
    """

    access_token_expires = timedelta(minutes=30)
    token, jti = create_access_token(user=user, expires_delta=access_token_expires)

    # Salva token no banco para revogação
    insert_sql = """
    INSERT INTO tokens ("user", active, jti)
    VALUES (%s, %s, %s)
    RETURNING jti;
    """
    async with session.cursor() as cur:
        await cur.execute(insert_sql, (user, True, jti))
        await cur.fetchone()
    await session.commit()

    return TokenResponse(access_token=token, token_type="bearer")


@router.get("/protected")
async def protected_endpoint(
    session: Session,
    token: str = Header(...),
) -> MessageResponse:
    """Verifies the provided authorization token and authorizes the request.

    This endpoint dependency function checks the token from the request header by verifying
    its payload. It ensures that the token is valid and active by querying the token store.
    If the token is invalid or revoked, it raises an HTTPException with a 401 Unauthorized status."""

    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=INVALID_TOKEN
        )

    jti = payload.get("jti")
    user = payload.get("sub")

    select_sql = "SELECT * FROM tokens WHERE jti = %s AND active = TRUE"
    async with session.cursor() as cur:
        await cur.execute(select_sql, (jti,))
        token_row = await cur.fetchone()

    if not token_row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token revoked or non existent",
        )

    return MessageResponse(message=f"Access authorized for {user}")


@router.post("/revoke")
async def revoke_token(token: str, session: Session) -> MessageResponse:
    """Revokes an authentication token by verifying its validity and marking it as inactive in the database."""

    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=INVALID_TOKEN
        )
    jti = payload.get("jti")
    update_sql = "UPDATE tokens SET active = FALSE WHERE jti = %s RETURNING jti"
    async with session.cursor() as cur:
        await cur.execute(update_sql, (jti,))
        result = await cur.fetchone()

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Token not found"
        )

    await session.commit()
    return MessageResponse(message="Token revoked")
