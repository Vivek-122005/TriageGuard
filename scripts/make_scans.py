"""Render documents to images and run real Tesseract OCR on them (M1 section 9).

The corpus already contains OCR-style text in test_hard (length-preserving
character confusions, see triageguard/data/noise.py). This script adds the
"real scan" robustness set the M1 plan describes: it renders a sample of
golden test documents as page images, runs the Tesseract CLI on them and
writes the OCR text next to the original labels.

Real OCR changes text length, so character spans no longer line up. The output
keeps document-level labels (type, fields, route) and the original PII
strings; M4 scores PII leakage on this set by searching for each original
identifier (and its digits) in the redacted OCR text.

Needs: Pillow (pip install pillow) and the tesseract binary on PATH.
Usage: .venv/bin/python scripts/make_scans.py [--n 150] [--split test_golden] [--corpus data/corpus]
"""

import argparse
import json
import random
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def render_png(text: str, path: Path, rng: random.Random) -> None:
    from PIL import Image, ImageDraw, ImageFilter, ImageFont

    lines = text.split("\n")
    font = None
    for cand in ("/System/Library/Fonts/Supplemental/Courier New.ttf", "/System/Library/Fonts/Menlo.ttc",
                 "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", "Courier New.ttf"):
        try:
            font = ImageFont.truetype(cand, 22)
            break
        except OSError:
            continue
    font = font or ImageFont.load_default(size=22)
    w, h = 1700, 60 + 30 * len(lines)
    img = Image.new("L", (w, h), 255)
    d = ImageDraw.Draw(img)
    for i, line in enumerate(lines):
        d.text((60, 30 + 30 * i), line, fill=0, font=font)
    # Mild scan degradation: slight rotation, blur and speckle.
    img = img.rotate(rng.uniform(-1.2, 1.2), expand=True, fillcolor=255)
    img = img.filter(ImageFilter.GaussianBlur(rng.uniform(0.3, 0.9)))
    px = img.load()
    for _ in range(w * h // 400):
        px[rng.randrange(img.width), rng.randrange(img.height)] = rng.choice([0, 255])
    img.save(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=150)
    ap.add_argument("--split", default="test_golden")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--corpus", default="data/corpus")
    a = ap.parse_args()
    if not shutil.which("tesseract"):
        sys.exit("tesseract not found on PATH (macOS: brew install tesseract)")

    rng = random.Random(a.seed)
    corpus = ROOT / a.corpus
    docs = [json.loads(l) for l in open(corpus / f"{a.split}.jsonl")]
    docs = rng.sample(docs, min(a.n, len(docs)))
    img_dir = ROOT / "data" / "scans" / corpus.name
    img_dir.mkdir(parents=True, exist_ok=True)
    out = corpus / "real_ocr.jsonl"
    with open(out, "w") as f:
        for d in docs:
            png = img_dir / f"{d['doc_id']}.png"
            render_png(d["text"], png, rng)
            ocr = subprocess.run(["tesseract", str(png), "-", "--psm", "6"], capture_output=True, text=True, check=True).stdout
            row = {k: d[k] for k in ("doc_id", "patient_id", "doc_type", "layout", "fields", "route", "route_signals")}
            row.update({"split": "real_ocr", "source_split": a.split, "text": ocr,
                        "pii_strings": [{"label": s["label"], "text": s["text"]} for s in d["pii"]]})
            f.write(json.dumps(row) + "\n")
    print(f"wrote {len(docs)} OCR documents to {out}")


if __name__ == "__main__":
    main()
