import pandas as pd
import json
import re
from pathlib import Path
from typing import Dict, List, Any

class BibleDataLoader:
    """
    Loads Bible reference data from a JSON file and provides access to book information.
    """
    def find_bible_json(self) -> str:
        path = Path(__file__).parents[2] / 'data'/ 'bible_references.json'
        path = path.resolve()

        if not path.exists():
            raise FileNotFoundError(
                f"could not find bible_references.json at {path}"
            )
        
        return str(path)
    
    def load_bible_data(self, json_path: str) -> Dict:
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def load_default(self) -> Dict:
        json_path = self.find_bible_json()
        return self.load_bible_data(json_path)

class BibleRegexBuilder:
    """
    Builds regex patterns for matching Bible references from text, 
    including cross-book and chapter ranges.
    """

    def __init__(self, bible_books: Dict):

        # Load bible data automatically
        self.bible_books = bible_books
        self.patterns = self.build_patterns()

    def build_patterns(self) -> List[re.Pattern]:
        aliases = []

        for book in self.bible_books['books']:
            aliases.extend(book['aliases'])
        
        aliases = sorted(set(aliases), key=len, reverse=True)
        alias_pattern = '|'.join(map(re.escape, aliases))

        book_pattern = (
            rf'(?<![A-Za-z])'
            rf'({alias_pattern})\.?'
            rf'(?=\s*\d)'
        )

        chapter_pattern = r'(\d+)'
        range_dash = r'\s*[-–—]{1,2}\s*'
        range_words = r'\s+(?:sampai|sampe|hingga|to)\s+'


        # Build regex patterns for chapter references
        return [
            # Cross-book range: "Kej 50 - Kel 2"
            re.compile(
                rf'{book_pattern}\s*{chapter_pattern}{range_dash}{book_pattern}\s*{chapter_pattern}',
                re.IGNORECASE
            ),
            # Cross-book with words: "Kej 50 sampai Kel 2"
            re.compile(
                rf'{book_pattern}\s*{chapter_pattern}{range_words}{book_pattern}\s*{chapter_pattern}',
                re.IGNORECASE
            ),
            # Range with dash: "Kej 1-3" or "1 Kor 5-7"
            re.compile(
                rf'{book_pattern}\s*{chapter_pattern}{range_dash}{chapter_pattern}',
                re.IGNORECASE
            ),

            # Range with words: "Kej 1 sampai 3"
            re.compile(
                rf'{book_pattern}\s*{chapter_pattern}{range_words}{chapter_pattern}',
                re.IGNORECASE
            ),
            # Single chapter: "Kej 1"
            re.compile(
                rf'{book_pattern}\s*{chapter_pattern}',
                re.IGNORECASE
            ),
        ]


