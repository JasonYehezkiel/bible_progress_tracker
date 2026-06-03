import logging
import pandas as pd
from datetime import date
from pathlib import Path
from typing import Dict, List, Tuple, Union
from tqdm.auto import tqdm

from bible import load_bible_data, build_book_lookup, build_sorted_books
from classification import MessageClassifier
from core import setup_logger
from extraction import BibleReferenceExtractor
from compliance import ComplianceChecker, ReadingPlanSchedule
from sessions import (
    get_session,
    get_or_create_member,
    get_member_by_names,
    get_processed_set,
    insert_message,
    mark_message_processed,
    insert_reference,
    expand_and_insert_progress,
    get_last_read_by_member_id,
)
from services import preprocess, apply_gap_fill, ref_as_last, format_header
from bible.normalization import BibleReferenceNormalizer
from core.config import READING_PLAN_PATH

setup_logger('bible_pipeline')
logger = logging.getLogger('bible_pipeline.pipelines')

class BibleProgressPipeline:
    """
    End-to-end orchestration: extract → persist → schedule → summarize.
    """
    def __init__(
            self,
            bible_books: List[Dict] = None,
            plan_path: Union[str, Path] = READING_PLAN_PATH,
    ):
        if bible_books is None:
            bible_books = load_bible_data()
        self.bible_books = bible_books

        self.book_lookup = build_book_lookup(self.bible_books['books'])
        self.sorted_books = build_sorted_books(self.book_lookup)

        self.classifier = MessageClassifier()
        self.extractor = BibleReferenceExtractor()
        self.normalizer = BibleReferenceNormalizer()
        
        self.schedule = ReadingPlanSchedule(self.sorted_books, plan_path)
        self.checker = ComplianceChecker(self.schedule)
    
    def prepare_progress(self, df: pd.DataFrame) -> pd.DataFrame:
        """Classify messages and return only progress-labeled rows."""
        df = df.copy()
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        nat_count = df['timestamp'].isna().sum()
        if nat_count:
            logger.warning('Dropped %d rows with unparseable timestamps', nat_count)
        df = df.dropna(subset=['timestamp'])

        df['timestamp'] = df['timestamp'].dt.floor('s')
        df['date'] = pd.to_datetime(df['timestamp'].dt.date)
        df['message_clean'] = df['message'].apply(preprocess)

        df = self.classifier.classify(df, text_column='message_clean')
        progress_df = df[df['label'] == 'progress']

        filtered = len(df) - len(progress_df)
        if filtered:
            logger.info('Classifier filtered: %d non-progress messages', filtered)

        return progress_df

    def _persist_row(
            self,
            session,
            row: pd.Series,
            refs: List[Dict],
            member_cache: Dict,
    ) -> Dict:
        """Write extracted refs for a single message row within an existing session."""
        name = row['sender']
        if name not in member_cache:
            member_cache[name] = get_or_create_member(session, name=name)
        member = member_cache[name]

        message = insert_message(
                session, 
                member=member,
                raw_text=row['message'],
                timestamp=row['timestamp']
            )
        
        if message.processed_at is not None:
            logger.debug('Message id=%d already processed. skipping', message.id)
            return {'refs': 0, 'chapters': 0, 'skipped': 0}

        if not refs:
            logger.debug('No refs extracted for sender=%s: %r', name, row['message'][:60])
            mark_message_processed(session, message)
            return {'refs': 0, 'chapters': 0, 'skipped': 0}
        
        logger.debug('Message for sender=%s → %d ref(s) found', name, len(refs))

        total_refs = 0
        skipped = 0
        total_chapters = 0

        db_last = get_last_read_by_member_id(session, member.id, row['date'])
        last = ref_as_last({
            'book_end': db_last.book_name,
            'end_chapter': db_last.chapter,
        }) if db_last else None

        for ref in self.normalizer.normalize(refs):
            total_refs += 1
            ref = apply_gap_fill(ref, last)
            db_ref = insert_reference(session, message=message, ref=ref)

            if db_ref is None:
                skipped += 1
                continue

            last = ref_as_last({'book_end': db_ref.book_end or db_ref.book_start, 
                                'end_chapter': db_ref.end_chapter or db_ref.start_chapter})
            
            total_chapters += expand_and_insert_progress(
                session,
                member=member,
                ref=db_ref,
                date_read=row['date'],
                book_lookup=self.book_lookup,
                sorted_books=self.sorted_books,
            )

        mark_message_processed(session, message)
        return {'refs': total_refs - skipped, 'chapters': total_chapters, 'skipped': skipped}
    
    # Batch processing
    def get_pending_rows(self, progress_df: pd.DataFrame) -> Tuple[List[pd.Series], int]:
        """Filter already-processed messages."""
        rows = [row for _, row in progress_df.iterrows()]
        candidates = [(row['sender'], row['timestamp']) for row in rows]

        with get_session() as session:
            already_done = get_processed_set(session, candidates)
        
        pending_rows = [row for row in rows
                        if (row['sender'], row['timestamp']) not in already_done]
        
        return pending_rows, len(candidates) - len(pending_rows)
        
    def process_batch(self, df: pd.DataFrame) -> Dict:
        """Process all rows in a DataFrame and persist results"""
        progress_df = self.prepare_progress(df)
        totals = {'refs': 0, 'chapters': 0, 'skipped': 0, 'resumed': 0}

        pending_rows, resumed = self.get_pending_rows(progress_df)
        totals['resumed'] = resumed

        if resumed:
            logger.info('Skipped %d already-processed messages', totals['resumed'])

        if not pending_rows:
            logger.info('Batch complete — nothing new to process')
            return totals
        
        messages = [row['message_clean'] for row in pending_rows]
        all_refs = self.extractor.extract_batch(messages)

        unique_senders = list({row['sender'] for row in pending_rows})
        with get_session() as session:
            member_cache = get_member_by_names(session, unique_senders)

            for row, refs in tqdm(
                zip(pending_rows, all_refs), 
                total=len(pending_rows), 
                desc='Persisting'
            ):
                try:
                    with session.begin_nested():
                        result = self._persist_row(session, row, refs, member_cache)
                        for k in ('refs', 'chapters', 'skipped'):
                            totals[k] += result[k]
                except Exception as e:
                    logger.error('Failed: sender=%s ts=%s message=%r — %s', 
                                 row['sender'], row['timestamp'], row['message'], e)
                
        logger.info(
            'Batch complete — refs=%d chapters=%d skipped=%d',
            totals['refs'], totals['chapters'], totals['skipped']
        )
        return totals
    
    def process(self, row: pd.Series) -> Dict:
        """Extract references from one message row and persist result"""
        return self.process_batch(pd.DataFrame([row]))
    
    # Summarize
    def summarize(self, target_date: date) -> None:
        """
        Daily compliance summary for all members
        """
        assigned = self.schedule.get_by_date(target_date)
        header = format_header(assigned)
        emoji = self.schedule.get_emoji(target_date)

        results = self.checker.check_all(target_date)

        non_compliant = [r.member for r in results if not r.is_complete]
        last_positions = {}
        if non_compliant:
            with get_session() as session:
                member_cache = get_member_by_names(session, non_compliant)
                for name in non_compliant:
                    member = member_cache.get(name)
                    if not member:
                        continue
                    last = get_last_read_by_member_id(session, member.id, target_date)
                    last_positions[name] = ({'book_name': last.book_name,
                                             'chapter': last.chapter} if last else None)

        lines = [f'📖 *{header}* 📖']
        for i, result in enumerate(results, 1):
            if result.is_complete:
                lines.append(f'{i}. {result.member} {emoji}')
            else:
                
                last = last_positions.get(result.member)
                last_str = f'{last['book_name'][:3]} {last['chapter']}' if last else '' 
                lines.append(f'{i}. {result.member} {last_str}')
        
        return '\n'.join(lines)