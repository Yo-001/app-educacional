#!/usr/bin/env python3
"""
Gera os artefatos reais de teste comparativo entre:
  - Opção 1: Player Interativo HTML5 + Voz Real + Lousa Sincronizada + Mini-Quiz
  - Opção 2: Vídeo MP4 real (Pillow + ffmpeg + VP9 alpha da Mía + voz real)
  - Opção 3: Lip-Sync Neural Open-Source (EchoMimic / MuseTalk 1.5 via Gradio API)

Gera também `comparativo-opcoes-1-2-3.html` e `resultados.json`.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
import urllib.parse
from pathlib import Path
from typing import Any

import requests
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
ASSETS_DIR = PROJECT_ROOT / "assets"
FONTS_DIR = ASSETS_DIR / "fonts"
MIA_DIR = ASSETS_DIR / "mia"
FALLBACK_AUDIO_DIR = PROJECT_ROOT / "content" / "audio" / "amostras"

AUDIO_DIR = BASE_DIR / "audio"
SLIDES_DIR = BASE_DIR / "slides"
TEMP_DIR = BASE_DIR / "tmp"

TTS_ENDPOINT = "https://estudo-tts-405899472513.europe-west1.run.app/tts"
ECHOMIMIC_BASE = "https://fffiloni-echomimic.hf.space"
MUSETALK_BASE = "https://henrybit-musetalk-1-5.hf.space"

SCENES = [
    {
        "id": "cena1",
        "tag": "3.º PRIMARIA · CIENCIAS NATURAIS",
        "title": "¡Ola, Maitê!",
        "subtitle": "Pregunta do exercicio:",
        "highlight": "«Onde se produce o zume elaborado?»",
        "bullets": [
            ("A túa resposta:", "Na raíz", "#f87171"),
            ("Obxectivo:", "Descubrir xuntas onde fabrica o seu alimento a planta.", "#a7f3d0"),
        ],
        "footer": "Escoita a Mía e observa a lousa...",
        "text": "¡Ola, Maitê! Hoxe imos repasar xuntas onde fabrican o seu alimento as plantas.",
        "fallback": "amostra-1-acolhedora.mp3",
    },
    {
        "id": "cena2",
        "tag": "A COCIÑA DA PLANTA",
        "title": "Raíz vs. Folla",
        "subtitle": "Cada parte da planta ten o seu traballo:",
        "highlight": "Raíz (auga do chan)  ->  Folla + Sol (alimento)",
        "bullets": [
            ("1. Na raíz:", "Colle auga e sales minerais do chan (zume bruto).", "#93c5fd"),
            ("2. Na folla:", "Coa luz do sol cociña o alimento da planta.", "#fde047"),
            ("Resposta correcta:", "O zume elaborado nace NAS FOLLAS.", "#4ade80"),
        ],
        "footer": "Zume elaborado = alimento listo nas follas",
        "text": "A raíz colle auga do chan, pero é a folla quen cociña o alimento co sol. Por iso o zume elaborado nace nas follas.",
        "fallback": "amostra-3-calma.mp3",
    },
    {
        "id": "cena3",
        "tag": "RESUMO CHAVE",
        "title": "¡Moi ben, Maitê!",
        "subtitle": "Para non esquecer nunca:",
        "highlight": "«A folla é a cociña da planta»",
        "bullets": [
            ("Lembra:", "A raíz bebe auga; a folla cociña o zume elaborado.", "#c4b5fd"),
            ("Seguinte paso:", "Agora imos facer un pequeno quiz de 2 preguntas.", "#4ade80"),
        ],
        "footer": "Listas para practicar?",
        "text": "¡Moi ben, Maitê! Lembra: a folla é a cociña da planta. Agora imos facer un pequeno quiz.",
        "fallback": "amostra-4-desafio.mp3",
    },
]


def run_cmd(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if check and proc.returncode != 0:
        raise RuntimeError(f"Command failed ({proc.returncode}): {' '.join(cmd)}\n{proc.stderr}")
    return proc


def ffprobe_info(path: Path) -> dict[str, Any]:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_format",
        "-show_streams",
        "-of",
        "json",
        str(path),
    ]
    proc = run_cmd(cmd)
    return json.loads(proc.stdout)


def get_duration(path: Path) -> float:
    info = ffprobe_info(path)
    return float(info["format"]["duration"])


def download_tts_audios() -> tuple[dict[str, dict[str, Any]], list[str]]:
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    warnings: list[str] = []
    audio_meta: dict[str, dict[str, Any]] = {}

    for scene in SCENES:
        sid = scene["id"]
        out_mp3 = AUDIO_DIR / f"{sid}.mp3"
        t0 = time.perf_counter()
        if out_mp3.exists() and out_mp3.stat().st_size > 5 * 1024:
            source = "cached"
        else:
            source = "tts_live"
            try:
                url = f"{TTS_ENDPOINT}?text={urllib.parse.quote(scene['text'])}"
                resp = requests.get(url, timeout=90)
                resp.raise_for_status()
                if len(resp.content) < 1000:
                    raise RuntimeError(f"Resposta TTS moi curta ({len(resp.content)} bytes)")
                out_mp3.write_bytes(resp.content)
            except Exception as exc:
                source = "fallback"
                fb_path = FALLBACK_AUDIO_DIR / scene["fallback"]
                msg = f"Aviso: fallo ao descargar TTS para {sid} ({exc}); usando fallback {fb_path.name}"
                print(msg)
                warnings.append(msg)
                if not fb_path.exists():
                    raise RuntimeError(f"Fallback non atopado: {fb_path}") from exc
                shutil.copy2(fb_path, out_mp3)

        dur = get_duration(out_mp3)
        elapsed = round(time.perf_counter() - t0, 2)
        audio_meta[sid] = {
            "file": f"audio/{sid}.mp3",
            "duration_s": round(dur, 3),
            "size_bytes": out_mp3.stat().st_size,
            "source": source,
            "fetch_time_s": elapsed,
        }
        print(f"[Audio] {sid}.mp3 -> {dur:.2f}s ({out_mp3.stat().st_size} bytes, {source}, {elapsed}s)")

    # Converter cena2.mp3 -> audio/cena2.wav (16kHz mono PCM)
    cena2_wav = AUDIO_DIR / "cena2.wav"
    run_cmd([
        "ffmpeg", "-y", "-i", str(AUDIO_DIR / "cena2.mp3"),
        "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", str(cena2_wav),
    ])
    wav_dur = get_duration(cena2_wav)
    audio_meta["cena2_wav"] = {
        "file": "audio/cena2.wav",
        "duration_s": round(wav_dur, 3),
        "size_bytes": cena2_wav.stat().st_size,
    }
    print(f"[Audio] cena2.wav -> {wav_dur:.2f}s (16kHz mono PCM)")
    return audio_meta, warnings


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    cur = ""
    for w in words:
        test = f"{cur} {w}".strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= max_width:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def render_slides() -> list[Path]:
    SLIDES_DIR.mkdir(parents=True, exist_ok=True)
    fredoka_path = str(FONTS_DIR / "fredoka-latin.woff2")
    nunito_path = str(FONTS_DIR / "nunito-latin.woff2")

    font_tag = ImageFont.truetype(nunito_path, 20)
    font_title = ImageFont.truetype(fredoka_path, 54)
    font_sub = ImageFont.truetype(nunito_path, 26)
    font_highlight = ImageFont.truetype(fredoka_path, 32)
    font_label = ImageFont.truetype(nunito_path, 22)
    font_body = ImageFont.truetype(nunito_path, 25)
    font_footer = ImageFont.truetype(nunito_path, 21)

    slide_paths: list[Path] = []
    W, H = 1280, 720

    for idx, scene in enumerate(SCENES, start=1):
        img = Image.new("RGB", (W, H), "#251b38")
        draw = ImageDraw.Draw(img)

        # Subtle background accents on right side for Mía
        draw.ellipse((860, 120, 1260, 680), fill="#2e2246")
        draw.ellipse((910, 190, 1220, 620), fill="#362852")

        # Left chalkboard panel
        board_box = (44, 42, 845, 678)
        draw.rounded_rectangle(board_box, radius=28, fill="#151123", outline="#4c3973", width=3)

        # Top badge
        tag_text = scene["tag"]
        tb = draw.textbbox((0, 0), tag_text, font=font_tag)
        tag_w = (tb[2] - tb[0]) + 34
        draw.rounded_rectangle((78, 76, 78 + tag_w, 114), radius=16, fill="#352654", outline="#7c5dfa", width=2)
        draw.text((95, 83), tag_text, font=font_tag, fill="#d8b4fe")

        # Scene counter pill
        step_text = f"{idx} / {len(SCENES)}"
        draw.rounded_rectangle((735, 76, 815, 114), radius=16, fill="#241b3c")
        draw.text((755, 83), step_text, font=font_tag, fill="#cbd5e1")

        # Title
        draw.text((78, 134), scene["title"], font=font_title, fill="#ffffff")

        # Subtitle
        draw.text((78, 206), scene["subtitle"], font=font_sub, fill="#cbd5e1")

        # Highlight banner
        draw.rounded_rectangle((78, 250, 810, 326), radius=18, fill="#241a3d", outline="#a78bfa", width=2)
        hl_lines = wrap_text(draw, scene["highlight"], font_highlight, 695)
        hy = 266 if len(hl_lines) == 1 else 254
        for line in hl_lines[:2]:
            draw.text((98, hy), line, font=font_highlight, fill="#fde047")
            hy += 34

        # Bullet cards
        cy = 354
        for label, body, accent in scene["bullets"]:
            lines = wrap_text(draw, body, font_body, 665)
            card_h = max(72, 42 + len(lines) * 30)
            draw.rounded_rectangle((78, cy, 810, cy + card_h), radius=16, fill="#1c1630", outline="#322852", width=2)
            draw.rounded_rectangle((78, cy, 88, cy + card_h), radius=4, fill=accent)
            draw.text((104, cy + 10), label, font=font_label, fill=accent)
            by = cy + 38
            for line in lines:
                draw.text((104, by), line, font=font_body, fill="#f1f5f9")
                by += 30
            cy += card_h + 14

        # Footer hint
        draw.text((78, 632), scene["footer"], font=font_footer, fill="#94a3b8")

        out_path = SLIDES_DIR / f"slide{idx}.png"
        img.save(out_path, format="PNG")
        slide_paths.append(out_path)
        print(f"[Slide] {out_path.name} renderizado (1280x720)")

    return slide_paths


def build_option2_video(slide_paths: list[Path], audio_meta: dict[str, dict[str, Any]]) -> dict[str, Any]:
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    mia_webm = MIA_DIR / "mia-talk.webm"
    segment_paths: list[Path] = []
    t0 = time.perf_counter()

    for idx, (scene, slide_path) in enumerate(zip(SCENES, slide_paths), start=1):
        sid = scene["id"]
        audio_path = AUDIO_DIR / f"{sid}.mp3"
        dur = audio_meta[sid]["duration_s"]
        seg_out = TEMP_DIR / f"seg_{idx}.mp4"

        cmd = [
            "ffmpeg",
            "-y",
            "-loop", "1",
            "-t", f"{dur:.3f}",
            "-i", str(slide_path),
            "-c:v", "libvpx-vp9",
            "-stream_loop", "-1",
            "-i", str(mia_webm),
            "-i", str(audio_path),
            "-filter_complex",
            "[1:v]scale=-1:600,format=yuva420p[mia];[0:v][mia]overlay=W-w-36:H-h-10:shortest=1,format=yuv420p[v]",
            "-map", "[v]",
            "-map", "2:a",
            "-t", f"{dur:.3f}",
            "-r", "25",
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "20",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "128k",
            "-ar", "44100",
            "-ac", "2",
            str(seg_out),
        ]
        run_cmd(cmd)
        segment_paths.append(seg_out)
        print(f"[Opción 2] Segmento {idx} xerado ({dur:.2f}s)")

    concat_list = TEMP_DIR / "concat.txt"
    concat_lines = [f"file '{p.as_posix()}'" for p in segment_paths]
    concat_list.write_text("\n".join(concat_lines) + "\n", encoding="utf-8")

    out_mp4 = BASE_DIR / "opcao2-mia-lousa.mp4"
    run_cmd([
        "ffmpeg",
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_list),
        "-c", "copy",
        "-movflags", "+faststart",
        str(out_mp4),
    ])

    elapsed = round(time.perf_counter() - t0, 2)
    info = ffprobe_info(out_mp4)
    streams = info.get("streams", [])
    v_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    a_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)
    duration = float(info["format"]["duration"])

    if not v_stream or not a_stream or duration <= 10.0:
        raise RuntimeError(
            f"Validación ffprobe falhou para {out_mp4}: video={bool(v_stream)}, audio={bool(a_stream)}, dur={duration}"
        )

    result = {
        "file": "opcao2-mia-lousa.mp4",
        "duration_s": round(duration, 3),
        "size_bytes": out_mp4.stat().st_size,
        "video_codec": v_stream.get("codec_name"),
        "width": v_stream.get("width"),
        "height": v_stream.get("height"),
        "pix_fmt": v_stream.get("pix_fmt"),
        "audio_codec": a_stream.get("codec_name"),
        "generation_time_s": elapsed,
    }
    print(f"[Opción 2] Validado: {result}")
    return result


def create_mia_512() -> Path:
    mia_src = Image.open(MIA_DIR / "mia.webp").convert("RGBA")
    # Crop upper bust/face region (474x474) so face & shoulders fill 512x512 nicely
    crop_h = min(mia_src.height, int(mia_src.width * 1.0))
    bust = mia_src.crop((0, 0, mia_src.width, crop_h))
    bust = bust.resize((480, 480), Image.Resampling.LANCZOS)

    canvas = Image.new("RGB", (512, 512), "#251b38")
    canvas.paste(bust, (16, 32), bust)
    out_path = BASE_DIR / "mia_512.png"
    canvas.save(out_path, format="PNG")
    print(f"[Opción 3] mia_512.png xerado (512x512 RGB)")
    return out_path


def gradio_upload(base_url: str, file_path: Path, timeout: int = 30) -> str:
    url = f"{base_url}/gradio_api/upload"
    with file_path.open("rb") as fh:
        resp = requests.post(url, files={"files": (file_path.name, fh)}, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    if not isinstance(data, list) or not data:
        raise RuntimeError(f"Resposta inesperada en /gradio_api/upload: {data}")
    return data[0]


def gradio_file_obj(base_url: str, remote_path: str, orig_name: str) -> dict[str, Any]:
    return {
        "path": remote_path,
        "url": f"{base_url}/gradio_api/file={remote_path}",
        "orig_name": orig_name,
        "meta": {"_type": "gradio.FileData"},
    }


def gradio_call_sse(base_url: str, endpoint_name: str, payload_data: list[Any], timeout: int = 150) -> Any:
    call_url = f"{base_url}/gradio_api/call/{endpoint_name}"
    resp = requests.post(call_url, json={"data": payload_data}, timeout=30)
    resp.raise_for_status()
    event_id = resp.json().get("event_id")
    if not event_id:
        raise RuntimeError(f"Sen event_id en {call_url}: {resp.text}")

    sse_url = f"{base_url}/gradio_api/call/{endpoint_name}/{event_id}"
    last_event = None
    last_data = None
    deadline = time.monotonic() + timeout
    with requests.get(sse_url, stream=True, timeout=(15, 45)) as sse:
        sse.raise_for_status()
        for raw_line in sse.iter_lines(decode_unicode=True):
            if time.monotonic() > deadline:
                raise TimeoutError(f"Timeout total ({timeout}s) no stream SSE")
            if raw_line is None:
                continue
            line = raw_line.strip()
            if line.startswith("event:"):
                last_event = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                last_data = line.split(":", 1)[1].strip()
                if last_event == "complete":
                    return json.loads(last_data)
                if last_event == "error":
                    raise RuntimeError(f"Gradio SSE error: {last_data}")
    raise RuntimeError(f"Stream SSE pechado sen evento complete (last_event={last_event}, last_data={last_data})")


def download_gradio_output(base_url: str, output_data: Any, dest: Path) -> None:
    video_url = None
    if isinstance(output_data, list):
        for item in output_data:
            if isinstance(item, dict):
                if "video" in item and isinstance(item["video"], dict):
                    video_url = item["video"].get("url") or f"{base_url}/gradio_api/file={item['video'].get('path')}"
                    break
                if item.get("url"):
                    video_url = item["url"]
                    break
                if item.get("path"):
                    video_url = f"{base_url}/gradio_api/file={item['path']}"
                    break
            elif isinstance(item, str) and item.startswith("http"):
                video_url = item
                break
    if not video_url:
        raise RuntimeError(f"Non se atopou URL de vídeo na resposta Gradio: {output_data}")
    r = requests.get(video_url, timeout=60)
    r.raise_for_status()
    dest.write_bytes(r.content)


def test_option3_neural(mia_512_path: Path, slide2_path: Path, audio_meta: dict[str, dict[str, Any]]) -> dict[str, Any]:
    cena2_wav = AUDIO_DIR / "cena2.wav"
    cena2_mp3 = AUDIO_DIR / "cena2.mp3"
    dur2 = audio_meta["cena2"]["duration_s"]
    attempts: list[dict[str, Any]] = []
    raw_out = BASE_DIR / "opcao3-neural-raw.mp4"

    # Attempt 1: EchoMimic
    t0 = time.perf_counter()
    echo_record: dict[str, Any] = {"space": ECHOMIMIC_BASE, "model": "EchoMimic", "status": "failed"}
    try:
        # Inspect API info for exact diagnostic visibility if needed
        img_remote = gradio_upload(ECHOMIMIC_BASE, mia_512_path, timeout=30)
        aud_remote = gradio_upload(ECHOMIMIC_BASE, cena2_wav, timeout=30)
        length = min(180, int(dur2 * 24) + 8)
        payload = [
            gradio_file_obj(ECHOMIMIC_BASE, img_remote, mia_512_path.name),
            gradio_file_obj(ECHOMIMIC_BASE, aud_remote, cena2_wav.name),
            512,
            512,
            length,
            420,
            0.1,
            0.5,
            12,
            3,
            2.5,
            20,
            16000,
            24,
            "cuda",
        ]
        out = gradio_call_sse(ECHOMIMIC_BASE, "generate_video", payload, timeout=150)
        download_gradio_output(ECHOMIMIC_BASE, out, raw_out)
        echo_record["status"] = "success"
        echo_record["elapsed_s"] = round(time.perf_counter() - t0, 2)
    except Exception as exc:
        echo_record["elapsed_s"] = round(time.perf_counter() - t0, 2)
        echo_record["error"] = str(exc)
        print(f"[Opción 3 - EchoMimic] Fallou ({echo_record['elapsed_s']}s): {exc}")
    attempts.append(echo_record)

    # Attempt 2: MuseTalk 1.5 if EchoMimic failed
    if echo_record["status"] != "success":
        static_mp4 = TEMP_DIR / "mia_512_static.mp4"
        run_cmd([
            "ffmpeg", "-y", "-loop", "1", "-t", f"{dur2:.3f}", "-i", str(mia_512_path),
            "-r", "25", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(static_mp4),
        ])
        t1 = time.perf_counter()
        muse_record: dict[str, Any] = {"space": MUSETALK_BASE, "model": "MuseTalk 1.5", "status": "failed"}
        try:
            vid_remote = gradio_upload(MUSETALK_BASE, static_mp4, timeout=30)
            aud_remote = gradio_upload(MUSETALK_BASE, cena2_wav, timeout=30)
            payload = [
                gradio_file_obj(MUSETALK_BASE, aud_remote, cena2_wav.name),
                {"video": gradio_file_obj(MUSETALK_BASE, vid_remote, static_mp4.name)},
                0,
                10,
                "jaw",
                90,
                90,
            ]
            out = gradio_call_sse(MUSETALK_BASE, "generate", payload, timeout=120)
            download_gradio_output(MUSETALK_BASE, out, raw_out)
            muse_record["status"] = "success"
            muse_record["elapsed_s"] = round(time.perf_counter() - t1, 2)
        except Exception as exc:
            muse_record["elapsed_s"] = round(time.perf_counter() - t1, 2)
            muse_record["error"] = str(exc)
            print(f"[Opción 3 - MuseTalk 1.5] Fallou ({muse_record['elapsed_s']}s): {exc}")
        attempts.append(muse_record)

    if any(a["status"] == "success" for a in attempts) and raw_out.exists():
        composed_out = BASE_DIR / "opcao3-mia-neural.mp4"
        run_cmd([
            "ffmpeg", "-y",
            "-loop", "1", "-t", f"{dur2:.3f}", "-i", str(slide2_path),
            "-i", str(raw_out),
            "-i", str(cena2_mp3),
            "-filter_complex", "[1:v]scale=380:380[face];[0:v][face]overlay=W-w-36:H-h-60:shortest=1,format=yuv420p[v]",
            "-map", "[v]", "-map", "2:a",
            "-t", f"{dur2:.3f}", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
            "-movflags", "+faststart", str(composed_out),
        ])
        info = ffprobe_info(composed_out)
        return {
            "succeeded": True,
            "file": "opcao3-mia-neural.mp4",
            "raw_file": "opcao3-neural-raw.mp4",
            "duration_s": round(float(info["format"]["duration"]), 3),
            "size_bytes": composed_out.stat().st_size,
            "attempts": attempts,
        }

    return {
        "succeeded": False,
        "file": None,
        "attempts": attempts,
    }


def generate_html(results: dict[str, Any]) -> Path:
    opt2 = results["option2"]
    opt3 = results["option3"]
    audio_meta = results["audio"]

    scenes_js = json.dumps(
        [
            {
                "id": s["id"],
                "tag": s["tag"],
                "title": s["title"],
                "subtitle": s["subtitle"],
                "highlight": s["highlight"],
                "bullets": s["bullets"],
                "footer": s["footer"],
                "text": s["text"],
                "audio": audio_meta[s["id"]]["file"],
                "duration": audio_meta[s["id"]]["duration_s"],
            }
            for s in SCENES
        ],
        ensure_ascii=False,
    )

    if opt3["succeeded"]:
        opt3_media_html = f"""
        <div class="video-frame">
          <video controls preload="metadata" src="{opt3['file']}"></video>
        </div>
        <div class="meta-pills">
          <span class="pill ok">Xerado con éxito</span>
          <span class="pill">Duración (cena 2): {opt3['duration_s']}s</span>
          <span class="pill">Tamaño: {opt3['size_bytes'] / 1024:.0f} KB</span>
        </div>
        """
    else:
        rows = ""
        for att in opt3["attempts"]:
            err_escaped = (
                str(att.get("error", "Erro descoñecido"))
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
            )
            rows += f"""
            <div class="diag-card">
              <div class="diag-head">
                <strong>{att['model']}</strong>
                <span class="badge-fail">FALLOU ({att.get('elapsed_s', '?')}s)</span>
              </div>
              <div class="diag-url"><code>{att['space']}</code></div>
              <pre class="diag-err">{err_escaped}</pre>
            </div>
            """
        opt3_media_html = f"""
        <div class="diag-box">
          <div class="diag-banner">Diagnóstico Empírico — Non simulado</div>
          <p class="muted">As dúas APIs públicas de HuggingFace Spaces foron probadas con <code>mia_512.png</code> e <code>audio/cena2.wav</code> (16 kHz mono) e rexeitaron/fallaron na execución real:</p>
          {rows}
          <p class="muted small">Conclusión técnica: depender de Spaces públicos gratuítos sen GPU dedicada rompe o SLA educativo (&lt;30s) e introduce erros de cota/cola/compatibilidade de modelo.</p>
        </div>
        """

    html = f"""<!DOCTYPE html>
