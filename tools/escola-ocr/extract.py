#!/usr/bin/env python3
"""Converte o texto OCR (ja classificado) em exercicios estruturados.

Opcao A: um passe de modelo barato por pagina -- reconstroi o enunciado
impresso e devolve JSON. As respostas ficam NULL (caligrafia nao e fonte
fiavel). Guarda sempre o texto OCR cru e o JSON original em page_extract,
para auditoria: nada e dado como certo sem rasto.

Uso:  python extract.py [limite]     (sem limite = todas as paginas pendentes)
      python extract.py stats
"""
import json
import os
import re
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(ROOT, "escola.db")
# Chave: variável de ambiente primeiro; senão o .env do Hermes desta máquina.
ENV = os.environ.get("ESCOLA_OCR_ENV") or os.path.join(
    os.path.expanduser("~"), "AppData", "Local", "hermes", ".env")

MODELS = ["deepseek/deepseek-v4-flash-0731"]   # free Gemma em 429 persistente; pago autorizado (18/11)   # free primeiro, pago como ultimo recurso (autorizado nov. 2026)
MAX_CHARS = 7000          # ~2k tokens de OCR; as paginas tem <=3.3k chars
TIMEOUT = 180
TRIES = 2

LANGS = {"ingles": "en-GB"}

SCHEMA = """
CREATE TABLE IF NOT EXISTS page_extract (
  page_id     INTEGER PRIMARY KEY REFERENCES pages(id),
  model       TEXT NOT NULL,
  corrected   TEXT,
  raw         TEXT,
  n_exercises INTEGER NOT NULL DEFAULT 0,
  created_at  TEXT NOT NULL
);
"""

PROMPT = """Eres profesor y corriges texto OCR de una pagina escolar escaneada.

Materia: {subject}   Tipo de pagina: {origin}   Calidad: {cls}

TEXTO OCR (puede tener errores: letras cambiadas, acentos perdidos, respuestas
manuscritas mezcladas con el enunciado impreso):

---
{ocr}
---

Tareas:
1. Reconstruye SOLO el texto impreso, corrigiendo errores OCR obvios. Usa el
   contexto del castellano/galego/ingles para arreglar palabras. No inventes
   contenido que no este en la pagina.
2. Divide el contenido en ejercicios individuales (los enunciados que el alumno
   tendria que responder). Ignora indices, titulos de tema y numeros de pagina.
3. Si un enunciado es ilegible o no existe, no lo inventes: omitelo. Mejor cero
   ejercicios que uno inventado.

Devuelve SOLO este JSON:
{{"texto_corregido": "...", "ejercicios": [{{"enunciado": "...", "tipo": "escolha_multipla|resposta_curta|calculo|aberta", "opciones": [], "topic": "...", "unit": "..."}}]}}

Si no hay ejercicios, "ejercicios": []."""


