"""Unit tests for AI Security and Secret Privacy."""

import unittest
from core.zetta.ai.providers import OpenAIProvider
from core.zetta.utils.errors import AuthenticationError


class TestAISecurity(unittest.TestCase):

    def test_api_key_not_exposed_in_string_or_exception(self):
        secret_key = "sk-proj-super-secret-key-12345"
        provider = OpenAIProvider(api_key=secret_key, base_url="http://invalid.localhost:9999")

        try:
            provider.generate(request=None)  # Will fail
        except Exception as e:
            err_str = str(e)
            self.assertNotIn(secret_key, err_str)

    def test_provider_repr_does_not_leak_key(self):
        secret_key = "sk-proj-super-secret-key-99999"
        provider = OpenAIProvider(api_key=secret_key)
        self.assertNotIn(secret_key, repr(provider))
        self.assertNotIn(secret_key, str(provider))


if __name__ == "__main__":
    unittest.main()
