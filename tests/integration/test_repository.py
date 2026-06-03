import pytest
import pandas as pd
from datetime import date, datetime, timezone

from sessions.db import Member, Message, BibleReference, ReadingProgress
from sessions import repository as repo

def make_ref_dict(**overides):
    base = {
        'book_start': 'Kejadian',
        'start_chapter': 1,
        'book_end': 'Kejadian',
        'end_chapter': 3,
        'is_valid': True,
    }
    base.update(overides)
    return base


# Members

class TestGetAllMembers:
    def test_returns_sorted_alphabetically(self, db_session):
        for name in ['Zara', 'Andi', 'Maya', 'Nur']:
            db_session.add(Member(name=name))
        db_session.flush()

        members = repo.get_all_members(db_session)
        names = [m.name for m in members]
        assert names == sorted(names)
    
    def test_empty_returns_empty_list(self, db_session):
        assert repo.get_all_members(db_session) == []

class GetMemberByNames:
    def test_bulk_fetch(self, db_session, db_member, db_member_two):
        result = repo.get_member_by_names(
            db_session, [db_member.name, db_member_two.name]
        )

        assert isinstance(result, dict)
        assert db_member.name in result
        assert db_member_two.name in result
    
    def test_missing_names_not_in_result(self, db_session, db_member):
        result = repo.get_member_by_names(db_session, [db_member.name, 'Gunawan'])
        assert 'Gunawan' not in result
        assert db_member.name in result
    
    def test_empty_list_returns_empty_dict(self, db_session):
        result = repo.get_member_by_names(db_session, [])
        assert result == {}

# Messages

class TestInsertMessage:
    def test_insert_new_message(self, db_session, db_member):
        ts = datetime(2024, 6, 1, 10, 0, 0)
        msg  = repo.insert_message(db_session, db_member, ts, 'Baca Kejadian 1')

        assert msg is not None
        assert msg.id is not None
        assert msg.member_id == db_member.id
        assert msg.processed_at is None
    
    def test_returns_existing_on_duplicate(self, db_session, db_message):
        dup = repo.insert_message(
            db_session,
            db_message.member,
            db_message.timestamp,
            'different text',
        )
        assert dup.id == db_message.id
    
    def test_timestamp_floored_to_second(self, db_session, db_member):
        ts_raw = datetime(2024, 6, 1, 10, 0, 0, 999999)
        msg = repo.insert_message(db_session, db_member, ts_raw, 'test')
        assert msg.timestamp.microsecond == 0


class TestMarkMessageProcessed:
    def test_sets_processed_at(self, db_session, db_message):
        assert db_message.processed_at is None
        repo.mark_message_processed(db_session, db_message)
        assert db_message.processed_at is not None
    
    def test_processed_at_is_recent_utc(self, db_session, db_message):
        before = datetime.now(timezone.utc)
        repo.mark_message_processed(db_session, db_message)
        after = datetime.now(timezone.utc)

        processed = db_message.processed_at.replace(tzinfo=timezone.utc)
        assert before <= processed <= after


class TestGetProcessedSet:
    def test_returns_empty_for_no_candidates(self, db_session):
        result = repo.get_processed_set(db_session, [])
        assert result == set()
    
    def test_excludes_unprocessed_messages(self, db_session, db_member, db_message):
        candidates = [(db_member.name, pd.Timestamp(db_message.timestamp))]
        result = repo.get_processed_set(db_session, candidates)
        assert result == set()
    
    def test_includes_processed_messages(self, db_session, db_member, db_message_processed):
        ts = pd.Timestamp(db_message_processed.timestamp)
        candidates = [(db_member.name, ts)]
        result = repo.get_processed_set(db_session, candidates)
        assert (db_member.name, ts) in result
    
    def test_unknown_sender_not_in_result(self, db_session):
        candidates = [('Nobody', pd.Timestamp('2024-01-01 00:00:00'))]
        result = repo.get_processed_set(db_session, candidates)
        assert result == set()

    def test_mixed_processed_and_unprocessed(self, db_session, db_member, db_message, db_message_processed):
        candidates = [
            (db_member.name, pd.Timestamp(db_message.timestamp)),
            (db_member.name, pd.Timestamp(db_message_processed.timestamp)),
        ]
        result = repo.get_processed_set(db_session, candidates)
        
        assert len(result) == 1
        assert (db_member.name, pd.Timestamp(db_message_processed.timestamp)) in result


# Bible References

