def build_ref(book_start, start_chapter=None, book_end=None, end_chapter=None):
    return {
        'book_start': book_start,
        'start_chapter': start_chapter,
        'book_end': book_end,
        'end_chapter': end_chapter,
    }
class TestBibleReferenceValidator:
    # same-book range
    def test_same_book_inverted_range_is_invalid(self, validator):
        book = {'id': 1, 'chapters': 50}
        assert validator.validate_chapters(book, 10, book, 5) is False
    
    def test_same_book_equal_chapters_is_valid(self, validator):
        book = {'id': 1, 'chapters': 50}
        assert validator.validate_chapters(book, 3, book, 3) is True
    
    def test_same_book_ascending_chapters_is_valid(self, validator):
        book = {'id': 1, 'chapters': 50}
        assert validator.validate_chapters(book, 1, book, 50) is True
    
    # out-of-range guards
    def test_start_chapter_exceeds_book_max_is_invalid(self, validator):
        book = {'id': 1, 'chapters': 50}
        assert validator.validate_chapters(book, 51, book, 50) is False
    
    def test_end_chapter_exceeds_book_max_is_invalid(self, validator):
        book = {'id': 1, 'chapters': 28}
        assert validator.validate_chapters(book, 1, book, 29) is False
    
    def test_zero_chapter_is_invalid(self, validator):
        book = {'id': 1, 'chapters': 50}
        assert validator.validate_chapters(book, 0, book, 1) is False
    
    # cross-book range
    def test_cross_book_valid_different_books(self, validator):
        start_book = {'id': 1, 'chapters': 50}
        end_book = {'id': 2, 'chapters': 40}
        assert validator.validate_chapters(start_book, 40, end_book, 5) is True
    
    def test_missing_book_data_is_invalid(self, validator):
        assert validator.validate_chapters(None, 1, None, 1) is False

class TestBookResolver:
    def test_exact_match_canonical_name(self, resolver):
        book, method = resolver.resolve('Kejadian')
        assert book is not None
        assert book['name'] == 'Kejadian'
        assert method == 'exact'
    
    def test_exact_match_alias(self, resolver):
        book, method = resolver.resolve('kej')
        assert book['name'] == 'Kejadian'
        assert method == 'exact'

    def test_exact_match_is_case_insensitive(self, resolver):
        book, method = resolver.resolve('MATIUS')
        assert book['name'] == 'Matius'
        assert method == 'exact'

    def test_fuzzy_match_typo(self, resolver):
        book, method = resolver.resolve('Kejadain')
        assert book is not None
        assert book['name'] == 'Kejadian'
        assert method == 'fuzzy'
    
    def test_unknown_book_returns_none(self, resolver):
        book, method = resolver.resolve('Zorgblat')
        assert book is None
        assert method == 'failed'
    
    def test_empty_string_returns_none(self, resolver):
        book, _ = resolver.resolve('')
        assert book is None
    
    def test_stats_increment_correctly(self, sample_books):
        from preprocessing.normalization.resolver import BookResolver
        r = BookResolver(sample_books, use_fuzzy=True)
        
        r.resolve('kej')
        r.resolve('Kejadain')
        r.resolve('Zorgblat')
 
        stats = r.get_stats()
        assert stats['exact'] >= 1
        assert stats['fuzzy'] >= 1
        assert stats['failed'] >= 1

