import pandas as pd
from datetime import date
from pathlib import Path
from typing import Dict, List, Tuple
from config.settings import READING_PLAN_PATH

ScheduledChapter = Tuple[str, int]

class ReadingPlanSchedule:
    """
    Load a reading plan CSV and each day's range into individual 
    (book_name, chapter) tuples — including cross-book days.
    """

    def __init__(self, bible_books: List[Dict], plan_path: Path = READING_PLAN_PATH):
        self.all_books = sorted(bible_books, key=lambda b: b['id'])

        raw = pd.read_csv(
            plan_path, 
            dtype={'book_end': str, 'end_chapter': 'Int64', 'emoji': str},
        )
        raw['date'] = pd.to_datetime(raw['date']).dt.date

        # date → [(book_name, chapter), ...]
        self.by_date: Dict[date, List[ScheduledChapter]] = {}
        # day → [(book_name, chapter), ...]
        self.by_day: Dict[int, List[ScheduledChapter]] = {}
        # date → emoji
        self.emoji: Dict[date, str] = {}

        for _, row in raw.iterrows():
            chapters = self.expand(row)
            self.by_date.setdefault(row['date'], []).extend(chapters)
            self.by_day.setdefault(int(row['day']), []).extend(chapters)
            if row['date'] not in self.emoji:
                raw_emoji = row.get('emoji')
                emoji = str(raw_emoji).strip()
                self.emoji[row['date']] = emoji

    def expand(self, row) -> List[ScheduledChapter]:
        """Expand one CSV row into individual (book_name, chapter) tuples"""
        book_start_name = row['book_start']
        book_end_name = row['book_end'] if pd.notna(row['book_end']) and str(row['book_end']).strip() else None
        end_ch = int(row['end_chapter']) if pd.notna(row['end_chapter']) else None
        is_cross_book = book_end_name is not None and book_end_name != book_start_name
        
        chapters: List[ScheduledChapter] = []

        if not is_cross_book:
            ch_end = end_ch or int(row['start_chapter'])
            for ch in range(int(row['start_chapter']), (end_ch or int(row['start_chapter'])) + 1):
                chapters.append((book_start_name, ch))
        
        else:
            # Cross-book: walk from start_book to end_book
            in_range = False
            for book in self.all_books:
                if book['name'] == book_start_name:
                    in_range = True
                if not in_range:
                    continue

                ch_start = int(row['start_chapter']) if book['name'] == book_start_name else 1
                ch_end = end_ch if book['name'] == book_end_name else book['chapters']

                for ch in range(ch_start, ch_end + 1):
                    chapters.append((book['name'], ch))
                
                if book['name'] == book_end_name:
                    break
        
        return chapters

    def get_by_date(self, target_date: date) -> List[ScheduledChapter]:
        """Return scheduled (book, chapter) list for a calendar date."""
        return self.by_date.get(target_date, [])

    def get_by_day(self, day: int) -> List[ScheduledChapter]:
        """Return scheduled (book, chapter) list for a plan day number."""
        return self.by_day.get(day, [])
    
    def get_emoji(self, target_date: date) -> str:
        """Return the completion emoji for a given date."""
        return self.emoji.get(target_date, '💥')
    
    @property
    def dates(self) -> List[date]:
        return sorted(self.by_date.keys())

    @property
    def total_days(self) -> int:
        return len(self.by_day)