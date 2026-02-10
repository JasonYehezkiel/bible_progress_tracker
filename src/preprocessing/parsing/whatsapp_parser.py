"""
Whatsapp chat export parser

This module provides utilities to parse raw WhatsApp chat export files
(from Android and iOS) into structured pandas DataFrame. it supports:

- Platform detection
- Message extraction with multiline support
- Timestamp normalization
- Sender normalization
- System message filtering
"""

import re
import pandas as pd
from typing import Dict, List, Optional
from src.preprocessing.parsing.text_cleaner import clean_text

class WhatsAppParser:
    """
    Parser for WhatsApp chat export files.
    """
    def __init__(self):

        # iOS format: [dd/mm/yy hh.mm.ss] Sender: Message
        self.message_ios_pattern = re.compile(
            r'\[(\d{1,2}/\d{1,2}/\d{2})\s+'
            r'(\d{1,2}\.\d{2}\.\d{2})\]\s*'
            r'~?\s*([^:]+):\s*(.+)'
        )

        # Android format: dd/mm/yyyy, hh:mm - Sender: Message
        self.message_android_pattern = re.compile(
            r'^(\d{1,2}/\d{1,2}/\d{2,4}),\s+'
            r'(\d{1,2}:\d{2})\s+-\s+'
            r'(.+)$'
        )


    def parse_chat_file(self, file_path: str, encoding: str = 'utf-8') -> pd.DataFrame:
        """
        Parse a Whatsapp chat export file into a DataFrame.

        Args:
            file_path: Path to WhatsApp chat export text file.
            encoding: File encoding to use when reading the file.
        
        Returns:
            A pandas DataFrame containing parsed chat messages with columns
        """

        with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
            content = f.read()
        
        # preprocess / clean entire file content
        content = self.preprocess_content(content)

        # Detect platform
        platform = self.detect_platform(content)

        # extract messages
        messages = self.extract_messages(content, platform)

        df = pd.DataFrame(messages)

        if df.empty:
            return pd.DataFrame(columns=['timestamp', 'sender', 'message'])
        
        # Parse timestamps
        df['timestamp'] = self.parse_timestamps(df, platform)


        return df[['timestamp', 'sender', 'message']]
    
        
    def extract_messages(self, content: str, platform: str) -> List[Dict[str, Optional[str]]]:
        """
        Extract messages from cleaned chat content.

        Args:
            content: Raw chat content as a string.
            platform: 'iOS' or 'Android' to determine the message format.

        Returns:
            List of message dictionaries with keys: date, time, sender, message.
        """
        pattern = self.message_ios_pattern if platform == 'iOS' else self.message_android_pattern
        messages = []
        current_message = None

        for raw_line in content.splitlines():
            line = raw_line.rstrip('\n')
            if not line.strip() and current_message is None:
                continue
        
            match = pattern.match(line)
            if match:
                # save previous message
                if current_message:
                    messages.append(current_message)
                
                if platform == 'iOS':
                    date, time, sender, message = match.groups()
                else:  # Android
                    date, time, content_line = match.groups()
                    if ':' in content_line:
                        sender, message = content_line.split(':', 1)
                    else:
                        sender, message = None, content_line

                current_message = {
                    "date": date,
                    "time": time,
                    "sender": sender.strip() if sender else None,
                    "message": message
                }
            else:
                # multiline continuation
                if current_message:
                    current_message["message"] += "\n" + line
        
        # Append last message
        if current_message:
            messages.append(current_message)

        return messages
    
    def detect_platform(self, content: str) -> str:
        """
        Detect WhatsApp export platform based on content format.

        Args:
            content: Raw chat content as string
        
        Returns:
            'iOS' if the content matches iOS export format, otherwise 'Android'.
        """
        sample_line = content[:100].strip()
        if sample_line.startswith('['):
            return 'iOS'
        
        return 'Android'
    
    def parse_timestamps(self, df: pd.DataFrame, platform: str) -> pd.Series:
        """
        Parse and normalize message timestamps
        
        Args:
            df: DataFrame containing 'date' and 'time' columns.
            platform: Platform identifier ('iOs' or 'Android').
        
        Returns:
            A pandas Series of datetime objects, with invalid parses coerced to NaT.
        """
        
        if platform == 'iOS':
            return  pd.to_datetime(
                df['date'] + ' ' + df['time'],
                format='%d/%m/%y %H.%M.%S',
                errors='coerce'
            )
        else:  # Android
            return pd.to_datetime(
                df['date'] + ' ' + df['time'],
                format='%d/%m/%y %H:%M',
                errors='coerce'
            )

    
    def get_unique_senders(self, df: pd.DataFrame) -> List[str]:
        """
        Retrieve a sorted list of unique messages senders.

        Args:
            df: DataFrame containing a 'sender' column'.
        
        Returns:
            A sorted list of unique sender names.
        """
        return sorted(df["sender"].unique().tolist())
    
    def preprocess_content(self, content: str) -> str:
        return clean_text(content)