"""Encryption service for securing API credentials using Fernet symmetric encryption."""

import json
import logging

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings

logger = logging.getLogger(__name__)

_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    """Get or create Fernet instance from master key."""
    global _fernet
    if _fernet is not None:
        return _fernet

    key = settings.encryption_master_key
    if not key:
        key = Fernet.generate_key().decode()
        logger.warning(
            "ENCRYPTION_MASTER_KEY not set — using ephemeral key. "
            "Encrypted credentials will be lost on restart. "
            "Set ENCRYPTION_MASTER_KEY in .env for persistence."
        )

    _fernet = Fernet(key.encode() if isinstance(key, str) else key)
    return _fernet


def encrypt(data: dict) -> str:
    """Encrypt a dict as a Fernet token string."""
    payload = json.dumps(data).encode("utf-8")
    return _get_fernet().encrypt(payload).decode("utf-8")


def decrypt(token: str) -> dict:
    """Decrypt a Fernet token string back to a dict."""
    try:
        payload = _get_fernet().decrypt(token.encode("utf-8"))
        return json.loads(payload)
    except InvalidToken:
        logger.error("Failed to decrypt credentials — invalid token or wrong key")
        raise ValueError("Invalid encryption token — master key may have changed")


def generate_key() -> str:
    """Generate a new Fernet key (for initial setup)."""
    return Fernet.generate_key().decode("utf-8")
