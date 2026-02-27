"""Tagging content module."""

import pandas as pd
import re
from collections import Counter

# System message patterns (in Indonesian + english)
SYSTEM_MESSAGE_PATTERN = re.compile(
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
MEDIA_PATTERN = re.compile(
    r"(omitted|tidak disertakan|terlampir|attached)",
    flags=re.IGNORECASE
)

# URL pattern
URL_PATTERN = re.compile(
    r'https?://[^\s]+|www\.[^\s]+',
    flags=re.IGNORECASE
)

def get_tags(message: str) -> dict:
    """
    Determine content tags for a single message.

    Args:
        message: Message text
    Returns:
        A list of tags
    """
    # Check if system message
    if SYSTEM_MESSAGE_PATTERN.match(message):
        return ['SYSTEM']
        
    # For user messages, check additional labels
    msg_len = len(message)

    if msg_len <= 100:
        tags = ['USER_SHORT']
    elif msg_len <= 300:
        tags = ['USER_MEDIUM']
    else:
        tags = ['USER_LONG']

    # check for media
    if MEDIA_PATTERN.search(message):
        tags.append('MEDIA')
    
    # check for URL
    if URL_PATTERN.search(message):
        tags.append('URL')

    return tags

def label_messages(df: pd.DataFrame, column: str = 'message') -> pd.DataFrame:
    """
    Add context tags to all messages in the DataFrame.

    Args:
        df: DataFrame with 'message' column

    Returns:
        DataFrame with added 'tags' column
    """
    df = df.copy()
    df['tags'] = df[column].apply(lambda m: get_tags(str(m)))

    return df

def get_statistics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Get statistics about tags distribution

    Args:
        df: DataFrame with 'tags' column

    Returns:
        DataFrame with tags counts
    """
    flat = [tag for tags in df['tags'] for tag in tags]
    total = len(df)
    return pd.DataFrame([
        {'tag': tag, 'count': count, 'percentage': f"{count/total*100:.2f}"}
        for tag, count in Counter(flat).most_common()
    ])