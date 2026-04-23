import pandas as pd
import re
from typing import Dict, List, Any


class BibleRegexBuilder:
    """
    Builds regex patterns for matching Bible references from text, 
    including cross-book and chapter ranges.
    """

    def __init__(self, bible_books: Dict):
        self.bible_books = bible_books
        self.patterns = self.build_patterns()

    def collect_aliases(self) -> tuple[str, str]:
        """
        Collect all book aliases into a single alternation string.
        sorted longest-first so shorter aliases cannot shadow longer ones.
        """
        aliases = {
            alias 
            for book in self.bible_books['books']
            for alias in book['aliases']
        }
        return '|'.join(map(re.escape, sorted(aliases, key=len, reverse=True)))
    
    def build_patterns(self) -> List[re.Pattern]:
        """
        Build regex patterns for matching Bible references, including:
        - Single book
        - Single Chapter
        - Chapter range within same book
        - Cross-book chapter range

        Returns:
            List of compiled regex patterns, ordered from most specific to least specific.
        """
        alias_pat = self.collect_aliases()

        def book_cap(group_name: str) -> str:
            """Named group matching a book token that precedes a digit."""
            return rf'(?P<{group_name}>(?<![A-Za-z])(?:{alias_pat})\.?)'
 
        def book_standalone_cap(group_name: str) -> str:
            """Named group matching a book token NOT followed by alphanumerics."""
            return rf'(?P<{group_name}>(?<![A-Za-z])(?:{alias_pat})\.?(?![A-Za-z\d]))'
 
        sc = r'(?P<start_chapter>\d+)'
        ec = r'(?P<end_chapter>\d+)'
        vs = r':\d+'                   
        rd = r'\s*[-\u2013\u2014]{1,2}\s*'
        rw = r'\s+(?:sampai|sampe|hingga|to)\s+'
 
        bs = book_cap('book_start')
        be = book_cap('book_end')
        bss = book_standalone_cap('book_start')
        f = re.IGNORECASE

        return [
            # Cross-chapter verse range: Kej 1:1 - 2:5
            re.compile(rf'{bs}\s*{sc}{vs}{rd}{ec}{vs}', f),
            re.compile(rf'{bs}\s*{sc}{vs}{rw}{ec}{vs}', f),
            # Verse range within chapter: Kej 1:1-5
            re.compile(rf'{bs}\s*{sc}{vs}{rd}\d+', f),
            # Chapter-to-verse: Kej 1 - 2:5
            re.compile(rf'{bs}\s*{sc}{rd}{ec}{vs}', f),
            # Single verse: Kej 1:1
            re.compile(rf'{bs}\s*{sc}{vs}', f),
            # Cross-book chapter range: Kej 50 - Kel 2
            re.compile(rf'{bs}\s*{sc}{rd}{be}\s*{ec}', f),
            re.compile(rf'{bs}\s*{sc}{rw}{be}\s*{ec}', f),
            # Same-book chapter range: Kej 1-3
            re.compile(rf'{bs}\s*{sc}{rd}{ec}', f),
            re.compile(rf'{bs}\s*{sc}{rw}{ec}', f),
            # Single chapter: Kej 1
            re.compile(rf'{bs}\s*{sc}', f),
            # Book only: Kejadian
            re.compile(bss, f),
        ]
        


class RuleBasedExtractor:
    """
    extract Bible references from text using compiled regex patterns.
 
    Provides two extraction levels:
        extract_ner_spans  — character-span dicts for NER / weak supervision
        extract_structure  — structured dicts
    """

    def __init__(self, patterns: List[re.Pattern]):
        self.patterns = patterns

    def get_non_overlapping_matches(self, text: str):
        """
        Yield non-overlapping pattern matches from the text.
        Proritize earlier patterns (more specific) over later ones.
        """
        covered: List[tuple[int, int]] = []

        for pattern in self.patterns:
            for match in pattern.finditer(text):
                s, e = match.start(), match.end()
                if any(not (e <= cs or ce <= s) for cs, ce in covered):
                    continue
                covered.append((s, e))
                yield match

    
    def extract_ner_spans(self, text: str) -> List[Dict[str, Any]]:
        """
        Return one BIBLE_REF span per reference found, covering the full match.

        Args:
            text: Input text.
        Returns:
            List of dicts with keys: start, end, label, text.
        """

        matches = sorted(
            self.get_non_overlapping_matches(text),
            key=lambda m: m.start(),
        )

        return [
            {
                'start': m.start(),
                'end': m.end(),
                'label': 'BIBLE_REF',
                'text': m.group(),
            }
            for m in matches
        ]
    
    def extract_structure(self, text: str) -> List[Dict[str, Any]]:
        """
        Return structured reference dicts, ordered by position.

        Args:
            text: Input text.
        Returns:
            List of dicts with keys: book_start, start_chapter, book_end, end_chapter, 
                                     span_start, span_end, span_label, span_text
        """
        matches = sorted(
            self.get_non_overlapping_matches(text),
            key=lambda m: m.start(),
        )
        results = []

        for m in matches:
            gd = m.groupdict()

            book_start_raw = (gd.get('book_start') or '').strip().rstrip('.')
            book_end_raw = (gd.get('book_end') or '').strip().rstrip('.') or None
            start_ch = int(gd['start_chapter']) if gd.get('start_chapter') else None
            end_ch = int(gd['end_chapter']) if gd.get('end_chapter') else None

            results.append({
                'book_start': book_start_raw,
                'start_chapter': start_ch,
                'book_end': book_end_raw,
                'end_chapter': end_ch,
            })
        
        return results
            

class BibleReferenceAnnotator:
    """
    Main user-facing class.
    Wraps BibleRegexBuilder and BibleReferenceExtractor and 
    provides methods to annotate DataFrames.
    """
    def __init__(self, bible_books: Dict):
        builder = BibleRegexBuilder(bible_books)
        self.parser = RuleBasedExtractor(builder.patterns)

    def annotate_dataframe(
            self, 
            df: pd.DataFrame, 
            text_column: str = 'message', 
            inplace: bool = False, 
            mask=None
        ) -> pd.DataFrame:
        """
        Annotate DataFrame with Bible reference labels for weak supervision.

        Args:
            df: Input DataFrame
            text_column: Name of column containing text to annotate
            inplace: If true, modify df in place; if False, return a copy
            mask: Optional mask for DataFrame

        Returns:
            DataFrame with added columns:
            - bible_references: List of extracted references
            - bible_ref_count: Number of references found
            - ner_spans: List of NER spans for references
        """
        if not inplace:
            df = df.copy()
        
        target = df[text_column] if mask is None else df.loc[mask, text_column]

        spans = target.apply(self.parser.extract_ner_spans)

        if mask is None:
            df['ner_spans'] = spans
        else:
            df['ner_spans'] = [[] for _ in range(len(df))]
            df.loc[mask, 'ner_spans'] = spans
        
        df['bible_ref_count'] = df['ner_spans'].apply(len)

        return df