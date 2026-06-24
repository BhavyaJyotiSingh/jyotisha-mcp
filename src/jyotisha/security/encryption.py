"""
AES-256-GCM Encryption and Decryption Helpers

Protects birth data and PII at rest in the SQLite database.
If JYOTISHA_ENCRYPTION_KEY is not defined, a key is auto-generated
and stored in the db directory for persistence across restarts.
"""

from __future__ import annotations
import os
import base64
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

KEY_ENV_VAR = "JYOTISHA_ENCRYPTION_KEY"
_CACHED_KEY: bytes | None = None

def _get_encryption_key() -> bytes:
    """Retrieve or generate the 256-bit AES key."""
    global _CACHED_KEY
    if _CACHED_KEY is not None:
        return _CACHED_KEY

    # 1. Try environment variable
    key_str = os.getenv(KEY_ENV_VAR)
    if key_str:
        try:
            key = base64.b64decode(key_str)
            if len(key) == 32:
                _CACHED_KEY = key
                return key
        except Exception:
            pass

    # 2. Try persisting to local file in db/ directory
    base_dir = Path(__file__).parent.parent.parent.parent
    key_file = base_dir / "db" / "secret.key"
    key_file.parent.mkdir(parents=True, exist_ok=True)

    if key_file.exists():
        try:
            key = key_file.read_bytes()
            if len(key) == 32:
                _CACHED_KEY = key
                return key
        except Exception:
            pass

    # 3. Generate a new key and persist
    new_key = AESGCM.generate_key(bit_length=256)
    try:
        key_file.write_bytes(new_key)
    except Exception:
        # Fallback to memory-only if writing fails
        pass
        
    _CACHED_KEY = new_key
    return new_key

def encrypt_data(plaintext: str) -> str:
    """
    Encrypt plaintext string using AES-256-GCM.
    Returns a URL-safe base64 string combining nonce and ciphertext.
    """
    if not plaintext:
        return ""
        
    key = _get_encryption_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)  # GCM standard 12-byte nonce
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    
    # Combine nonce + ciphertext
    combined = nonce + ciphertext
    return base64.urlsafe_b64encode(combined).decode("utf-8")

def decrypt_data(ciphertext_b64: str) -> str:
    """
    Decrypt base64 ciphertext using AES-256-GCM.
    Returns the original plaintext string.
    """
    if not ciphertext_b64:
        return ""
        
    try:
        key = _get_encryption_key()
        aesgcm = AESGCM(key)
        combined = base64.urlsafe_b64decode(ciphertext_b64.encode("utf-8"))
        
        if len(combined) < 12:
            raise ValueError("Invalid ciphertext length.")
            
        nonce = combined[:12]
        ciphertext = combined[12:]
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext.decode("utf-8")
    except Exception as e:
        raise ValueError(f"Decryption failed: {e}")
