"""Unit tests for PromptTemplate and PromptRegistry."""

import unittest
from core.zetta.ai.prompts import PromptRegistry, PromptTemplate
from core.zetta.utils.errors import ValidationError


class TestPrompts(unittest.TestCase):

    def test_prompt_template_formatting(self):
        tmpl = PromptTemplate(
            name="test_tmpl",
            template="Hello {name}, welcome to {place}!",
            version="1.0.0",
        )
        formatted = tmpl.format(name="Alice", place="ZETTA")
        self.assertEqual(formatted, "Hello Alice, welcome to ZETTA!")

    def test_prompt_template_missing_variable(self):
        tmpl = PromptTemplate(
            name="test_tmpl",
            template="Hello {name}, welcome to {place}!",
        )
        with self.assertRaises(ValidationError):
            tmpl.format(name="Alice")

    def test_prompt_registry(self):
        registry = PromptRegistry()
        tmpl = registry.get("system_default")
        self.assertIsNotNone(tmpl.system_prompt)


if __name__ == "__main__":
    unittest.main()
