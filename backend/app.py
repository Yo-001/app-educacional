"""Backend de geração de exercícios (Cloud Run, stdlib pura — zero dependências).

POST /generate {"text": "...", "topics": "..."} -> {"ejercicios": [...]}
GET  /health -> {"ok": true}

O que faz: recebe o texto do livro/cuaderno (OCR das fotos feitas no app) e
as matérias do exame (digitado pelos pais), chama um modelo pago no
OpenRouter com prompt de professora de 3.º Primaria (castellano) e devolve
16 exercícios validados no formato exato do app (mc/vf/ordenar/parejas).

Segurança: a chave do OpenRouter vive SÓ aqui (variável de ambiente da
Cloud Run). Rate limit por IP, corpo máximo 200 KB, CORS restrito ao GitHub
Pages do app. O front faz fallback offline (extractExercises) se isto cair.
"""
import json
import os
import re
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MODEL = "openai/gpt-4o-mini"
API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
MAX_BODY = 200_000
RATE_LIMIT = 30  # por hora por IP
WINDOW = 3600
_hits = {}

SYSTEM = """Eres una profesora de 3.º de Primaria en Galicia (España). Generas ejercicios de refuerzo en español (castellano) para una niña de 8 años, a partir del texto del libro y el cuaderno que te paso y de las materias del examen indicadas.

Reglas:
- Genera 16 ejercicios que cubran los temas. Sin repetir preguntas.
- Mezcla los tipos:
  1) Opción múltiple: {"q":"...","a":"...","opts":["...","...","...","..."]} — «a» debe ser EXACTAMENTE una de las opts; los otros tres distractores plausibles y de la misma categoría (nada absurdo ni gracioso).
  2) Verdadero/falso: {"q":"Lee: «...» ¿Verdadero o falso?","tipo":"vf","a":"Verdadero","opts":["Verdadero","Falso"]}
  3) Ordenar: {"q":"Toca las etapas ..., en orden:","tipo":"ordenar","pasos":["paso 1","paso 2","paso 3"],"a":"paso 1 → paso 2 → paso 3"}
  4) Parejas: {"q":"Toca parejas: une cada ... con su ...:","tipo":"parejas","pares":[["término","definición"],["término","definición"],["término","definición"]],"a":"resumen corto"}
- Frases cortas y vocabulario de 8 años. 100% español. Nada de preguntas tontas.
- Responde SOLO con JSON válido: {"ejercicios":[...16 objetos...]} sin texto adicional."""


def clean_str(s, n=4000):
    return re.sub(r"\s+", " ", (s or "")).strip()[:n]


def validate(items):
    """Valida cada exercício no schema exato do app; descarta inválidos."""
    out = []
    for it in items or []:
        if not isinstance(it, dict):
            continue
        q = clean_str(it.get("q"), 300)
        if not q:
            continue
        tipo = it.get("tipo")
        if tipo == "vf":
            out.append({"q": q, "tipo": "vf",
                        "a": "Verdadero" if it.get("a") == "Verdadero" else "Falso",
                        "opts": ["Verdadero", "Falso"]})
        elif tipo == "ordenar":
            pasos = [clean_str(p, 120) for p in (it.get("pasos") or [])]
            pasos = [p for p in pasos if p]
            if 3 <= len(pasos) <= 5 and len(set(pasos)) == len(pasos):
                out.append({"q": q, "tipo": "ordenar", "pasos": pasos,
                            "a": " → ".join(pasos)})
        elif tipo == "parejas":
            pares = []
            for p in (it.get("pares") or []):
                if isinstance(p, (list, tuple)) and len(p) == 2:
                    a, b = clean_str(p[0], 80), clean_str(p[1], 80)
                    if a and b:
                        pares.append([a, b])
            if 3 <= len(pares) <= 5:
                out.append({"q": q, "tipo": "parejas", "pares": pares,
                            "a": "-".join(p[0] for p in pares)})
        else:
            opts = [clean_str(o, 120) for o in (it.get("opts") or [])]
            opts = [o for o in opts if o]
            opts = list(dict.fromkeys(opts))
            a = clean_str(it.get("a"), 120)
            if a and len(opts) == 4 and a in opts:
                out.append({"q": q, "a": a, "opts": opts})
    return out


def parse_payload(body):
    """Extrai ejercicios do JSON do modelo ({ejercicios:[...]} ou array puro)."""
    try:
        d = json.loads(body)
    except Exception:
        return None
    if isinstance(d, dict):
        v = d.get("ejercicios")
        return v if isinstance(v, list) else None
    if isinstance(d, list):
        return d
    return None


def call_model(text, topics):
    user = ("Materias/temas del examen:\n" + (topics or "sin especificar") +
            "\n\nTexto del libro/cuaderno (OCR, puede tener errores):\n" + text[:6000])
    payload = json.dumps({
        "model": MODEL,
        "response_format": {"type": "json_object"},
        "temperature": 0.6,
        "max_tokens": 4000,
        "messages": [{"role": "system", "content": SYSTEM},
                     {"role": "user", "content": user}],
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions", data=payload,
        headers={"Content-Type": "application/json",
                 "Authorization": "Bearer " + API_KEY,
                 "HTTP-Referer": "https://yo-001.github.io/estudo-moedas/",
                 "X-Title": "estudo-exams"})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = json.loads(r.read().decode("utf-8", "ignore"))
    content = data["choices"][0]["message"]["content"]
    return parse_payload(content) or []


class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "https://yo-001.github.io")
        self.send_header("Access-Control-Allow-Methods", "POST,GET,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        if self.path == "/health":
            self._json(200, {"ok": True})
        else:
            self._json(404, {"error": "no encontrado"})

    def do_POST(self):
        if self.path != "/generate":
            return self._json(404, {"error": "no encontrado"})
        ip = self.headers.get("X-Forwarded-For", "desconocido").split(",")[-1].strip()
        now = time.time()
        hist = [t for t in _hits.get(ip, []) if now - t < WINDOW]
        if len(hist) >= RATE_LIMIT:
            return self._json(429, {"error": "demasiadas peticiones, prueba en unos minutos"})
        try:
            n = int(self.headers.get("Content-Length", "0"))
        except Exception:
            n = 0
        if n <= 0 or n > MAX_BODY:
            return self._json(400, {"error": "cuerpo inválido o demasiado grande"})
        raw = self.rfile.read(n)
        try:
            reqj = json.loads(raw.decode("utf-8", "ignore"))
        except Exception:
            return self._json(400, {"error": "JSON inválido"})
        text = clean_str(reqj.get("text", ""), 12000)
        if len(text) < 80:
            return self._json(400, {"error": "Texto muy corto: sube fotos del libro/cuaderno o escribe el contenido."})
        if not API_KEY:
            return self._json(503, {"error": "generador no configurado"})
        _hits[ip] = hist + [now]
        try:
            items = call_model(text, clean_str(reqj.get("topics", ""), 2000))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "ignore")[:300]
            return self._json(502, {"error": "OpenRouter " + str(e.code), "detalle": body})
        except Exception as e:
            return self._json(502, {"error": "fallo del generador: " + type(e).__name__})
        valid = validate(items)
        if not valid:
            return self._json(502, {"error": "sin ejercicios válidos"})
        self._json(200, {"ejercicios": valid})


def main():
    port = int(os.environ.get("PORT", "8080"))
    ThreadingHTTPServer(("0.0.0.0", port), H).serve_forever()


if __name__ == "__main__":
    main()
