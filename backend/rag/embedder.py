"""
Embedding backend for the RAG pipeline.

Primary: sentence-transformers 'all-MiniLM-L6-v2' (384-dim), as specified
in the architecture. This is what runs in any normal environment with
internet access to huggingface.co.

Fallback: if the MiniLM weights can't be downloaded (this sandbox's
network allowlist blocks huggingface.co — see Phase 3 chat notes), a
TF-IDF + TruncatedSVD embedder trained on the actual corpus text steps in
automatically, projected to the same 384-dim output so the rest of the
pipeline (FAISS index, similarity search) doesn't need to know which
backend produced a vector. This is a resilience fallback, not the
intended default — real deployments should use MiniLM directly.
"""

from __future__ import annotations

import logging
from pathlib import Path

import joblib
import numpy as np

logger = logging.getLogger(__name__)

EMBEDDING_DIM = 384
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

FALLBACK_DIR = Path(__file__).resolve().parent / "index"
FALLBACK_DIR.mkdir(exist_ok=True)
FALLBACK_VECTORIZER_PATH = FALLBACK_DIR / "fallback_tfidf.joblib"
FALLBACK_SVD_PATH = FALLBACK_DIR / "fallback_svd.joblib"


class Embedder:
    def __init__(self):
        self.backend = None  # "minilm" | "tfidf_svd"
        self._model = None
        self._vectorizer = None
        self._svd = None
        self._try_load_minilm()

    def _try_load_minilm(self) -> None:
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(MODEL_NAME)
            self.backend = "minilm"
            logger.info("Embedder: loaded real MiniLM (%s)", MODEL_NAME)
        except Exception as exc:
            logger.warning(
                "Embedder: could not load MiniLM (%s) — falling back to local "
                "TF-IDF+SVD embedder. This is expected in network-restricted "
                "environments; a normal deployment with internet access will "
                "use MiniLM directly. Reason: %s", MODEL_NAME, exc,
            )
            self.backend = "tfidf_svd"

    def fit_fallback(self, corpus_texts: list[str]) -> None:
        """Only relevant for the tfidf_svd backend: fits vocabulary + SVD
        projection on the actual corpus text. Must be called once before
        embed_texts() when running in fallback mode."""
        if self.backend != "tfidf_svd":
            return
        from sklearn.decomposition import TruncatedSVD
        from sklearn.feature_extraction.text import TfidfVectorizer

        self._vectorizer = TfidfVectorizer(max_features=20000, ngram_range=(1, 2), min_df=1)
        tfidf_matrix = self._vectorizer.fit_transform(corpus_texts)
        n_components = min(EMBEDDING_DIM, tfidf_matrix.shape[0] - 1, tfidf_matrix.shape[1] - 1)
        self._svd = TruncatedSVD(n_components=n_components, random_state=42)
        self._svd.fit(tfidf_matrix)
        joblib.dump(self._vectorizer, FALLBACK_VECTORIZER_PATH)
        joblib.dump(self._svd, FALLBACK_SVD_PATH)
        logger.info("Embedder: fitted fallback TF-IDF+SVD on %d documents, %d components",
                     len(corpus_texts), n_components)

    def load_fallback(self) -> bool:
        if FALLBACK_VECTORIZER_PATH.exists() and FALLBACK_SVD_PATH.exists():
            self._vectorizer = joblib.load(FALLBACK_VECTORIZER_PATH)
            self._svd = joblib.load(FALLBACK_SVD_PATH)
            return True
        return False

    def embed_texts(self, texts: list[str], batch_size: int = 32) -> np.ndarray:
        if not texts:
            return np.zeros((0, EMBEDDING_DIM), dtype=np.float32)

        if self.backend == "minilm":
            vectors = self._model.encode(
                texts, batch_size=batch_size, show_progress_bar=False, convert_to_numpy=True
            )
        else:
            if self._vectorizer is None or self._svd is None:
                raise RuntimeError(
                    "Fallback embedder used before fitting — call fit_fallback() "
                    "or load_fallback() first."
                )
            tfidf_matrix = self._vectorizer.transform(texts)
            vectors = self._svd.transform(tfidf_matrix)
            # pad/truncate to a fixed EMBEDDING_DIM so downstream code (FAISS
            # index dimension) is agnostic to which backend produced this
            if vectors.shape[1] < EMBEDDING_DIM:
                pad = np.zeros((vectors.shape[0], EMBEDDING_DIM - vectors.shape[1]), dtype=np.float32)
                vectors = np.hstack([vectors, pad])

        # L2-normalize so FAISS inner-product search behaves as cosine similarity
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return (vectors / norms).astype(np.float32)

    def embed_query(self, text: str) -> np.ndarray:
        return self.embed_texts([text])[0]
