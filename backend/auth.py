"""
CyberForge - Password Security Module
======================================
Implements secure cryptographic password hashing using:
  - PBKDF2-HMAC with SHA-256 (NIST SP 800-132 compliant)
  - Cryptographically secure random 256-bit salt (os.urandom)
  - 260,000 iterations (OWASP 2023 recommendation for PBKDF2-SHA256)
  - No external library dependency — uses Python's built-in hashlib + secrets

WHY NOT PLAIN SHA-256?
  - Plain SHA256 can hash billions of guesses/second on a GPU.
  - PBKDF2 with 260,000 iterations forces an attacker to spend 260,000x
    more computing time per guess, making brute-force impractical.

WHY RANDOM SALT?
  - Two users with the same password produce completely different hashes.
  - Defeats rainbow table attacks (precomputed hash lookups).
"""

import hashlib
import os
import hmac


ITERATIONS = 260_000        # OWASP 2023 recommended for PBKDF2-SHA256
SALT_BYTES = 32             # 256-bit random cryptographic salt
HASH_ALGORITHM = "sha256"


def hash_password(plain_password: str) -> str:
    """
    Hash a plaintext password using PBKDF2-HMAC-SHA256.

    Process:
      1. Generate a 256-bit cryptographically random salt.
      2. Apply PBKDF2 with SHA-256 and 260,000 iterations.
      3. Return 'iterations$salt_hex$hash_hex' — safe to store in DB.

    Example output:
      '260000$3a9f...b12c$7d4e...a1f0'
    """
    salt = os.urandom(SALT_BYTES)
    key = hashlib.pbkdf2_hmac(
        HASH_ALGORITHM,
        plain_password.encode("utf-8"),
        salt,
        ITERATIONS
    )
    return f"{ITERATIONS}${salt.hex()}${key.hex()}"


def verify_password(plain_password: str, stored_hash: str) -> bool:
    """
    Verify a plaintext password against a stored PBKDF2 hash.

    Process:
      1. Extract the original salt from the stored hash string.
      2. Re-hash the provided password with the same salt & iterations.
      3. Compare using constant-time hmac.compare_digest (prevents timing attacks).
    """
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
