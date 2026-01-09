import re
import json
from pathlib import Path
from typing import Dict, List, Optional
from src.preprocessing.resolution.book_resolver import BookResolver
from src.preprocessing.bible_reference_validator import BibleReferenceValidator

class BibleReferenceNormalizer:
    """
    
    """

    def __init__(self, json_path: Optional[str] = None):

        # Load bible data automatically
        if json_path is None:
            json_path = self.find_bible_json()

        self.bible_data = self.load_bible_data(json_path)
        self.books = self.bible_data['books']

        self.resolver = BookResolver(self.books, use_fuzzy=True)
        self.validator = BibleReferenceValidator()
        

    def find_bible_json(self) -> str:
        path = Path(__file__).parents[3] / 'data'/ 'bible_references.json'
        path = path.resolve()

        if not path.exists():
            raise FileNotFoundError(
                f"could not find bible_references.json at {path}"
            )
        
        return str(path)

    def load_bible_data(self, json_path: str) -> Dict:
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def normalize(self, candidates: list[Dict]) -> List[Dict]:

        normalized = []

        for ref in candidates:
                book_data, _ = self.resolver.resolve(ref["book_text"])

                if not book_data:
                    continue

                start_ch, end_ch = ref["start_chapter"], ref["end_chapter"]

                is_valid = self.validator.validate_chapters(
                    book_data, start_ch, end_ch
                )
                
                normalized.append({
                    'book': book_data["name"],
                    'book_id': book_data["id"],
                    'testament': book_data["testament"],
                    'start_chapter': start_ch,
                    'end_chapter': end_ch,
                    'chapters': list(range(start_ch, end_ch + 1)),
                    'raw_text': ref["book_text"],
                    'normalized_text': f"{book_data['name']} {start_ch}-{end_ch}",
                    'is_valid': is_valid,
                    'confidence': ref.get('confidence', 1.0),
                    'source': ref.get('source', 'rule')
                })
                    
        return normalized
    
    def get_stats(self) -> Dict:
        return self.resolver.get_stats()