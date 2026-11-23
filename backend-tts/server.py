"""Serviço dedicado TTS OmniVoice (perfil mia_amostra2) para Cloud Run GPU L4."""
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import soundfile
import torch

MODEL_DIR = os.environ.get("MODEL_DIR", "/app/model")
TTS_CACHE_DIR = os.environ.get("TTS_CACHE_DIR", "/cache/mp3")
VOICE_REF_AUDIO = os.environ.get("VOICE_REF_AUDIO", "/cache/_voice/ref_clip_clean.wav")
VOICE_PROMPT_CACHE_DIR = os.environ.get("VOICE_PROMPT_CACHE_DIR", "/cache/_voice")
VOICE_REF_TEXT = os.environ.get(
    "VOICE_REF_TEXT",
    "Y se pone el tutú y se pone a bailar como una bailarina.",
)
TTS_NUM_STEP = int(os.environ.get("TTS_NUM_STEP", "16"))
TTS_SPEED = float(os.environ.get("TTS_SPEED", "1.06"))
TTS_GUIDANCE = float(os.environ.get("TTS_GUIDANCE", "2.0"))

TTS_RATE = int(os.environ.get("TTS_RATE", "300"))
WINDOW = 3600
_hits = {}
_rate_lock = threading.Lock()

_mem_cache = {}
_cache_lock = threading.Lock()

_ready_ev = threading.Event()
_init_err = None
_device = "cuda" if torch.cuda.is_available() else "cpu"
_model = None
_prompt = None
_gpu_lock = threading.Lock()

_GL_WORD_RE = re.compile(
    r"\b(moi|ben|xenial|gañaches|moedas|tentalo|outra|imos|aló|acertaches|tesouro|non|limpo|feito|galego|auga|folla|follas|osíxeno|cal|cales|cantos|onde|verdadeiro|unha|dous|catro|árbores|raíz|talo|froito|semente|fungos|coñecemento|lingua)\b",
    re.IGNORECASE,
)
_GL_STEM_RE = re.compile(r"(unha|coñec)", re.IGNORECASE)
_EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001FAFF"
    "\U00002600-\U000027BF"
    "\U0000FE00-\U0000FE0F"
    "\U0000200D"
    "]+",
    flags=re.UNICODE,
)


def _clean_str(s, n=400):
    return re.sub(r"\s+", " ", (s or "")).strip()[:n]


def _detect_tts_lang(text, default_lang="es"):
    """Detecta idioma para OmniVoice ('gl' ou 'es')."""
    s = text or ""
    if _GL_WORD_RE.search(s) or _GL_STEM_RE.search(s):
        return "gl"
    return default_lang if default_lang in ("gl", "es") else "es"


def _normalize_tts_text(text, lang="es"):
    """Normaliza texto para síntese TTS removendo emojis e expandindo símbolos."""
    s = _EMOJI_RE.sub("", text or "")
    s = s.replace("«", "").replace("»", "")
    s = s.replace("×", " por ").replace("÷", " entre ").replace("=", " igual a ").replace("→", ", ")
    plus_word = " máis " if lang == "gl" else " más "
    s = re.sub(r"(?<=\d)\s*\+\s*(?=\d)|\s+\+\s+", plus_word, s)
    s = re.sub(r"\s+([.!?,])", r"\1", s)
    s = re.sub(r"([.!?,¡¿])\1+", r"\1", s)
    return re.sub(r"\s+", " ", s).strip()


def _tts_cache_key(norm_text, lang):
    raw = "|".join([
        "v4_gpu_fp16",
        "amostra-2-entusiasmada",
        str(lang),
        str(VOICE_REF_TEXT),
        str(TTS_SPEED),
        str(TTS_GUIDANCE),
        str(TTS_NUM_STEP),
        str(True),
        str(True),
        norm_text,
    ])
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def trim_speech_padding(audio_tensor, sample_rate):
    """Remove generated edge silence before timing, retaining 50 ms of context."""
    if audio_tensor.numel() == 0 or sample_rate <= 0:
        return audio_tensor
    envelope = audio_tensor.abs()
    if envelope.ndim > 1:
        envelope = envelope.amax(dim=tuple(range(envelope.ndim - 1)))
    voiced = torch.nonzero(envelope > 10 ** (-50.0 / 20.0))
    if voiced.numel() == 0:
        return audio_tensor
    margin = int(sample_rate * 0.05)
    start = max(0, int(voiced[0].item()) - margin)
    end = min(audio_tensor.shape[-1], int(voiced[-1].item()) + 1 + margin)
    return audio_tensor[..., start:end]


