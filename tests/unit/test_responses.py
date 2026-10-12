"""Unit tests for ResponseParser."""

import unittest
from pydantic import BaseModel
from core.zetta.ai.responses import ResponseParser
from core.zetta.utils.errors import ValidationError


class SampleResponseSchema(BaseModel):
    name: str
    count: int


class TestResponses(unittest.TestCase):

    def test_parse_json(self):
        text = '```json\n{"name": "Zetta", "count": 5}\n```'
        parsed = ResponseParser.parse_json(text)
        self.assertEqual(parsed["name"], "Zetta")
        self.assertEqual(parsed["count"], 5)

    def test_parse_structured(self):
        text = '{"name": "Zetta", "count": 10}'
        model = ResponseParser.parse_structured(text, SampleResponseSchema)
        self.assertEqual(model.name, "Zetta")
        self.assertEqual(model.count, 10)

    def test_malformed_json_raises_validation_error(self):
        text = "Invalid raw text without json"
        with self.assertRaises(ValidationError):
            ResponseParser.parse_json(text)


if __name__ == "__main__":
    unittest.main()
