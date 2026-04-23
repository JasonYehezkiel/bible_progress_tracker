import logging
import pandas as pd
from datetime import date
from pathlib import Path
from typing import Dict, List, Union
from tqdm.auto import tqdm

from logger import setup_logger
from services import apply_gap_fill, preprocess, format_header
from config import CONFIG_PATH, AGGREGATION_STRATEGY
from extraction import BibleReferenceExtractor
from preprocessing.normalization import BibleReferenceNormalizer
from reading_plan import ComplianceChecker, ReadingPlanSchedule
from sessions import (
    get_session,
    get_or_create_member,
    get_all_members,
    insert_message,
    mark_message_processed,
    is_message_processed,
    insert_reference,
    expand_and_insert_progress,
    get_last_read_by_member,
    get_all_progress_by_date,
)

setup_logger('bible_pipeline')
logger = logging.getLogger('bible_pipeline.pipelines')

class BibleProgressPipeline:
    """
    End-to-end orchestration: extract → persist → schedule → summarize.
    """
    def __init__(
            self,
            bible_books: List[Dict],
            saved_path: Union[str, Path],
            config_path: Union[str, Path] = CONFIG_PATH,
            aggregation_strategy: str = AGGREGATION_STRATEGY,
            plan_path: Union[str, Path] = None
    ):
        self.bible_books = bible_books
        self.extractor = BibleReferenceExtractor(saved_path, config_path, aggregation_strategy)
        self.normalizer = BibleReferenceNormalizer()
        
        plan_kwargs = {'bible_books': bible_books}
        if plan_path:
            plan_kwargs['plan_path'] = Path(plan_path)
        self.schedule = ReadingPlanSchedule(**plan_kwargs)
        self.checker = ComplianceChecker(self.schedule)

    def process(self, row: pd.Series) -> Dict:
        """Extract references from one message row and persist result"""
        with get_session() as session:
            if is_message_processed(session, row['sender'], row['timestamp']):

                logger.debug(
                    'Already processed: sender=%s ts=%s, skipping', row['sender'], row['timestamp']
                    )
                return {'refs': 0, 'chapters': 0, 'skipped': 0, 'resumed': 1}
        
        message = preprocess(row['message'])
        refs = self.extractor.extract(message)
        return self.persist(row, refs)

    def process_batch(self, df: pd.DataFrame) -> Dict:
        """Process all rows in a DataFrame and persist results"""
        totals = {'refs': 0, 'chapters': 0, 'skipped': 0, 'resumed': 0}

        pending_rows = []
        for _, row in df.iterrows():
            with get_session() as session:
                if is_message_processed(session, row['sender'], row['timestamp']):
                    totals['resumed'] += 1
                else:
                    pending_rows.append(row)

        if totals['resumed']:
            logger.info('Skipped %d already-processed messages', totals['resumed'])

        if not pending_rows:
            logger.info('Batch complete — nothing new to process')
            
        messages = [preprocess(row['message']) for row in pending_rows]
        all_refs = self.extractor.extract_batch(messages)

        for row, refs in tqdm(
            zip(pending_rows, all_refs),
            total=len(pending_rows),
            desc='Persisting',
        ):
            try:
                result = self.persist(row, refs)
                for k in ('refs', 'chapters', 'skipped'):
                    totals[k] += result[k]
            except Exception as e:
                logger.error('Failed: sender=%s ts=%s — %s', row['sender'], row['timestamp'], e)
                continue
            
        logger.info(
            'Batch complete — refs=%d chapters=%d skipped=%d',
            totals['refs'], totals['chapters'], totals['skipped']
        )
        return totals
    
    def persist(self, row: pd.Series, refs: List[Dict]) -> Dict:
        """Write extracted refs to the DB for a single message row."""
        with get_session() as session:
            member = get_or_create_member(session, name=row['sender'])
            message = insert_message(
                session, 
                member=member,
                raw_text=row['message'],
                timestamp=row['timestamp']
            )
            
            if not refs:
                logger.debug('No refs extracted for sender=%s: %r', row['sender'], row['message'][:60])
                mark_message_processed(session, message)
                return {'refs': 0, 'chapters': 0, 'skipped': 0, 'resumed': 0}

            logger.debug('Message for sender=%s → %d ref(s) found', row['sender'], len(refs))

            total_refs = 0
            skipped = 0
            total_chapters = 0

            last = get_last_read_by_member(session, member.name, row['date'])

            for ref in self.normalizer.normalize(refs):
                total_refs += 1
                ref = apply_gap_fill(ref, last)
                db_ref = insert_reference(session, message=message, ref=ref)

                if db_ref is None:
                    skipped += 1
                    continue

                last = db_ref

                total_chapters += expand_and_insert_progress(
                    session,
                    member=member,
                    ref=db_ref,
                    date_read=row['date'],
                    bible_books=self.bible_books,
                )

            mark_message_processed(session, message)

        return {'refs': total_refs - skipped, 'chapters': total_chapters, 'skipped': skipped, 'resumed': 0}
    
    # Compliance
    def check_member(self, member_name: str, target_date: date) -> Dict:
        """Check one member's compliance on a specific date"""
        return self.checker.check_member(member_name, target_date).to_dict()

    def check_all(self, target_date: date) ->  List[Dict]:
        """Check compliance for all members who logged reading on a specific date"""
        return [r.to_dict() for r in self.checker.check_all(target_date)]
    
    # Summarize
    def summarize(self, target_date: date) -> None:
        """
        Daily compliance summary for all members
        """
        assigned = self.schedule.get_by_date(target_date)
        header = format_header(assigned)
        emoji = self.schedule.get_emoji(target_date)
        assigned_set = set(assigned)

        with get_session() as session:
            all_members = get_all_members(session)

            progress_rows = get_all_progress_by_date(session, target_date)
            read_by_member: Dict[int, set] = {}
            for row in progress_rows:
                read_by_member.setdefault(row.member_id, set()).add(
                    (row.book_name, row.chapter)
                )
            
            last_read = {}
            for member in all_members:
                read = read_by_member.get(member.id, set())
                if not (assigned_set and assigned_set.issubset(read)):
                    last = get_last_read_by_member(session, member.name, target_date)
                    last_read[member.id] = (
                        f'{last.book_name[:3]} {last.chapter}' if last else ''
                    )

            print(f'📖 *{header}* 📖')
            for i, member in enumerate(all_members, 1):
                read = read_by_member.get(member.id, set())
                done = assigned_set and assigned_set.issubset(read)
                if done:
                    print(f'{i}. {member.name} {emoji}')
                else:
                    last = last_read.get(member.id)
                    print(f'{i}. {member.name} {last}')
    
    def get_normalizer_stats(self) -> Dict:
        """Normalizer resolution stats from the underlying extractor."""
        return self.normalizer.get_stats()