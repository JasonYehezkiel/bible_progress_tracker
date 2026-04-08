from services import (
    apply_gap_fill,
    format_header,
)

class TestApplyGapFill:
    def ref(self, **kwargs):
        base = {
            'book_start': 'Kejadian', "book_end": None,
            'start_chapter': 5, 'end_chapter': 5,
        }
        return {**base, **kwargs}
    
    def test_no_last_returns_unchanged(self):
        ref = self.ref()
        assert apply_gap_fill(ref, None)['start_chapter'] == 5
    
    def test_different_book_returns_unchanged(self, last_read):
        ref = self.ref()
        assert apply_gap_fill(ref, last_read(book='Keluaran'))['start_chapter'] == 5
    
    def test_no_gap_returns_unchanged(self, last_read):
        ref = self.ref(start_chapter=5)
        assert apply_gap_fill(ref, last_read(chapter=4))['start_chapter'] == 5
    
    def test_gap_is_filled(self, last_read):
        ref = self.ref(start_chapter=6, end_chapter=6)
        filled = apply_gap_fill(ref, last_read(chapter=3))
        assert filled['start_chapter'] == 4
    
    def test_multi_chapter_ref_skipped(self, last_read):
        ref = self.ref(start_chapter=3, end_chapter=5)
        assert apply_gap_fill(ref, last_read(chapter=1))['start_chapter'] == 3
    
class TestFormatHeader:
    def test_empty(self):
        assert format_header([]) == 'No reading scheduled'
    
    def test_single_book_single_chapter(self):
        assert format_header([('Kejadian', 1)]) == 'Kej 1'
    
    def test_single_book_multi_chapter(self):
        assert format_header([('Kejadian', 1), ('Kejadian', 2), ('Kejadian', 3)]) == 'Kej 1 - 3'
    
    def test_cross_book(self):
        assert format_header([('Kejadian', 50), ('Keluaran', 1)]) == 'Kej 50 - Kel 1'