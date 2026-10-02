"""
Phase 2 validation: run full ingestion -> feature building -> trained
model -> SHAP explanation on several different real DPRs and show the
risk scores and top contributing factors are genuinely document-specific,
not static/templated output.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ingestion.pipeline import extract_document
from risk_model.predictor import assess_document

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "dprs" / "DPR_dataset"

SAMPLE_FILES = [
    "BridgesDPRTemplate.pdf",
    "DPR-West-Bengal.pdf",
    "DPR_Format.pdf",
    "Aonla_DPR.pdf",
    "Swargate-Katraj DPR.pdf",
]


def run():
    for filename in SAMPLE_FILES:
        path = DATA_DIR / filename
        if not path.exists():
            print(f"SKIP (not found): {filename}")
            continue

        doc = extract_document(str(path), max_ocr_pages=8)
        assessment = assess_document(doc)

        print("=" * 90)
        print(f"FILE: {filename}")
        print(f"risk_score={assessment.risk_score}  bucket={assessment.risk_bucket}  "
              f"probs={assessment.bucket_probabilities}")
        print("top contributing factors (feature, value, SHAP push on score):")
        for c in assessment.top_contributions[:6]:
            direction = "+" if c.shap_contribution >= 0 else ""
            print(f"    {c.feature:28s} value={c.value:8.3f}  shap={direction}{c.shap_contribution:.2f}")
        print()


if __name__ == "__main__":
    run()