def api_key():
    key = os.environ.get("OPENROUTER_API_KEY")
    if key:
        return key.strip().strip('"').strip("'")
    with open(ENV, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            m = re.match(r"\s*OPENROUTER_API_KEY\s*=\s*(.+)", line)
            if m:
                return m.group(1).strip().strip('"').strip("'")
    raise SystemExit("OPENROUTER_API_KEY ausente em " + ENV)


def call(model, prompt, key):
    body = json.dumps({
        "model": model,
        "temperature": 0.1,
        "max_tokens": 6000,
        "response_format": {"type": "json_object"},
        "messages": [{"role": "user", "content": prompt}],
    }).encode()
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions", data=body,
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json",
                 "HTTP-Referer": "https://localhost/escola-ocr", "X-Title": "escola-ocr"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        data = json.load(r)
    if "error" in data:
        raise RuntimeError(str(data["error"])[:200])
    
    # DIAGNOSTICO: imprimir finish_reason e usage
    choice = data["choices"][0]
    content = choice["message"]["content"]
    finish_reason = choice.get("finish_reason", "unknown")
    usage = data.get("usage", {})
    print("  API response info:")
    print("    finish_reason: %s" % finish_reason)
    print("    usage: %s" % json.dumps(usage, indent=4))
    print("    content length: %d chars" % len(content))
    
    return content


def parse_json(text):
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-z]*\n?|\n?```$", "", text).strip()
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < 0:
        raise ValueError("sem JSON na resposta")
    return json.loads(text[start:end + 1])


def ensure(con):
    con.executescript(SCHEMA)
    con.commit()


def pending(con, limit=None):
    sql = """
    SELECT p.id, s.slug, d.origin, COALESCE(d.page_class,'impressa'), pt.text
    FROM pages p
    JOIN documents d ON d.id = p.document_id
    JOIN subjects s ON s.id = d.subject_id
    JOIN page_text pt ON pt.page_id = p.id
    LEFT JOIN page_extract pe ON pe.page_id = p.id
    WHERE d.usable = 1 AND pe.page_id IS NULL AND length(trim(pt.text)) > 40
    ORDER BY s.slug, p.id
    """
    if limit:
        sql += " LIMIT %d" % int(limit)
    return con.execute(sql).fetchall()


def run(limit=None):
    key = api_key()
    con = sqlite3.connect(DB)
    ensure(con)
    rows = pending(con, limit)
    print("paginas pendentes: %d" % len(rows))
    ok = err = total_ex = 0
    for pid, slug, origin, cls, ocr in rows:
        prompt = PROMPT.format(subject=slug, origin=origin, cls=cls, ocr=ocr[:MAX_CHARS])
        data, used = None, None
        for model in MODELS:
            for attempt in range(1, TRIES + 1):
                try:
                    data = parse_json(call(model, prompt, key))
                    used = model
                    break
                except Exception as exc:      # rede, rate limit, JSON invalido
                    print("  ! p%s %s tent.%d: %s" % (pid, model.split("/")[-1], attempt, str(exc)[:110]))
                    time.sleep(3 * attempt)
            if data:
                break
        if not data:
            err += 1
            continue
        exs = data.get("ejercicios") or []
        lang = LANGS.get(slug, "es-ES")
        now = datetime.now().isoformat(timespec="seconds")
        con.execute("DELETE FROM exercises WHERE page_id=?", (pid,))
        for ex in exs:
            st = (ex.get("enunciado") or "").strip()
            if len(st) < 8:
                continue
            opts = ex.get("opciones") or []
            con.execute(
                "INSERT INTO exercises (subject_id, page_id, unit, topic, kind, statement, answer,"
                " options, difficulty, lang, source, created_at)"
                " VALUES ((SELECT subject_id FROM documents d JOIN pages p ON p.document_id=d.id"
                " WHERE p.id=?), ?, ?, ?, ?, ?, NULL, ?, 1, ?, 'ocr+llm', ?)",
                (pid, pid, ex.get("unit"), ex.get("topic"), ex.get("tipo") or "aberta", st,
                 json.dumps(opts, ensure_ascii=False) if opts else None, lang, now))
        con.execute("INSERT OR REPLACE INTO page_extract (page_id, model, corrected, raw, n_exercises, created_at)"
                    " VALUES (?,?,?,?,?,?)",
                    (pid, used, data.get("texto_corregido"), json.dumps(data, ensure_ascii=False),
                     len(exs), now))
        con.commit()
        ok += 1
        total_ex += len(exs)
        print("  + p%-2d %-10s %-7s %d exercicios" % (pid, slug, origin, len(exs)))
    print("feito: %d paginas, %d exercicios, %d falhas" % (ok, total_ex, err))


def stats():
    con = sqlite3.connect(DB)
    ensure(con)
    print("paginas extraidas: %d de %d uteis" % (
        con.execute("SELECT COUNT(*) FROM page_extract").fetchone()[0],
        con.execute("SELECT COUNT(*) FROM documents WHERE usable=1").fetchone()[0]))
    print("exercicios: %d" % con.execute("SELECT COUNT(*) FROM exercises").fetchone()[0])
    for r in con.execute("""SELECT s.slug, COUNT(e.id) FROM subjects s
        LEFT JOIN exercises e ON e.subject_id=s.id GROUP BY s.slug ORDER BY 2 DESC"""):
        print("  %-11s %3d" % r)


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    if arg == "stats":
        stats()
    else:
        run(int(arg) if arg.isdigit() else None)
