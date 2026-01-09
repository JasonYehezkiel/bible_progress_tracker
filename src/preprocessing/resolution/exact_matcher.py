from typing import Dict, List, Optional, Tuple

class ExactBookMatcher:
    """
    Rule-based matching for Bible book names
    """
    def __init__(self, books: List[Dict]):
        self.books = books
        self.alias_to_book = self.build_alias_mapping()

    def build_alias_mapping(self) -> Dict[str, Dict]:
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
        Attempt fuzzy matching
        Returns:
            (book_data, confidence) or (None, 0.0)
        """

        if not query_text:
            return None, 0.0
        
        query =  ' '.join(query_text.lower().split())
        book = self.alias_to_book.get(query)

        if book:
            return book, 1.0
        
        return None, 0.0