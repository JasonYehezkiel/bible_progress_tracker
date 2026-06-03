from dotenv import load_dotenv
import os
from pathlib import Path

load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[3]

# --- Environment --- #
ENV = os.getenv('ENV', 'development')
LOG_LEVEL = os.getenv('LOG_LEVEL', 'DEBUG')

# --- Paths --- #
DATA_DIR = BASE_DIR / 'data'
LOG_DIR = BASE_DIR /  'logs'
MODEL_DIR = BASE_DIR / 'models'
PROCESSED_DIR = DATA_DIR / 'processed'
READING_PLAN_PATH = DATA_DIR / 'reading_plan.csv'

def resolve(env_var: str, default: Path) -> Path:
    """Helper function to resolve a path from an environment variable"""
    raw = os.getenv(env_var)
    if not raw:
        return default
    p = Path(raw)
    return (BASE_DIR / p).resolve() if not p.is_absolute() else p

CONFIG_PATH = resolve('CONFIG_PATH', BASE_DIR / 'config/indobert_config.json')
CLS_MODEL_PATH = resolve('CLS_MODEL_PATH', BASE_DIR / 'models/random_forest_model.joblib')
CLS_VECTORIZER_PATH = resolve('CLS_VECTORIZER_PATH', BASE_DIR / 'models/tfidf_vectorizer.joblib')
MODEL_PATH = resolve('MODEL_SAVED_PATH', BASE_DIR / 'models/indobert-bible-ner-v4')
DATABASE_PATH = resolve('DATABASE_PATH', BASE_DIR / 'data/bible_progress.db')

# --- Model --- #
AGGREGATION_STRATEGY = 'simple'
BATCH_SIZE = 32
FUZZY_THRESHOLD = 65
W_BIGRAM_JACCARD = 0.60
W_JARO_WINKLER = 0.40