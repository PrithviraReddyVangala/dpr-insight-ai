"""
Phase 1 validation: run the ingestion pipeline against real DPRs from the
local dataset and report what was actually extracted. Not a mocked unit
test — this is a smoke test against the real corpus to verify the
extraction is producing meaningful, document-specific structure.
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ingestion import extract_document, SectionCategory

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "dprs" / "DPR_dataset"

SAMPLE_FILES = [
    "BridgesDPRTemplate.pdf",
    "DPR4.pdf",
    "DPR-West-Bengal.pdf",
    "Carnation_DPR.pdf",
]


def run():
    for filename in SAMPLE_FILES:
        path = DATA_DIR / filename
        if not path.exists():
            print(f"SKIP (not found): {filename}")
            continue

        print("=" * 90)
        print(f"FILE: {filename}")
        t0 = time.time()
        doc = extract_document(str(path))
        elapsed = time.time() - t0

        print(f"pages={doc.page_count}  body_font_size={doc.body_font_size}  "
              f"scanned_pages={doc.scanned_page_count}  sections={len(doc.sections)}  "
              f"time={elapsed:.1f}s")
        if doc.extraction_warnings:
            print("warnings:", doc.extraction_warnings)

        by_cat = {}
        for s in doc.sections:
            by_cat.setdefault(s.category, []).append(s)

        for category in SectionCategory:
            secs = by_cat.get(category, [])
            if not secs:
                continue
            total_chars = sum(s.char_count for s in secs)
            print(f"  [{category.value:12s}] {len(secs)} section(s), {total_chars} chars total")
            for s in secs[:3]:
                preview = s.text[:90].replace("\n", " ")
                print(f"      - \"{s.heading_text[:60]}\" (p{s.page_start+1}-{s.page_end+1}): {preview}...")
        print()


if __name__ == "__main__":
    run()
