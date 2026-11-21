#!/usr/bin/env python3
"""Base de dados do conteudo escolar (Drive "Estudo te" -> SQLite).

Uso:
  python escola_db.py sync     # baixa os scans do Drive para extracao/
  python escola_db.py ocr      # OCR das paginas ainda sem texto (Windows OCR)
  python escola_db.py stats    # resumo do estado
  python escola_db.py export   # exercícios corrigíveis -> ../content/ejercicios-libro.json
"""
import hashlib
import json
import os
import re
import subprocess
import sqlite3
import sys
import tempfile
import urllib.parse
import urllib.request
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(ROOT, "escola.db")
SCHEMA = os.path.join(ROOT, "schema.sql")
EXTRACAO = os.path.join(ROOT, "extracao")
OCR_PS1 = os.path.join(ROOT, "ocr_winrt.ps1")
TOKEN = r"C:\Users\leona\AppData\Local\hermes\google_token.json"
DRIVE_ROOT = "1x82SETDWyx7xqvbVWvkun9yYZ-RDqUfL"
SUBJECTS = {  # nome no Drive -> slug
    "Castellano": "castellano", "Mates": "mates", "Sociais": "sociais",
    "Ingles": "ingles", "Inglês": "ingles", "Galego": "galego",
}
# idioma de OCR por materia: o OCR do Windows e' por idioma de reconhecimento
OCR_LANG = {"castellano": "es-ES", "mates": "es-ES", "sociais": "es-ES",
            "galego": "es-ES", "ingles": "en-GB"}  # gl-ES nao existe no Windows; es-ES le galego
NOW = lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    return con


def init():
    con = db()
    with open(SCHEMA, encoding="utf-8") as fh:
        con.executescript(fh.read())
    con.commit()
    return con


def token():
    with open(TOKEN, encoding="utf-8") as fh:
        return json.load(fh)["access_token"]


def drive_ls(at, query):
    url = ("https://www.googleapis.com/drive/v3/files?q=" + urllib.parse.quote(query)
           + "&fields=files(id,name,mimeType,size)&pageSize=100")
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + at})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)["files"]


def drive_get(at, fid, dest):
    url = "https://www.googleapis.com/drive/v3/files/%s?alt=media" % fid
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + at})
    with urllib.request.urlopen(req, timeout=180) as r, open(dest, "wb") as fh:
        data = r.read()
        fh.write(data)
    return data


def cmd_sync():
    con = init()
    at = token()
    total = 0
    for subj in drive_ls(at, "'%s' in parents and trashed=false" % DRIVE_ROOT):
        slug = SUBJECTS.get(subj["name"])
        if not slug:
            print("skip materia desconhecida:", subj["name"])
            continue
        con.execute("INSERT OR IGNORE INTO subjects(slug,name,drive_id) VALUES(?,?,?)",
                    (slug, subj["name"], subj["id"]))
        con.commit()
        sid = con.execute("SELECT id FROM subjects WHERE slug=?", (slug,)).fetchone()["id"]
        # filhos: pastas (Livro/Caderno) ou imagens soltas (Ingles)
        for child in drive_ls(at, "'%s' in parents and trashed=false" % subj["id"]):
            if child["mimeType"].endswith("folder"):
                origin = child["name"].lower()
                files = drive_ls(at, "'%s' in parents and trashed=false" % child["id"])
            else:
                origin = "solto"
                files = [child]
            for f in files:
                if not re.search(r"\.(jpe?g|png|pdf)$", f["name"], re.I):
                    continue
                dest_dir = os.path.join(EXTRACAO, slug, origin)
                os.makedirs(dest_dir, exist_ok=True)
                dest = os.path.join(dest_dir, f["name"])
                if not os.path.exists(dest) or os.path.getsize(dest) == 0:
                    data = drive_get(at, f["id"], dest)
                else:
                    with open(dest, "rb") as fh:
                        data = fh.read()
                sha = hashlib.sha256(data).hexdigest()
                con.execute(
                    "INSERT OR IGNORE INTO documents(subject_id,origin,drive_id,name,local_path,sha256,bytes,downloaded_at)"
                    " VALUES(?,?,?,?,?,?,?,?)",
                    (sid, origin, f["id"], f["name"], os.path.relpath(dest, ROOT), sha, len(data), NOW()))
                con.commit()
                total += 1
                print("  baixado:", os.path.relpath(dest, ROOT))
    print("sync: %d imagens registadas" % total)