class TestBibleReferenceNormalizer:
    def test_unresolveable_book_is_skipped(self, normalizer):
        result = normalizer.normalize([build_ref('ZorgblatXYZ')])
        assert result == []
    
    def test_unresolvable_book_does_not_affect_valid_refs_after_it(self, normalizer):
        refs = [
            build_ref('ZorgblatXYZ'),
            build_ref('Kejadian', start_chapter=1),
        ]
        result = normalizer.normalize(refs)
        assert len(result) == 1
        assert result[0]['book_start'] == 'Kejadian'
    
    def test_single_book_no_chapters_expands_to_full_range(self, normalizer):
        result = normalizer.normalize([build_ref('Kejadian')])
        assert len(result) == 1
        r = result[0]
        assert r['book_start'] == r['book_end'] == 'Kejadian'
        assert r['start_chapter'] == 1
        assert r['end_chapter'] == 50
        assert r['is_valid'] is True
    
    def test_single_book_via_alias_resolves_to_canonical_name(self, normalizer):
        result = normalizer.normalize([build_ref('kej')])
        assert len(result) == 1
        assert result[0]['book_start'] == 'Kejadian'
        assert result[0]['book_end'] == 'Kejadian'
    
    def test_cross_book_no_chapters_defaults_to_full_ranges(self, normalizer):
        result = normalizer.normalize([build_ref('Kejadian', book_end='Keluaran')])
        assert len(result) == 1
        r = result[0]
        assert r['book_start'] == 'Kejadian'
        assert r['book_end'] == 'Keluaran'
        assert r['start_chapter'] == 1
        assert r['end_chapter'] == 40
        assert r['is_valid'] is True
    
    def test_cross_book_unresolvable_end_is_skipped(self, normalizer):
        result = normalizer.normalize([build_ref('Kejadian', book_end='ZorgblatXYZ')])
        assert result == []
    
    def test_single_chapter_ref(self, normalizer):
        result = normalizer.normalize([build_ref('Matius', start_chapter=5)])
        assert len(result) == 1
        r = result[0]
        assert r['book_start'] == r['book_end'] == 'Matius'
        assert r['start_chapter'] == r['end_chapter'] == 5
        assert r['is_valid'] is True
 
    def test_single_chapter_first(self, normalizer):
        result = normalizer.normalize([build_ref('Kejadian', start_chapter=1)])
        r = result[0]
        assert r['start_chapter'] == r['end_chapter'] == 1
 
    def test_single_chapter_last(self, normalizer):
        result = normalizer.normalize([build_ref('Matius', start_chapter=28)])
        r = result[0]
        assert r['start_chapter'] == r['end_chapter'] == 28
        assert r['is_valid'] is True
    
    def test_cross_book_with_start_chapter_fills_end_chapter_to_max(self, normalizer):
        result = normalizer.normalize([
            build_ref('Matius', start_chapter=20, book_end='Yohanes')
        ])
        assert len(result) == 1
        r = result[0]
        assert r['book_start'] == 'Matius'
        assert r['book_end'] == 'Yohanes'
        assert r['start_chapter'] == 20
        assert r['end_chapter'] == 21
        assert r['is_valid'] is True
    
    def test_out_of_range_chapter_is_marked_invalid(self, normalizer):
        result = normalizer.normalize([build_ref('Matius', start_chapter=99)])
        assert len(result) == 1
        assert result[0]['is_valid'] is False
    
    def test_valid_chapter_is_marked_valid(self, normalizer):
        result = normalizer.normalize([build_ref('Yohanes', start_chapter=3)])
        assert result[0]['is_valid'] == True
    
    def test_batch_preserves_insertion_order(self, normalizer):
        refs = [
            build_ref('Kejadian', start_chapter=1),
            build_ref('Matius', start_chapter=5),
            build_ref('Yohanes', start_chapter=3),
        ]
        result = normalizer.normalize(refs)
        assert len(result) == 3
        assert result[0]['book_start'] == 'Kejadian'
        assert result[1]['book_start'] == 'Matius'
        assert result[2]['book_start'] == 'Yohanes'
    
    def test_empty_input_returns_empty_list(self, normalizer):
        assert normalizer.normalize([]) == []
    
    def test_get_stats_returns_expected_keys(self, normalizer):
        stats = normalizer.get_stats()
        assert 'exact' in stats
        assert 'fuzzy' in stats
        assert 'failed' in stats