import re
import json
from pathlib import Path
from typing import Dict, List, Optional

class BibleReferenceNormalizer:

    def __init__(self, json_path: Optional[str] = None):

        # Load bible data automatically
        if json_path is None:
            json_path = self.find_bible_json()

        self.bible_data = self.load_bible_data(json_path)

        self.books = self.bible_data['books']
        self.alias_to_book = self.build_alias_mapping()
        self.name_to_book = {book['name'].lower(): book for book in self.books}

        # Build regex patterns for chapter references
        self.chapter_patterns = [
            # Range: e.g.Kej 1-3
            re.compile(
                r'(\d?\s?[a-zA-Z\-]+(?:\s+[a-zA-Z\-]+)*)\s+(\d+)\s*-\s*(\d+)',
                re.IGNORECASE
            ),

            # Range: e.g.Kej 1 sampai 3
            re.compile(
                r'(\d?\s?[a-zA-Z\-]+(?:\s+[a-zA-Z\-]+)*)\s+(\d+)\s+(?:sampai|hingga|to)\s+(\d+)',
                re.IGNORECASE
            ),

            # Single chapter: e.g. Kej 1
            re.compile(
                r'(\d?\s?[a-zA-Z\-]+(?:\s+[a-zA-Z\-]+)*)\s+(\d+)',
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
    
    def build_alias_mapping(self) -> Dict[str, Dict]:
        mapping = {}

        for book in self.books:

            for alias in book['aliases']:
                mapping[alias.lower()] = book
            
            mapping[book['name'].lower()] = book
        
        return mapping
    
    def extract_all_references(self, text: str) -> List[Dict]:
        references = []
        text_lower = text.lower()

        for pattern in self.chapter_patterns:
            matches = pattern.finditer(text_lower)
            for match in matches:
                raw_text = match.group(0)

                if any(raw_text in ref['raw_text'] for ref in references):
                    continue
                
                groups = match.groups()

                if len(groups) == 3:
                    # Range pattern (e.g., "Kej 1-3")
                    book_abbr, start_ch, end_ch = groups
                    book_data = self.get_book_data(book_abbr)

                    if book_data:
                        start_ch = int(start_ch)
                        end_ch = int(end_ch)

                        is_valid = self.validate_chapters(
                            book_data, start_ch, end_ch
                        )

                        references.append({
                            'book': book_data['name'],
                            'book_id': book_data['id'],
                            'testament': book_data['testament'],
                            'start_chapter': start_ch,
                            'end_chapter': end_ch,
                            'chapters': list(range(start_ch, end_ch + 1)),
                            'raw_text': match.group(0),
                            'normalized_text': f"{book_data['name']} {start_ch}-{end_ch}",
                            'is_valid': is_valid
                        })
                
                elif len(groups) == 2:
                    # Single chapter pattern (e.g., "Kej 1")
                    book_abbr, chapter = groups
                    book_data = self.get_book_data(book_abbr)

                    if book_data:
                        chapter = int(chapter)

                        is_valid = self.validate_chapters(
                            book_data, chapter, chapter
                        )

                        references.append({
                            'book': book_data['name'],
                            'book_id': book_data['id'],
                            'testament': book_data['testament'],
                            'start_chapter': chapter,
                            'end_chapter': chapter,
                            'chapters': [chapter],
                            'raw_text': match.group(0),
                            'normalized_text': f"{book_data['name']} {chapter}",
                            'is_valid': is_valid
                        })
                    
        return references
                    
    def get_book_data(self, abbreviation: str) -> Optional[Dict]:

        abbr_clean = ' '.join(abbreviation.lower().split())
        return self.alias_to_book.get(abbr_clean)
    
    def validate_chapters(self, book_data: Dict, start_ch: int, end_ch: int) -> bool:

        if start_ch < 1 or end_ch < 1:
            return False
        if start_ch > end_ch:
            return False
        if end_ch > book_data['chapters']:
            return False
        return True
    
    