import json
import os
import sys
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))
import app  # noqa: E402


def _sample_lesson():
    return {
        "title": "Repaso con Mía",
        "summary": "Repasamos as plantas con calma.",
        "scenes": [
            {
                "kind": "intro",
                "badge": "Naturais",
                "title": "Ola, Maitê!",
                "narration": "¡Hola, Maitê! ✨ Hoxe imos repasar as partes da planta. 🌸",
                "points": ["Raíz", "Talo", "Folla", "Froito"],
                "wrong": "",
                "right": "",
                "tip": "Imos paso a paso.",
            },
            {
                "kind": "explain",
                "badge": "Naturais",
                "title": "A raíz",
                "narration": "A raíz suxeita a planta e absorbe auga da terra. 💧",
                "points": ["Baixo a terra", "Absorbe auga"],
                "wrong": "Folla",
                "right": "Raíz",
                "tip": "Pensa nos pés da árbore.",
            },
            {
                "kind": "outro",
                "badge": "Ánimo",
                "title": "Moi ben feito!",
                "narration": "Xenial, Maitê! Xa o sabes perfectamente.",
                "points": ["Segue así"],
                "wrong": "",
                "right": "",
                "tip": "A por outra!",
            },
        ],
    }


class ValidateLessonTests(unittest.TestCase):
    def test_accepts_valid_and_strips_emojis_and_caps_points(self):
        res = app.validate_lesson(_sample_lesson())
        self.assertIsNotNone(res)
        self.assertEqual(res["lessonVer"], 2)
        self.assertEqual(res["title"], "Repaso con Mía")
        self.assertEqual(len(res["scenes"]), 3)
        intro = res["scenes"][0]
        self.assertNotIn("✨", intro["narration"])
        self.assertNotIn("🌸", intro["narration"])
        self.assertEqual(intro["points"], ["Raíz", "Talo"])
        self.assertNotIn("💧", res["scenes"][1]["narration"])

    def test_accepts_wrapped_lesson_and_defaults(self):
        wrapped = {
            "lesson": {
                "scenes": [
                    {"kind": "unknown", "title": "Escena 1", "narration": "Primeira frase."},
                    {"kind": "outro", "title": "Escena 2", "narration": "Segunda frase."},
                ]
            }
        }
        res = app.validate_lesson(wrapped)
        self.assertIsNotNone(res)
        self.assertEqual(res["title"], "Vídeo de Mía")
        self.assertEqual(res["scenes"][0]["kind"], "explain")

    def test_rejects_fewer_than_two_scenes_or_empty(self):
        self.assertIsNone(app.validate_lesson({}))
        self.assertIsNone(app.validate_lesson(None))
        self.assertIsNone(app.validate_lesson({"scenes": []}))
        self.assertIsNone(
            app.validate_lesson({
                "scenes": [
                    {"kind": "intro", "title": "Única", "narration": "Só unha escena."}
                ]
            })
        )

    def test_quiz_omitted_or_invalid_defaults_to_empty_without_invalidating_scenes(self):
        lesson = _sample_lesson()
        res = app.validate_lesson(lesson)
        self.assertIsNotNone(res)
        self.assertEqual(res["quiz"], [])

        lesson_bad_type = dict(_sample_lesson(), quiz="non-lista")
        res2 = app.validate_lesson(lesson_bad_type)
        self.assertIsNotNone(res2)
        self.assertEqual(len(res2["scenes"]), 3)
        self.assertEqual(res2["quiz"], [])

    def test_quiz_valid_dedupes_opts_and_discards_answer_not_in_opts(self):
        lesson = dict(
            _sample_lesson(),
            quiz=[
                {
                    "q": "¿Que parte absorbe a auga da terra?",
                    "a": "Raíz",
                    "opts": ["Folla", "Raíz", "Talo", "Raíz"],
                },
                {
                    "q": "Pregunta con resposta fóra das opcións",
                    "a": "Flor",
                    "opts": ["Raíz", "Talo", "Folla"],
                },
                {
                    "q": "Con menos de 2 opcións únicas",
                    "a": "Raíz",
                    "opts": ["Raíz", "Raíz"],
                },
                "non-dict",
            ],
        )
        res = app.validate_lesson(lesson)
        self.assertIsNotNone(res)
        self.assertEqual(len(res["quiz"]), 1)
        self.assertEqual(
            res["quiz"][0],
            {
                "q": "¿Que parte absorbe a auga da terra?",
                "a": "Raíz",
                "opts": ["Folla", "Raíz", "Talo"],
            },
        )

    def test_quiz_caps_at_three_questions(self):
        items = [
            {"q": f"Pregunta {i}", "a": "Si", "opts": ["Si", "Non", "Quizais"]}
            for i in range(5)
        ]
        res = app.validate_lesson(dict(_sample_lesson(), quiz=items))
        self.assertIsNotNone(res)
        self.assertEqual(len(res["quiz"]), 3)
        self.assertEqual([x["q"] for x in res["quiz"]], ["Pregunta 0", "Pregunta 1", "Pregunta 2"])

    def test_visual_normalization_preserves_valid_and_caps_items(self):
        lesson = {
            "title": "As plantas",
            "scenes": [
                {
                    "kind": "explain",
                    "title": "Partes",
                    "narration": "Cada parte ten a súa función.",
                    "visual": {
                        "type": "diagram",
                        "theme": "plants",
                        "icon": "🌿",
                        "items": [
                            {"emoji": "🌱", "label": "Raíz", "role": "step"},
                            {"emoji": "🪵", "label": "Talo", "role": "good"},
                            {"emoji": "", "label": "", "role": "bad"},
                            "non-dict",
                            {"emoji": "🍃", "label": "Folla", "role": "invalid-role"},
                            {"emoji": "🍎", "label": "Froito", "role": "accent"},
                        ],
                        "formula": "36 + 17 = 53",
                        "highlight": "Nas follas",
                    },
                },
                {
                    "kind": "outro",
                    "title": "Moi ben!",
                    "narration": "Fixéchelo xenial!",
                    "visual": {"type": "celebrate", "theme": "math", "highlight": "Mini-Quiz!"},
                },
            ],
        }
        res = app.validate_lesson(lesson)
        self.assertIsNotNone(res)
        self.assertEqual(res["lessonVer"], 2)
        vis = res["scenes"][0]["visual"]
        self.assertEqual(vis["type"], "diagram")
        self.assertEqual(vis["theme"], "plants")
        self.assertEqual(vis["icon"], "🌿")
        self.assertEqual(vis["formula"], "36 + 17 = 53")
        self.assertEqual(vis["highlight"], "Nas follas")
        self.assertEqual(
            vis["items"],
            [
                {"emoji": "🌱", "label": "Raíz", "role": "step"},
                {"emoji": "🪵", "label": "Talo", "role": "good"},
                {"emoji": "🍃", "label": "Folla", "role": "step"},
            ],
        )

    def test_visual_defaults_when_omitted_or_invalid(self):
        lesson = {
            "scenes": [
                {"kind": "intro", "title": "Ola", "narration": "Benvida."},
                {
                    "kind": "explain",
                    "title": "Comparar",
                    "narration": "Ollo co erro.",
                    "wrong": "Folla",
                    "right": "Raíz",
                    "visual": {"type": "bogus", "theme": "unknown"},
                },
                {"kind": "explain", "title": "Paso a paso", "narration": "Así se fai."},
                {"kind": "outro", "title": "Fin", "narration": "Ata logo."},
            ]
        }
        res = app.validate_lesson(lesson)
        self.assertIsNotNone(res)
        self.assertEqual(res["lessonVer"], 2)
        self.assertEqual(res["scenes"][0]["visual"]["type"], "hero")
        self.assertEqual(res["scenes"][0]["visual"]["theme"], "stars")
        self.assertEqual(res["scenes"][1]["visual"]["type"], "compare")
        self.assertEqual(res["scenes"][1]["visual"]["theme"], "stars")
        self.assertEqual(res["scenes"][2]["visual"]["type"], "flow")
        self.assertEqual(res["scenes"][3]["visual"]["type"], "celebrate")


