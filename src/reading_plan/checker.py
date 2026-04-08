from datetime import date
from typing import Dict, List, Tuple

from sessions.database import get_session
from sessions.crud import get_progress_by_member_date, get_all_progress_by_date
from reading_plan.schedule import ReadingPlanSchedule, ScheduledChapter

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
    ):
        self.member = member
        self.target_date = target_date
        self.assigned = assigned
        read_set = set(read)
        self.completed = [c for c in assigned if c in read_set]
        self.missing = [c for c in assigned if c not in read_set]
    
    @property
    def completion_rate(self) -> float:
        if not self.assigned:
            return 1.0
        return len(self.completed) / len(self.assigned)
    
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
    Checks reading compliance for members against the plan schedule
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

        with get_session() as session:
            all_rows = get_all_progress_by_date(session, target_date)
        
        by_member: Dict[str, List[ScheduledChapter]] = {}
        for row in all_rows:
            by_member.setdefault(row.member.name, []).append((row.book_name, row.chapter))
        
        return [
            ComplianceResult(
                member=name,
                target_date=target_date,
                assigned=assigned,
                read=chapters
            )
            for name, chapters in by_member.items()
        ]