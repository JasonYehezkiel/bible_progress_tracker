import pytest
from datetime import date, datetime, timezone
from unittest.mock import MagicMock, patch

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

# 1. Bible data constants
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

BOOK_LOOKUP = {b['name']: b for b in SAMPLE_BOOKS}

SORTED_BOOKS = sorted(BOOK_LOOKUP.values(), key=lambda b: b['id'])

# 2. NLP component mocks
# unit/test_classification.py
@pytest.fixture
def classifier():
    mock_model = MagicMock()
    mock_vectorizer = MagicMock()
    mock_model.predict.return_value = [1]
    mock_vectorizer.transform.return_value = MagicMock()

    with patch('classification.joblib.load', side_effect=[mock_model, mock_vectorizer]):
        from classification import MessageClassifier

        return MessageClassifier(model_path='/fake/model', vectorizer_path='/fake/vectorizer')

# unit/test_extractor.py
@pytest.fixture
def extractor():
    with patch("extraction.indobert.load_ner_model") as mock_load, \
         patch("extraction.indobert.pipeline") as mock_pipeline:
        mock_load.return_value = (MagicMock(), MagicMock())
        mock_pipeline.return_value = MagicMock()

        from extraction.indobert import BibleReferenceExtractor

        return BibleReferenceExtractor(saved_path="/fake/path")

# unit/test_whatsapp_parser.py
@pytest.fixture
def parser():
    from ingestion import WhatsAppParser
    return WhatsAppParser()

# 3. Bible normalization fixtures
# unit/test_normalizer.py
@pytest.fixture()
def sample_books():
    return SAMPLE_BOOKS

@pytest.fixture()
def validator():
    from bible.normalization.validator import BibleReferenceValidator
    return BibleReferenceValidator()

@pytest.fixture()
def resolver(sample_books):
    from bible.normalization.resolver import BookResolver
    return BookResolver(sample_books, use_fuzzy=True)

@pytest.fixture()
def normalizer():
    from bible.normalization import BibleReferenceNormalizer
    return BibleReferenceNormalizer()

# unit/test_db.py
@pytest.fixture(scope='session')
def db_engine():
    from sessions.db import Base
    engine = create_engine(
        'sqlite:///:memory:',
        connect_args={'check_same_thread': False},
        echo=False,
    )
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()

@pytest.fixture()
def db_session(db_engine):
    connection = db_engine.connect()
    outer_tx = connection.begin()
    session = Session(bind=connection)

    session.begin_nested()

    @event.listens_for(session, 'after_transaction_end')
    def restart_savepoint(sess, transaction):
        if transaction.nested and not transaction._parent.nested:
            sess.begin_nested()
    
    yield session

    session.close()
    outer_tx.rollback()
    connection.close()

@pytest.fixture
def db_member(db_session):
    from sessions.db import Member

    member = Member(name='Adi Santoso')
    db_session.add(member)
    db_session.flush()
    return member

@pytest.fixture
def db_member_two(db_session):
    from sessions.db import Member

    member = Member(name='Siti Nurhaliza')
    db_session.add(member)
    db_session.flush()
    return member

@pytest.fixture
def db_message(db_session, db_member):
    from sessions.db import Message

    msg = Message(
        member_id=db_member.id,
        timestamp=datetime(2024, 1, 15, 8, 30, 0),
        raw_text='Hari ini baca Kejadian 1-3',
        processed_at=None,
    )
    db_session.add(msg)
    db_session.flush()
    return msg

@pytest.fixture
def db_message_processed(db_session, db_member):
    from sessions.db import Message

    msg = Message(
        member_id=db_member.id,
        timestamp=datetime(2024, 1, 14, 7, 0, 0),
        raw_text='Kemarin baca Keluaran 1',
        processed_at=datetime(2024, 1, 14, 7, 5, 0, tzinfo=timezone.utc),
    )
    db_session.add(msg)
    db_session.flush()
    return msg

@pytest.fixture
def db_reference(db_session, db_message):
    from sessions.db import BibleReference

    ref = BibleReference(
        message_id=db_message.id,
        book_start='Kejadian',
        start_chapter=1,
        book_end='Kejadian',
        end_chapter=3,
    )
    db_session.add(ref)
    db_session.flush()
    return ref

@pytest.fixture
def db_progress(db_session, db_member, db_reference):
    from sessions.db import ReadingProgress

    rows = []
    for ch in range(1, 4):
        rp = ReadingProgress(
            member_id=db_member.id,
            book_id=1,
            book_name='Kejadian',
            chapter=ch,
            date_read=date(2024, 1, 15),
            ref_id=db_reference.id,
        )
        db_session.add(rp)
        rows.append(rp)

    db_session.flush()
    return rows

# 7. Pipeline-level data helpers
@pytest.fixture
def book_lookup():
    return BOOK_LOOKUP

@pytest.fixture
def sorted_books():
    return SORTED_BOOKS

# unit/test_services.py
@pytest.fixture
def last_read():
    def factory(book="Kejadian", chapter=3):
        m = MagicMock()
        m.book_name = book
        m.chapter = chapter
        return m
    return factory