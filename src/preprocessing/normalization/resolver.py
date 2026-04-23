import logging
from typing import Dict, List, Optional, Tuple
from rapidfuzz import fuzz, process

from logger import setup_logger
from config.settings import FUZZY_THRESHOLD

setup_logger('bible_pipeline')
logger = logging.getLogger('bible_pipeline.preprocessing.normalization.resolver')

MATCH_EXACT = 'exact'
MATCH_FUZZY = 'fuzzy'
MATCH_FAILED = 'failed'

def build_alias_map(books: List[Dict]) -> Dict[str, Dict]:
        """Map all known book name variations to canonical book data."""
        mapping = {}
        for book in books:
            mapping[book['name'].lower()] = book
            for alias in book['aliases']:
                mapping[alias.lower()] = book
        return mapping

class ExactBookMatcher:
    """Rule-based matching for Bible book names."""
    def __init__(self, books: List[Dict]):
        self.alias_map = build_alias_map(books)
    
    def match(self, query_text: str) -> Optional[Dict]:
        """
        Attempt exatch matching against all known aliases.
        
        Returns:
            a dict with book data if a match is found, otherwise None
        """
        if not query_text:
            return None
        query =  ' '.join(query_text.lower().split())
        return self.alias_map.get(query)

class FuzzyBookMatcher:
    """Fuzzy matcher for Bible book names"""
    def __init__(self,
                 books: List[Dict],
                 similarity_threshold: int = FUZZY_THRESHOLD):
        
        self.similarity_threshold = similarity_threshold
        self.alias_map = build_alias_map(books)
        self.variations = list(self.alias_map.keys())
    
    def match(self, query_text: str) -> Optional[Dict]:
        """
        Attempt approximate fuzzy matching
        
        Returns:
            a dict with book data if a match is found, otherwise None
        """
        if not query_text:
            return None
        query = " ".join(query_text.lower().split())
        # fuzzy match
        result = process.extractOne(
            query,
            self.variations,
            scorer=fuzz.partial_ratio,
            score_cutoff=self.similarity_threshold
        )
        if not result:
            return None
        matched_variation, _, _ = result 
        return self.alias_map.get(matched_variation)
    
class BookResolver:
    """
    Resolves faw book text into canonical book data
    """
    def __init__(self, books: List[Dict], use_fuzzy: bool = True):
        self.exact = ExactBookMatcher(books)
        self.fuzzy = FuzzyBookMatcher(books) if use_fuzzy else None
        self.stats = {MATCH_EXACT: 0, MATCH_FUZZY: 0, MATCH_FAILED: 0}
    
    def resolve(self, book_text: str) -> Tuple[Optional[Dict], str]:
        """
        Resolve raw book text to canonical book data.
        
        Returns:
            a tuple that contains:
            - Canonical book name
            - Method use for matching
        """
        book = self.exact.match(book_text)
        if book:
            self.stats[MATCH_EXACT] += 1
            return book, MATCH_EXACT
        
        if self.fuzzy:
            book = self.fuzzy.match(book_text)
            if book:
                self.stats[MATCH_FUZZY] += 1
                return book, MATCH_FUZZY
        
        logger.warning("No match found for: %r", book_text)
        self.stats[MATCH_FAILED] += 1
        return None, MATCH_FAILED
    
    def get_stats(self) -> Dict[str, int]:
        """Get matching statistics."""
        return self.stats