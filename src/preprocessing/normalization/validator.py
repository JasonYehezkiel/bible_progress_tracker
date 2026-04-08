from typing import Dict, Optional


class BibleReferenceValidator:
    """
    Validate Bible references against known book chapter counts.
    """

    @staticmethod
    def validate_chapters(
        start_book_data: Dict,
        start_ch: Optional[int],
        end_book_data: Optional[Dict],
        end_ch: Optional[int],
    ) -> bool:
        """
        Validate chapter numbers against known book metadata.

        Args:
            start_book_data: Resolved metadata for book_start
            start_ch: Starting chapter number. None for book-only references.
            end_book_data: Resolved metadata for book_end. Only for cross-book ranges.
            end_ch: Ending chapter number. None for book-only references.

        Returns:
            True if the reference is valid, False otherwise.
        """
        if not start_book_data or not end_book_data:
            return False
        if start_ch is None or end_ch is None:
            return False
        
        if start_ch < 1 or end_ch < 1:
            return False
        if start_ch > start_book_data['chapters']:
            return False
        if end_ch > end_book_data['chapters']:
            return False
        if end_book_data['id'] == start_book_data['chapters'] and start_ch > end_ch:
            return False

        return True