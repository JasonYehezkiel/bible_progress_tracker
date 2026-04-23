from pathlib import Path
from typing import Generator

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session, relationship, sessionmaker
from contextlib import contextmanager
from config.settings import DATABASE_PATH

engine = create_engine(
    f'sqlite:///{DATABASE_PATH}',
    connect_args={'check_same_thread': False},
    echo=False,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Yield a database session and close it after use."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

# Base
class Base(DeclarativeBase):
    pass

# Models
class Member(Base):
    __tablename__ = 'members'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True)

    messages = relationship('Message', back_populates='member')
    reading_progress = relationship('ReadingProgress', back_populates='member')

    def __repr__(self) -> str:
        return f'<Member id={self.id} name={self.name!r}>'

class Message(Base):
    __tablename__ = 'messages'

    id = Column(Integer, primary_key=True, autoincrement=True)
    member_id = Column(Integer, ForeignKey('members.id'), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    raw_text = Column(Text, nullable=False)
    processed_at = Column(DateTime, nullable=True, default=None)

    __table_args__ = (
        UniqueConstraint('member_id', 'timestamp', name='uq_member_timestamp'),
    )

    member = relationship('Member', back_populates='messages')
    references = relationship('BibleReference', back_populates='message')

    @property
    def is_processed(self) -> bool:
        return self.processed_at is not None

    def __repr__(self) -> str:
        return f'<Message id={self.id} member_id={self.member_id} processed={self.is_processed}>'

class BibleReference(Base):
    __tablename__ = 'references'

    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(Integer, ForeignKey('messages.id'), nullable=False)
    book_start = Column(String(100), nullable=False)
    start_chapter = Column(Integer, nullable=False)
    book_end = Column(String(100), nullable=False)   
    end_chapter = Column(Integer, nullable=False)
    is_valid = Column(Boolean, default=True, nullable=False)

    message = relationship('Message', back_populates='references')
    reading_progress = relationship('ReadingProgress', back_populates='reference')

    @property
    def member(self):
        return self.message.member

    def __repr__(self) -> str:
        return (
            f'<BibleReference id={self.id} '
            f'{self.book_start} {self.start_chapter}-{self.end_chapter}>'
        )

class ReadingProgress(Base):
    __tablename__ = 'reading_progress'

    id = Column(Integer, primary_key=True, autoincrement=True)
    member_id = Column(Integer, ForeignKey('members.id'), nullable=False)
    book_id = Column(Integer, nullable=False)
    book_name = Column(String(100), nullable=False)
    chapter = Column(Integer, nullable=False)   
    date_read = Column(Date, nullable=False)
    ref_id = Column(Integer, ForeignKey('references.id'), nullable=True)

    __table_args__ = (
        UniqueConstraint('member_id', 'book_id', 'chapter', name='uq_member_book_chapter'), 
    )

    member = relationship('Member', back_populates='reading_progress')
    reference = relationship('BibleReference', back_populates='reading_progress')

    def __repr__(self) -> str:
        return (
            f'<ReadingProgress member_id={self.member_id} '
            f'{self.book_name} ch.{self.chapter}'
        )

def create_tables():
    """Create all tables if they don't exist."""
    Base.metadata.create_all(bind=engine)
    print(f'Tables created at: {DATABASE_PATH}')