class BibleReferenceExtractor:
    """
    Extract Bible references and NER spans from text using regex patterns."""

    def __init__(self, patterns: List[re.Pattern]):
        self.patterns = patterns

    def get_non_overlapping_matches(self, text: str):
        """
        Yield non-overlapping pattern matches from the text.
        Proritize earlier patterns (more specific) over later ones.

        Args:
            text: input text to search for matches
        Returns:
        """
        matched_ranges = []

        for pattern in self.patterns:
            for match in pattern.finditer(text):
                match_range = (match.start(), match.end())
                
                # Check for overlap with existing matches
                overlaps = any(
                    not (match.end() <= start or end <= match.start())
                    for start, end in matched_ranges
                )

                if overlaps:
                    continue

                matched_ranges.append(match_range)
                yield match

    def extract_structured(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract Bible reference ranges from text.

        Args:
            text: Input text containing Bible references.

        Returns:
            List of dictionaries with extracted references:
            - book_start: Starting book name
            - start_chapter: Starting chapter number
            - book_end: Ending book name
            - end_chapter: Ending chapter number
            - raw_text: Original matched text

        """
        results = []

        for match in self.get_non_overlapping_matches(text):
            groups = match.groups()

            if len(groups) == 2:
                book_text, chapter = groups
                results.append({
                    "book_start": book_text.strip(),
                    "start_chapter": int(chapter),
                    "book_end": book_text.strip(),
                    "end_chapter": int(chapter),
                    "raw_text": match.group(0)
                })
            
            elif len(groups) == 3:
                book_text, start_ch, end_ch = groups
                results.append({
                    "book_start": book_text.strip(),
                    "start_chapter": int(start_ch),
                    "book_end": book_text.strip(),
                    "end_chapter": int(end_ch),
                    "raw_text": match.group(0)
                })
            
            elif len(groups) == 4:
                book_start, start_ch, book_end, end_ch = groups
                results.append({
                    "book_start": book_start.strip(),
                    "start_chapter": int(start_ch),
                    "book_end": book_end.strip(),
                    "end_chapter": int(end_ch),
                    "raw_text": match.group(0)
                })
        
        return results
    
    def extract_ner_spans(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract Bible reference ranges as NER spans.

        Args:
            text: Input text containing Bible references.
        Returns:
            List of dictionaries with NER spans:
            - start: Start index of the match
            - end: End index of the match
            - label: "BOOK", "CHAPTER"
            - text: Original matched text
        """

        spans = []
        for match in self.get_non_overlapping_matches(text):
            groups = match.groups()

            # Single chapter range
            if len(groups) == 2:
                book_text, chapter = groups

                spans.append({
                    "start": match.start(1),
                    "end": match.end(1),
                    "label": "BOOK",
                    "text": book_text
                })

                spans.append({
                    "start": match.start(2),
                    "end": match.end(2),
                    "label": "CHAPTER",
                    "text": chapter
                })
        
            # Chapter range
            elif len(groups) == 3:
                    book_text, start_ch, end_ch = groups

                    spans.append({
                        "start": match.start(1),
                        "end": match.end(1),
                        "label": "BOOK",
                        "text": book_text
                    })

                    spans.append({
                        "start": match.start(2),
                        "end": match.end(2),
                        "label": "CHAPTER",
                        "text": start_ch
                    })

                    spans.append({
                        "start": match.start(3),
                        "end": match.end(3),
                        "label": "CHAPTER",
                        "text": end_ch
                    })

            # cross-book range
            elif len(groups) == 4:
                book_start, start_ch, book_end, end_ch = match.groups()

                # Start book span
                spans.append({
                    "start": match.start(1),
                    "end": match.end(1),
                    "label": "BOOK",
                    "text": book_start
                })

                # Start chapter span
                spans.append({
                    "start": match.start(2),
                    "end": match.end(2),
                    "label": "CHAPTER",
                    "text": start_ch
                })

                # End book span
                spans.append({
                    "start": match.start(3),
                    "end": match.end(3),
                    "label": "BOOK",
                    "text": book_end
                })

                # End chapter span
                spans.append({
                    "start": match.start(4),
                    "end": match.end(4),
                    "label": "CHAPTER",
                    "text": end_ch
                })
        
        return spans
    

class BibleReferenceAnnotator:
    """
    Main user-facing class:
    - loads bible metadata
    - extract references
    - annotate DataFrames
    """
    def __init__(self, bible_books: Dict):
        builder = BibleRegexBuilder(bible_books)
        self.extractor = BibleReferenceExtractor(builder.patterns)
    
    def initialize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Set default negative values for all annotation columns,

        Args:
            df: Input DataFrame
        
        Returns:
            DataFrame with added columns
        """
        df['bible_references'] = [[] for _ in range(len(df))]
        df['ner_spans'] = [[] for _ in range(len(df))]
        df['bible_ref_count'] = 0

        return df
    
    def apply_annotations(self, df: pd.DataFrame, text_column: str) -> pd.DataFrame:
        """
        Apply Bible Reference extraction to populate annotation columns

        Args:
            df: Input DataFrame
            text_column: Name of column containing text to annotate
        
        Returns:
            DataFrame with added columns
        """
        df['bible_references'] = df[text_column].apply(self.extractor.extract_structured)
        df['ner_spans'] = df[text_column].apply(self.extractor.extract_ner_spans)
        df['bible_ref_count'] = df['bible_references'].str.len()

        return df

    def annotate_dataframe(self, df: pd.DataFrame, text_column: str = 'message', 
                           inplace: bool = False, mask=None) -> pd.DataFrame:
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
            - intent: Classified intent label
            - ner_spans: List of NER spans for references
        """
        if not inplace:
            df = df.copy()
        
        df = self.initialize_columns(df)

        if mask is not None:
            df.loc[mask] = self.apply_annotations(df.loc[mask].copy(), text_column)
        else:
            df = self.apply_annotations(df, text_column)

        return df