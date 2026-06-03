import json
from pathlib import Path
from typing import Dict, List
from core.config import DATA_DIR

DATA_PATH = DATA_DIR / 'bible_references.json'

def load_bible_data(path: Path = DATA_PATH) -> Dict:
    """Load Bible reference data from a JSON file and provides access to 
    book information."""
    path = path.resolve()
    if not path.exists():
        raise FileNotFoundError(f"Could not find bible_references.json at {path}")
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def build_book_lookup(bible_books: Dict[str, Dict]):
    """Index books by canonical names."""
    return {b['name']: b for b in bible_books} if bible_books else {}

def build_sorted_books(book_lookup: Dict[str, Dict]) -> List[Dict]:
    """Return books sorted by canonical id for cross-book range traversal."""
    return sorted(book_lookup.values(), key=lambda b: b['id'])
