from datetime import date
from typing import Dict, FrozenSet, List

from sessions.db import get_session
from sessions.repository import get_all_members, get_progress_by_member_date, get_all_progress_by_date
from compliance.schedule import ReadingPlanSchedule, ScheduledChapter

READING_STATUS =  {
    'ahead': {'label': 'Ahead', 'emoji': '🚀', 'color': '#22c55e', 'bg': '#f0fdf4'},
    'on_time': {'label': 'On Time', 'emoji': '✅', 'color': '#3b82f6', 'bg': '#eff6ff'},
    'late': {'label': 'Late', 'emoji': '❌', 'color': '#ef4444', 'bg': '#fef2f2'}
}

class ComplianceResult:
    """
    Compliance result for a one member on one date
    """
    def __init__(
            self,
            member: str,
            target_date: date,
            assigned: List[ScheduledChapter],
            read: List[ScheduledChapter],
            future_chapters: FrozenSet[ScheduledChapter] = frozenset(),
    ):
        self.member = member
        self.target_date = target_date
        self.assigned = assigned

        assigned_set = set(assigned)
        read_set = set(read)
        self.completed = [c for c in assigned if c in read_set]
        self.missing = [c for c in assigned if c not in read_set]
        self.extra = [c for c in read if c not in assigned_set and c in future_chapters]
    
    @property
    def is_complete(self) -> bool:
        """True when every assigned chapter was read."""
        return self.completion_rate == 1.0
    
    @property
    def completion_rate(self) -> float:
        """Fraction of assigned chapters completed 
        (1.0 when nothing is assigned)"""
        if not self.assigned:
            return 1.0
        return len(self.completed) / len(self.assigned)
    
    @property
    def status(self) -> str:
        """One of 'ahead', 'on_time', or 'late'"""
        if self.completion_rate == 1.0 and self.extra:
            return 'ahead'
        if self.completion_rate == 1.0:
            return 'on_time'
        return 'late'
    
    def to_dict(self) -> Dict:
        return {
            'member': self.member,
            'date': self.target_date,
            'assigned': len(self.assigned),
            'completed': len(self.completed),
            'missing': self.missing,
            'completion_rate': round(self.completion_rate, 3),
            'is_complete': self.is_complete,
        }
    
    def __repr__(self) -> str:
        return (
            f'<ComplianceResult {self.member} {self.target_date} '
            f'{len(self.completed)}/{len(self.assigned)} chapters>'
        )

class ComplianceChecker:
    """
    Checks reading compliance for members against the plan schedule.
    """
    def __init__(self, schedule: ReadingPlanSchedule):
        self.schedule = schedule
    
    def check_member(self, member_name: str, target_date: date) -> ComplianceResult:
        """Check one member's compliance for a given date."""
        assigned = self.schedule.get_by_date(target_date)

        with get_session() as session:
            rows = get_progress_by_member_date(session, member_name, target_date)

            read = [(r.book_name, r.chapter) for r in rows]
        
        return ComplianceResult(
            member=member_name,
            target_date=target_date,
            assigned=assigned,
            read=read,
        )

    def check_all(self, target_date: date) -> List[ComplianceResult]:
        """Check compliance for all members who logged any reading on a specific date"""
        assigned = self.schedule.get_by_date(target_date)
        future_chapters = frozenset(ch for d, chapters in self.schedule.by_date.items() 
                                    if d > target_date for ch in chapters)

        with get_session() as session:
            all_members = get_all_members(session)
            all_rows = get_all_progress_by_date(session, target_date)

            id_to_name = {m.id: m.name for m in all_members}
            by_member = {m.name: [] for m in all_members}
            for row in all_rows:
                name = id_to_name.get(row.member_id)
                if name:
                    by_member[name].append((row.book_name, row.chapter))
        
        return [
            ComplianceResult(
                member=name,
                target_date=target_date,
                assigned=assigned,
                read=chapters,
                future_chapters=future_chapters,
            )
            for name, chapters in by_member.items()
        ]