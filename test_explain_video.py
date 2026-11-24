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
        self.assertEqual(res["lessonVer"], 3)
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
                            123,
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
        self.assertEqual(res["lessonVer"], 3)
        vis = res["scenes"][0]["visual"]
        self.assertEqual(vis["type"], "diagram")
        self.assertEqual(vis["theme"], "plants")
        self.assertEqual(vis["icon"], "🌿")
        self.assertEqual(vis["formula"], "36 + 17 = 53")
        self.assertEqual(vis["highlight"], "Nas follas")
        expected_beats = [
            {"emoji": "🌱", "label": "Raíz", "role": "step"},
            {"emoji": "🪵", "label": "Talo", "role": "good"},
            {"emoji": "🍃", "label": "Folla", "role": "step"},
        ]
        self.assertEqual(vis["beats"], expected_beats)
        self.assertEqual(vis["items"], expected_beats)

    def test_visual_defaults_when_omitted_or_invalid(self):
        lesson = {
            "scenes": [
                {"kind": "intro", "title": "Ola", "narration": "Benvida."},
                {
                    "kind": "apply",
                    "title": "Comparar",
                    "narration": "Ollo co erro.",
                    "wrong": "Folla",
                    "right": "Raíz",
                    "visual": {"type": "bogus", "theme": "unknown"},
                },
                {"kind": "analogy", "title": "Como unha palliña", "narration": "Así se fai."},
                {"kind": "outro", "title": "Fin", "narration": "Ata logo."},
            ]
        }
        res = app.validate_lesson(lesson)
        self.assertIsNotNone(res)
        self.assertEqual(res["lessonVer"], 3)
        self.assertEqual(res["scenes"][0]["visual"]["type"], "story")
        self.assertEqual(res["scenes"][0]["visual"]["theme"], "stars")
        self.assertEqual(res["scenes"][1]["kind"], "apply")
        self.assertEqual(res["scenes"][1]["visual"]["type"], "compare")
        self.assertEqual(res["scenes"][1]["visual"]["theme"], "stars")
        self.assertEqual(res["scenes"][2]["kind"], "analogy")
        self.assertEqual(res["scenes"][2]["visual"]["type"], "story")
        self.assertEqual(res["scenes"][3]["visual"]["type"], "celebrate")

    def test_visual_beats_strings_dicts_and_legacy_type_mapping(self):
        long_narration = "A" * 330
        lesson = {
            "scenes": [
                {
                    "kind": "intro",
                    "title": "Ola!",
                    "narration": long_narration,
                    "visual": {"type": "hero", "theme": "plants"},
                },
                {
                    "kind": "analogy",
                    "title": "A cociña",
                    "narration": "As follas cociñan a comida.",
                    "visual": {
                        "type": "flow",
                        "theme": "plants",
                        "highlight": "A" * 40,
                        "beats": [
                            "Raíz bebe auga",
                            {"emoji": "🍃", "label": "Folla cociña moitísimo texto extra", "role": "accent"},
                            "",
                            {"emoji": "☀️", "label": "Sol", "role": "bad-role"},
                            {"emoji": "💧", "label": "Extra", "role": "step"},
                        ],
                    },
                },
                {
                    "kind": "apply",
                    "title": "Na pregunta",
                    "narration": "Por iso a conta dá 53.",
                    "visual": {
                        "type": "equation",
                        "theme": "math",
                        "formula": "12345678901234567890123456789012345",
                    },
                },
            ]
        }
        res = app.validate_lesson(lesson)
        self.assertIsNotNone(res)
        self.assertEqual(res["lessonVer"], 3)
        self.assertEqual(len(res["scenes"][0]["narration"]), 330)
        self.assertEqual(res["scenes"][0]["visual"]["type"], "story")
        vis1 = res["scenes"][1]["visual"]
        self.assertEqual(vis1["type"], "story")
        self.assertEqual(len(vis1["highlight"]), 30)
        self.assertEqual(
            vis1["beats"],
            [
                {"emoji": "", "label": "Raíz bebe auga", "role": "step"},
                {"emoji": "🍃", "label": "Folla cociña moitísimo t", "role": "accent"},
                {"emoji": "☀️", "label": "Sol", "role": "step"},
            ],
        )
        vis2 = res["scenes"][2]["visual"]
        self.assertEqual(vis2["type"], "math_blocks")
        self.assertEqual(len(vis2["formula"]), 32)


class CallExplainFallbackTests(unittest.TestCase):
    def setUp(self):
        self._orig_urlopen = app.urllib.request.urlopen
        self._orig_key = app.API_KEY
        app.API_KEY = "test-key"

    def tearDown(self):
        app.urllib.request.urlopen = self._orig_urlopen
        app.API_KEY = self._orig_key

    def _fake_resp(self, payload_obj):
        raw = json.dumps({"choices": [{"message": {"content": json.dumps(payload_obj)}}]}).encode("utf-8")

        class _Resp:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                return raw

        return _Resp()

    def test_uses_explain_model_and_falls_back_to_model_on_invalid_or_error(self):
        calls = []

        def fake_urlopen_invalid(req, timeout=60):
            body = json.loads(req.data.decode("utf-8"))
            calls.append(body)
            if body["model"] == app.EXPLAIN_MODEL:
                return self._fake_resp({"scenes": []})
            return self._fake_resp(_sample_lesson())

        app.urllib.request.urlopen = fake_urlopen_invalid
        res = app.call_explain("Maitê", [{"q": "Q1", "expected": "A", "given": "B"}])
        self.assertIsNotNone(res)
        self.assertEqual(res["lessonVer"], 3)
        self.assertEqual([c["model"] for c in calls], [app.EXPLAIN_MODEL, app.MODEL])
        self.assertEqual(calls[0]["max_tokens"], 1800)
        self.assertEqual(calls[0]["temperature"], 0.65)
        self.assertEqual(calls[1]["max_tokens"], 1800)
        self.assertEqual(calls[1]["temperature"], 0.65)

        calls.clear()

        def fake_urlopen_error(req, timeout=60):
            body = json.loads(req.data.decode("utf-8"))
            calls.append(body)
            if body["model"] == app.EXPLAIN_MODEL:
                raise urllib.error.URLError("timeout")
            return self._fake_resp(_sample_lesson())

        app.urllib.request.urlopen = fake_urlopen_error
        res2 = app.call_explain("Maitê", [{"q": "Q1", "expected": "A", "given": "B"}])
        self.assertIsNotNone(res2)
        self.assertEqual([c["model"] for c in calls], [app.EXPLAIN_MODEL, app.MODEL])


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
