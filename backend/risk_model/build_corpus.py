"""
One-time (well, re-runnable) corpus builder: runs the Phase 1 ingestion
pipeline across every PDF in the local dataset, builds feature vectors,
computes weak-supervision risk labels, and writes the result to a CSV
that risk_trainer.py trains on.

Not part of the live request path — this is offline corpus/training-data
preparation, run explicitly via `python3 -m risk_model.build_corpus`.
"""

from __future__ import annotations

import csv
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ingestion.pipeline import extract_document
from risk_model.feature_builder import FEATURE_NAMES, build_feature_vector
from risk_model.risk_labeling import compute_risk_label

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "dprs"
OUTPUT_CSV = Path(__file__).resolve().parent / "corpus_features.csv"

# Corpus-build-time-only cap (see pipeline.extract_document docstring).
# 3 of the 33 files are 100% scanned at 100-200+ pages each; OCR-ing every
# page of every file would take well over an hour for training-data
# construction. Capping still runs real OCR on real pages of every
# document, it just bounds worst-case runtime for this offline step.
MAX_OCR_PAGES_FOR_CORPUS_BUILD = 8


def get_unique_files():
    pdf_files = sorted(DATA_DIR.rglob("*.pdf"))
    # de-dupe filename collisions like "BridgesDPRTemplate (1).pdf"
    seen_names = set()
    unique_files = []
    for f in pdf_files:
        if f.name in seen_names:
            continue
        seen_names.add(f.name)
        unique_files.append(f)
    return unique_files


def build_corpus(start: int = 0, end: int | None = None):
    """Processes files[start:end] and APPENDS to OUTPUT_CSV (writing the
    header only if the file doesn't exist yet). Run in batches — see
    run_corpus_batches.sh — so each invocation finishes within a bounded
    time window regardless of how OCR-heavy a given batch is."""
    unique_files = get_unique_files()
    batch = unique_files[start:end]
    already_done = set()
    file_exists = OUTPUT_CSV.exists()
    if file_exists:
        with open(OUTPUT_CSV, newline="") as f:
            already_done = {row["filename"] for row in csv.DictReader(f)}

    fieldnames = ["filename", "risk_score", "risk_bucket"] + FEATURE_NAMES
    with open(OUTPUT_CSV, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()

        for i, pdf_path in enumerate(batch, start + 1):
            if pdf_path.name in already_done:
                print(f"[{i}/{len(unique_files)}] {pdf_path.name} ... SKIP (already done)", flush=True)
                continue
            t0 = time.time()
            print(f"[{i}/{len(unique_files)}] {pdf_path.name} ...", flush=True)
            try:
                doc = extract_document(str(pdf_path), max_ocr_pages=MAX_OCR_PAGES_FOR_CORPUS_BUILD)
                features = build_feature_vector(doc)
                risk_score, bucket = compute_risk_label(doc, features)

                row = {"filename": pdf_path.name, "risk_score": round(risk_score, 2), "risk_bucket": bucket.value}
                row.update({k: features[k] for k in FEATURE_NAMES})
                writer.writerow(row)
                f.flush()
                print(f"    OK  sections={len(doc.sections)} risk={risk_score:.1f} ({bucket.value})  "
                      f"[{time.time()-t0:.1f}s]", flush=True)
            except Exception as exc:
                print(f"    FAILED: {exc}", flush=True)

    print(f"\nBatch [{start}:{end}] done. Total files: {len(unique_files)}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--end", type=int, default=None)
    args = parser.parse_args()
    build_corpus(args.start, args.end)
