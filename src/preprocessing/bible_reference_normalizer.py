import re
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from src.extraction.exact_matcher import ExactBookMatcher
from src.extraction.fuzzy_matcher import FuzzyBookMatcher

class BibleReferenceNormalizer:
    """
    Extracts and normalizes Bible chapter RANGE references only
    Example:
        - Kej 1-3
        - Kej 1 sampai 3
    """

    def __init__(self, 
                 json_path: Optional[str] = None, 
                 use_fuzzy: bool = True):

        # Load bible data automatically
        if json_path is None:
            json_path = self.find_bible_json()

        self.bible_data = self.load_bible_data(json_path)
        self.books = self.bible_data['books']
        
        # Matchers
        self.exact_matcher = ExactBookMatcher(self.books)
        self.fuzzy_matcher = FuzzyBookMatcher(self.books) if use_fuzzy else None

        # Matcher pipeline
        self.matchers = [self.exact_matcher]
        if self.fuzzy_matcher:
            self.matchers.append(self.fuzzy_matcher)
        
        # Track extraction stats
        self.extraction_stats = {
            'exact_match': 0,
            'fuzzy_match': 0,
            'failed': 0
        }

        book_pattern = r'\b(\d?\s?[A-Za-z]+(?:\s+[A-Za-z]+){0,2})\b'

        # Build regex patterns for chapter references
        self.chapter_patterns = [
            # Range with dash: "Kej 1-3" or "1 Kor 5-7"
            re.compile(
                rf'{book_pattern}\s+(\d+)\s*-\s*(\d+)',
                re.IGNORECASE
            ),

            # Range with words: "Kej 1 sampai 3"
            re.compile(
                rf'{book_pattern}\s+(\d+)\s+(?:sampai|hingga|to)\s+(\d+)',
                re.IGNORECASE
            )
        ]


    def find_bible_json(self) -> str:
        path = Path(__file__).parent / '../../data/bible_references.json'
        path = path.resolve()

        if not path.exists():
            raise FileNotFoundError(
                f"could not find bible_references.json at {path}"
            )
        
        return str(path)

    def load_bible_data(self, json_path: str) -> Dict:
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def extract_all_references(self, text: str) -> List[Dict]:
        references = []
        text_lower = text.lower()

        for pattern in self.chapter_patterns:
            for match in pattern.finditer(text_lower):
                book_text, start_ch, end_ch = match.groups()

                book_data, match_method = self.resolve_book(book_text)

                if not book_data:
                    continue

                start_ch, end_ch = int(start_ch), int(end_ch)
                is_valid = self.validate_chapters(book_data, start_ch, end_ch)

                references.append({
                    'book': book_data['name'],
                    'book_id': book_data['id'],
                    'testament': book_data['testament'],
                    'start_chapter': start_ch,
                    'end_chapter': end_ch,
                    'chapters': list(range(start_ch, end_ch + 1)),
                    'raw_text': match.group(0),
                    'normalized_text': f"{book_data['name']} {start_ch}-{end_ch}",
                    'is_valid': is_valid,
                    'extraction_method': match_method
                })
                
                    
        return references

    def get_stats(self) -> Dict:
        return self.extraction_stats
                    
    def resolve_book(self, book_text: str) -> Tuple[Optional[Dict], str]:
        """
        Try matchers in order: exact -> fuzzy
        """

        for matcher in self.matchers:
            book, confidence = matcher.match(book_text)
            if book:
                method = 'exact' if confidence == 1.0 else 'fuzzy'
                self.extraction_stats[f'{method}_match'] += 1
                return book, method
        
        self.extraction_stats['failed'] += 1
        return None, 'failed'
    
    def validate_chapters(self, book_data: Dict, start_ch: int, end_ch: int) -> bool:

        if start_ch < 1 or end_ch < 1:
            return False
        if start_ch > end_ch:
            return False
        if end_ch > book_data['chapters']:
            return False
        return True