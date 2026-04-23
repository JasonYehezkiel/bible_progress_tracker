import logging
from typing import Dict
from extraction.ner_parser import parse_ner_response, tokenize


class TestTokenize:
    def test_simple_word_and_number(self):
        tokens = tokenize('Kej 1')
        assert ('WORD', 'kej') in tokens
        assert ('NUM', '1') in tokens

    def test_whitespace_is_skipped(self):
        tokens = tokenize('  Kej  1  ')
        kinds = [k for k, _ in tokens]
        assert 'SKIP' not in kinds
    
    def test_range_tokens_recognised(self):
        for raw in ['-', '–', '—', 'sampai', 'sampe', 'smpe', 'hingga', 's/d', 's.d.', 'sd']:
            tokens = tokenize(raw)
            assert any(k == 'RANGE' for k, _ in tokens), f'Expected RANGE for {raw!r}'
    
    def test_colon_token(self):
        tokens = tokenize('1:5')
        kinds = [k for k, _ in tokens]
        assert 'COLON' in kinds
    
    def test_comma_token(self):
        tokens = tokenize('1, 2')
        kinds = [k for k, _ in tokens]
        assert 'COMMA' in kinds
    
    def test_semicolon_token(self):
        tokens = tokenize('Kej 1; Kej 2')
        kinds = [k for k, _ in tokens]
        assert 'SEMI' in kinds
    
    def test_reduplicated_expanded_to_hypenated(self):
        tokens = tokenize('raja2')
        assert ('WORD', 'raja-raja') in tokens
    
    def test_hyphenated_word_is_single_word_token(self):
        tokens = tokenize('Raja-Raja')
        word_tokens = [(k, v) for k, v in tokens if k == 'WORD']
        assert len(word_tokens) == 1
        assert word_tokens[0][1] == 'raja-raja'
    
    def test_numbered_prefix_as_num_token(self):
        tokens = tokenize('2 Raja-Raja')
        assert tokens[0] == ('NUM', '2')

class TestParseNerResponse:

    def test_empty_spans_list_returns_empty(self):
        assert parse_ner_response([]) == []
    
    def test_whitespace_only_span_returns_empty(self):
        assert parse_ner_response(['  ']) == []
    
    def test_simple_book_and_chapter(self):
        refs = parse_ner_response(['Kej 1'])
        assert len(refs) == 1
        assert refs[0]['book_start'] == 'kej'
        assert refs[0]['start_chapter'] == 1
        assert refs[0]['book_end'] is None
        assert refs[0]['end_chapter'] is None
    
    def test__book_only_no_chapter(self):
        refs = parse_ner_response(['Wahyu'])
        assert len(refs) == 1
        assert refs[0]['book_start'] == 'wahyu'
        assert refs[0]['start_chapter'] is None
    
    def test_numbered_book_prefix(self):
        refs = parse_ner_response(['1 Kor 13'])
        assert len(refs) == 1
        assert refs[0]['book_start'] == '1 kor'
        assert refs[0]['start_chapter'] == 13
    
    def test_numbered_book_with_hyphenated_name(self):
        refs = parse_ner_response(['2 Raja-Raja 1'])
        assert len(refs) == 1
        assert refs[0]['book_start'] == '2 raja-raja'
        assert refs[0]['start_chapter'] == 1
    
    def test_same_book__chapter_range_dash(self):
        refs = parse_ner_response(['Kej 1-3'])
        assert len(refs) == 1
        assert refs[0]['start_chapter'] == 1
        assert refs[0]['end_chapter'] == 3
        assert refs[0]['book_end'] is None
    
    def test_same_book__chapter_range_word(self):
        refs = parse_ner_response(['Kej 2 sampai 5'])
        assert len(refs) == 1
        assert refs[0]['start_chapter'] == 2
        assert refs[0]['end_chapter'] == 5
    
    def test_cross_book_range(self):
        refs = parse_ner_response(['Gal 6 - Ef 1'])
        assert len(refs) == 1
        assert refs[0]['book_start'] == 'gal'
        assert refs[0]['book_end'] == 'ef'
        assert refs[0]['start_chapter'] == 6
        assert refs[0]['end_chapter'] == 1
    
    def test_bare_cross_book_no_chapters(self):
        refs = parse_ner_response(['Mzm - Yes'])
        assert len(refs) == 1
        assert refs[0]['book_start'] == 'mzm'
        assert refs[0]['book_end'] == 'yes'
        assert refs[0]['start_chapter'] is None
        assert refs[0]['end_chapter'] is None
    
    def test_comma_separated_chapters(self):
        refs = parse_ner_response(['Kej 1, 2, 3'])
        assert len(refs) == 3
        chapters = [r['start_chapter'] for r in refs]
        assert chapters == [1, 2, 3]
        assert all(r['book_start'] == 'kej' for r in refs)
    
    def test_verse_annotation_ignored_for_chapter_tracking(self):
        refs = parse_ner_response(['Kej 1:1'])
        assert len(refs) == 1
        assert refs[0]['start_chapter'] == 1
    
    def test_verse_range_within_chapter(self):
        refs = parse_ner_response(['Kej 1:1-5'])
        assert len(refs) == 1
        assert refs[0]['start_chapter'] == 1
        assert refs[0]['end_chapter'] is None
    
    def test_context_book_used_for_bare_chapter(self):
        refs = parse_ner_response(['3'], initial_ctx_book='kej')
        assert len(refs) == 1
        assert refs[0]['book_start'] == 'kej'
        assert refs[0]['start_chapter'] == 3
    
    def test_context_book_updated_across_spans(self):
        refs = parse_ner_response(['Kel 3', '4'])
        assert refs[0]['book_start'] == 'kel'
        assert refs[1]['book_start'] == 'kel'
        assert refs[1]['start_chapter'] == 4
    
    def test_semicolon_separates_refs_in_one_span(self):
        refs = parse_ner_response(['Kej 1, Kel 2'])
        assert len(refs) == 2
        assert refs[0]['book_start'] == 'kej'
        assert refs[1]['book_start'] == 'kel'
    
    def test_multiple_spans(self):
        refs = parse_ner_response(['Kej 1', 'Kel 2', 'Im 3'])
        assert len(refs) == 3
        books = [r['book_start'] for r in refs]
        assert books == ['kej', 'kel', 'im']

