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
import glob
import hashlib
import json
import mimetypes
import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.dirname(BASE_DIR)

def _load_api_key():
    k = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if k:
        return k
    sec = os.path.join(BASE_DIR, "secrets.json")
    if os.path.isfile(sec):
        try:
            with open(sec, "r", encoding="utf-8") as f:
                return (json.load(f).get("OPENROUTER_API_KEY") or "").strip()
        except Exception:
            pass
    return ""

MODEL = "openai/gpt-4o-mini"           # geração de exercícios, OCR principal e chat (barato: ~$0.15/1M in, $0.6/1M out)
OCR_MODEL = "google/gemini-2.5-flash"  # OCR de reserva: não recusa fotos com pessoas (o gpt-4o-mini recusa, mas traduz galego→português)
API_KEY = _load_api_key()
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


TTS_VOICE = "gl-ES-SabelaNeural"          # fallback remoto (Cloud Run) se OmniVoice non estiver dispoñible
TTS_VOICE_FALLBACK = "es-ES-ElviraNeural"
TTS_PITCH = "+20Hz"
TTS_SPEED = "+8%"
TTS_CACHE_DIR = os.environ.get("TTS_CACHE_DIR", os.path.join(BASE_DIR, "tts_cache"))
_tts_cache = {}
_tts_lock = threading.Lock()
_omni_proc = None

_DEFAULT_PROFILE = {
    "id": "amostra-2-entusiasmada",
    "voicestudio_profile_id": "mia_amostra2",
    "language": "gl",
    "params": {
        "instruct": "high pitch",
        "speed": 1.1,
        "guidance_scale": 2.7,
        "num_step": 20,
        "denoise": True,
        "postprocess_output": True,
    },
    "reference": {
        "clip": "content/audio/raw/ref_clip.wav",
        "ref_text": (
            "Pongo una música y se pone a llorar. Pongo un suéter caro y se pone "
            "a gritar. Le doy una guitarra y se pone a bailar."
        ),
    },
}


def _load_voice_profile():
    p = os.path.join(REPO_DIR, "content", "audio", "voice-profile.json")
    if os.path.isfile(p):
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
        except Exception:
            pass
    return _DEFAULT_PROFILE


def _fx_file_for_text(text):
    prof = _load_voice_profile()
    norm = re.sub(r"\s+", " ", (text or "").strip().lower())
    for item in (prof.get("fx") or {}).values():
        if not isinstance(item, dict):
            continue
        ft = re.sub(r"\s+", " ", (item.get("text") or "").strip().lower())
        rel = item.get("file") or ""
        if ft and ft == norm and rel:
            fp = os.path.join(REPO_DIR, rel.replace("/", os.sep))
            if os.path.isfile(fp):
                return fp
    return None


def _resolve_ref_audio(prof):
    rel = ((prof.get("reference") or {}).get("clip") or "").replace("/", os.sep)
    if rel:
        cand = os.path.join(REPO_DIR, rel)
        if os.path.isfile(cand):
            return cand
    appdata = os.environ.get("APPDATA", "")
    pid = prof.get("voicestudio_profile_id") or "mia_amostra2"
    vs_voice = os.path.join(appdata, "OmniVoice", "voices", f"{pid}.wav")
    if os.path.isfile(vs_voice):
        return vs_voice
    return None


def _voicestudio_python():
    env_py = os.environ.get("OMNIVOICE_PYTHON", "").strip()
    if env_py and os.path.isfile(env_py):
        return env_py
    appdata = os.environ.get("APPDATA", "")
    cand = os.path.join(appdata, "VoiceStudio", "runtime", "project", ".venv", "Scripts", "python.exe")
    if os.path.isfile(cand):
        return cand
    return None


def _omnivoice_cli():
    env_cli = os.environ.get("OMNIVOICE_CLI", "").strip()
    if env_cli and os.path.isfile(env_cli):
        return env_cli
    found = shutil.which("omnivoice-infer")
    if found:
        return found
    appdata = os.environ.get("APPDATA", "")
    cand = os.path.join(appdata, "VoiceStudio", "runtime", "project", ".venv", "Scripts", "omnivoice-infer.exe")
    if os.path.isfile(cand):
        return cand
    return None


