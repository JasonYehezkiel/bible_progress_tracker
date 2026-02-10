import pandas as pd
import re
from typing import List, Optional

class MessageFilter:
    """
    Filtering class for Whatsapp chat DataFrames.
    Support filtering by:
    - System messages
    - Message length
    - Specific senders
    - Date range
    """

    def __init__(self):
        # System message patterns (in Indonesian + english)
        self.system_message_pattern = re.compile(
            r"^("

            # Encryption notice
            r"Messages and calls are end-to-end encrypted.*|"
            r"Pesan dan panggilan terenkripsi.*|"

            # Group created
            r".+ created group.*|"
            r".+ membuat grup.*|"

            # Added members
            r".+ added .+|"
            r".+ menambahkan .+|"

            # Changed group settings
            r".+ changed .*|"
            r".+ mengubah .*|"

            # Removed members
            r".+ removed .+|"
            r".+ mengeluarkan .+|"
            
            # Left group
            r".+ left|"
            r".+ keluar|"

            # Message deleted
            r"This message was deleted\.?|"
            r"You deleted this message\.?|"
            r"Pesan ini dihapus\.?|"
            r"Anda menghapus pesan ini\.?|"

            r")$",
            flags=re.IGNORECASE
        )


        # filter media messages pattern
        self.media_message_pattern = re.compile(
            r"^("
            r"<.*?omitted>|"
            r"<.*?tidak disertakan>|"
            r"<(terlampir|attached):.*>"
            r")$",
            flags=re.IGNORECASE
        )

    
    def filter_system_messages(self, df: pd.DataFrame, drop: bool = True) -> pd.DataFrame:
        """
        Identify and optionally remove system messages from a chat DataFrame.

        Args:
            df: DataFrame containing parsed chat messages.
            drop: if True, system messages are removed
                  if False, a boolean column 'is_system_message' is added.

        Returns:
            Filtered DataFrame.
        """
        is_system = df['message'].str.contains(self.system_message_pattern, na=False)

        if drop:
            return df.loc[~is_system].reset_index(drop=True)

        df = df.copy()
        df['is_system_message'] = is_system

        return df
    
    def filter_messages_by_length(self, df: pd.DataFrame, min_length: int = 1, max_length: Optional[int] = None) -> pd.DataFrame:
        """
        Filter messages by their character length.

        Args:
            df: WhatsApp chat DataFrame with 'message' column
            min_length: Minimum length of message to keep
            max_length: Maximum length of message to keep
        
        Returns:
            Filtered DataFrame.
        """
        mask = df['message'].str.len() >= min_length
        if max_length is not None:
            mask &= df['message'].str.len() <= max_length
        return df.loc[mask]
    
    def filter_non_text_messages(self, df: pd.DataFrame, drop: bool = True) -> pd.DataFrame:
        """
        Filter non-text messages (e.g., emojis, media attachments)

        Args:
            df: WhatsApp chat DataFrame with 'message' column
        
        Returns:
            Filtered DataFrame.
        """

        is_media = df['message'].str.contains(self.media_message_pattern, na=False)

        has_text = df['message'].str.contains(r'[A-Za-z0-9]', regex=True,na=False)

        is_non_text = is_media | (~has_text)

        if drop:
            return df.loc[~is_non_text].reset_index(drop=True)
        
        df = df.copy()
        df['is_media_message'] = is_media
        df['has_text'] = has_text
        df['is_non_text_message'] = is_non_text

        return df


    def filter_by_senders(self, df: pd.DataFrame, senders: List[str], include: bool = True) -> pd.DataFrame:
        """
        Filter messages by sender(s).

        Args:
            df: WhatsApp chat DataFrame with 'sender' column
            senders: list of sender names to filter.
            include: if True, keep messages from these senders.
                  if False, remove messages from these senders.
        
        Returns:
            Filtered DataFrame.
        """
        if include:
             return df.loc[df['sender'].isin(senders)].reset_index(drop=True)
        else:
             return df.loc[~df['sender'].isin(senders)].reset_index(drop=True)
    
    def filter_by_date_range(self, df: pd.DataFrame, start: Optional[pd.Timestamp] = None, end: Optional[pd.Timestamp]= None) -> pd.DataFrame:
        """
        Filter messages within a date range.

        Args:
            df: WhatsApp chat DataFrame with 'timestamp' column.
            start: Start datetime (inclusive).
            end: End datetime (inclusive).

        Returns:
            Filtered DataFrame.
        """
        mask = pd.Series(True, index=df.index)
        if start is not None:
            mask &= df['timestamp'] >= start
        if end is not None:
            mask &= df['timestamp'] <= end
        return df.loc[mask].reset_index(drop=True)