def apply_mastering(audio_tensor, sample_rate=24000):
    """Applies the broadcast pre-stage (highpass + gentle compression)."""
    try:
        from pedalboard import Compressor, HighpassFilter, Pedalboard

        board = Pedalboard([
            HighpassFilter(cutoff_frequency_hz=60.0),
            Compressor(threshold_db=-15.0, ratio=1.5, attack_ms=2.0, release_ms=100.0),
        ])
        audio_np = audio_tensor.detach().cpu().to(torch.float32).numpy()
        was_1d = audio_np.ndim == 1
        if was_1d:
            audio_np = audio_np[None, :]
        effected = board(audio_np, sample_rate, reset=False)
        if was_1d:
            effected = effected[0]
        return torch.from_numpy(effected)
    except Exception:
        return audio_tensor


def normalize_audio(audio_tensor, target_dBFS=-2.0):
    """Peak-normalizes audio to target_dBFS when above -50 dBFS silence floor."""
    if audio_tensor.numel() == 0:
        return audio_tensor
    max_val = torch.abs(audio_tensor).max()
    silence_floor = 10 ** (-50.0 / 20.0)
    if max_val > silence_floor:
        target_amp = 10 ** (target_dBFS / 20.0)
        audio_tensor = audio_tensor * (target_amp / max_val)
    return audio_tensor


def _put_mem_cache(key, mp3_bytes):
    with _cache_lock:
        if len(_mem_cache) >= 400:
            _mem_cache.clear()
        _mem_cache[key] = mp3_bytes


