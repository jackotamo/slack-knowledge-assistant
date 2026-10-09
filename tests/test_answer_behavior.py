import json
import subprocess
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock
from assistant.config import PROJECT_ROOT
from assistant.generator import OpenAIGenerator
from assistant.loader import load_passages
from assistant.service import AssistantService


class AnswerTests(unittest.TestCase):
    def setUp(self):
        self.passages = load_passages(PROJECT_ROOT / "data/sops")
        self.generator = Mock()
        self.service = AssistantService(self.passages, self.generator)

    def test_no_evidence_never_calls_generator(self):
        answer = self.service.answer_question("cafeteria menu")
        self.assertTrue(answer.abstained)
        self.generator.generate.assert_not_called()

    def test_valid_citation_is_rendered_and_resolved(self):
        self.generator.generate.return_value = {
            "insufficient_evidence": False, "reason": "",
            "claims": [{"text": "Open the fictional account portal.", "source_ids": ["S1"]}]}
        answer = self.service.answer_question("reset forgotten password")
        self.assertFalse(answer.abstained)
        self.assertIn("[S1]", answer.text)
        self.assertEqual(answer.sources[0].passage.section, "Reset a forgotten password")

    def test_invalid_or_missing_citations_abstain(self):
        for ids in (["S99"], [], "S1", [None]):
            self.generator.generate.return_value = {
                "insufficient_evidence": False,
                "claims": [{"text": "An answer", "source_ids": ids}]}
            with self.subTest(ids=ids):
                self.assertTrue(self.service.answer_question("reset password").abstained)

    def test_insufficient_and_malformed_answers_abstain(self):
        for payload in ({"insufficient_evidence": True, "claims": []},
                        {}, [], {"insufficient_evidence": False, "claims": []}):
            self.generator.generate.return_value = payload
            self.assertTrue(self.service.answer_question("reset password").abstained)

    def test_responses_api_with_fake_client(self):
        client = Mock()
        client.responses.create.return_value = SimpleNamespace(output_text=json.dumps({
            "insufficient_evidence": True, "reason": "Not documented", "claims": []}))
        generator = OpenAIGenerator(None, "test-model", client=client)
        self.assertTrue(AssistantService(self.passages, generator).answer_question("reset password").abstained)
        request = client.responses.create.call_args.kwargs
        self.assertEqual(request["model"], "test-model")
        self.assertFalse(request["store"])
        self.assertEqual(request["text"]["format"]["type"], "json_schema")
        self.assertIn("S1", request["input"])

    def test_invalid_json_abstains(self):
        client = Mock()
        client.responses.create.return_value = SimpleNamespace(output_text="not JSON")
        service = AssistantService(self.passages, OpenAIGenerator(None, "test", client))
        self.assertTrue(service.answer_question("reset password").abstained)

    def test_missing_key_error(self):
        with self.assertRaisesRegex(ValueError, "OPENAI_API_KEY"):
            OpenAIGenerator(None, "test").generate("question", [])

    def test_search_only_cli_without_dependencies(self):
        # -S disables site packages: proves offline search needs no installed SDK.
        result = subprocess.run([sys.executable, "-S", "main.py", "--search-only",
                                 "reset forgotten password"], cwd=PROJECT_ROOT,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Reset a forgotten password", result.stdout)
        self.assertIn("lines", result.stdout)


if __name__ == "__main__":
    unittest.main()
