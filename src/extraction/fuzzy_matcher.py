from typing import Dict, List, Optional, Tuple
from rapidfuzz import fuzz, process

class FuzzyBookMatcher:
    """
    Fuzzy matcher for Bible book names
    """

    def __init__(self,
                 books: List[Dict],
                 similarity_threshold: int = 80):
        
        self.similarity_threshold = similarity_threshold
        self.books = books

        self.variation_to_book = self.build_variation_mapping()
        self.variations = list(self.variation_to_book.keys())


    def build_variation_mapping(self) -> Dict[str, Dict]:
        """
        Map all known book name variations to canonical book data
        """

        mapping = {}

        for book in self.books:
            mapping[book['name'].lower()] = book
            for alias in book['aliases']:
                mapping[alias.lower()] = book

        return mapping
    
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

        if not book:
            return None, 0.0
        
        return book, score / 100.0