import re
from typing import List, Dict, Optional
import pandas as pd

from src.preprocessing.text_cleaner import clean_text

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


        # System message patterns (in Indonesian)
        self.system_message_pattern = re.compile(
            r'^('
            r'Pesan dan panggilan terenkripsi|'
            r'Messages and calls are end-to-end encrypted|'

            r'.* (membuat grup|created group)|'
            r'.* (ditambahkan|menambahkan|added)|'
            r'.* (mengubah|changed)|'
            r'.* (mengeluarkan|removed)|'
            r'.* (keluar|left)|'
            r'<(terlampir|attached):'
            r')',
            flags=re.IGNORECASE
        )

    def parse_chat_file(self, file_path: str, encoding: str = 'utf-8') -> pd.DataFrame:

        with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
            content = f.read()
        
        platform = self.detect_platform(content)
        messages = self.extract_messages(content, platform)
        df = pd.DataFrame(messages)

        if not df.empty:
            df['timestamp'] = self.parse_timestamps(df, platform)

        return df
    
        
    def extract_messages(self, content: str, platform: str) -> List[Dict[str, Optional[str]]]:
        """
        Extract messages from raw chat content.
        args:
            content: Raw chat content as a string.
            platform: 'iOS' or 'Android' to determine the message format.
        returns:
            List of message dictionaries with keys: date, time, sender, message.
        """
        pattern = self.message_ios_pattern if platform == 'iOS' else self.message_android_pattern
    
        messages = []
        current_message = None

        for raw_line in content.splitlines():
            line = raw_line.rstrip('\n')

            if not line.strip() and current_message is None:
                continue
        
            match= pattern.match(line)
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
                        sender, message = None, content_line # system message

                current_message = {
                    "date": date,
                    "time": time,
                    "sender": clean_text(sender) if sender else None,
                    "message": clean_text(message)
                }
                continue
            
            # multiline continuation
            if current_message:
                current_message["message"] += "\n" + clean_text(line)
        
        # Append last message
        if current_message:
            messages.append(current_message)

        return messages

    def filter_system_messages(self, df: pd.DataFrame, drop: bool = True) -> pd.DataFrame:

        is_system = df['message'].str.extract(self.system_message_pattern)[0].notna()

        if drop:
            return df.loc[~is_system].reset_index(drop=True)

        df = df.copy()
        df['is_system_message'] = is_system

        return df
    
    def detect_platform(self, content: str) -> str:
        sample_line = content[:100].strip()
        if sample_line.startswith('['):
            return 'iOS'
        
        return 'Android'
    
    def parse_timestamps(self, df: pd.DataFrame, platform: str) -> pd.Series:
        
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
        return sorted(df["sender"].unique().tolist())