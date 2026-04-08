import logging
from datetime import date, datetime, timezone
from typing import List, Dict, Optional

from sqlalchemy.orm import Session
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from logger import setup_logger
from sessions.database import Member, Message, BibleReference, ReadingProgress

setup_logger('bible_pipeline')
logger = logging.getLogger('bible_pipeline.sessions.crud')

# Members

def get_or_create_member(session: Session, name: str) -> Member:
    """Get an existing member by name or create a new one"""
    member = session.query(Member).filter_by(name=name).first()
    if not member:
        member = Member(name=name)
        session.add(member)
        session.flush()
        logger.debug('Created new member: %s', name)
    return member

def get_all_members(session: Session) -> List[Member]:
    """Return all members sorted alphabetically by name."""
    return session.query(Member).order_by(Member.name).all()

# Messages

def insert_message(
        session: Session,
        member: Member,
        timestamp: datetime,
        raw_text: str,
) -> Optional[Message]:
    """Insert a message row without marking it as processed."""
    existing = session.query(Message).filter_by(
        member_id=member.id,
        timestamp=timestamp,
    ).first()
    if existing:
        logger.debug('Message already exists id=%d sender=%s', existing.id, member.name)
        return existing
    
    message = Message(
        member_id=member.id,
        timestamp=timestamp,
        raw_text=raw_text,
        processed_at=None,
    )
    session.add(message)
    session.flush()
    return message

def mark_message_processed(session: Session, message: Message) -> None:
    """Mark a message as fully processed by setting processed_at to now."""
    message.processed_at = datetime.now(timezone.utc)
    session.flush()

def get_unprocessed_messages(session: Session) -> List[Message]:
    """Return all messages where processed_at is NULL"""
    return session.query(Message).filter(Message.processed_at.is_(None)).all()

def is_message_processed(session: Session, name: str, timestamp: datetime) -> bool:
    """Check if a message from a sender at this timestamp is already processed."""
    member = session.query(Member).filter_by(name=name).first()
    if not member:
        return False
    message = session.query(Message).filter_by(
        member_id=member.id,
        timestamp=timestamp,
    ).first()
    return message is not None and message.processed_at is not None

# Bible References

def insert_reference(
        session: Session,
        message: Message,
        ref: Dict,
) -> Optional[BibleReference]:
    """
    Insert one normalized reference dict from the pipeline.
    Skips invalid refs — only persist what's usable.
    """
    if not ref.get('is_valid', False):
        logger.debug('Skipping invalid ref: %s', ref)
        return None
    
    reference = BibleReference(
        message_id=message.id,
        book_start=ref['book_start'],
        start_chapter=ref['start_chapter'],
        book_end=ref['book_end'],
        end_chapter=ref['end_chapter'],
        is_valid=ref['is_valid'],
    )
    session.add(reference)
    session.flush()
    return reference

# Reading Progress

def insert_reading_progress(
    session: Session,
    member: Member,
    book_id: int,
    book_name: str,
    chapter: int,
    date_read: date,
    ref: BibleReference,
) -> None:
    """
    Insert one chapter into reading_progress.
    Silently skips duplicates (upsert on unique member+book+chapter).
    """
    stmt = (
        sqlite_insert(ReadingProgress)
        .values(
            member_id=member.id,
            book_id=book_id,
            book_name=book_name,
            chapter=chapter,
            date_read=date_read,
            ref_id=ref.id,
        )
        .on_conflict_do_nothing(
            index_elements=['member_id', 'book_id', 'chapter']
        )
    )
    session.execute(stmt)

def expand_and_insert_progress(
        session: Session,
        member: Member,
        ref: BibleReference,
        date_read: date,
        bible_books: List[Dict],
) -> int:
    """
    Expand a BibleReference range into individual chapter rows
    and insert each one into reading_progress.
 
    Args:
        bible_books: The full books list from load_bible_data(), used to
                     look up book_id and chapter counts for cross-book ranges.
 
    Returns:
        Number of chapters inserted
    """
    book_lookup = {b['name']:  b for b in bible_books}

    start_book = book_lookup.get(ref.book_start)
    end_book = book_lookup.get(ref.book_end) if ref.book_end else start_book

    if not start_book or not end_book:
        logger.warning(
            'Unknown book in ref id=%s: book_start=%r book_end=%r',
            ref.id, ref.book_start, ref.book_end,
        )
        return 0
    
    inserted = 0

    # Single book range
    if start_book['id'] == end_book['id']:
        for ch in range(ref.start_chapter, ref.end_chapter + 1):
            insert_reading_progress(
                session, member,
                book_id=start_book['id'],
                book_name=start_book['name'],
                chapter=ch,
                date_read=date_read,
                ref=ref,
            )
            inserted += 1
    
    # Cross-book range
    else:
        all_books = sorted(bible_books, key=lambda b: b['id'])
        in_range = False
        for book in all_books:
            if book['id'] == start_book['id']:
                in_range=True
            if not in_range:
                continue

            ch_start = ref.start_chapter if book['id'] == start_book['id'] else 1
            ch_end = ref.end_chapter if book['id'] == end_book['id'] else book['chapters']

            for ch in range(ch_start, ch_end + 1):
                insert_reading_progress(
                    session, member,
                    book_id=book['id'],
                    book_name=book['name'],
                    chapter=ch,
                    date_read=date_read,
                    ref=ref,
                )
                inserted += 1
        
            if book['id'] == end_book['id']:
                break

    return inserted

# Reading Progress Queries

def get_progress_by_member_date(
        session: Session,
        member_name: str,
        target_date: date,
) -> List[ReadingProgress]:
    """Return all ReadingProgress rows for a member on a specific date."""
    member = session.query(Member).filter_by(name=member_name).first()
    if not member:
        return []
    return (
        session.query(ReadingProgress)
        .filter_by(member_id=member.id, date_read=target_date)
        .all()
    )

def get_all_progress_by_date(
        session: Session,
        target_date: date,
) -> List[ReadingProgress]:
    """Return all ReadingProgress rows across all members on a specific date"""
    return (
        session.query(ReadingProgress)
        .filter_by(date_read=target_date)
        .all()
    )

def get_last_read_by_member(
        session: Session, 
        name: str,
        up_to_date: date,
) -> Optional[ReadingProgress]:
    """Return the most recently read chapter for a member across all dates."""
    member = session.query(Member).filter_by(name=name).first()
    if not member:
        return None
    return (
        session.query(ReadingProgress)
        .filter(
            ReadingProgress.member_id == member.id,
            ReadingProgress.date_read <= up_to_date,
        )
        .order_by(
            ReadingProgress.date_read.desc(),
            ReadingProgress.book_id.desc(),
            ReadingProgress.chapter.desc(),
        )
        .first()
    )