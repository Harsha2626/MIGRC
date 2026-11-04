"""Symmetric encryption for secrets stored in the database (OAuth tokens, connector credentials).

Uses Fernet (AES-128-CBC + HMAC). Key source, in order:
  1. ENCRYPTION_KEY env var (a urlsafe-base64 32-byte Fernet key) - recommended in production.
  2. Derived from SECRET_KEY (so existing deployments work without new config; rotating
     SECRET_KEY then makes stored secrets undecryptable - set ENCRYPTION_KEY to avoid that).

Stored format is prefixed 'enc:v1:' so legacy plaintext values are recognised and can be
migrated lazily: decrypt() returns legacy plaintext unchanged.
"""
import base64
import hashlib
import os

from cryptography.fernet import Fernet, InvalidToken

PREFIX = 'enc:v1:'


def _fernet():
    key = os.environ.get('ENCRYPTION_KEY')
    if not key:
        secret = os.environ.get('SECRET_KEY') or 'migrc-dev-secret-key-change-in-production'
        key = base64.urlsafe_b64encode(hashlib.sha256(b'migrc-enc-v1:' + secret.encode()).digest()).decode()
    return Fernet(key.encode() if isinstance(key, str) else key)


def is_encrypted(value):
    return isinstance(value, str) and value.startswith(PREFIX)


def encrypt(plaintext):
    """Encrypt a string; None/'' pass through unchanged. Idempotent for already-encrypted values."""
    if plaintext is None or plaintext == '':
        return plaintext
    if is_encrypted(plaintext):
        return plaintext
    return PREFIX + _fernet().encrypt(plaintext.encode()).decode()


def decrypt(value):
    """Decrypt a stored value. Legacy plaintext (no prefix) is returned as-is. Raises ValueError
    if an encrypted value cannot be decrypted (wrong key)."""
    if value is None or value == '' or not is_encrypted(value):
        return value
    try:
        return _fernet().decrypt(value[len(PREFIX):].encode()).decode()
    except InvalidToken as e:
        raise ValueError('cannot decrypt stored secret (wrong ENCRYPTION_KEY/SECRET_KEY?)') from e
