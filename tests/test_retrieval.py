import unittest
from pathlib import Path
from assistant.config import PROJECT_ROOT
from assistant.loader import load_passages
from assistant.search import search


class RetrievalTests(unittest.TestCase):
    def setUp(self):
        self.passages = load_passages(PROJECT_ROOT / "data/sops")

    def test_three_documents_loaded(self):
        self.assertEqual(len({p.path for p in self.passages}), 3)

    def test_relevant_section_and_exact_line_range(self):
        result = search("How do I reset a forgotten password?", self.passages)[0]
        self.assertEqual(result.passage.section, "Reset a forgotten password")
        self.assertEqual(result.passage.title, "Fictional Password Reset SOP")
        p = result.passage
        lines = Path(p.path).read_text(encoding="utf-8").splitlines()
        self.assertEqual(p.text, "\n".join(lines[p.start_line - 1:p.end_line]))
        self.assertIn("Reset password", p.text)
        self.assertTrue(all("training material" not in r.passage.text
                            for r in search("reset forgotten password", self.passages)))

    def test_unrelated_and_stop_word_queries_return_nothing(self):
        for question in ("What is the cafeteria menu?", "how do I", "", "quantum astronomy"):
            with self.subTest(question=question):
                self.assertEqual(search(question, self.passages), [])

    def test_expected_topics_and_unique_ids(self):
        for question, title in (("employee onboarding", "Onboarding"),
                                ("report technology incident", "Incident")):
            results = search(question, self.passages)
            self.assertIn(title, results[0].passage.title)
            self.assertEqual(len({r.identifier for r in results}), len(results))

    def test_missing_folder_is_actionable(self):
        with self.assertRaisesRegex(ValueError, "does not exist"):
            load_passages(PROJECT_ROOT / "nonexistent-sops")


if __name__ == "__main__":
    unittest.main()
