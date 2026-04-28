from datetime import datetime, timedelta, timezone
import logging

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

MAX_PASSWORD_BYTES = 72


def verify_password(plain_password: str, password_hash: str) -> bool:
    if not plain_password or not password_hash:
        return False
    try:
        return pwd_context.verify(plain_password, password_hash)
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False


def get_password_hash(password: str) -> str:
    if not password:
        raise ValueError("Password cannot be empty")
    
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > MAX_PASSWORD_BYTES:
        raise ValueError(f"Password too long (max {MAX_PASSWORD_BYTES} bytes for security constraints)")
    
    try:
        return pwd_context.hash(password)
    except Exception as e:
        logger.error(f"Password hashing error: {e}")
        raise ValueError("Failed to hash password due to internal error") from e


def create_access_token(subject: str, role: str, ngo_id: str | None = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": subject,
        "role": role,
        "ngo_id": ngo_id,
        "exp": expire,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        return None
