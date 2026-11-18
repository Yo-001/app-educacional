"""Backend de geração de exercícios (Cloud Run, stdlib pura — zero dependências).

POST /generate {"text": "...", "topics": "..."} -> {"ejercicios": [...]}
POST /ocr      {"images": ["data:image/jpeg;base64,..."]} -> {"text": "..."}
POST /chat     {"text": "...", "name": "...", "messages": [...]} -> {"text": "..."}
GET  /health -> {"ok": true}

O que faz: /ocr transcribe as fotos do livro/cuaderno con un modelo de visión
no OpenRouter (fíase do Tesseract do navegador, que lía mal páxinas con
ilustracións). /generate recibe ese texto e as materias do exame (digitadas
polos pais), chama un modelo no OpenRouter con prompt de profesora de 3.º
Primaria (castellano) e devolve 16 exercícios validados no formato exato do
app (mc/vf/ordenar/parejas).

Segurança: a chave do OpenRouter vive SÓ aqui (variável de ambiente da
Cloud Run). Rate limit por IP, corpo máximo 200 KB (/generate; 8 MB en /ocr),
CORS restrito ao GitHub
Pages do app. O front faz fallback offline (extractExercises) se isto cair.
"""
import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MODEL = "openai/gpt-4o-mini"           # geração de exercícios, OCR principal e chat (barato: ~$0.15/1M in, $0.6/1M out)
OCR_MODEL = "google/gemini-2.5-flash"  # OCR de reserva: não recusa fotos com pessoas (o gpt-4o-mini recusa, mas traduz galego→português)
API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
MAX_BODY = 200_000
MAX_BODY_OCR = 8_000_000  # fotos comprimidas chegan a ~1 MB cada
RATE_LIMIT = 30   # /generate e /ocr, por hora por IP
CHAT_RATE = 120   # /chat, por hora por IP
TTS_RATE = 300    # /tts, por hora por IP
EXAM_RATE = 30    # /exam, por hora por IP
WINDOW = 3600
_hits = {}

SYSTEM = """Eres una profesora de 3.º de Primaria en Galicia (España). Generas ejercicios de refuerzo EN GALEGO para una niña de 8 años, a partir del texto del libro y el cuaderno que te paso y de las materias del examen indicadas.

Reglas:
- TODO el contenido va en galego: enunciados, opciones, respuestas, pasos y parejas. Los nombres de los campos JSON siguen en castellano (q, a, opts, pasos, pares, tipo).
- Genera 16 ejercicios que cubran los temas. Sin repetir preguntas.
- Mezcla los tipos:
  1) Opción múltiple: {"q":"...","a":"...","opts":["...","...","...","..."]} — «a» debe ser EXACTAMENTE una de las opts; los otros tres distractores plausibles y de la misma categoría (nada absurdo ni gracioso).
  2) Verdadero/falso: {"q":"Le: «...» ¿Verdadeiro ou falso?","tipo":"vf","a":"Verdadeiro","opts":["Verdadeiro","Falso"]}
  3) Ordenar: {"q":"Toca as etapas ..., en orde:","tipo":"ordenar","pasos":["paso 1","paso 2","paso 3"],"a":"paso 1 → paso 2 → paso 3"}
  4) Parejas: {"q":"Toca as parellas: une cada ... coa súa ...:","tipo":"parejas","pares":[["termo","definición"],["termo","definición"],["termo","definición"]],"a":"resumo curto"}
- Frases cortas y vocabulario de 8 años. Galego correcto (normativa galega, non castelán nin portugués). Nada de preguntas tontas.
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
            # a resposta é sempre o rótulo galego que o botón amosa
            yes = clean_str(it.get("a"), 20).strip().lower() in ("verdadeiro", "verdadero", "true", "v")
            out.append({"q": q, "tipo": "vf",
                        "a": "Verdadeiro" if yes else "Falso",
                        "opts": ["Verdadeiro", "Falso"]})
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


OCR_PROMPT = """Transcribe TODO el texto visible de esta foto de página de libro o cuaderno escolar (puede estar en español o en gallego).
Reglas:
- Escribe el texto en el mismo orden en que aparece, línea por línea, incluyendo títulos y las palabras de los ejercicios.
- No inventes ni corrijas nada: transcribe tal cual, aunque haya palabras mal escritas.
- Ignora dibujos, decoraciones, sellos y números de página.
- Responde SOLO con la transcripción, sin comentarios."""


def _ocr_once(model, data_url):
    payload = json.dumps({
        "model": model,
        "temperature": 0,
        "max_tokens": 3000,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": OCR_PROMPT},
            {"type": "image_url", "image_url": {"url": data_url}},
        ]}],
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
    return (content or "").strip()


# o gpt-4o-mini às vezes se recusa a ler fotos com pessoas; nesses casos
# repetimos com o Gemini, que transcribe sempre (mas pode traduzir o galego,
# por isso ele só entra como reserva)
_OCR_REJEITA = ("lo siento", "no puedo", "no podo", "i'm sorry", "i cannot", "i can't")


def call_ocr(data_url):
    text = _ocr_once(MODEL, data_url)
    low = text.lower()
    if not text or any(h in low for h in _OCR_REJEITA):
        alt = _ocr_once(OCR_MODEL, data_url)
        if alt:
            return alt
    return text


CHAT_SYSTEM = """Eres Gatuno, un gato tutor divertido y cariñoso que conversa con una niña de 8 años en Galicia (España). Respondes SIEMPRE en el mismo idioma en que escribe la niña (español, gallego u otro).

