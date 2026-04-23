import json
import pickle
import shutil
import logging
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

from training.config import (
    TFIDF_MAX_FEATURES, TFIDF_MIN_DF, LOCAL_MODEL_PATH, VECTORIZER_PATH,
    METADATA_PATH, SNAPSHOTS_DIR, USE_SEMANTIC_EMBEDDINGS, SEMANTIC_MODEL_NAME,
)

logger = logging.getLogger(__name__)

_ST_AVAILABLE = False
try:
    from sentence_transformers import SentenceTransformer
    import transformers
    transformers.logging.set_verbosity_error()
    _ST_AVAILABLE = True
except ImportError:
    pass


def normalize_arabic(text: str) -> str:
    import re
    text = re.sub(r'[ؐ-ًؚ-ٰٟـ]', '', text)
    text = re.sub(r'[أإآٱ]', 'ا', text)
    text = text.replace('ؤ', 'و').replace('ئ', 'ي').replace('ى', 'ي')
    text = re.sub(r'[^؀-ۿ\w\s]', ' ', text)
    return re.sub(r'\s+', ' ', text).strip().lower()


class ModelTrainer:
    def __init__(self, training_data: pd.DataFrame):
        self.training_data = training_data
        self.question_embeddings = None

    def train(self):
        logger.info(f"Training on {len(self.training_data)} pairs...")

        self.questions = self.training_data["customer_question"].tolist()
        self.agent_responses = self.training_data["agent_response"].tolist()
        self.categories = self.training_data["category"].tolist()

        normalized = [normalize_arabic(q) for q in self.questions]

        self.vectorizer = TfidfVectorizer(
            max_features=TFIDF_MAX_FEATURES,
            min_df=TFIDF_MIN_DF,
            ngram_range=(1, 3),
            analyzer="char_wb",
            sublinear_tf=True,
            lowercase=True,
        )
        self.question_vectors = self.vectorizer.fit_transform(normalized)
        logger.info(f"TF-IDF features: {self.question_vectors.shape[1]}")

        if USE_SEMANTIC_EMBEDDINGS and _ST_AVAILABLE:
            logger.info(f"Computing semantic embeddings ({SEMANTIC_MODEL_NAME})...")
            st_model = SentenceTransformer(SEMANTIC_MODEL_NAME)
            self.question_embeddings = st_model.encode(
                self.questions, show_progress_bar=True, convert_to_numpy=True
            )
        elif USE_SEMANTIC_EMBEDDINGS:
            logger.warning("sentence-transformers not installed — skipping semantic embeddings.")

    def save(self):
        VECTORIZER_PATH.parent.mkdir(parents=True, exist_ok=True)

        with open(VECTORIZER_PATH, "wb") as f:
            pickle.dump(self.vectorizer, f)

        model_dict = {
            "customer_questions": self.questions,
            "agent_responses": self.agent_responses,
            "categories": self.categories,
            "n_features": self.question_vectors.shape[1],
            "n_samples": len(self.agent_responses),
        }
        if self.question_embeddings is not None:
            model_dict["question_embeddings"] = self.question_embeddings

        with open(LOCAL_MODEL_PATH, "wb") as f:
            pickle.dump(model_dict, f)

        metadata = {
            "n_features": self.question_vectors.shape[1],
            "n_samples": len(self.agent_responses),
            "n_categories": len(set(self.categories)),
            "training_date": pd.Timestamp.now().isoformat(),
            "semantic_embeddings": self.question_embeddings is not None,
        }
        with open(METADATA_PATH, "w") as f:
            json.dump(metadata, f, indent=2)

        self._save_snapshot(model_dict, metadata)
        logger.info(f"Model saved → {LOCAL_MODEL_PATH}")

    def _save_snapshot(self, model_dict: dict, metadata: dict, max_snapshots: int = 5):
        SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        stamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
        snap_dir = SNAPSHOTS_DIR / stamp
        snap_dir.mkdir()

        shutil.copy2(LOCAL_MODEL_PATH, snap_dir / "local_model.pkl")
        shutil.copy2(VECTORIZER_PATH, snap_dir / "vectorizer.pkl")
        with open(snap_dir / "metadata.json", "w") as f:
            json.dump({**metadata, "snapshot_date": stamp}, f, indent=2)

        logger.info(f"Snapshot saved: {stamp}")

        all_snaps = sorted(SNAPSHOTS_DIR.iterdir(), key=lambda p: p.name)
        for old in all_snaps[:-max_snapshots]:
            shutil.rmtree(old)