def ocr_image(path, lang):
    """Windows OCR (offline). Devolve (texto, aviso)."""
    ps = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", OCR_PS1, "-Path", path, "-Lang", lang]
    out = subprocess.run(ps, capture_output=True, timeout=180)
    raw = out.stdout or b""
    for enc in ("utf-8", "cp1252"):
        try:
            txt = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        txt = raw.decode("utf-8", "replace")
    txt = txt.replace("\r\n", "\n")
    err = (out.stderr or b"").decode("utf-8", "replace")
    if out.returncode != 0 or txt.startswith("ERRO"):
        return None, (txt.strip() or err.strip())[:200]
    body = txt.split("---\n", 1)[1] if "---\n" in txt else ""
    return body.strip(), None


def cmd_ocr(limit=None):
    con = init()
    rows = con.execute(
        "SELECT d.id, d.local_path, s.slug FROM documents d JOIN subjects s ON s.id=d.subject_id"
        " WHERE d.id NOT IN (SELECT document_id FROM pages JOIN page_text ON page_text.page_id=pages.id)"
        " ORDER BY s.slug, d.origin, d.name").fetchall()
    if limit:
        rows = rows[:limit]
    print("OCR pendente: %d documentos" % len(rows))
    for row in rows:
        path = os.path.join(ROOT, row["local_path"])
        lang = OCR_LANG.get(row["slug"], "es-ES")
        text, warn = ocr_image(path, lang)
        if text is None:
            print("  FALHOU", row["local_path"], "->", warn)
            continue
        page_no = 1
        cur = con.execute("INSERT OR IGNORE INTO pages(document_id,page_no) VALUES(?,?)", (row["id"], page_no))
        pid = con.execute("SELECT id FROM pages WHERE document_id=? AND page_no=?", (row["id"], page_no)).fetchone()["id"]
        con.execute("INSERT OR REPLACE INTO page_text(page_id,lang,engine,text,chars,ocr_at) VALUES(?,?,?,?,?,?)",
                    (pid, lang, "windows-ocr", text, len(text), NOW()))
        con.commit()
        print("  ok  %-45s %5d chars" % (row["local_path"].split("extracao/")[-1], len(text)))


APP_SLUG = {
    "mates": "mat",
    "mat": "mat",
    "castellano": "cast",
    "cast": "cast",
    "galego": "gal",
    "gal": "gal",
    "sociais": "soc",
    "soc": "soc",
    "naturais": "nat",
    "nat": "nat",
    "ingles": "ingles",
}
CONTENT_OUT = os.path.join(ROOT, "..", "..", "content", "ejercicios-libro.json")
TEMA = "do libro 📖"


