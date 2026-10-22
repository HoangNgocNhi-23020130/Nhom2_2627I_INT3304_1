"""
backend/app/core/security.py
Băm mật khẩu và quản lý JWT Token.
"""
import hashlib
import os
import secrets
from datetime import datetime, timedelta
import jwt

SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "ottv2_super_secret_jwt_key_2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # Token có hạn 7 ngày


def hash_password(password: str) -> str:
    """Tạo salt ngẫu nhiên và băm mật khẩu bằng PBKDF2-HMAC-SHA256."""
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations=100_000
    ).hex()
    return f"{salt}${key}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Kiểm tra mật khẩu nhập vào với chuỗi băm trong DB."""
    try:
        salt, stored_key = hashed_password.split("$")
        calculated_key = hashlib.pbkdf2_hmac(
            "sha256",
            plain_password.encode("utf-8"),
            salt.encode("utf-8"),
            iterations=100_000
        ).hex()
        return secrets.compare_digest(stored_key, calculated_key)
    except Exception:
        return False


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None