def _load_model():
    global _model, _prompt, _init_err
    try:
        from omnivoice import OmniVoice, VoiceClonePrompt

        dtype = torch.float16 if _device == "cuda" else torch.float32
        _model = OmniVoice.from_pretrained(MODEL_DIR, device_map=_device, dtype=dtype)

        st = os.stat(VOICE_REF_AUDIO)
        raw = f"{VOICE_REF_AUDIO}|{st.st_size}|{int(st.st_mtime)}|{VOICE_REF_TEXT}"
        h = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]
        os.makedirs(VOICE_PROMPT_CACHE_DIR, exist_ok=True)
        pt_path = os.path.join(VOICE_PROMPT_CACHE_DIR, f"mia_prompt_{h}.pt")

        loaded = None
        if os.path.isfile(pt_path):
            try:
                loaded = VoiceClonePrompt.load(pt_path, map_location=_device)
            except Exception:
                loaded = None

        if loaded is None:
            loaded = _model.create_voice_clone_prompt(
                ref_audio=VOICE_REF_AUDIO,
                ref_text=VOICE_REF_TEXT,
            )
            with tempfile.TemporaryDirectory() as td:
                tmp_pt = os.path.join(td, f"mia_prompt_{h}.pt")
                loaded.save(tmp_pt)
                shutil.copyfile(tmp_pt, pt_path)

        _prompt = loaded
    except Exception as exc:
        _init_err = repr(exc)
    finally:
        _ready_ev.set()


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
        self.send_header("Access-Control-Allow-Methods", "GET,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Private-Network", "true")

    def _json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_audio(self, mp3_bytes):
        self.send_response(200)
        self._cors()
        self.send_header("Cache-Control", "public, max-age=604800")
        self.send_header("Content-Type", "audio/mpeg")
        self.send_header("Content-Length", str(len(mp3_bytes)))
        self.end_headers()
        self.wfile.write(mp3_bytes)

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/health":
            self._json(200, {
                "ok": True,
                "ready": _ready_ev.is_set() and _init_err is None,
                "error": _init_err,
                "device": _device,
                "tts_engine": "omnivoice",
                "profile": "amostra-2-entusiasmada",
            })
        elif parsed.path == "/tts":
            self._do_tts(parsed.query)
        else:
            self._json(404, {"error": "no encontrado"})

    def _do_tts(self, query):
        ip = self.headers.get("X-Forwarded-For", "desconocido").split(",")[-1].strip()
        now = time.time()
        with _rate_lock:
            hist = [t for t in _hits.get(ip, []) if now - t < WINDOW]
            if len(hist) >= TTS_RATE:
                return self._json(429, {"error": "demasiadas peticiones"})
            _hits[ip] = hist + [now]

        qs = urllib.parse.parse_qs(query)
        text = _clean_str((qs.get("text") or [""])[0], 400)
        if not text:
            return self._json(400, {"error": "falta el texto"})

        lang = _detect_tts_lang(text)
        norm_text = _normalize_tts_text(text, lang)
        if not norm_text:
            return self._json(400, {"error": "falta el texto"})

        key = _tts_cache_key(norm_text, lang)
        mp3_path = os.path.join(TTS_CACHE_DIR, f"{key}.mp3")

        with _cache_lock:
            cached = _mem_cache.get(key)
        if cached:
            return self._send_audio(cached)

        if os.path.isfile(mp3_path):
            try:
                with open(mp3_path, "rb") as f:
                    data = f.read()
                if data:
                    _put_mem_cache(key, data)
                    return self._send_audio(data)
            except Exception:
                pass

        if not _ready_ev.wait(timeout=180):
            return self._json(502, {"error": "tts_unavailable", "detail": "model_load_timeout"})

        with _gpu_lock:
            if os.path.isfile(mp3_path):
                try:
                    with open(mp3_path, "rb") as f:
                        data = f.read()
                    if data:
                        _put_mem_cache(key, data)
                        return self._send_audio(data)
                except Exception:
                    pass

            if _init_err or _model is None:
                return self._json(502, {"error": "tts_unavailable", "detail": _init_err})

            try:
                with torch.inference_mode():
                    audio = _model.generate(
                        text=norm_text,
                        language=lang,
                        speed=TTS_SPEED,
                        guidance_scale=TTS_GUIDANCE,
                        num_step=TTS_NUM_STEP,
                        denoise=True,
                        postprocess_output=True,
                        voice_clone_prompt=_prompt,
                    )[0]
                audio = torch.as_tensor(audio, dtype=torch.float32).detach().cpu()

                sr = int(getattr(_model, "sampling_rate", 24000))
                audio = trim_speech_padding(audio, sr)
                audio = apply_mastering(audio, sr)
                audio = normalize_audio(audio, target_dBFS=-2.0)

                audio_np = audio.detach().cpu().to(torch.float32).numpy()
                if audio_np.ndim == 2:
                    audio_np = audio_np.T

                with tempfile.TemporaryDirectory() as td:
                    wav_tmp = os.path.join(td, "out.wav")
                    mp3_tmp = os.path.join(td, "out.mp3")
                    soundfile.write(wav_tmp, audio_np, sr, subtype="PCM_16")
                    res = subprocess.run(
                        [
                            "ffmpeg",
                            "-y",
                            "-i",
                            wav_tmp,
                            "-codec:a",
                            "libmp3lame",
                            "-qscale:a",
                            "2",
                            mp3_tmp,
                        ],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.PIPE,
                        timeout=60,
                    )
                    if res.returncode != 0 or not os.path.isfile(mp3_tmp):
                        err_msg = (res.stderr or b"").decode("utf-8", "ignore")[:200]
                        raise RuntimeError("ffmpeg failed: " + err_msg)
                    with open(mp3_tmp, "rb") as f:
                        mp3_bytes = f.read()
            except Exception as exc:
                return self._json(502, {"error": "tts_unavailable", "detail": repr(exc)})

        try:
            os.makedirs(TTS_CACHE_DIR, exist_ok=True)
            with open(mp3_path, "wb") as f:
                f.write(mp3_bytes)
        except Exception:
            pass

        _put_mem_cache(key, mp3_bytes)
        return self._send_audio(mp3_bytes)


def main():
    threading.Thread(target=_load_model, daemon=True).start()
    port = int(os.environ.get("PORT", "8080"))
    ThreadingHTTPServer(("0.0.0.0", port), H).serve_forever()


if __name__ == "__main__":
    main()
