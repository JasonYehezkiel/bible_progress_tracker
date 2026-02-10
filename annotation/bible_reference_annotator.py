import pandas as pd
import re
from typing import Dict, List, Any

class BibleReferenceAnnotator:
    """
    Annotate text with Bible reference labels for weak supervision.
    """

    def __init__(self, bible_books: Dict):

        aliases = []
        for book in bible_books['books']:
            aliases.extend(book['aliases'])
        
        aliases = sorted(set(aliases), key=len, reverse=True)

        alias_pattern = '|'.join(map(re.escape, aliases))

        book_pattern = rf"(?<![A-Za-z])(?:[_*:\(\[]{{0,2}})?({alias_pattern})\.?(?:[_*\)\]]{{0,2}})?(?=\s*\d)"

        chapter_pattern = r'(\d+)'
        range_dash = r'\s*[-–—]{1,2}\s*'
        range_words = r'\s+(?:sampai|hingga|to)\s+'


        # Build regex patterns for chapter references
        self.patterns = [
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
            # Single chapter: "Kej 1"
            re.compile(
                rf'{book_pattern}\s*{chapter_pattern}',
                re.IGNORECASE
            )
        ]
    
    def extract(self, text: str) -> List[Dict[str, Any]]:
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

        for pattern in self.patterns:
            for match in pattern.finditer(text):
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

        for pattern in self.patterns:
            for match in pattern.finditer(text):
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

                        # Merge chapter range into one span
                        chapter_start_idx = match.start(2)
                        chapter_end_idx = match.end(3)

                        spans.append({
                            "start": chapter_start_idx,
                            "end": chapter_end_idx,
                            "label": "CHAPTER",
                            "text": text[chapter_start_idx:chapter_end_idx]
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
    
    def classify_intent(self, references: list) -> str:
        """
        Classify if text contains Bible references.

        Args:
            text: Input text to classify
            references: List of extracted Bible references
        Returns:
            'PROGRESS_REPORT' if references found, else 'OTHER'
        """
        if references:
            return 'PROGRESS_REPORT'
     
        return 'OTHER'


    
    def annotate_dataframe(self, df: pd.DataFrame, text_column: str = 'message', 
                           inplace: bool = False) -> pd.DataFrame:
        """
        Annotate DataFrame with Bible reference labels for weak supervision.

        Args:
            df: Input DataFrame
            text_column: Name of column containing text to annotate
            inplace: If true, modify df in place; if False, return a copy

        Returns:
            DataFrame with added columns:
            - bible_references: List of extracted references
            - bible_ref_count: Number of references found
            - intent: Classified intent label
            - ner_spans: List of NER spans for references
        """
        if not inplace:
            df = df.copy()
        
        df['bible_references'] = df[text_column].apply(self.extract)
        df['bible_ref_count'] = df['bible_references'].str.len()
        df['intent'] = df['bible_references'].apply(self.classify_intent)
        df['ner_spans'] = df[text_column].apply(self.extract_ner_spans)

        return df