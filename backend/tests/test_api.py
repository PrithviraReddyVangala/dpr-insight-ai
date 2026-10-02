"""
Phase 4 validation: exercises the full API in-process via FastAPI's
TestClient (no real network server needed) — upload -> poll status ->
fetch document detail -> fetch risk -> attempt chat (expected to fail
gracefully with no GEMINI_API_KEY in this sandbox).
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from api.main import app

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "dprs" / "DPR_dataset"
TEST_FILE = DATA_DIR / "BridgesDPRTemplate.pdf"


def run():
    client = TestClient(app)

    print("=== health ===")
    r = client.get("/api/health")
    print(r.status_code, r.json())

    print("\n=== upload ===")
    with open(TEST_FILE, "rb") as f:
        r = client.post("/api/documents/upload", files={"file": ("BridgesDPRTemplate.pdf", f, "application/pdf")})
    print(r.status_code, r.json())
    doc_id = r.json()["id"]

    print("\n=== poll status ===")
    for i in range(60):
        r = client.get(f"/api/documents/{doc_id}/status")
        data = r.json()
        print(f"  [{i}] status={data['status']} stage={data['progress_stage']} "
              f"pct={data['progress_pct']:.0f} msg={data['progress_message']}")
        if data["status"] in ("ready", "failed"):
            break
        time.sleep(0.5)

    if data["status"] == "failed":
        print("FAILED:", data["error_message"])
        return

    print("\n=== document detail ===")
    r = client.get(f"/api/documents/{doc_id}")
    detail = r.json()
    print(f"status={r.status_code} pages={detail['page_count']} sections={len(detail['sections'])} "
          f"risk_score={detail['risk_score']} risk_bucket={detail['risk_bucket']}")
    for s in detail["sections"][:3]:
        print(f"  - [{s['category']}] {s['heading_text'][:50]} ({s['char_count']} chars)")

    print("\n=== risk detail ===")
    r = client.get(f"/api/documents/{doc_id}/risk")
    risk = r.json()
    print(f"status={r.status_code} score={risk['risk_score']} bucket={risk['risk_bucket']}")
    print("top contributions:")
    for c in risk["top_contributions"][:5]:
        print(f"    {c['feature']:28s} value={c['value']:.3f} shap={c['shap_contribution']:+.2f}")

    print("\n=== chat (expected to fail gracefully: no GEMINI_API_KEY in this sandbox) ===")
    r = client.post(f"/api/documents/{doc_id}/chat", json={"query": "What is the scope of this project?"})
    print(f"status={r.status_code}")
    print(r.json())

    print("\n=== list documents ===")
    r = client.get("/api/documents")
    print(f"status={r.status_code} count={len(r.json())}")

    print("\n=== delete ===")
    r = client.delete(f"/api/documents/{doc_id}")
    print(r.status_code, r.json())


if __name__ == "__main__":
    run()
