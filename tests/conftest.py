import pytest
from unittest.mock import MagicMock, patch

# Needed Variables
BOOK_KEJADIAN = {
    'id': 1,
    'name': 'Kejadian',
    'chapters': 50,
    'aliases': ['kej', 'kejadian'],
}
 
BOOK_KELUARAN = {
    'id': 2,
    'name': 'Keluaran',
    'chapters': 40,
    'aliases': ['kel', 'keluaran'],
}
 
BOOK_MATIUS = {
    'id': 40,
    'name': 'Matius',
    'chapters': 28,
    'aliases': ['mat', 'matius'],
}
 
BOOK_YOHANES = {
    'id': 43,
    'name': 'Yohanes',
    'chapters': 21,
    'aliases': ['yoh', 'yohanes'],
}
 
SAMPLE_BOOKS = [BOOK_KEJADIAN, BOOK_KELUARAN, BOOK_MATIUS, BOOK_YOHANES]

# unit/test_extractor.py
@pytest.fixture
def extractor():
    with patch("extraction.extractor.load_ner_model") as mock_load, \
         patch("extraction.extractor.pipeline") as mock_pipeline:
        mock_load.return_value = (MagicMock(), MagicMock())
        mock_pipeline.return_value = MagicMock()

        from extraction.extractor import BibleReferenceExtractor

        return BibleReferenceExtractor(saved_path="/fake/path")

# unit/test_normalizer.py
@pytest.fixture()
def sample_books():
    return SAMPLE_BOOKS

@pytest.fixture()
def validator():
    from preprocessing.normalization.validator import BibleReferenceValidator
    return BibleReferenceValidator()

@pytest.fixture()
def resolver(sample_books):
    from preprocessing.normalization.resolver import BookResolver
    return BookResolver(sample_books, use_fuzzy=True)

@pytest.fixture()
def normalizer():
    from preprocessing.normalization import BibleReferenceNormalizer
    return BibleReferenceNormalizer()

# unit/test_services.py
@pytest.fixture
def last_read():
    def factory(book="Kejadian", chapter=3):
        m = MagicMock()
        m.book_name = book
        m.chapter = chapter
        return m
    return factory

# unit/test_whatsapp_parser.py
@pytest.fixture
def parser():
    from preprocessing import WhatsAppParser
    return WhatsAppParser()