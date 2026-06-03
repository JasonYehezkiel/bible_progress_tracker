import logging
from typing import Dict, List, Optional, Tuple
from rapidfuzz import fuzz, process, distance

from core import setup_logger
from core.config import FUZZY_THRESHOLD, W_BIGRAM_JACCARD, W_JARO_WINKLER

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
        Attempt exact matching against all known aliases.
        
        Returns:
            a dict with book data if a match is found, otherwise None
        """
        if not query_text:
            return None
        query =  ' '.join(query_text.lower().split())
        return self.alias_map.get(query)

class FuzzyBookMatcher:
    """Fuzzy matching for Bible book names."""
    def __init__(self,
                 books: List[Dict],
                 similarity_threshold: int = FUZZY_THRESHOLD):
        
        self.similarity_threshold = similarity_threshold
        self.alias_map = build_alias_map(books)
        self.variations = list(self.alias_map.keys())
    
    def get_candidates(self, query: str) -> List[str]:
        """Pre-filter variation list to reduce fuzzy search space and
           prevent cross-initial false positives."""
        if not query:
            return self.variations
        
        if query[0].isdigit() or query[0].isalpha():
            first = query[0]
            filtered = [v for v in self.variations if v.startswith(first)]
            return filtered if filtered else self.variations
        
        return self.variations

    @staticmethod
    def bigram_jaccard(a: str, b: str) -> float:
        "Compute similarity between two strings using bigram Jaccard index."
        bigrams_a = set(zip(a, a[1:]))
        bigrams_b = set(zip(b, b[1:]))
        union = bigrams_a | bigrams_b
        if not union:
            return 0.0
        return len(bigrams_a & bigrams_b) / len(union)

    @staticmethod
    def jaro_winkler(a: str, b: str) -> float:
        "Compute similarity using jaro-Winkler distance metric."
        return distance.JaroWinkler.similarity(a, b)
    
    def ensemble_score(self, query: str, candidate: str) -> float:
        "Compute a weighted ensemble similarity score between two strings."
        bj = self.bigram_jaccard(query, candidate)
        jw = self.jaro_winkler(query, candidate)
        return (
            W_BIGRAM_JACCARD * bj
            + W_JARO_WINKLER * jw
        )
    
    def match(self, query_text: str) -> Optional[Dict]:
        """
        Attempt approximate fuzzy matching
        
        Returns:
            a dict with book data if a match is found, otherwise None
        """
        if not query_text:
            return None
        
        query = " ".join(query_text.lower().split())
        candidates = self.get_candidates(query)
            
        # fuzzy match
        top_hits = process.extract(
            query,
            candidates,
            scorer=fuzz.WRatio,
            score_cutoff=self.similarity_threshold,
        )
        if not top_hits:
            return None
        
        best_hit = max(top_hits, key=lambda hit:  self.ensemble_score(query, hit[0]))
        best_variation = best_hit[0]

        return self.alias_map.get(best_variation)
    
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