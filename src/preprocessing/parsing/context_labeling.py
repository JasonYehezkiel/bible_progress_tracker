import pandas as pd
import re
from collections import Counter

class ContextLabeler:
    """
    Label WhatsApp chat messages based on their context.

    Primary tags:
    - 'user': Regular user messages
    - 'system': System-generated messages

    Additional tags for user messages:
    - 'media': Messages containing media attachments
    - 'url': Messages containing URLs
    - 'reflection': Bible study content, guidelines, devotional reflections
    - 'recap': Progress tracking/status updates (numbered list with names)
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
            r".+ ditambahkan.*|"

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
            r"Anda menghapus pesan ini\.?"

            r")$",
            flags=re.IGNORECASE
        )


        # Media message patterns
        self.media_message_pattern = re.compile(
            r"(omitted|tidak disertakan|terlampir|attached)",
            flags=re.IGNORECASE
        )

        # URL pattern
        self.url_pattern = re.compile(
            r'https?://[^\s]+|www\.[^\s]+',
            flags=re.IGNORECASE
        )

    
    def label_messages(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add context labels to all messages in the DataFrame.

        Args:
            df: DataFrame with 'message' column

        Returns:
            DataFrame with added columns:
            - 'primary_label': 'user' or 'system'
            - 'additional_labels': list of additional labels (empty list if none)
        """
        df = df.copy()

        #Intialize label columns
        df['primary_label'] = 'USER'
        df['additional_labels'] = [[] for _ in range(len(df))]

        # Label each message
        for idx, row  in df.iterrows():
            message = str(row['message'])
            labels = self.get_labels(message)

            df.at[idx, 'primary_label'] = labels['primary']
            df.at[idx, 'additional_labels'] = labels['additional']
        
        return df

    def get_labels(self, message: str) -> dict:
        """
        Determine labels for a single message.

        Args:
            message: Message text
        Returns:
            Dictionary with 'primary' and 'additional' labels.
        """
        labels = {
            'primary': 'USER',
            'additional': []
        }

        # Check if system message
        if self.system_message_pattern.match(message):
            labels['primary'] = 'SYSTEM'
            return labels
        
        # For user messages, check additional labels

        msg_len = len(message)
        if msg_len <= 200:
            labels['additional'].append('SHORT')
        elif msg_len > 200:
            labels['additional'].append('LONG')

        # check for media
        if self.media_message_pattern.search(message):
            labels['additional'].append('MEDIA')
        
        # check for URL
        if self.url_pattern.search(message):
            labels['additional'].append('URL')
        
        # Check for Question
        if '?' in message:
            labels['additional'].append('QUESTION')
    
    
        return labels
    
    def get_label_statistics(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Get statistics about label distribution

        Args:
            df: DataFrame with 'primary_label' and 'additional_labels' columns

        Returns:
            DataFrame with label counts
        """
        stats = []

        # primary label counts
        primary_counts = df['primary_label'].value_counts()
        for label, count in primary_counts.items():
            stats.append({
                'label_type': 'primary',
                'label': label,
                'count': count,
                'percentage': f"{count/len(df)*100:.2f}"
            })
        
        # additional label counts
        additional_labels_flat = [
            label for labels in df['additional_labels']
            for label in labels
        ]

        if additional_labels_flat:
            additional_counts = Counter(additional_labels_flat)

            for label, count in additional_counts.items():
                stats.append({
                    'label_type': 'additional',
                    'label': label,
                    'count': count,
                    'percentage': f"{count/len(df)*100:.2f}"
                })
        
        return pd.DataFrame(stats)



    # def filter_by_senders(self, df: pd.DataFrame, senders: List[str], include: bool = True) -> pd.DataFrame:
    #     """
    #     Filter messages by sender(s).

    #     Args:
    #         df: WhatsApp chat DataFrame with 'sender' column
    #         senders: list of sender names to filter.
    #         include: if True, keep messages from these senders.
    #               if False, remove messages from these senders.
        
    #     Returns:
    #         Filtered DataFrame.
    #     """
    #     if include:
    #          return df.loc[df['sender'].isin(senders)].reset_index(drop=True)
    #     else:
    #          return df.loc[~df['sender'].isin(senders)].reset_index(drop=True)
    
    # def filter_by_date_range(self, df: pd.DataFrame, start: Optional[pd.Timestamp] = None, end: Optional[pd.Timestamp]= None) -> pd.DataFrame:
    #     """
    #     Filter messages within a date range.

    #     Args:
    #         df: WhatsApp chat DataFrame with 'timestamp' column.
    #         start: Start datetime (inclusive).
    #         end: End datetime (inclusive).

    #     Returns:
    #         Filtered DataFrame.
    #     """
    #     mask = pd.Series(True, index=df.index)
    #     if start is not None:
    #         mask &= df['timestamp'] >= start
    #     if end is not None:
    #         mask &= df['timestamp'] <= end
    #     return df.loc[mask].reset_index(drop=True)