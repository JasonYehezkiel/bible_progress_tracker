from typing import Dict, Optional, Tuple
from src.preprocessing.resolution.exact_matcher import ExactBookMatcher
from src.preprocessing.resolution.fuzzy_matcher import FuzzyBookMatcher

class BookResolver:
    """
    Resolves faw book text into canonical book data
    """

    def __init__(self, books: Dict, use_fuzzy: bool = True):
        self.exact_matcher = ExactBookMatcher(books)
        self.fuzzy_matcher = FuzzyBookMatcher(books) if use_fuzzy else None

        self.matchers = [self.exact_matcher]
        if self.fuzzy_matcher:
            self.matchers.append(self.fuzzy_matcher)
        
        self.stats = {
            'exact_match': 0,
            'fuzzy_match': 0,
            'failed': 0
        }
    
    def resolve(self, book_text: str) -> Tuple[Optional[Dict], str]:
        for matcher in self.matchers:
            book, confidence = matcher.match(book_text)
            if book:
                method = 'exact' if confidence == 1.0 else 'fuzzy'
                self.stats[f'{method}_match'] += 1
                return book, method
        
        self.stats['failed'] += 1
        return None, 'failed'
    
    def get_stats(self) -> Dict:
        return self.stats