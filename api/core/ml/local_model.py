import pickle
import logging
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path

import numpy as np
from rank_bm25 import BM25Okapi
from sklearn.metrics.pairwise import cosine_similarity

from core.ml.arabic_normalizer import normalize_arabic

logger = logging.getLogger(__name__)

_ST_AVAILABLE = False
try:
    from sentence_transformers import SentenceTransformer
    import transformers
    transformers.logging.set_verbosity_error()
    _ST_AVAILABLE = True
except ImportError:
    pass

# Default hybrid scoring weights
_TFIDF_W = 0.5
_BM25_W = 0.5
_SEM_TFIDF_W = 0.3
_SEM_BM25_W = 0.2
_SEM_W = 0.5


class LocalModelService:
    def __init__(
        self,
        model_path: Path,
        vectorizer_path: Path,
        use_semantic: bool = False,
        semantic_model_name: str = "paraphrase-multilingual-MiniLM-L12-v2",
    ):
        self.model_path = model_path
        self.vectorizer_path = vectorizer_path
        self.use_semantic = use_semantic
        self.semantic_model_name = semantic_model_name
        self.st_model = None
        self.question_embeddings = None
        self._load()

    def _load(self):
        with open(self.vectorizer_path, "rb") as f:
            self.vectorizer = pickle.load(f)

        with open(self.model_path, "rb") as f:
            model = pickle.load(f)

        self.customer_questions = model.get("customer_questions", model["agent_responses"])
        self.agent_responses = model["agent_responses"]
        self.categories = model["categories"]

        normalized = [normalize_arabic(q) for q in self.customer_questions]
        self.question_vectors = self.vectorizer.transform(normalized)
        self.bm25 = BM25Okapi([q.split() for q in normalized])
        self._normalized_questions = normalized

        self.question_embeddings = model.get("question_embeddings")
        if self.use_semantic and _ST_AVAILABLE:
            if self.question_embeddings is not None:
                self.st_model = SentenceTransformer(self.semantic_model_name)
                logger.info("Semantic scoring enabled.")
            else:
                logger.warning("use_semantic=True but model has no embeddings — run training first.")
        elif self.use_semantic and not _ST_AVAILABLE:
            logger.warning("use_semantic=True but sentence-transformers not installed.")

        logger.info(f"ML model loaded: {model['n_samples']} training samples")

    def _fuzzy_fallback(self, normalized_q: str) -> tuple[int, float]:
        best_idx, best_ratio = 0, 0.0
        for i, tq in enumerate(self._normalized_questions):
            r = SequenceMatcher(None, normalized_q, tq).ratio()
            if r > best_ratio:
                best_ratio = r
                best_idx = i
        return best_idx, best_ratio

    @lru_cache(maxsize=512)
    def generate(self, question: str, threshold: float = 0.70) -> dict:
        normalized_q = normalize_arabic(question)

        q_vector = self.vectorizer.transform([normalized_q])
        tfidf_scores = cosine_similarity(q_vector, self.question_vectors)[0]

        tokens = normalized_q.split() or [""]
        bm25_raw = self.bm25.get_scores(tokens)
        bm25_max = bm25_raw.max()
        bm25_norm = bm25_raw / (bm25_max + 1e-10) if bm25_max > 0 else np.zeros_like(bm25_raw)

        if self.st_model is not None and self.question_embeddings is not None:
            q_emb = self.st_model.encode([question], convert_to_numpy=True)
            sem_scores = cosine_similarity(q_emb, self.question_embeddings)[0]
            total = _SEM_TFIDF_W + _SEM_BM25_W + _SEM_W
            final_scores = (
                (_SEM_TFIDF_W / total) * tfidf_scores
                + (_SEM_BM25_W / total) * bm25_norm
                + (_SEM_W / total) * sem_scores
            )
        else:
            total = _TFIDF_W + _BM25_W
            final_scores = (
                (_TFIDF_W / total) * tfidf_scores
                + (_BM25_W / total) * bm25_norm
            )

        best_idx = int(np.argmax(final_scores))
        confidence = float(final_scores[best_idx])

        if confidence < threshold and self.st_model is None:
            fuzz_idx, fuzz_ratio = self._fuzzy_fallback(normalized_q)
            if fuzz_ratio >= 0.68 and fuzz_ratio > confidence:
                best_idx = fuzz_idx
                confidence = fuzz_ratio * 0.85

        response = self.agent_responses[best_idx] if confidence >= threshold else ""
        category = self.categories[best_idx] if confidence >= threshold else "Unknown"

        return {
            "response": response,
            "confidence": confidence,
            "category": category,
            "source": "local_model",
        }
