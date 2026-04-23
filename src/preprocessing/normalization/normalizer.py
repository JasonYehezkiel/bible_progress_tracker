import logging
from typing import Dict, List
from bible_data import load_bible_data
from logger import setup_logger
from preprocessing.normalization.resolver import BookResolver
from preprocessing.normalization.validator import BibleReferenceValidator

setup_logger('bible_pipeline')
logger = logging.getLogger('bible_pipeline.preprocessing.normalization.normalizer')

class BibleReferenceNormalizer:
    """
    Normalize extracted Bible references into canonical form.
    """

    def __init__(self, use_fuzzy: bool = True):
        bible_data = load_bible_data()
        self.books = bible_data['books']
        self.resolver = BookResolver(self.books, use_fuzzy=use_fuzzy)
        self.validator = BibleReferenceValidator()
    
    def normalize(self, candidates: list[Dict]) -> List[Dict]:
        """
        Normalize a list of raw references from NER response.

        Args:
            candidates: Output of NER response — list of dicts with
                        book_start, start_chapter, book_end, end_chapter.
        Returns:
            List of normalized references dict. Unresolveable books are skipped
        """

        normalized = []

        for ref in candidates:
                # resolve book_start
                start_book_data, _ = self.resolver.resolve(ref["book_start"])
                if not start_book_data:
                    logger.warning("Skipping ref, unresolveable start book: %r", ref['book_start'])
                    continue

                start_ch = ref['start_chapter']
                end_ch = ref['end_chapter']
                book_end = ref.get('book_end')

                # resolve book_end
                end_book_data = None
                if book_end:
                     end_book_data, _ = self.resolver.resolve(book_end)
                     if not end_book_data:
                          logger.warning("Skipping ref, unresolveable end book: %r", book_end)
                          continue
                     
                # Default single book
                if start_ch is None and end_ch is None and end_book_data is None:
                     start_ch = 1
                     end_ch = start_book_data['chapters']
                     end_book_data = start_book_data
                
                # Default book-only cross-book range
                elif start_ch is None and end_ch is None and end_book_data is not None:
                     start_ch = 1
                     end_ch = end_book_data['chapters']
                
                # Single chapter
                elif start_ch is not None and end_ch is None and end_book_data is None:
                     end_ch = start_ch
                     end_book_data = start_book_data
                
                # # cross-book with start chapter but no end chapter
                elif start_ch is not None and end_ch is None and end_book_data is not None:
                     end_ch = end_book_data['chapters']
                
                # Fill end_book_data for same-book refs
                if end_book_data is None or end_book_data['id'] == start_book_data['id']:
                    end_book_data = start_book_data

                # Validate
                is_valid = self.validator.validate_chapters(
                    start_book_data, start_ch, end_book_data, end_ch
                )

                normalized.append({
                    'book_start': start_book_data['name'],
                    'start_chapter': start_ch,
                    'book_end': end_book_data['name'],
                    'end_chapter': end_ch,
                    'is_valid': is_valid,
                })
                    
        return normalized
    
    def get_stats(self) -> Dict:
        """Get Resolver stats"""
        return self.resolver.get_stats()