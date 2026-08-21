import base64
import hashlib
from cryptography.fernet import Fernet
from app.core.config import settings

# Derive a 32-byte url-safe base64 key from JWT_SECRET or ENCRYPTION_KEY
def get_encryption_key() -> bytes:
    if settings.ENCRYPTION_KEY:
        try:
            # Check if it is already a valid Fernet key
            key_bytes = settings.ENCRYPTION_KEY.encode()
            Fernet(key_bytes)
            return key_bytes
        except Exception:
            pass
    
    # Otherwise, derive key using SHA256 of the JWT_SECRET
    secret_bytes = settings.JWT_SECRET.encode()
    hasher = hashlib.sha256()
    hasher.update(secret_bytes)
    key_32 = hasher.digest()
    return base64.urlsafe_b64encode(key_32)


_fernet = Fernet(get_encryption_key())


def encrypt_token(token: str) -> str:
    """Encrypt a plaintext token using Fernet symmetric encryption."""
    if not token:
        return ""
    return _fernet.encrypt(token.encode()).decode()


def decrypt_token(encrypted_token: str) -> str:
    """Decrypt an encrypted token back to plaintext."""
    if not encrypted_token:
        return ""
    try:
        return _fernet.decrypt(encrypted_token.encode()).decode()
    except Exception as e:
        # For testing / fallback or debugging
        raise ValueError("Failed to decrypt token. Key may have changed or token is invalid.") from e