class TestInsertReference:
    def test_inserts_valid_reference(self, db_session, db_message):
        ref_dict = make_ref_dict()
        ref = repo.insert_reference(db_session, db_message, ref_dict)
        
        assert ref is not None
        assert ref.id is not None
        assert ref.book_start == "Kejadian"
        assert ref.start_chapter == 1
        assert ref.end_chapter == 3
    
    def test_skips_invalid_reference(self, db_session, db_message):
        ref_dict = make_ref_dict(is_valid=False)
        result = repo.insert_reference(db_session, db_message, ref_dict)
        assert result is None
    
    def test_missing_is_valid_key_skips(self, db_session, db_message):
        result = repo.insert_reference(db_session, db_message, {})
        assert result is None


# Reading Progress


class TestInsertReadingProgress:
    def test_insert_single_row(self, db_session, db_member, db_reference):
        repo.insert_reading_progress(
            db_session,
            member=db_member,
            book_id=1,
            book_name='Kejadian',
            chapter=5,
            date_read=datetime(2024, 3, 1),
            ref=db_reference,
        )
        db_session.flush()

        row = db_session.query(ReadingProgress).filter_by(
            member_id=db_member.id, book_id=1, chapter=5
        ).first()

        assert row is not None
        assert row.date_read == date(2024, 3, 1)
    
    def test_duplicate_insert_silently_ignored(self, db_session, db_member, db_reference):
        kwargs = dict(
            session=db_session, member=db_member, book_id=1,
            book_name='Kejadian', chapter=7, date_read=datetime(2024, 3, 1), ref=db_reference,
        )
        repo.insert_reading_progress(**kwargs)
        db_session.flush()
        repo.insert_reading_progress(**kwargs)
        db_session.flush()

        count = db_session.query(ReadingProgress).filter_by(
            member_id=db_member.id, book_id=1, chapter=7
        ).count()

        assert count == 1

class TestExpandAndInsertProgress:

    def test_single_book_range(self, db_session, db_member, db_reference,
                               book_lookup, sorted_books):
        inserted = repo.expand_and_insert_progress(
            db_session, db_member, db_reference,
            date_read=date(2024, 1, 15),
            book_lookup=book_lookup,
            sorted_books=sorted_books,
        )
        assert inserted == 3

        rows = db_session.query(ReadingProgress).filter_by(
            member_id=db_member.id, book_id=1
        ).all()
        chapters = [r.chapter for r in rows]
        assert chapters == [1, 2, 3]

    def test_cross_book_range(self, db_session, db_member, db_message, 
                              book_lookup, sorted_books):
        ref = BibleReference(
            message_id=db_message.id,
            book_start='Kejadian', start_chapter=49,
            book_end='Keluaran', end_chapter=2,
            is_valid=True,
        )
        db_session.add(ref)

        inserted = repo.expand_and_insert_progress(
            db_session, db_member, ref,
            date_read=date(2024, 1, 20),
            book_lookup=book_lookup,
            sorted_books=sorted_books,
        )

        assert inserted == 4

        kej_rows = db_session.query(ReadingProgress).filter_by(
            member_id=db_member.id, book_id=1
        ).all()
        kel_rows = db_session.query(ReadingProgress).filter_by(
            member_id=db_member.id, book_id=2
        ).all()

        assert [r.chapter for r in kej_rows] == [49, 50]
        assert [r.chapter for r in kel_rows] == [1, 2]
    
    def test_unknown_book_return_zero(self, db_session, db_member, db_message,
                                      book_lookup, sorted_books):
        ref = BibleReference(
            message_id=db_message.id,
            book_start='Wahyu', start_chapter=1, # Not in SAMPLE_BOOKS
            book_end='Wahyu', end_chapter=3,
            is_valid=True,
        )
        db_session.add(ref)
        db_session.flush()

        inserted = repo.expand_and_insert_progress(
            db_session, db_member, ref,
            date_read=date(2024, 1, 20),
            book_lookup=book_lookup,
            sorted_books=sorted_books,
        )

        assert inserted == 0
    
    def test_idempotent_on_duplicate_chapters(self, db_session, db_member, 
                                              db_reference, book_lookup, sorted_books):
        d = date(2024, 1, 15)
        inserted_first  = repo.expand_and_insert_progress(
            db_session, db_member, db_reference, d, book_lookup, sorted_books
        )
        db_session.flush()
        inserted_second = repo.expand_and_insert_progress(
            db_session, db_member, db_reference, d, book_lookup, sorted_books
        )
        db_session.flush()
 
        assert inserted_first == 3
        assert inserted_second == 3

        count = db_session.query(ReadingProgress).filter_by(
            member_id=db_member.id, book_id=1
        ).count()
        assert count == 3
    