# Helper functions
def ner_hit(word: str, score: float = 0.99) -> Dict:
    return {'entity_group': 'BIBLE_REF', 'word': word, 'score': score, 'start': 0, 'end': len(word)}

def ner_miss(word: str) -> Dict:
    return {'entity_group': 'O', 'word': word, 'score': 0.95, 'start': 0, 'end': len(word)}

class TestBibleReferenceExtractor:
    def test_returns_list(self, extractor):
        extractor.ner_pipeline.return_value = [[]]
        result = extractor.extract('Kej 1')
        assert isinstance(result, list)
 
    def test_non_bible_ref_entities_ignored(self, extractor):
        extractor.ner_pipeline.return_value = [
            [ner_miss('sudah'), ner_miss('dibaca')]
        ]
        assert extractor.extract('sudah dibaca') == []
 
    def test_mixed_entities_only_bible_ref_returned(self, extractor):
        extractor.ner_pipeline.return_value = [[ner_miss('Baca'), ner_hit('Kej 1'), ner_miss('selesai')]]
        refs = extractor.extract('Baca Kej 1 selesai')
        assert len(refs) == 1
        assert refs[0]['book_start'] == 'kej'
 
    def test_single_ref_book_and_chapter_parsed(self, extractor):
        extractor.ner_pipeline.return_value = [[ner_hit('Kej 1')]]
        refs = extractor.extract('Kej 1')
        assert len(refs) == 1
        ref = refs[0]
        assert ref['book_start'] == 'kej'
        assert ref['start_chapter'] == 1
        assert ref['book_end'] is None
        assert ref['end_chapter'] is None
 
    def test_range_ref_same_book(self, extractor):
        extractor.ner_pipeline.return_value = [[ner_hit('Kej 1-3')]]
        refs = extractor.extract('Kej 1-3')
        assert len(refs) == 1
        assert refs[0]['start_chapter'] == 1
        assert refs[0]['end_chapter'] == 3
 
    def test_multiple_hits_in_one_message(self, extractor):
        extractor.ner_pipeline.return_value = [[ner_hit('Kej 1'), ner_hit('Kel 2')]]
        refs = extractor.extract('Kej 1 Kel 2')
        assert len(refs) == 2
 
    def test_no_hits_returns_empty_list(self, extractor):
        extractor.ner_pipeline.return_value = [[]]
        assert extractor.extract('halo semua') == []
    
    def test_extract_batch_returns_one_list_per_message(self, extractor):
        extractor.ner_pipeline.return_value = [
            [ner_hit('Kej 1')],
            [ner_hit('Kel 2'), ner_hit('Im 3')],
        ]
        results = extractor.extract_batch(['msg1', 'msg2'])
        assert len(results) == 2
        assert len(results[0]) == 1
        assert len(results[1]) == 2
    
    def test_extract_batch_empty_message_yields_empty_sublist(self, extractor):
        extractor.ner_pipeline.return_value = [[], [ner_hit('Kej 1')]]
        results = extractor.extract_batch(['nothing', 'Kej 1'])
        assert results[0] == []
        assert len(results[1]) == 1
    
    def test_return_spans_true_yields_span_dicts(self, extractor):
        extractor.ner_pipeline.return_value = [[ner_hit('Kej 1')]]
        results = extractor.extract_batch(['Kej 1'], return_spans=True)
        span = results[0][0]
        assert 'start' in span
        assert 'end' in span
        assert 'label' in span
        assert span['label'] == 'BIBLE_REF'
        assert span['text'] == 'Kej 1'
    
    def test_return_spans_false_yields_parsed_dicts(self, extractor):
        extractor.ner_pipeline.return_value = [[ner_hit('Kej 1')]]
        results = extractor.extract_batch(['Kej 1'])
        assert 'book_start' in results[0][0]
    
    def test_unparseable_span_logs_warning_and_returns_empty(self, extractor, caplog):
        extractor.ner_pipeline.return_value = [[ner_hit('???')]]
        with caplog.at_level(logging.WARNING, logger='bible_pipeline.extraction.extractor'):
            refs = extractor.extract('???')
            assert refs == []
            assert any('no parsed ref' in rec.message.lower() for rec in caplog.records)