"""
encryption_service.py
──────────────────────
Paper: "All candidate data is encrypted in transit and at rest,
        with access controls limiting exposure."

Encryption Strategy:
    At Rest   → Fernet symmetric encryption (AES-128-CBC)
    In Transit → HTTPS/TLS (ProductionConfig enforces this)
    Passwords  → werkzeug bcrypt hash (User model)
    Files      → UUID filename + deleted after parse
"""

import os
from cryptography.fernet import Fernet, InvalidToken


def _get_fernet() -> Fernet:
    key = os.getenv("ENCRYPTION_KEY")
    if not key:
        raise EnvironmentError(
            "ENCRYPTION_KEY not set in environment. "
            "Generate: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
    try:
        return Fernet(key.encode())
    except Exception:
        raise ValueError("Invalid ENCRYPTION_KEY — must be a valid Fernet key.")


def encrypt(plain_text: str) -> str:
    if not plain_text:
        return ""
    try:
        fernet    = _get_fernet()
        encrypted = fernet.encrypt(plain_text.encode("utf-8"))
        return encrypted.decode("utf-8")
    except Exception as e:
        raise RuntimeError(f"Encryption failed: {e}")


def decrypt(encrypted_text: str) -> str:
    if not encrypted_text:
        return ""
    try:
        fernet    = _get_fernet()
        decrypted = fernet.decrypt(encrypted_text.encode("utf-8"))
        return decrypted.decode("utf-8")
    except InvalidToken:
        raise ValueError("Decryption failed — data may be tampered or key is incorrect.")
    except Exception as e:
        raise RuntimeError(f"Decryption failed: {e}")


def encrypt_if_not_empty(value: str) -> str:
    if not value or not value.strip():
        return value
    return encrypt(value)


def decrypt_if_not_empty(value: str) -> str:
    if not value or not value.strip():
        return value
    try:
        return decrypt(value)
    except Exception:
        return value


def generate_new_key() -> str:
    return Fernet.generate_key().decode("utf-8")


# ══════════════════════════════════════════════════════════════════════════════
#  BLIND INDEX (deterministic hash for encrypted-column lookups)
# ══════════════════════════════════════════════════════════════════════════════
#
# Fernet encryption is intentionally non-deterministic (random IV per call),
# so the same plaintext produces different ciphertext every time. That's
# correct for confidentiality, but it means you CANNOT:
#   - query WHERE email = <ciphertext>  (never matches on next login)
#   - enforce UNIQUE on the encrypted column (duplicates go undetected)
#
# Fix: alongside the encrypted value, store a deterministic HMAC-SHA256 hash
# ("blind index") of the normalized plaintext. Same email -> same hash, every
# time -> safe to index, safe to use in WHERE/UNIQUE. The hash reveals nothing
# about the plaintext (can't be reversed) but lets you look records up.
#
# Uses a SEPARATE key from the Fernet key (ENCRYPTION_KEY), so compromising
# one doesn't compromise the other. Set HMAC_INDEX_KEY in .env:
#   python -c "import secrets; print(secrets.token_hex(32))"

import hashlib
import hmac


def _get_hmac_key() -> bytes:
    key = os.getenv("HMAC_INDEX_KEY")
    if not key:
        raise EnvironmentError(
            "HMAC_INDEX_KEY not set in environment. "
            "Generate: python -c \"import secrets; print(secrets.token_hex(32))\""
        )
    return key.encode("utf-8")


def blind_index(value: str) -> str:
    """
    Deterministic, non-reversible hash of a normalized value.
    Use for lookups/uniqueness on encrypted columns (e.g. email).
    Always normalize (lowercase + strip) before hashing so
    'User@Mail.com' and 'user@mail.com' resolve to the same index.
    """
    if not value:
        return ""
    normalized = value.strip().lower()
    digest = hmac.new(_get_hmac_key(), normalized.encode("utf-8"), hashlib.sha256)
    return digest.hexdigest()  # 64 hex chars, fixed length