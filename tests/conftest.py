import pytest
from unittest.mock import MagicMock, patch

@pytest.fixture
def known_members():
    return ['Alice', 'Bob', 'Charlie']

# tests/test_extractor.py
@pytest.fixture
def extractor():
    with patch("extraction.extractor.load_ner_model") as mock_load, \
         patch("extraction.extractor.pipeline") as mock_pipeline:
        mock_load.return_value = (MagicMock(), MagicMock())
        mock_pipeline.return_value = MagicMock()

        from extraction.extractor import BibleReferenceExtractor

        return BibleReferenceExtractor(saved_path="/fake/path")

# tests/test_services.py
@pytest.fixture
def last_read():
    def factory(book="Kejadian", chapter=3):
        m = MagicMock()
        m.book_name = book
        m.chapter = chapter
        return m
    return factory

# tests/test_whatsapp_parser.py
@pytest.fixture
def parser():
    from preprocessing import WhatsAppParser
    return WhatsAppParser()