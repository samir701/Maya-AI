"""ZETTA Structured Response Parser."""

import json
import re
from typing import Any, Dict, Type, TypeVar
from pydantic import BaseModel
from core.zetta.utils.errors import ValidationError

T = TypeVar("T", bound=BaseModel)


class ResponseParser:
    """Parses and validates plain text and JSON AI response payloads."""

    @staticmethod
    def extract_json_block(text: str) -> str:
        """Extract JSON text block if enclosed in ```json markdown fences."""
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return text.strip()

    @classmethod
    def parse_json(cls, text: str) -> Dict[str, Any]:
        """Parse text response to JSON dictionary."""
        cleaned = cls.extract_json_block(text)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            raise ValidationError(f"Failed to parse AI response as valid JSON: {e}. Raw Text: '{text[:100]}...'")

    @classmethod
    def parse_structured(cls, text: str, schema_cls: Type[T]) -> T:
        """Parse and validate response text against a Pydantic model schema."""
        data_dict = cls.parse_json(text)
        try:
            return schema_cls.model_validate(data_dict)
        except Exception as e:
            raise ValidationError(f"AI response failed schema validation for {schema_cls.__name__}: {e}")