def cmd_export():
    """Exercicios que o app consegue corrigir -> content/ejercicios-libro.json.

    Suporta: parejas, ordenar, dis (voz), vf, escri e escolha múltipla (opts).
    """
    con = init()
    out = {}
    for r in con.execute(
        "SELECT s.slug, e.kind, e.statement, e.answer, e.options, e.difficulty, e.lang"
        " FROM exercises e JOIN subjects s ON s.id=e.subject_id"
        " WHERE (e.answer IS NOT NULL AND trim(e.answer) <> '')"
        "    OR e.kind IN ('parejas', 'ordenar')"
        " ORDER BY s.slug, e.difficulty, e.id"
    ):
        key = APP_SLUG.get(r["slug"])
        st = (r["statement"] or "").strip()
        ans = (r["answer"] or "").strip()
        kind = (r["kind"] or "").strip().lower()
        if not key or len(st) < 15:
            continue

        raw_opts = None
        if r["options"]:
            try:
                raw_opts = json.loads(r["options"])
            except Exception:
                raw_opts = None

        dif = r["difficulty"] or 1
        is_parejas = kind == "parejas" or (
            isinstance(raw_opts, list)
            and len(raw_opts) >= 2
            and all(isinstance(p, list) and len(p) == 2 for p in raw_opts)
        )
        is_ordenar = (not is_parejas) and (
            kind == "ordenar"
            or (
                isinstance(raw_opts, list)
                and len(raw_opts) >= 3
                and all(not isinstance(x, list) for x in raw_opts)
                and re.search(r"\b(ordena|en orden|en orde|order)\b", st, re.I)
                and (not ans or ans not in [str(o).strip() for o in raw_opts])
            )
        )

        if is_parejas:
            if not isinstance(raw_opts, list):
                continue
            pares = [
                [str(p[0]).strip(), str(p[1]).strip()]
                for p in raw_opts
                if isinstance(p, list) and len(p) == 2 and str(p[0]).strip() and str(p[1]).strip()
            ]
            if len(pares) < 2:
                continue
            item = {
                "q": st,
                "tipo": "parejas",
                "pares": pares,
                "a": ans or "-".join(p[0] for p in pares),
                "tema": TEMA,
                "dif": dif,
            }
        elif is_ordenar:
            if not isinstance(raw_opts, list):
                continue
            pasos = [str(o).strip() for o in raw_opts if str(o).strip()]
            if len(pasos) < 2:
                continue
            item = {
                "q": st,
                "tipo": "ordenar",
                "pasos": pasos,
                "a": ans if (ans and "→" in ans) else " → ".join(pasos),
                "tema": TEMA,
                "dif": dif,
            }
        else:
            if not ans or len(ans) > 60 or not re.search(r"[0-9a-záéíóúñü]", ans, re.I):
                continue
            item = {"q": st, "a": ans, "tema": TEMA, "dif": dif}
            opts = (
                [str(o).strip() for o in raw_opts if str(o).strip()]
                if isinstance(raw_opts, list)
                else []
            )
            vf_sets = ({"verdadero", "falso"}, {"verdadeiro", "falso"}, {"true", "false"})
            is_vf = kind == "vf" or (len(opts) == 2 and {o.lower() for o in opts} in vf_sets)

            if kind in ("voz", "dis"):
                item["tipo"] = "dis"
                item["lang"] = (
                    "en-US"
                    if (key == "ingles" or (r["lang"] or "").lower().startswith("en"))
                    else "es-ES"
                )
            elif is_vf:
                if len(opts) != 2 or ans not in opts:
                    continue
                item["tipo"] = "vf"
                item["opts"] = opts
            elif kind in ("escrita", "escri") or raw_opts is None:
                item["tipo"] = "escri"
            elif len(opts) >= 3 and ans in opts:
                item["opts"] = opts
            else:
                item["tipo"] = "escri"

        out.setdefault(key, []).append(item)

    path = os.path.abspath(CONTENT_OUT)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    print("escrito %s" % path)
    counts = {}
    for k in sorted(out):
        by_t = {}
        for i in out[k]:
            t = i.get("tipo", "opts")
            by_t[t] = by_t.get(t, 0) + 1
            counts[t] = counts.get(t, 0) + 1
        det = ", ".join(f"{t}={by_t[t]}" for t in sorted(by_t))
        print("  %-8s %3d exercicios (%s)" % (k, len(out[k]), det))
    print("  por tipo:", ", ".join(f"{t}={counts[t]}" for t in sorted(counts)))
    print("  total: %d exercicios (de %d na base)" % (
        sum(len(v) for v in out.values()),
        con.execute("SELECT COUNT(*) c FROM exercises").fetchone()["c"]))


def cmd_stats():
    con = init()
    for t in ("subjects", "documents", "pages", "page_text", "exercises"):
        n = con.execute("SELECT COUNT(*) c FROM %s" % t).fetchone()["c"]
        print("%-12s %4d" % (t, n))
    print("\nchars de texto OCR por materia:")
    for r in con.execute("SELECT s.slug, COUNT(pt.page_id) p, SUM(pt.chars) c FROM page_text pt"
                         " JOIN pages p2 ON p2.id=pt.page_id JOIN documents d ON d.id=p2.document_id"
                         " JOIN subjects s ON s.id=d.subject_id GROUP BY s.slug ORDER BY s.slug"):
        print("  %-12s %2d paginas %6d chars" % (r["slug"], r["p"], r["c"] or 0))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "stats"
    if cmd == "sync":
        cmd_sync()
    elif cmd == "ocr":
        cmd_ocr(int(sys.argv[2]) if len(sys.argv) > 2 else None)
    elif cmd == "export":
        cmd_export()
    else:
        cmd_stats()