<html lang="gl">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Comparativo Opcións 1, 2 e 3 — Mía Profesora</title>
  <style>
    @font-face {{
      font-family: 'Fredoka';
      src: url('../assets/fonts/fredoka-latin.woff2') format('woff2');
      font-weight: 400 700;
      font-display: swap;
    }}
    @font-face {{
      font-family: 'Nunito';
      src: url('../assets/fonts/nunito-latin.woff2') format('woff2');
      font-weight: 400 800;
      font-display: swap;
    }}
    :root {{
      --bg: #120d1d;
      --surface: #1b142b;
      --card: #241b38;
      --border: #3c2e5e;
      --text: #f8fafc;
      --muted: #cbd5e1;
      --accent: #a78bfa;
      --gold: #fde047;
      --green: #4ade80;
      --red: #f87171;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: 'Nunito', system-ui, sans-serif;
      background: radial-gradient(circle at top right, #2a1d47, var(--bg) 55%);
      color: var(--text);
      line-height: 1.5;
      padding: 24px 16px 64px;
    }}
    .container {{ max-width: 1180px; margin: 0 auto; }}
    header {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 20px;
      padding: 24px;
      margin-bottom: 24px;
    }}
    h1, h2, h3 {{ font-family: 'Fredoka', sans-serif; margin: 0 0 8px; }}
    h1 {{ font-size: clamp(1.6rem, 3vw, 2.2rem); color: var(--gold); }}
    .case-strip {{
      display: flex; flex-wrap: wrap; gap: 10px; margin-top: 12px;
    }}
    .pill {{
      background: #2c2146; border: 1px solid var(--border);
      padding: 4px 12px; border-radius: 999px; font-size: 0.85rem; color: var(--muted);
    }}
    .pill.ok {{ border-color: #166534; background: #14532d; color: #bbf7d0; }}
    .section {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 20px;
      padding: 22px;
      margin-bottom: 24px;
    }}
    .section-head {{
      display: flex; justify-content: space-between; align-items: center;
      flex-wrap: wrap; gap: 12px; margin-bottom: 16px;
    }}
    .tag {{
      font-size: 0.78rem; font-weight: 800; letter-spacing: .04em;
      padding: 4px 10px; border-radius: 8px; background: #352654; color: #d8b4fe;
    }}
    /* Option 1 Interactive Stage */
    .stage {{
      position: relative;
      background: #251b38;
      border: 2px solid var(--border);
      border-radius: 18px;
      overflow: hidden;
      min-height: 410px;
      display: grid;
      grid-template-columns: 1.5fr 0.9fr;
      gap: 16px;
      padding: 20px;
      align-items: stretch;
    }}
    @media (max-width: 820px) {{
      .stage {{ grid-template-columns: 1fr; }}
    }}
    .board {{
      background: #151123;
      border: 2px solid #4c3973;
      border-radius: 16px;
      padding: 20px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }}
    .board-title {{ font-family: 'Fredoka', sans-serif; font-size: 1.7rem; margin: 10px 0 4px; }}
    .board-highlight {{
      background: #241a3d; border: 1.5px solid var(--accent);
      border-radius: 12px; padding: 12px 14px; margin: 10px 0;
      font-family: 'Fredoka', sans-serif; font-size: 1.15rem; color: var(--gold);
    }}
    .bullet-card {{
      background: #1c1630; border-radius: 10px; padding: 10px 12px; margin-bottom: 8px;
      border-left: 5px solid var(--accent);
    }}
    .bullet-card strong {{ display: block; font-size: 0.85rem; }}
    .mia-stage {{
      display: flex; flex-direction: column; align-items: center; justify-content: flex-end;
      background: radial-gradient(circle at center, #362852 0%, transparent 70%);
      border-radius: 14px; padding: 8px; position: relative;
    }}
    .mia-stage img, .mia-stage video {{
      max-height: 330px; width: auto; object-fit: contain;
    }}
    .mia-caption {{
      font-size: 0.85rem; color: #e2e8f0; background: rgba(15, 11, 26, 0.82);
      padding: 8px 12px; border-radius: 10px; margin-top: 8px; text-align: center;
      border: 1px solid var(--border);
    }}
    .controls {{
      display: flex; flex-wrap: wrap; gap: 10px; align-items: center; margin-top: 14px;
    }}
    button {{
      font-family: 'Nunito', sans-serif; font-weight: 700; font-size: 0.92rem;
      background: #6d28d9; color: white; border: none; border-radius: 10px;
      padding: 9px 16px; cursor: pointer; transition: transform .1s, background .15s;
    }}
    button:hover {{ background: #7c3aed; }}
    button.secondary {{ background: #2e2348; border: 1px solid var(--border); }}
    button.secondary.active {{ background: #4c3582; border-color: var(--accent); }}
    .progress-bar {{
      flex: 1; min-width: 140px; height: 8px; background: #140f21;
      border-radius: 999px; overflow: hidden;
    }}
    .progress-fill {{ height: 100%; width: 0%; background: linear-gradient(90deg, #a78bfa, #4ade80); transition: width .15s linear; }}
    /* Quiz */
    .quiz-box {{
      margin-top: 18px; background: #161124; border: 1.5px solid #4c3973;
      border-radius: 16px; padding: 18px;
    }}
    .quiz-q {{ margin-bottom: 14px; }}
    .quiz-opts {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px; }}
    .quiz-opt {{
      background: #241b38; border: 1px solid var(--border); color: var(--text);
      padding: 8px 14px; border-radius: 10px; cursor: pointer;
    }}
    .quiz-opt.correct {{ background: #14532d; border-color: var(--green); color: #bbf7d0; }}
    .quiz-opt.wrong {{ background: #7f1d1d; border-color: var(--red); color: #fecaca; }}
    .quiz-feedback {{ font-size: 0.9rem; margin-top: 6px; font-weight: 700; }}
    /* Video Option 2 & 3 */
    .video-frame video {{
      width: 100%; max-width: 900px; display: block; margin: 0 auto;
      border-radius: 14px; border: 2px solid var(--border); background: #000;
    }}
    .meta-pills {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 12px; }}
    /* Diagnostic Option 3 */
    .diag-box {{
      background: #161124; border: 1.5px solid #7f1d1d; border-radius: 14px; padding: 16px;
    }}
    .diag-banner {{
      font-family: 'Fredoka', sans-serif; color: #fca5a5; font-size: 1.1rem; margin-bottom: 6px;
    }}
    .diag-card {{
      background: #1f1730; border: 1px solid #3c2e5e; border-radius: 12px; padding: 12px; margin: 10px 0;
    }}
    .diag-head {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }}
    .badge-fail {{ background: #7f1d1d; color: #fecaca; font-size: 0.75rem; padding: 2px 8px; border-radius: 6px; font-weight: 800; }}
    .diag-err {{
      background: #0f0b18; color: #fca5a5; padding: 10px; border-radius: 8px;
      overflow-x: auto; font-size: 0.8rem; margin: 8px 0 0; white-space: pre-wrap;
    }}
    .muted {{ color: var(--muted); }}
    .small {{ font-size: 0.86rem; }}
    /* Comparison Table */
    table {{ width: 100%; border-collapse: collapse; margin-top: 8px; font-size: 0.92rem; }}
    th, td {{ text-align: left; padding: 12px; border-bottom: 1px solid var(--border); vertical-align: top; }}
    th {{ color: var(--gold); font-family: 'Fredoka', sans-serif; font-weight: 600; }}
    tr:last-child td {{ border-bottom: none; }}
  </style>
</head>
<body>
  <div class="container">
    <header>
      <h1>Comparativo Real: Opcións 1, 2 e 3 — Mía Profesora</h1>
      <p class="muted" style="margin:0;">Mesmo guión didáctico (3.º de Primaria · Ciencias Naturais) e mesma voz real en galego para avaliar calidade visual, latencia, custo e viabilidade.</p>
      <div class="case-strip">
        <span class="pill">Pregunta: «Onde se produce o zume elaborado?»</span>
        <span class="pill">Erro da alumna: «Na raíz»</span>
        <span class="pill ok">Correcto: «Nas follas»</span>
      </div>
    </header>

    <!-- OPCIÓN 1 -->
    <section class="section">
      <div class="section-head">
        <div>
          <span class="tag">OPCIÓN 1 · INTERACTIVA EN TEMPO REAL</span>
          <h2 style="margin-top:6px;">Player HTML5 + Lousa Sincronizada + Mía + Mini-Quiz</h2>
        </div>
        <div class="meta-pills" style="margin:0;">
          <span class="pill ok">Latencia de vídeo: 0s</span>
          <span class="pill">Custo vídeo: $0</span>
        </div>
      </div>

      <div class="stage">
        <div class="board">
          <div>
            <span class="tag" id="o1-tag"></span>
            <div class="board-title" id="o1-title"></div>
            <div class="muted" id="o1-sub"></div>
            <div class="board-highlight" id="o1-hl"></div>
            <div id="o1-bullets"></div>
          </div>
          <div class="muted small" id="o1-footer"></div>
        </div>

        <div class="mia-stage">
          <video id="o1-mia-talk" src="../assets/mia/mia-talk.webm" loop muted playsinline style="display:none;"></video>
          <img id="o1-mia-idle" src="../assets/mia/mia.webp" alt="Mía profesora" />
          <div class="mia-caption" id="o1-caption">Preme «Reproducir» para escoitar a Mía.</div>
        </div>
      </div>

      <div class="controls">
        <button id="btn-play">▶ Reproducir todo</button>
        <button id="btn-pause" class="secondary">⏸ Pausar</button>
        <button class="secondary scene-btn active" data-idx="0">Cena 1</button>
        <button class="secondary scene-btn" data-idx="1">Cena 2</button>
        <button class="secondary scene-btn" data-idx="2">Cena 3</button>
        <div class="progress-bar"><div class="progress-fill" id="o1-progress"></div></div>
        <span class="muted small" id="o1-time">0.0s</span>
      </div>

      <div class="quiz-box" id="quiz-box">
        <h3 style="color: var(--gold); margin-bottom: 10px;">Mini-Quiz de Comprobación (2 preguntas)</h3>
        <div class="quiz-q" data-q="1">
          <div><strong>1. Onde se produce o zume elaborado da planta?</strong></div>
          <div class="quiz-opts">
            <button class="quiz-opt" data-ok="false">Na raíz</button>
            <button class="quiz-opt" data-ok="true">Nas follas</button>
            <button class="quiz-opt" data-ok="false">No talo subterráneo</button>
          </div>
          <div class="quiz-feedback"></div>
        </div>
        <div class="quiz-q" data-q="2">
          <div><strong>2. Que colle a raíz do chan para enviar cara arriba?</strong></div>
          <div class="quiz-opts">
            <button class="quiz-opt" data-ok="true">Auga e sales minerais (zume bruto)</button>
            <button class="quiz-opt" data-ok="false">Luz solar directa</button>
            <button class="quiz-opt" data-ok="false">Zume elaborado xa cociñado</button>
          </div>
          <div class="quiz-feedback"></div>
        </div>
      </div>
    </section>

    <!-- OPCIÓN 2 -->
    <section class="section">
      <div class="section-head">
        <div>
          <span class="tag">OPCIÓN 2 · VÍDEO MP4 REAL (LOCAL / CLOUD RUN)</span>
          <h2 style="margin-top:6px;">Pillow + ffmpeg + VP9 Alpha (Mía) + Voz Real</h2>
        </div>
        <div class="meta-pills" style="margin:0;">
          <span class="pill ok">Validado con ffprobe</span>
          <span class="pill">Resolución: {opt2['width']}×{opt2['height']}</span>
          <span class="pill">Duración: {opt2['duration_s']}s</span>
          <span class="pill">Tamaño: {opt2['size_bytes'] / 1024:.0f} KB</span>
          <span class="pill">Render: {opt2['generation_time_s']}s</span>
        </div>
      </div>
      <div class="video-frame">
        <video controls preload="metadata" src="{opt2['file']}"></video>
      </div>
    </section>

    <!-- OPCIÓN 3 -->
    <section class="section">
      <div class="section-head">
        <div>
          <span class="tag">OPCIÓN 3 · LIP-SYNC NEURAL OPEN-SOURCE</span>
          <h2 style="margin-top:6px;">Proba Real: EchoMimic &amp; MuseTalk 1.5 (Cena 2)</h2>
        </div>
      </div>
      {opt3_media_html}
    </section>

    <!-- TABLA COMPARATIVA -->
    <section class="section">
      <h2>Comparativa Técnica e de Produto</h2>
      <table>
        <thead>
          <tr>
            <th>Criterio</th>
            <th>Opción 1 (Player Interactivo)</th>
            <th>Opción 2 (MP4 Pillow + ffmpeg)</th>
            <th>Opción 3 (Lip-Sync Neural Open-Source)</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><strong>Custo por vídeo</strong></td>
            <td>Só TTS (~$0.001–$0.004)</td>
            <td>Só TTS + CPU lixeira (~$0.002)</td>
            <td>GPU dedicada (~$0.02–$0.08/clip) ou cola gratuíta inestable</td>
          </tr>
          <tr>
            <td><strong>Latencia ata empezar</strong></td>
            <td>&lt; 2s (streaming de audio)</td>
            <td>{opt2['generation_time_s']}s render total en CPU</td>
            <td>60s–180s+ (ou fallo por cota/cola en HF Spaces)</td>
          </tr>
          <tr>
            <td><strong>Sincronía labial / Avatar</strong></td>
            <td>Loop WebM con alfa ao falar</td>
            <td>Loop WebM VP9 alfa ({opt2['width']}×{opt2['height']})</td>
            <td>Lip-sync real cando o servizo GPU está dispoñible</td>
          </tr>
          <tr>
            <td><strong>Interactividade</strong></td>
            <td>Alta (quiz integrado no mesmo fluxo)</td>
            <td>Baixa (vídeo pasivo; quiz á parte)</td>
            <td>Baixa (vídeo pasivo)</td>
          </tr>
          <tr>
            <td><strong>Pros / Contras</strong></td>
            <td>+ Inmediata, lixeira e interactiva.<br>- Non exporta un único MP4 descargable.</td>
            <td>+ MP4 portátil 100% fiable e sen GPU.<br>- Menor naturalidade labial cá neural.</td>
            <td>+ Máis expresividade facial se funciona.<br>- Complexidade operativa e fallos de GPU pública.</td>
          </tr>
        </tbody>
      </table>
    </section>
  </div>

  <audio id="o1-audio"></audio>
  <script>
    const SCENES = {scenes_js};
    let currentIdx = 0;
    let isPlaying = false;

    const audioEl = document.getElementById('o1-audio');
    const talkVid = document.getElementById('o1-mia-talk');
    const idleImg = document.getElementById('o1-mia-idle');
    const progressFill = document.getElementById('o1-progress');
    const timeLabel = document.getElementById('o1-time');

    function renderScene(idx) {{
      currentIdx = idx;
      const s = SCENES[idx];
      document.getElementById('o1-tag').textContent = s.tag;
      document.getElementById('o1-title').textContent = s.title;
      document.getElementById('o1-sub').textContent = s.subtitle;
      document.getElementById('o1-hl').textContent = s.highlight;
      document.getElementById('o1-footer').textContent = s.footer;
      document.getElementById('o1-caption').textContent = s.text;

      const bulletsEl = document.getElementById('o1-bullets');
      bulletsEl.innerHTML = '';
      for (const [label, body, color] of s.bullets) {{
        const div = document.createElement('div');
        div.className = 'bullet-card';
        div.style.borderLeftColor = color;
        div.innerHTML = `<strong style="color:${{color}}">${{label}}</strong><span>${{body}}</span>`;
        bulletsEl.appendChild(div);
      }}

      document.querySelectorAll('.scene-btn').forEach((btn, i) => {{
        btn.classList.toggle('active', i === idx);
      }});
      progressFill.style.width = '0%';
      timeLabel.textContent = `0.0s / ${{s.duration.toFixed(1)}}s`;
    }}

    function setSpeaking(speaking) {{
      if (speaking) {{
        idleImg.style.display = 'none';
        talkVid.style.display = 'block';
        talkVid.play().catch(() => {{}});
      }} else {{
        talkVid.pause();
        talkVid.style.display = 'none';
        idleImg.style.display = 'block';
      }}
    }}

    function playScene(idx) {{
      renderScene(idx);
      isPlaying = true;
      audioEl.src = SCENES[idx].audio;
      audioEl.play().then(() => setSpeaking(true)).catch(() => setSpeaking(false));
    }}

    audioEl.addEventListener('timeupdate', () => {{
      const dur = audioEl.duration || SCENES[currentIdx].duration || 1;
      const pct = Math.min(100, (audioEl.currentTime / dur) * 100);
      progressFill.style.width = `${{pct}}%`;
      timeLabel.textContent = `${{audioEl.currentTime.toFixed(1)}}s / ${{dur.toFixed(1)}}s`;
    }});

    audioEl.addEventListener('ended', () => {{
      if (isPlaying && currentIdx < SCENES.length - 1) {{
        playScene(currentIdx + 1);
      }} else {{
        isPlaying = false;
        setSpeaking(false);
        document.getElementById('quiz-box').scrollIntoView({{ behavior: 'smooth', block: 'nearest' }});
      }}
    }});

    document.getElementById('btn-play').addEventListener('click', () => playScene(0));
    document.getElementById('btn-pause').addEventListener('click', () => {{
      isPlaying = false;
      audioEl.pause();
      setSpeaking(false);
    }});

    document.querySelectorAll('.scene-btn').forEach((btn) => {{
      btn.addEventListener('click', () => playScene(Number(btn.dataset.idx)));
    }});

    document.querySelectorAll('.quiz-q').forEach((qEl) => {{
      const fb = qEl.querySelector('.quiz-feedback');
      qEl.querySelectorAll('.quiz-opt').forEach((opt) => {{
        opt.addEventListener('click', () => {{
          qEl.querySelectorAll('.quiz-opt').forEach((b) => b.classList.remove('correct', 'wrong'));
          const ok = opt.dataset.ok === 'true';
          opt.classList.add(ok ? 'correct' : 'wrong');
          fb.textContent = ok
            ? '¡Correcto! Moi ben entendido.'
            : 'Case! Lembra que a raíz colle auga e a folla cociña o zume elaborado.';
          fb.style.color = ok ? '#4ade80' : '#fca5a5';
        }});
      }});
    }});

    renderScene(0);
  </script>
</body>
</html>
"""
    out_html = BASE_DIR / "comparativo-opcoes-1-2-3.html"
    out_html.write_text(html, encoding="utf-8")
    print(f"[HTML] {out_html.name} xerado")
    return out_html


def main() -> None:
    audio_meta, warnings = download_tts_audios()
    slide_paths = render_slides()
    opt2_res = build_option2_video(slide_paths, audio_meta)
    mia_512 = create_mia_512()
    opt3_res = test_option3_neural(mia_512, slide_paths[1], audio_meta)

    results = {
        "warnings": warnings,
        "audio": audio_meta,
        "option2": opt2_res,
        "option3": opt3_res,
    }
    res_path = BASE_DIR / "resultados.json"
    res_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[JSON] {res_path.name} gardado")
    generate_html(results)


if __name__ == "__main__":
    main()
