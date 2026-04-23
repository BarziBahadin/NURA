import os
from pathlib import Path

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR.parent / "models"  # maps to /app/ml_models inside Docker

TRAINING_CSV = DATA_DIR / "training_pairs.csv"
ARTICLES_JSON = BASE_DIR.parent / ".manafest" / "articals.json"

LOCAL_MODEL_PATH = MODELS_DIR / "local_model.pkl"
VECTORIZER_PATH = MODELS_DIR / "vectorizer.pkl"
METADATA_PATH = MODELS_DIR / "metadata.json"
SNAPSHOTS_DIR = MODELS_DIR / "snapshots"

EXCLUDED_CATEGORIES = {"PUK"}
PUK_KEYWORDS = ["puk", "pin lock", "sim lock", "رمز puk", "رمز البوك"]

MIN_CONFIDENCE_LOCAL = float(os.getenv("ML_CONFIDENCE_THRESHOLD", "0.70"))

TFIDF_MAX_FEATURES = 500
TFIDF_MIN_DF = 1
TFIDF_WEIGHT = 0.5
BM25_WEIGHT = 0.5

USE_SEMANTIC_EMBEDDINGS = os.getenv("USE_SEMANTIC_EMBEDDINGS", "False") == "True"
SEMANTIC_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
SEM_TFIDF_WEIGHT = 0.3
SEM_BM25_WEIGHT = 0.2
SEM_WEIGHT = 0.5
