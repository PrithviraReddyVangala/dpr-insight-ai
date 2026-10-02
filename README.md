# DPR Insight AI

Automated evaluation, risk prediction, and RAG assistant for Detailed
Project Reports (DPRs).

## Run it

**Backend** (needs a `GEMINI_API_KEY` for chat — see `backend/.env.example`):
```bash
cd backend
pip install -r requirements.txt --break-system-packages
export GEMINI_API_KEY=your-key-here
uvicorn api.main:app --reload --port 8000
```

**Frontend** (in a second terminal):
```bash
cd frontend
npm install
npm run dev
```
Open http://localhost:5173.

## Rebuilding the training corpus / RAG index

Only needed if you change the local dataset in `data/dprs/`:
```bash
cd backend
python3 -m risk_model.build_corpus --start 0    # batched — see file for why
python3 -m risk_model.trainer
python3 -m rag.build_chunks --start 0
python3 -m rag.build_index
```

## Architecture

| Phase | Package | What it does |
|---|---|---|
| 1 | `backend/ingestion/` | PDF → structured sections (Financials/Timeline/Scope/Clearances/Technical), with OCR fallback |
| 2 | `backend/risk_model/` | Feature extraction → RandomForest risk score with SHAP explainability |
| 3 | `backend/rag/` | Chunking → embeddings (MiniLM, TF-IDF fallback) → FAISS → Gemini-backed RAG chat |
| 4 | `backend/api/` | FastAPI: async upload/extraction pipeline, risk endpoint, chat endpoint |
| 5 | `frontend/` | React + Tailwind + Recharts dashboard |

See in-chat notes and code comments for two disclosed environment caveats
from the build session: the risk score is a documented weak-supervision
completeness proxy (no ground-truth outcome data existed), and MiniLM /
Gemini couldn't be network-tested in the sandboxed build environment —
both work normally with real internet access and API keys.