class TestGetAllProgressGrouped:
    def test_groups_by_member_id(self, db_session, db_member, db_member_two, 
                                 db_reference, db_progress):
        rp = ReadingProgress(
            member_id=db_member_two.id,
            book_id=40, book_name="Matius", chapter=1,
            date_read=date(2024, 1, 15), ref_id=db_reference.id,
        )
        db_session.add(rp)
        db_session.flush()

        grouped = repo.get_all_progress_grouped(db_session)

        assert db_member.id in grouped
        assert db_member_two.id in grouped
        assert len(grouped[db_member.id]) == 3
        assert len(grouped[db_member_two.id]) == 1
    
    def test_empty_db_returns_empty_dict(self, db_session):
        result = repo.get_all_progress_grouped(db_session)
        assert result == {}
    

class TestGetProgressByMemberDate:
    def test_returns_rows_for_matching_date(self, db_session, db_member, db_progress):
        rows = repo.get_progress_by_member_date(
            db_session, db_member.name, date(2024, 1, 15)
        )
        assert len(rows) == 3
    
    def test_returns_empty_for_wrong_date(self, db_session, db_member, db_progress):
        rows = repo.get_progress_by_member_date(
            db_session, db_member.name, date(2099, 1, 1)
        )
        assert rows == []
    
    def test_returns_empty_for_unknown_member(self, db_session):
        rows = repo.get_progress_by_member_date(
            db_session, 'Unknown', date(20, 1, 1)
        )
        assert rows == []


class TestGetProgressByMember:
    def test_returns_all_rows(self, db_session, db_member, db_progress):
        rows = repo.get_progress_by_member(
            db_session, db_member.name
        )
        assert len(rows) == 3
    
    def test_returns_empty_for_unknown_member(self, db_session):
        rows = repo.get_progress_by_member(db_session, 'Unknown')
        assert rows == []

class TestGetAllProgressByDate:
    def test_returns_rows_across_members(self, db_session, db_member, 
                                         db_member_two, db_reference, db_progress):
        rp = ReadingProgress(
            member_id=db_member_two.id,
            book_id=40, book_name="Matius", chapter=1,
            date_read=date(2024, 1, 15), ref_id=db_reference.id,
        )
        db_session.add(rp)
        db_session.flush()

        rows = repo.get_all_progress_by_date(db_session, date(2024, 1, 15))
        member_ids = [r.member_id for r in rows]
        assert db_member.id in member_ids
        assert db_member_two.id in member_ids
    
    def test_returns_empty_for_date_with_no_rows(self, db_session):
        rows = repo.get_all_progress_by_date(db_session, date(2099, 12, 31))
        assert rows == []

class TestGetLastReadByMemberId:
    def test_return_latest_chapter(self, db_session, db_member, db_reference,
                                   db_progress):
        rp = ReadingProgress(
            member_id=db_member.id,
            book_id=40, book_name="Kejadian", chapter=5,
            date_read=date(2024, 1, 20), ref_id=db_reference.id,
        )
        db_session.add(rp)
        db_session.flush()

        last = repo.get_last_read_by_member_id(
            db_session, db_member.id, up_to_date=date(2024, 1, 20)
        )
        assert last is not None
        assert last.chapter == 5
    
    def test_respects_up_to_date_cutoff(self, db_session, db_member, db_reference,
                                        db_progress):
        rp = ReadingProgress(
            member_id=db_member.id,
            book_id=40, book_name="Kejadian", chapter=10,
            date_read=date(2024, 2, 1), ref_id=db_reference.id,
        )
        db_session.add(rp)
        db_session.flush()

        last = repo.get_last_read_by_member_id(
            db_session, db_member.id, up_to_date=date(2024, 1, 15)
        )

        assert last.chapter == 3
    
    def test_returns_none_for_member_with_no_progress(self, db_session, db_member_two):
        last = repo.get_last_read_by_member_id(
            db_session, db_member_two.id, up_to_date=date(2024, 12, 31)
        )
        assert last is None
    
    def test_prefers_higher_book_on_same_date(self, db_session, db_member, 
                                              db_reference, db_message):
        kel_ref = BibleReference(
            message_id=db_message.id,
            book_start='Keluaran', start_chapter=1,
            book_end='Keluaran', end_chapter=1,
            is_valid=True,
        )
        db_session.add(kel_ref)
        db_session.flush()

        d = date(2024, 1, 15)
        for book_id, book_name, chapter, ref in [
            (1, 'Kejadian', 1, db_reference),
            (2, 'Keluaran', 1, kel_ref)
        ]:
            db_session.add(ReadingProgress(
                member_id=db_member.id,
                book_id=book_id, book_name=book_name,
                chapter=chapter, date_read=d, ref_id=ref.id,
            ))
        db_session.flush()

        last = repo.get_last_read_by_member_id(
            db_session, db_member.id, up_to_date=d,
        )
        assert last.book_id == 2