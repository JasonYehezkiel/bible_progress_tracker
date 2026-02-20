import json
from pathlib import Path
from typing import Dict, List, Optional
from src.utils.bible_reference_utils import BibleDataLoader
from src.preprocessing.resolution.book_resolver import BookResolver
from src.preprocessing.normalization.bible_reference_validator import BibleReferenceValidator

class BibleReferenceNormalizer:
    """
    Normalize extracted Bible references into canonical form.
    """

    def __init__(self, bible_books: Dict):

        self.books = self.bible_data['books']

        self.resolver = BookResolver(self.books, use_fuzzy=True)
        self.validator = BibleReferenceValidator()
    
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
                })
                    
        return normalized
    
    def get_stats(self) -> Dict:
        return self.resolver.get_stats()