class ExplainEndpointTests(unittest.TestCase):
    def setUp(self):
        self._orig_key = app.API_KEY
        self._orig_call = app.call_explain
        app.API_KEY = "test-key"
        app._hits.clear()

        def fake_call_explain(name, errors):
            return app.validate_lesson(_sample_lesson())

        app.call_explain = fake_call_explain
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), app.H)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        app.API_KEY = self._orig_key
        app.call_explain = self._orig_call
        app._hits.clear()

    def _post_explain(self, payload, ip="10.0.0.1"):
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}/explain",
            data=data,
            headers={
                "Content-Type": "application/json",
                "X-Forwarded-For": ip,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            with e:
                return e.code, json.loads(e.read().decode("utf-8"))

    def test_empty_errors_returns_400(self):
        status, body = self._post_explain({"name": "Maitê", "errors": []}, ip="10.0.0.2")
        self.assertEqual(status, 400)
        self.assertIn("error", body)

    def test_valid_error_returns_200_with_lesson(self):
        payload = {
            "name": "Maitê",
            "errors": [
                {
                    "subjNm": "Naturais",
                    "tema": "As plantas",
                    "q": "¿Que parte absorbe auga?",
                    "expected": "Raíz",
                    "given": "Folla",
                }
            ],
        }
        status, body = self._post_explain(payload, ip="10.0.0.3")
        self.assertEqual(status, 200)
        self.assertIn("lesson", body)
        self.assertGreaterEqual(len(body["lesson"]["scenes"]), 2)
        self.assertEqual(body["lesson"]["quiz"], [])

    def test_rate_limit_30_ok_31_returns_429(self):
        payload = {
            "name": "Maitê",
            "errors": [{"q": "Pregunta", "expected": "Resposta", "given": "Outra"}],
        }
        for i in range(30):
            status, _ = self._post_explain(payload, ip="10.0.0.99")
            self.assertEqual(status, 200, f"request {i + 1} failed")
        status, body = self._post_explain(payload, ip="10.0.0.99")
        self.assertEqual(status, 429)
        self.assertIn("error", body)


if __name__ == "__main__":
    unittest.main(verbosity=2)
