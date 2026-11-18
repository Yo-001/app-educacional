#!/usr/bin/env python3
"""Gera folhas de contacto numeradas (1 por materia) para classificar
rapidamente quais paginas sao impressas (uteis) e quais sao manuscritas."""
import os
import sqlite3
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "state", "contact")
THUMB = 300
COLS = 5


def font(size):
    for name in ("arial.ttf", "segoeui.ttf", "calibri.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def main():
    os.makedirs(OUT, exist_ok=True)
    con = sqlite3.connect(os.path.join(ROOT, "escola.db"))
    rows = con.execute(
        "SELECT s.slug, d.id, d.local_path, d.origin FROM documents d"
        " JOIN subjects s ON s.id=d.subject_id ORDER BY s.slug, d.origin, d.name").fetchall()
    by_subj = {}
    for slug, did, path, origin in rows:
        by_subj.setdefault(slug, []).append((did, path, origin))

    f = font(40)
    for slug, items in by_subj.items():
        n = len(items)
        cols = min(COLS, n)
        rowsn = (n + cols - 1) // cols
        sheet = Image.new("RGB", (cols * THUMB, rowsn * THUMB), "white")
        d = ImageDraw.Draw(sheet)
        for i, (did, path, origin) in enumerate(items):
            img = Image.open(os.path.join(ROOT, path)).convert("RGB")
            img.thumbnail((THUMB - 8, THUMB - 8))
            x = (i % cols) * THUMB + 4
            y = (i // cols) * THUMB + 4
            sheet.paste(img, (x, y))
            label = "#%d %s" % (did, origin[:4])
            d.rectangle([x, y, x + 120, y + 34], fill="black")
            d.text((x + 4, y + 2), label, fill="yellow", font=f)
        dest = os.path.join(OUT, "%s.jpg" % slug)
        sheet.save(dest, quality=72)
        print("%-11s %2d paginas -> %s" % (slug, n, dest.replace(ROOT + os.sep, "")))


if __name__ == "__main__":
    main()
