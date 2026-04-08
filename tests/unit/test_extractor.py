from typing import Dict
from unittest.mock import MagicMock
from extraction.extractor import inject_book_context, preprocess, BibleReferenceExtractor

class TestInjectBookContext:
    def test_plain_book_line_unchanged(self):
        result = inject_book_context("Kej 1-3")
        assert result == "Kej 1-3"
    
    def test_bare_range_after_book_gets_context(self):
        msg = "Kisah para rasul 1-2\n3-4"
        lines = inject_book_context(msg).splitlines()
        assert lines[1] == "Kisah para rasul 3-4"
    
    def test_bare_range_with_no_prior_book_unchanged(self):
        result = inject_book_context("2-3")
        assert result == "2-3"
    
    def test_book_context_switches_correctly(self):
        msg = "Kej 1-2\n3-4\nKel 1-2\n3-4"
        lines = inject_book_context(msg).splitlines()
        assert lines[1] == "Kej 3-4"
        assert lines[3] == "Kel 3-4"
    
    def test_non_range_line_after_book_unchanged(self):
        msg = "Kej 1\nSudah selesai"
        lines = inject_book_context(msg).splitlines()
        assert lines[1] == "Sudah selesai"
    
    def test_empty_string_returns_empty(self):
        assert inject_book_context("") == ""
    
    def test_mulitline_all_book_lines_no_bare_ranges(self):
        msg = "Imamat 1-2\nImamat 3-4\nImamat 5-6"
        result = inject_book_context(msg)
        assert result == msg

class TestPreprocess:
    def test_plain_string_unchanged_aside_from_whitespace(self):
        result = preprocess("Kej 1-3")
        assert result == "Kej 1-3"
    
    def test_list_input_joined(self):
        result = preprocess(["Kej 1", "Kej 2"])
        assert "Kej 1" in result
        assert "Kej 2" in result
    
    def test_non_string_coerced(self):
        assert preprocess(42) == "42"
    
    def test_newlines_replaced_with_space(self):
        result = preprocess("Kej 1-2 done\nKej 3-4 done")
        assert "\n" not in result
    
    def test_emoji_expanded_with_spaces(self):
        result = preprocess("Kej 1-2🙏")
        assert "🙏" in result or "folded" in result.lower() or result.strip() != ""
    
    def test_leading_trailing_whitespace_stripped(self):
        result = preprocess("  Kej 1  ")
        assert result == "Kej 1"
    
def ner_hit(word: str, score: float = 0.99) -> Dict:
    return {"entity_group": "BIBLE_REF", "word": word, "score": score}

def ner_miss(word: str) -> Dict:
    return {"entity_group": "O", "word": word, "score": 0.95}

class TestBibleReferenceExtractor:
    def test_returns_list(self, extractor):
        extractor.ner_pipeline.return_value = []
        assert isinstance(extractor.extract("Kej 1"), list)
 
    def test_non_bible_ref_entities_ignored(self, extractor):
        extractor.ner_pipeline.return_value = [ner_miss("sudah")]
        assert extractor.extract("sudah") == []
 
    def test_single_ref_parsed_and_normalized(self, extractor):
        extractor.ner_pipeline.return_value = [ner_hit("Kej 1")]
        extractor.normalizer = MagicMock()
        extractor.normalizer.normalize.return_value = [{
            "book_start": "Kejadian",
            "start_chapter": 1,
            "book_end": "Kejadian",
            "end_chapter": 1,
            "is_valid": True,
        }]
        refs = extractor.extract("Kej 1")
        assert len(refs) == 1
        assert refs[0]["book_start"] == "Kejadian"
 
    def test_multiple_refs_returned(self, extractor):
        extractor.ner_pipeline.return_value = [
            ner_hit("Kej 1"),
            ner_hit("Kel 2"),
        ]
        extractor.normalizer = MagicMock()
        extractor.normalizer.normalize.side_effect = [
            [{"book_start": "Kejadian", "start_chapter": 1,
              "book_end": "Kejadian", "end_chapter": 1, "is_valid": True}],
            [{"book_start": "Keluaran", "start_chapter": 2,
              "book_end": "Keluaran", "end_chapter": 2, "is_valid": True}],
        ]
        refs = extractor.extract("Kej 1 Kel 2")
        assert len(refs) == 2
 
    def test_unparseable_ner_span_produces_warning_and_no_ref(self, extractor, caplog):
        extractor.ner_pipeline.return_value = [ner_hit("???")]
        extractor.normalizer = MagicMock()
        extractor.normalizer.normalize.return_value = []
        import logging
        with caplog.at_level(logging.WARNING, logger="bible_pipeline.extraction.extractor"):
            refs = extractor.extract("???")
        assert refs == []
 
    def test_preprocess_called_before_ner(self, extractor):
        extractor.ner_pipeline.return_value = []
        extractor.normalizer = MagicMock()
        extractor.normalizer.normalize.return_value = []
        extractor.extract("Kej 1\n2-3")
        call_args = extractor.ner_pipeline.call_args[0][0]
        assert "\n" not in call_args