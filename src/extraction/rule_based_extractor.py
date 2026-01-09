import re
from typing import Dict, List

class RuleBasedExtractor:
    """
    Extract raw chapter RANGE references from text.
    """

    def __init__(self):
        book_pattern = r'\b(\d?\s?[A-Za-z]+(?:\s+[A-Za-z]+){0,2})\b'

        # Build regex patterns for chapter references
        self.patterns = [
            # Range with dash: "Kej 1-3" or "1 Kor 5-7"
            re.compile(
                rf'{book_pattern}\s+(\d+)\s*-\s*(\d+)',
                re.IGNORECASE
            ),

            # Range with words: "Kej 1 sampai 3"
            re.compile(
                rf'{book_pattern}\s+(\d+)\s+(?:sampai|hingga|to)\s+(\d+)',
                re.IGNORECASE
            )
        ]
    
    def extract(self, text: str) -> List[Dict]:
        results = []

        for pattern in self.patterns:
            for match in pattern.finditer(text):
                book_text, start_ch, end_ch = match.groups()

                results.append({
                    "book_text": book_text,
                    "start_chapter": int(start_ch),
                    "end_chapter": int(end_ch),
                    "raw_text": match.group(0),
                    "confidence": 1.0,
                    "source": "rule"
                })
        
        return results