def _ffmpeg_bin():
    found = shutil.which("ffmpeg")
    if found:
        return found
    appdata = os.environ.get("APPDATA", "")
    cand = os.path.join(appdata, "OmniVoice", "media_tools", "shims", "ffmpeg.exe")
    if os.path.isfile(cand):
        return cand
    return None


def _omnivoice_model_arg():
    local_app = os.environ.get("LOCALAPPDATA", "")
    hf_cache = os.path.join(local_app, "OmniVoice", "hf_cache")
    snaps = sorted(glob.glob(os.path.join(hf_cache, "models--k2-fsa--OmniVoice", "snapshots", "*")))
    for s in snaps:
        if (os.path.isfile(os.path.join(s, "model.safetensors"))
                and os.path.isfile(os.path.join(s, "config.json"))
                and os.path.isdir(os.path.join(s, "audio_tokenizer"))):
            return s, hf_cache, True
    return "k2-fsa/OmniVoice", hf_cache if os.path.isdir(hf_cache) else "", False


def _omni_env(hf_cache, offline):
    env = os.environ.copy()
    if hf_cache:
        env.setdefault("HF_HOME", hf_cache)
        env.setdefault("HF_HUB_CACHE", hf_cache)
    if offline:
        env.setdefault("HF_HUB_OFFLINE", "1")
    env.setdefault("TORCH_COMPILE_DISABLE", "1")
    env.setdefault("TORCHDYNAMO_DISABLE", "1")
    env.setdefault("TORCHINDUCTOR_DISABLE", "1")
    env.setdefault("FOR_DISABLE_CONSOLE_CTRL_HANDLER", "1")
    return env


_WORKER_CODE = r"""
import json, sys, torch, torchaudio
_proto_out = sys.stdout
sys.stdout = sys.stderr
from omnivoice.models.omnivoice import OmniVoice
from omnivoice.utils.dtype import tts_dtype_name

cfg = json.loads(sys.argv[1])
device = "cuda" if torch.cuda.is_available() else ("mps" if torch.backends.mps.is_available() else "cpu")
model = OmniVoice.from_pretrained(cfg["model"], device_map=device, dtype=getattr(torch, tts_dtype_name(device)))
prompt = None
if cfg.get("ref_audio"):
    prompt = model.create_voice_clone_prompt(ref_audio=cfg["ref_audio"], ref_text=cfg.get("ref_text"))
_proto_out.write(json.dumps({"ready": True, "device": device}) + "\n")
_proto_out.flush()

for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    req = json.loads(line)
    kw = dict(
        text=req["text"],
        language=req.get("language") or None,
        instruct=req.get("instruct") or None,
        speed=float(req.get("speed", 1.1)),
        guidance_scale=float(req.get("guidance_scale", 2.7)),
        num_step=int(req.get("num_step", 20)),
        denoise=bool(req.get("denoise", True)),
        postprocess_output=bool(req.get("postprocess_output", True)),
    )
    if prompt is not None:
        kw["voice_clone_prompt"] = prompt
    audios = model.generate(**kw)
    torchaudio.save(req["output"], audios[0], model.sampling_rate)
    _proto_out.write(json.dumps({"ok": True, "output": req["output"]}) + "\n")
    _proto_out.flush()
"""


def _ensure_omni_worker(py_exe, model_arg, ref_audio, ref_text, hf_cache, offline):
    global _omni_proc
    if _omni_proc is not None and _omni_proc.poll() is None:
        return _omni_proc
    cfg = json.dumps({"model": model_arg, "ref_audio": ref_audio, "ref_text": ref_text})
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    proc = subprocess.Popen(
        [py_exe, "-c", _WORKER_CODE, cfg],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
        env=_omni_env(hf_cache, offline),
        creationflags=flags,
    )
    ready_line = proc.stdout.readline()
    if not ready_line:
        proc.kill()
        raise RuntimeError("omnivoice worker failed to start")
    _omni_proc = proc
    return proc


