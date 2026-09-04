"""
Authentication stage of the request pipeline.

An API-key check written as a FastAPI *dependency* — a reusable unit that FastAPI
runs BEFORE the endpoint body. If it raises, the endpoint never executes. This is
the same "ordered pipeline stage" idea the whole app is built on: auth is a stage
you attach in front of any route that needs protecting.

Clients authenticate by sending:  Authorization: Bearer <api-key>
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings

# Parses the "Authorization: Bearer <token>" header. auto_error=False lets us
# return our own clean 401 instead of FastAPI's default when the header is missing.
_bearer = HTTPBearer(auto_error=False)


async def require_api_key(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> None:
    """
    Reject the request unless a valid API key was supplied. Attach this to a
    route (via `dependencies=[Depends(require_api_key)]`) to protect it.
    """
    if credentials is None or credentials.credentials != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
