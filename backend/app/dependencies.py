"""Application-level dependencies for DB, settings, and JWT auth."""

from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
	credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
	db: AsyncSession = Depends(get_db),
) -> User:
	if credentials is None or not credentials.credentials:
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing auth token")

	payload = decode_access_token(credentials.credentials)
	if payload is None or not payload.get("sub"):
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid auth token")

	result = await db.execute(select(User).where(User.id == payload["sub"]))
	user = result.scalar_one_or_none()
	if user is None:
		raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
	return user


def require_roles(*allowed_roles: str) -> Callable:
	allowed = {role.upper() for role in allowed_roles}

	async def _role_guard(current_user: User = Depends(get_current_user)) -> User:
		if current_user.role.upper() not in allowed:
			raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
		return current_user

	return _role_guard


__all__ = ["get_db", "get_settings", "get_current_user", "require_roles"]