def _wav_to_mp3_or_bytes(wav_path):
    ff = _ffmpeg_bin()
    if ff:
        mp3_path = wav_path[:-4] + ".mp3"
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        res = subprocess.run(
            [ff, "-y", "-i", wav_path, "-codec:a", "libmp3lame", "-qscale:a", "3", mp3_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=30,
            creationflags=flags,
        )
        if res.returncode == 0 and os.path.isfile(mp3_path):
            with open(mp3_path, "rb") as f:
                return f.read(), "audio/mpeg", ".mp3"
    with open(wav_path, "rb") as f:
        return f.read(), "audio/wav", ".wav"


def _synth_omnivoice(text, prof):
    params = prof.get("params") or {}
    ref_audio = _resolve_ref_audio(prof)
    ref_text = (prof.get("reference") or {}).get("ref_text") or ""
    lang = prof.get("language") or "gl"
    instruct = params.get("instruct") or "high pitch"
    speed = params.get("speed", 1.1)
    guidance = params.get("guidance_scale", 2.7)
    num_step = params.get("num_step", 20)
    denoise = bool(params.get("denoise", True))
    postproc = bool(params.get("postprocess_output", True))
    model_arg, hf_cache, offline = _omnivoice_model_arg()

    with tempfile.TemporaryDirectory() as tmpdir:
        wav_out = os.path.join(tmpdir, "out.wav")
        py_exe = _voicestudio_python()
        if py_exe:
            try:
                proc = _ensure_omni_worker(py_exe, model_arg, ref_audio, ref_text, hf_cache, offline)
                req = json.dumps({
                    "text": text,
                    "language": lang,
                    "instruct": instruct,
                    "speed": speed,
                    "guidance_scale": guidance,
                    "num_step": num_step,
                    "denoise": denoise,
                    "postprocess_output": postproc,
                    "output": wav_out,
                })
                proc.stdin.write(req + "\n")
                proc.stdin.flush()
                resp = proc.stdout.readline()
                if resp and json.loads(resp).get("ok") and os.path.isfile(wav_out):
                    return _wav_to_mp3_or_bytes(wav_out)
            except Exception:
                global _omni_proc
                if _omni_proc is not None:
                    try:
                        _omni_proc.kill()
                    except Exception:
                        pass
                    _omni_proc = None

        cli = _omnivoice_cli()
        if cli:
            cmd = [
                cli,
                "--model", model_arg,
                "--text", text,
                "--language", str(lang),
                "--instruct", str(instruct),
                "--speed", str(speed),
                "--guidance_scale", str(guidance),
                "--num_step", str(num_step),
                "--denoise", "true" if denoise else "false",
                "--postprocess_output", "true" if postproc else "false",
                "--output", wav_out,
            ]
            if ref_audio:
                cmd.extend(["--ref_audio", ref_audio])
                if ref_text:
                    cmd.extend(["--ref_text", ref_text])
            flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            res = subprocess.run(
                cmd,
                env=_omni_env(hf_cache, offline),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                timeout=180,
                creationflags=flags,
            )
            if res.returncode == 0 and os.path.isfile(wav_out):
                return _wav_to_mp3_or_bytes(wav_out)
            raise RuntimeError("omnivoice-infer failed: " + (res.stderr or b"").decode("utf-8", "ignore")[:200])

    raise RuntimeError("omnivoice unavailable")


def _synth_edge_tts(text):
    """Fallback remoto (Cloud Run) se OmniVoice/VoiceStudio non estiver dispoñible."""
    import asyncio
    import edge_tts

    async def _go(voice):
        c = edge_tts.Communicate(text, voice, rate=TTS_SPEED, pitch=TTS_PITCH)
        buf = bytearray()
        async for chunk in c.stream():
            if chunk.get("type") == "audio":
                buf.extend(chunk["data"])
        return bytes(buf)

    for voice in (TTS_VOICE, TTS_VOICE_FALLBACK):
        try:
            audio = asyncio.run(_go(voice))
            if audio:
                return audio, "audio/mpeg", ".mp3"
        except Exception:
            continue
    raise RuntimeError("edge-tts: ninguna voz disponible")


def _tts_cache_key(text, prof):
    params = prof.get("params") or {}
    raw = "|".join([
        str(prof.get("id") or "amostra-2-entusiasmada"),
        str(prof.get("language") or "gl"),
        str(params.get("instruct") or "high pitch"),
        str(params.get("speed", 1.1)),
        str(params.get("guidance_scale", 2.7)),
        str(params.get("num_step", 20)),
        text,
    ])
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def _synth_tts(text):
    """Sintetiza co perfil Amostra 2 (OmniVoice/VoiceStudio) + caché en disco; fallback edge-tts."""
    fx_path = _fx_file_for_text(text)
    if fx_path:
        with open(fx_path, "rb") as f:
            return f.read(), "audio/mpeg"

    prof = _load_voice_profile()
    key = _tts_cache_key(text, prof)
    os.makedirs(TTS_CACHE_DIR, exist_ok=True)
    for ext, ctype in ((".mp3", "audio/mpeg"), (".wav", "audio/wav")):
        cached_file = os.path.join(TTS_CACHE_DIR, key + ext)
        if os.path.isfile(cached_file):
            with open(cached_file, "rb") as f:
                data = f.read()
            if data:
                return data, ctype

    with _tts_lock:
        for ext, ctype in ((".mp3", "audio/mpeg"), (".wav", "audio/wav")):
            cached_file = os.path.join(TTS_CACHE_DIR, key + ext)
            if os.path.isfile(cached_file):
                with open(cached_file, "rb") as f:
                    data = f.read()
                if data:
                    return data, ctype

        if _voicestudio_python() or _omnivoice_cli():
            audio, ctype, ext = _synth_omnivoice(text, prof)
        else:
            audio, ctype, ext = _synth_edge_tts(text)

        if audio:
            try:
                with open(os.path.join(TTS_CACHE_DIR, key + ext), "wb") as f:
                    f.write(audio)
            except Exception:
                pass
        return audio, ctype


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

    def _allowed_origin(self):
        origin = (self.headers.get("Origin") or "").strip()
        if origin == "https://yo-001.github.io" or origin == "null":
            return origin
        if re.match(r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$", origin):
            return origin
        return "https://yo-001.github.io"

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", self._allowed_origin())
        self.send_header("Vary", "Origin")
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

    def _serve_static(self, rel_path):
        rel = urllib.parse.unquote(rel_path).lstrip("/") or "index.html"
        full = os.path.abspath(os.path.join(REPO_DIR, rel))
        if not (full == REPO_DIR or full.startswith(REPO_DIR + os.sep)):
            return False
        if not os.path.isfile(full):
            return False
        ctype, _ = mimetypes.guess_type(full)
        if full.endswith(".webp"):
            ctype = "image/webp"
        elif full.endswith(".webm"):
            ctype = "video/webm"
        elif full.endswith(".woff2"):
            ctype = "font/woff2"
        with open(full, "rb") as f:
            data = f.read()
        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", ctype or "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
        return True

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/health":
            engine = "omnivoice" if (_voicestudio_python() or _omnivoice_cli()) else "edge-tts"
            self._json(200, {"ok": True, "tts_engine": engine, "profile": "amostra-2-entusiasmada"})
        elif parsed.path == "/tts":
            self._do_tts()
        elif self._serve_static(parsed.path):
            return
        else:
            self._json(404, {"error": "no encontrado"})

    def _do_tts(self):
        """Voz neural da Mía (Amostra 2 OmniVoice/VoiceStudio + caché en disco)."""
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
        h = hashlib.sha1(("amostra-2-entusiasmada|" + text).encode("utf-8")).digest()
        if h in _tts_cache:
            audio, ctype = _tts_cache[h]
            return self._send_audio(audio, ctype)
        try:
            audio, ctype = _synth_tts(text)
        except Exception as e:
            return self._json(502, {"error": "voz indisponível: " + type(e).__name__})
        if not audio:
            return self._json(502, {"error": "voz vacía"})
        if len(_tts_cache) > 400:
            _tts_cache.clear()
        _tts_cache[h] = (audio, ctype)
        self._send_audio(audio, ctype)

    def _send_audio(self, audio, ctype="audio/mpeg"):
        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(audio)))
        self.end_headers()
        self.wfile.write(audio)

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
