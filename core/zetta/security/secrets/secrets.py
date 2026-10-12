"""ZETTA Secret Handling."""

import os
import re
from typing import Optional


class SecretManager:
    """Manages sensitive API credentials, keys, and secret masking securely."""

    def __init__(self) -> None:
        self._registered_secrets = set()

    def register_secret(self, secret: str) -> None:
        """Register a secret string to be masked in output logs."""
        if secret and len(secret) > 3:
            self._registered_secrets.add(secret)

    def get_secret(self, key: str) -> Optional[str]:
        """Retrieve secret from environment without exposing raw values in codebase."""
        val = os.getenv(key)
        if val:
            self.register_secret(val)
        return val

    def mask_secrets(self, text: str) -> str:
        """Mask known secrets, Bearer tokens, API keys, and sensitive values in text."""
        if not text:
            return ""

        masked = text
        for secret in self._registered_secrets:
            if secret in masked:
                masked = masked.replace(secret, "*****")

        # Regex patterns for standard API keys and tokens
        masked = re.sub(r"(sk-[a-zA-Z0-9_-]{20,})", "*****", masked)
        masked = re.sub(r"(Bearer\s+)[a-zA-Z0-9_.-]+", r"\1*****", masked)
        masked = re.sub(r"(password=)[^\s&]+", r"\1*****", masked, flags=re.IGNORECASE)
        return masked

