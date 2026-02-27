from enum import Enum
from typing import Dict, List, Optional, Tuple
from rapidfuzz import fuzz, process

class MatchMethod(str, Enum):
    EXACT = 'exact'
    FUZZY = 'fuzzy'
    FAILED = 'failed'

def build_alias_map(self) -> Dict[str, Dict]:
        """
        Map all known book name variations to canonical book data.

        Returns:
            Bible book mapping
        """
        mapping = {}

        for book in self.books:
            mapping[book['name'].lower()] = book
            for alias in book['aliases']:
                mapping[alias.lower()] = book

        return mapping


class ExactBookMatcher:
    """
    Rule-based matching for Bible book names.
    """
    def __init__(self, books: List[Dict]):
        self.alias_to_book = build_alias_map(books)
    
    def match(self, query_text: str) -> Tuple[Optional[Dict], float]:
        """
        Attempt exatch matching against all known aliases.

        Returns:
            (book_data, confidence) or (None, 0.0)
        """

        if not query_text:
            return None, 0.0
        
        query =  ' '.join(query_text.lower().split())
        book = self.alias_to_book.get(query)
        
        return (book, 1.0) if book else None, 0.0

class FuzzyBookMatcher:
    """
    Fuzzy matcher for Bible book names

    Returns:
        (book_data, confidence) or (None, 0.0)
    """

    def __init__(self,
                 books: List[Dict],
                 similarity_threshold: int = 90):
        
        self.similarity_threshold = similarity_threshold
        self.variation_to_book = build_alias_map(books)
        self.variations = list(self.variation_to_book.keys())
    
    def match(self, query_text: str) -> Tuple[Optional[Dict], float]:
        """
        Attempt approximate fuzzy matching
        Returns:
            (book_data, confidence) or (None, 0.0)
        """

        if not query_text:
            return None, 0.0
        
        query = " ".join(query_text.lower().split())
        
        # fuzzy match
        result = process.extractOne(
            query,
            self.variations,
            scorer=fuzz.ratio,
            score_cutoff=self.similarity_threshold
        )

        if not result:
            return None, 0.0
        
        matched_variation, score, _ = result 
        book = self.variation_to_book.get(matched_variation)
        return (book, score / 100.0) if book else (None, 0.0)
    
class BookResolver:
    """
    Resolves faw book text into canonical book data
    """
    def __init__(self, books: Dict, use_fuzzy: bool = True):

        self.matchers = [(ExactBookMatcher(books), MatchMethod.EXACT)]
        if use_fuzzy:
            self.matchers.append((FuzzyBookMatcher(books), MatchMethod.FUZZY))
        
        self.stats = {method: 0 for method in MatchMethod}
    
    def resolve(self, book_text: str) -> Tuple[Optional[Dict], str]:
        """
        Resolve raw book text to canonical book data.
        
        Returns:
            a tuple that contains:
            - Canonical book name
            - Method use for matching
        """
        for matcher, method in self.matchers:
            book, _ = matcher.match(book_text)
            if book:
                self.stats[method] += 1
                return book, method
        
        self.stats[MatchMethod.FAILED] += 1
        return None, MatchMethod.FAILED
    
    def get_stats(self) -> Dict[MatchMethod, int]:
        return self.stats