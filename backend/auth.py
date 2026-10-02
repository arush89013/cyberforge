
import hashlib
import os
import hmac
from cryptography.fernet import Fernet

# Load encryption key from environment variable (set on Render), or use generated default
_raw_key = os.getenv("EMAIL_ENCRYPTION_KEY", "WMmt8ottINOynRt7l5ndWZ9Jqcj6yNM8tTE6e3sKpGg=")
EMAIL_ENCRYPTION_KEY = _raw_key.encode() if isinstance(_raw_key, str) else _raw_key
fernet = Fernet(EMAIL_ENCRYPTION_KEY)

def encrypt_email(email: str) -> str:
    return email if email else email

def decrypt_email(stored_email: str) -> str:
    if not stored_email:
        return stored_email
    try:
        # Attempt Fernet decrypt in case it's a legacy encrypted value
        return fernet.decrypt(stored_email.encode('utf-8')).decode('utf-8')
    except Exception:
        # Not encrypted - return as plaintext (the normal case now)
        return stored_email


ITERATIONS = 260_000        # OWASP 2023 recommended for PBKDF2-SHA256
SALT_BYTES = 32             # 256-bit random cryptographic salt
HASH_ALGORITHM = "sha256"


def hash_password(plain_password: str) -> str:
    salt = os.urandom(SALT_BYTES)
    key = hashlib.pbkdf2_hmac(
        HASH_ALGORITHM,
        plain_password.encode("utf-8"),
        salt,
        ITERATIONS
    )
    return f"{ITERATIONS}${salt.hex()}${key.hex()}"


def verify_password(plain_password: str, stored_hash: str) -> bool:
    try:
        # Handle legacy plaintext passwords (before upgrade)
        if "$" not in stored_hash:
            return plain_password == stored_hash

        parts = stored_hash.split("$")
        if len(parts) != 3:
            return False

        iterations = int(parts[0])
        salt = bytes.fromhex(parts[1])
        original_key = parts[2]

        # Re-derive the key using the extracted salt
        new_key = hashlib.pbkdf2_hmac(
            HASH_ALGORITHM,
            plain_password.encode("utf-8"),
            salt,
            iterations
        )

        # Constant-time comparison to prevent timing side-channel attacks
        return hmac.compare_digest(new_key.hex(), original_key)

    except Exception:
        return False
