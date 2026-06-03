import re
import emoji
import logging
from types import SimpleNamespace
from typing import Dict, List, Optional
from core.logger import setup_logger

setup_logger('bible_pipeline')
logger = logging.getLogger('bible_pipeline.services')

def preprocess(message) -> str:
    """Normalize a message before NER: coerce type,  expand emoji, collapse whitespace."""
    if isinstance(message, list):
        message = ' '.join(str(x) for x in message)
    elif not isinstance(message, str):
        message = str(message)
    
    message = emoji.replace_emoji(message, replace=lambda s, _: f" {s} ")
    message = message.replace("\n", " ")
    message = re.sub(r'-{2,}', '-', message)
    message = re.sub(r'([a-zA-Z])(\d)', r'\1 \2', message)
    message = re.sub(r'(\d)([a-zA-Z])', r'\1 \2', message)
    message = re.sub(r'[_*]', r' \g<0> ', message)
    message = re.sub(r" {2,}", " ", message).strip()

    return message

def apply_gap_fill(ref: Dict, last: Optional[object]) -> Dict:
        """Apply gap-filling logic to a reference before inserting into DB."""
        book_end = ref.get('book_end') or ref['book_start']
        if ref['book_start'] != book_end:
            return ref

        if last is None:
             last = SimpleNamespace(book_name=ref['book_start'], chapter=0)
        
        if last.book_name != ref['book_start']:
             return ref
        
        next_expected = last.chapter + 1
        if next_expected > ref['start_chapter']:
            filled = dict(ref)
            filled['start_chapter'] = next_expected
            logger.debug(
                 'Overlap-trim: %s ch%d→%d (last was ch%d)',
                 ref['book_start'], ref['start_chapter'], next_expected, last.chapter,
            )
            return filled
        
        if next_expected == ref['start_chapter']:
             return ref
        
        # next_expected < start_chapter → gap
        filled = dict(ref)
        filled['start_chapter'] = next_expected
        logger.debug(
            'Gap-fill: %s ch%d→%d (last was ch%d)',
            ref['book_start'], next_expected, ref['start_chapter'], last.chapter,
        )
        return filled

def ref_as_last(ref: dict) -> SimpleNamespace:
    """Wrap a normalized ref dict as a lightweight proxy."""
    return SimpleNamespace(
         book_name=ref.get('book_end') or ref.get('book_start'),
         chapter=ref.get('end_chapter') or ref.get('start_chapter')
    )


def format_header(assigned: List) -> str:
        """Format scheduled chapters as a compact header string."""
        if not assigned:
            return 'No reading scheduled'
        
        books = [book for book, _ in assigned]
        chapters = [ch for _, ch in assigned]
        unique_books = list(dict.fromkeys(books))

        def abbrev(name: str) -> str:
            return name[:3]
        
        if len(unique_books) == 1:
            if len(chapters) == 1:
                return f'{abbrev(unique_books[0])} {chapters[0]}'
            return f'{abbrev(unique_books[0])} {chapters[0]} - {chapters[-1]}'
        
        # Cross-book: show first and last
        first_book, first_ch = assigned[0]
        last_book, last_ch = assigned[-1]
        return f'{abbrev(first_book)} {first_ch} - {abbrev(last_book)} {last_ch}'
    