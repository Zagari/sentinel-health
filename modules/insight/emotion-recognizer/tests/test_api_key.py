"""Unit test to verify the OpenAI API key is loaded and working."""

import os
import sys
import unittest

# Ensure the emotion-recognizer package is importable
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), os.pardir)
)

from analysis.summarizer import setup_openai_api, create_chat_completion, extract_message_content


class TestApiKey(unittest.TestCase):
    """Verify the OpenAI API key is configured and functional."""

    def test_api_key_is_loaded(self):
        """setup_openai_api() should succeed and populate openai.api_key."""
        import openai
        setup_openai_api()
        self.assertIsNotNone(openai.api_key, "API key was not loaded from .env")
        self.assertTrue(len(openai.api_key) > 0, "API key is empty")

    def test_api_key_works(self):
        """A minimal chat completion should return a non-empty response."""
        setup_openai_api()
        response = create_chat_completion("Reply with the single word: OK")
        self.assertIsNotNone(response, "API call returned None — check key or network")
        content = extract_message_content(response)
        self.assertIsInstance(content, str)
        self.assertTrue(len(content) > 0, "API returned an empty response")
        print(f"API response: {content}")


if __name__ == "__main__":
    unittest.main()
