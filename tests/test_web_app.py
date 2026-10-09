"""Streamlit's local test harness exercises the chat without a browser/server."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from assistant.config import Config, PROJECT_ROOT
from assistant.documents import DocumentCollection


class WebTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.collection = DocumentCollection(Path(self.temporary.name))
        self.collection_patch = patch("assistant.documents.DocumentCollection", return_value=self.collection)
        self.config_patch = patch("assistant.config.load_config", return_value=Config(
            PROJECT_ROOT / "data/sops", None, "test-model"))
        self.collection_patch.start()
        self.config_patch.start()
        self.app = AppTest.from_file(str(PROJECT_ROOT / "web_app.py"), default_timeout=15)

    def tearDown(self):
        self.collection_patch.stop()
        self.config_patch.stop()
        self.temporary.cleanup()

    def test_search_chat_and_citations_without_key(self):
        self.app.run()
        self.assertFalse(self.app.exception)
        self.app.chat_input[0].set_value("reset forgotten password").run()
        self.assertFalse(self.app.exception)
        self.assertTrue(self.app.expander)
        self.assertTrue(any("[S1]" in element.value for element in self.app.text))

    def test_missing_key_is_clear(self):
        self.app.run()
        self.app.toggle[0].set_value(False).run()
        self.app.chat_input[0].set_value("reset password").run()
        self.assertFalse(self.app.exception)
        self.assertTrue(any("API key is missing" in element.value for element in self.app.error))

    def test_no_evidence_message(self):
        self.app.run()
        self.app.chat_input[0].set_value("cafeteria menu").run()
        self.assertTrue(any("No relevant evidence" in element.value for element in self.app.text))

    def test_uploaded_document_can_be_removed(self):
        self.collection.add("uploaded.md", b"# Local upload\nUnique procedure text")
        self.app.run()
        self.assertTrue(any("uploaded.md" == element.value for element in self.app.text))
        next(button for button in self.app.button if button.label == "Remove").click().run()
        self.assertFalse(self.app.exception)
        self.assertEqual(self.collection.list_documents(), [])

    def test_api_failure_does_not_expose_exception_or_key(self):
        self.config_patch.stop()
        with patch("assistant.config.load_config", return_value=Config(
                PROJECT_ROOT / "data/sops", "fake-private-key", "test")), \
                patch("assistant.generator.OpenAIGenerator") as generator:
            generator.return_value.generate.side_effect = RuntimeError("fake-private-key")
            self.app.run()
            self.app.toggle[0].set_value(False).run()
            self.app.chat_input[0].set_value("reset password").run()
            self.assertFalse(self.app.exception)
            self.assertTrue(any("Answer generation failed" in e.value for e in self.app.error))
            for element in [*self.app.text, *self.app.error, *self.app.warning]:
                self.assertNotIn("fake-private-key", element.value)


if __name__ == "__main__":
    unittest.main()
