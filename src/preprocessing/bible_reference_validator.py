from typing import Dict

class BibleReferenceValidator:

    @staticmethod
    def validate_chapters(book_data: Dict, start_ch: int, end_ch: int) -> bool:

        if start_ch < 1 or end_ch < 1:
            return False
        if start_ch > end_ch:
            return False
        if end_ch > book_data['chapters']:
            return False
        return True