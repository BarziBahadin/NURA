import os
from pathlib import Path

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR.parent / "models"  # maps to /app/ml_models inside Docker

TRAINING_CSV = DATA_DIR / "training_pairs.csv"
MANUAL_TRAINING_CSV = DATA_DIR / "manual_training_pairs.csv"
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


def _load_dotenv() -> dict[str, str]:
    env_path = BASE_DIR.parent / ".env"
    values: dict[str, str] = {}
    if not env_path.exists():
        return values
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


_DOTENV = _load_dotenv()


def env_value(key: str, default: str = "") -> str:
    return os.getenv(key) or _DOTENV.get(key) or default


POSTGRES_HOST = env_value("POSTGRES_HOST", "localhost")
if POSTGRES_HOST == "postgres":
    POSTGRES_HOST = "localhost"
POSTGRES_PORT = int(env_value("POSTGRES_PORT", "5432"))
POSTGRES_DB = env_value("POSTGRES_DB", "nura_db")
POSTGRES_USER = env_value("POSTGRES_USER", "nura_user")
POSTGRES_PASSWORD = env_value("POSTGRES_PASSWORD")
INCLUDE_APPROVED_GAPS = env_value("TRAINING_INCLUDE_APPROVED_GAPS", "true").lower() in {"1", "true", "yes", "on"}
