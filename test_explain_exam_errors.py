import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))
import app  # noqa: E402


class ExplainExamErrorsTests(unittest.TestCase):
    def test_exam_ingles_includes_marker_and_instructions(self):
        prompt = app._explain_user_prompt([
            {
                "subj": "ingles",
                "subjNm": "Inglés",
                "tema": "ingles",
                "q": "I ___ happy.",
                "given": "is",
                "expected": "am",
                "exam": True,
            }
        ])
        self.assertIn("[EXAMEN]", prompt)
        self.assertIn("IMPORTANTE", prompt)
        self.assertIn("inglés", prompt)

    def test_non_exam_excludes_examen_marker(self):
        prompt = app._explain_user_prompt([
            {
                "subj": "mat",
                "subjNm": "Matemáticas",
                "tema": "Sumas",
                "q": "2 + 2",
                "given": "5",
                "expected": "4",
                "exam": False,
            }
        ])
        self.assertNotIn("[EXAMEN]", prompt)
        self.assertNotIn("IMPORTANTE", prompt)
        self.assertNotIn("inglés", prompt)


if __name__ == "__main__":
    unittest.main(verbosity=2)