Reglas:
- Respuestas MUY cortas (2-3 frases, máximo ~40 palabras), vocabulario sencillo de 8 años, 0-2 emojis.
- Eres un gato: a veces dices "miau" o ronroneas "prrr", y te gustan los juegos de gatos.
- Fomentas el aprendizaje: si pide ayuda con la escuela, la guías con preguntas paso a paso; NUNCA das la respuesta directa de un deber sin que ella lo piense primero.
- Propones juegos (adivinanzas, "palabras que empiezan por X", sumas locas, adivina el animal), chistes cortos y cosas divertidas cuando está aburrida.
- El nombre de la niña es: {name}. Llámala SIEMPRE por su nombre con cariño. NUNCA la llames "gatito", "gatita", "gatuna" ni con diminutivos de gato: la gata eres TÚ; ella es {name}, una niña.
- Temas seguros solo: escuela, animales, juegos, chistes, familia, hobbies. Si pide algo inapropiado, o habla de miedo o tristeza fuerte, responde con calma y sugiere contárselo a sus padres.
- Nunca hables de política, violencia, romance ni nada de adultos."""


def call_chat(messages, name, text):
    """Resposta curta do gato tutor; histórico saneado (≤14 msgs, ≤600 car)."""
    msgs = [{"role": "system",
             "content": CHAT_SYSTEM.replace("{name}", name or "pequeña")}]
    for m in (messages or [])[-14:]:
        if isinstance(m, dict) and m.get("role") in ("user", "assistant") \
                and isinstance(m.get("content"), str):
            msgs.append({"role": m["role"], "content": clean_str(m["content"], 600)})
    msgs.append({"role": "user", "content": clean_str(text, 600)})
    payload = json.dumps({
        "model": MODEL,
        "temperature": 0.9,
        "max_tokens": 220,
        "messages": msgs,
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions", data=payload,
        headers={"Content-Type": "application/json",
                 "Authorization": "Bearer " + API_KEY,
                 "HTTP-Referer": "https://yo-001.github.io/estudo-moedas/",
                 "X-Title": "estudo-exams"})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.loads(r.read().decode("utf-8", "ignore"))
    content = data["choices"][0]["message"]["content"]
    return (content or "").strip()[:800]


TTS_VOICE = "gl-ES-SabelaNeural"          # voz galega: os exercicios lense en galego
TTS_VOICE_FALLBACK = "es-ES-ElviraNeural"  # se o servizo non ten a voz galega
TTS_PITCH = "+30Hz"
_tts_cache = {}


def _synth_tts(text):
    """Sintetiza com edge-tts (vozes neurais da Microsoft, gratuito, sem chave)."""
    import asyncio

    import edge_tts

    async def _go(voice):
        c = edge_tts.Communicate(text, voice, pitch=TTS_PITCH)
        buf = bytearray()
        async for chunk in c.stream():
            if chunk.get("type") == "audio":
                buf.extend(chunk["data"])
        return bytes(buf)

    for voice in (TTS_VOICE, TTS_VOICE_FALLBACK):
        try:
            audio = asyncio.run(_go(voice))
            if audio:
                return audio
        except Exception:
            continue
    raise RuntimeError("edge-tts: ninguna voz disponible")


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
        elif self.path.startswith("/tts?") or self.path == "/tts":
            self._do_tts()
        else:
            self._json(404, {"error": "no encontrado"})

    def _do_tts(self):
        """Voz neural do gato (edge-tts, sem chave) com cache em memória."""
        ip = self.headers.get("X-Forwarded-For", "desconocido").split(",")[-1].strip()
        now = time.time()
        key = ip + "|/tts"
        hist = [t for t in _hits.get(key, []) if now - t < WINDOW]
        if len(hist) >= TTS_RATE:
            return self._json(429, {"error": "demasiadas peticiones"})
        _hits[key] = hist + [now]
        qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        text = clean_str((qs.get("text") or [""])[0], 400)
        if not text:
            return self._json(400, {"error": "falta el texto"})
        h = hashlib.sha1(text.encode("utf-8")).digest()
        if h in _tts_cache:
            return self._send_audio(_tts_cache[h])
        try:
            mp3 = _synth_tts(text)
        except Exception as e:
            return self._json(502, {"error": "voz indisponível: " + type(e).__name__})
        if not mp3:
            return self._json(502, {"error": "voz vacía"})
        if len(_tts_cache) > 400:
            _tts_cache.clear()
        _tts_cache[h] = mp3
        self._send_audio(mp3)

    def _send_audio(self, mp3):
        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", "audio/mpeg")
        self.send_header("Content-Length", str(len(mp3)))
        self.end_headers()
        self.wfile.write(mp3)

    def do_POST(self):
        if self.path not in ("/generate", "/ocr", "/chat", "/exam"):
            return self._json(404, {"error": "no encontrado"})
        ip = self.headers.get("X-Forwarded-For", "desconocido").split(",")[-1].strip()
        now = time.time()
        key = ip + "|" + self.path
        lim = CHAT_RATE if self.path == "/chat" else (TTS_RATE if self.path == "/tts" else (EXAM_RATE if self.path == "/exam" else RATE_LIMIT))
        hist = [t for t in _hits.get(key, []) if now - t < WINDOW]
        if len(hist) >= lim:
            return self._json(429, {"error": "demasiadas peticiones, prueba en unos minutos"})
        try:
            n = int(self.headers.get("Content-Length", "0"))
        except Exception:
            n = 0
        limit = MAX_BODY_OCR if self.path == "/ocr" else MAX_BODY
        if n <= 0 or n > limit:
            return self._json(400, {"error": "cuerpo inválido o demasiado grande"})
        raw = self.rfile.read(n)
        try:
            reqj = json.loads(raw.decode("utf-8", "ignore"))
        except Exception:
            return self._json(400, {"error": "JSON inválido"})
        _hits[key] = hist + [now]
        if self.path == "/ocr":
            return self._do_ocr(reqj)
        if self.path == "/chat":
            return self._do_chat(reqj)
        if self.path == "/exam":
            return self._do_exam(reqj)
        self._do_generate(reqj)

    def _do_chat(self, reqj):
        text = clean_str(reqj.get("text", ""), 600)
        if not text:
            return self._json(400, {"error": "mensaje vacío"})
        if not API_KEY:
            return self._json(503, {"error": "chat no configurado"})
        name = clean_str(reqj.get("name", ""), 30)
        hist = reqj.get("messages") if isinstance(reqj.get("messages"), list) else []
        try:
            reply = call_chat(hist, name, text)
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "ignore")[:300]
            return self._json(502, {"error": "OpenRouter " + str(e.code), "detalle": body})
        except Exception as e:
            return self._json(502, {"error": "fallo del chat: " + type(e).__name__})
        if not reply:
            return self._json(502, {"error": "el gato se quedó sin palabras"})
        self._json(200, {"text": reply})

    def _do_ocr(self, reqj):
        if not API_KEY:
            return self._json(503, {"error": "generador no configurado"})
        imgs = reqj.get("images") if isinstance(reqj.get("images"), list) else []
        imgs = [u for u in imgs if isinstance(u, str)
                and re.match(r"^data:image/(jpeg|jpg|png|webp);base64,", u)
                and len(u) < MAX_BODY_OCR][:8]
        if not imgs:
            return self._json(400, {"error": "no hay fotos válidas"})
        try:
            pages = [call_ocr(u) for u in imgs]
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "ignore")[:300]
            return self._json(502, {"error": "OpenRouter " + str(e.code), "detalle": body})
        except Exception as e:
            return self._json(502, {"error": "fallo del lector: " + type(e).__name__})
        text = "\n\n".join(p for p in pages if p).strip()
        if not text:
            return self._json(502, {"error": "no se vio texto en las fotos"})
        self._json(200, {"text": text})

    def _do_generate(self, reqj):
        text = clean_str(reqj.get("text", ""), 12000)
        if len(text) < 80:
            return self._json(400, {"error": "Texto muito curto: suba fotos do livro/cuaderno ou escreva o conteúdo."})
        if not API_KEY:
            return self._json(503, {"error": "generador no configurado"})
        try:
            items = call_model(text, clean_str(reqj.get("topics", ""), 2000))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "ignore")[:300]
            return self._json(502, {"error": "OpenRouter " + str(e.code), "detalle": body})
        except Exception as e:
            return self._json(502, {"error": "fallo do generador: " + type(e).__name__})
        valid = validate(items)
        if not valid:
            return self._json(502, {"error": "sin ejercicios válidos"})
        return self._json(200, {"ejercicios": valid})

    def _do_exam(self, reqj):
        """Gera exercícios via IA com rate limit por IP e dia."""
        text = clean_str(reqj.get("text", ""), 12000)
        if len(text) < 80:
            return self._json(400, {"error": "Texto muito curto: suba fotos do livro/cuaderno ou escreva o conteúdo."})
        if not API_KEY:
            return self._json(503, {"error": "generador no configurado"})
        try:
            items = call_model(text, clean_str(reqj.get("topics", ""), 2000))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "ignore")[:300]
            return self._json(502, {"error": "OpenRouter " + str(e.code), "detalle": body})
        except Exception as e:
            return self._json(502, {"error": "fallo do generador: " + type(e).__name__})
        valid = validate(items)
        if not valid:
            return self._json(502, {"error": "sin ejercicios válidos"})
        return self._json(200, {"ejercicios": valid})


def main():
    port = int(os.environ.get("PORT", "8080"))
    ThreadingHTTPServer(("0.0.0.0", port), H).serve_forever()


if __name__ == "__main__":
    main()
