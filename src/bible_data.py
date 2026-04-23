import json
from pathlib import Path
from typing import Dict
from config.settings import DATA_DIR

DATA_PATH = DATA_DIR / 'bible_references.json'

def load_bible_data(path: Path = DATA_PATH) -> Dict:
    """Load Bible reference data from a JSON file and provides access to 
    book information."""
    path = path.resolve()
    if not path.exists():
        raise FileNotFoundError(f"Could not find bible_references.json at {path}")
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)
