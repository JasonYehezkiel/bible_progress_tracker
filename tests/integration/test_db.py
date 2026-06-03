import pytest
from datetime import datetime, date, timezone
from unittest.mock import MagicMock, patch
 
from sessions.db import get_session

class TestGetSession:
    def test_commit_on_success(self):
        mock_session = MagicMock()

        with patch('sessions.db.SessionLocal', return_value=mock_session):
            with get_session() as session:
                assert session is mock_session
        
        mock_session.commit.assert_called_once()
        mock_session.rollback.assert_not_called()
        mock_session.close.assert_called_once()

    def test_rolls_back_on_exception(self):
        mock_session = MagicMock()

        with patch('sessions.db.SessionLocal', return_value=mock_session):
            with pytest.raises(ValueError):
                with get_session():
                    raise ValueError('boom')
        
        mock_session.rollback.assert_called_once()
        mock_session.commit.assert_not_called()
        mock_session.close.assert_called_once()
    
    def test_close_always_called_even_when_commit_fails(self):
        mock_session = MagicMock()
        mock_session.commit.side_effect = RuntimeError('commit failed')

        with patch('sessions.db.SessionLocal', return_value=mock_session):
            with pytest.raises(RuntimeError):
                with get_session():
                    pass
        
        mock_session.close.assert_called_once()

class TestIsProcessed:
    def test_false_when_processed_at_is_none(self, db_message):
        assert db_message.processed_at is None
        assert db_message.is_processed is False

    def tes_true_when_processed_at_is_set(self, db_message):
        assert db_message.processed_at is not None
        assert db_message.is_processed is True

class TestMemberProxy:
    def test_reference_member_walks_through_message(self, db_session, db_reference, db_member):
        db_session.refresh(db_reference)
        assert db_reference.member is not None
        assert db_reference.member.id == db_member.id
        assert db_reference.member.name == db_member.name