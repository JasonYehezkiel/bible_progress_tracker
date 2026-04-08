import pytest
import textwrap
import pandas as pd

class TestDetectPlatform:
    def test_ios_detected_by_bracket(self, parser):
        assert parser.detect_platform("[01/01/24 10.00.00] Alice: hi") == "iOS"
    
    def test_android_detected_when_no_bracket(self, parser):
        assert parser.detect_platform("01/01/2024, 10:00 - Alice: hi") == "Android"
    
    def test_empty_content_defaults_android(self, parser):
        assert parser.detect_platform("") == "Android"

class TestExtractMessageIOS:
    IOS_CHAT = textwrap.dedent("""\
        [01/01/24 10.00.00] ~Alice: Kejadian 1-3
        [01/01/24 10.05.00] Bob: Kejadian 4-6
        [01/01/24 10.10.00] Charlie: Kejadian 1-3
    """)

    def test_returns_correct_count(self, parser):
        msgs = parser.extract_messages(self.IOS_CHAT, "iOS")
        assert len(msgs) == 3
    
    def test_sender_parsed(self, parser):
        msgs = parser.extract_messages(self.IOS_CHAT, "iOS")
        assert msgs[0]["sender"] == "Alice"
        assert msgs[1]["sender"] == "Bob"
        assert msgs[2]["sender"] == "Charlie"
    
    def test_tilde_stripped_from_sender(self, parser):
        msgs = parser.extract_messages(self.IOS_CHAT, "iOS")
        assert not msgs[0]["sender"].startswith("~")
    
    def test_message_content(self, parser):
        msgs = parser.extract_messages(self.IOS_CHAT, "iOS")
        assert msgs[0]["message"] == "Kejadian 1-3"
        assert msgs[1]["message"] == "Kejadian 4-6"
        assert msgs[2]["message"] == "Kejadian 1-3"
    
    def test_date_and_time_captured(self, parser):
        msgs = parser.extract_messages(self.IOS_CHAT, "iOS")
        assert msgs[0]["date"] == "01/01/24"
        assert msgs[0]["time"] == "10.00.00"

class TestExtractMessageAndroid:
    ANDROID_CHAT = textwrap.dedent("""\
        01/01/24, 10:00 - Alice: Kejadian 1-3
        01/01/24, 10:05 - Bob: Kejadian 4-6
        01/01/24, 10:10 - Charlie: Kejadian 1-3
        01/01/24, 10:15 - Messages and calls are end-to-end encrypted.
    """)

    def test_returns_correct_count(self, parser):
        msgs = parser.extract_messages(self.ANDROID_CHAT, "Android")
        assert len(msgs) == 4
    
    def test_sender_parsed(self, parser):
        msgs = parser.extract_messages(self.ANDROID_CHAT, "Android")
        assert msgs[0]["sender"] == "Alice"
        assert msgs[1]["sender"] == "Bob"
        assert msgs[2]["sender"] == "Charlie"
    
    def test_message_content(self, parser):
        msgs = parser.extract_messages(self.ANDROID_CHAT, "Android")
        assert msgs[0]["message"] == "Kejadian 1-3"
        assert msgs[1]["message"] == "Kejadian 4-6"
        assert msgs[2]["message"] == "Kejadian 1-3"
    
    def test_system_message_has_no_sender(self, parser):
        msgs = parser.extract_messages(self.ANDROID_CHAT, "Android")
        assert msgs[3]["sender"] is None
    
    def test_date_and_time_captured(self, parser):
        msgs = parser.extract_messages(self.ANDROID_CHAT, "Android")
        assert msgs[0]["date"] == "01/01/24"
        assert msgs[0]["time"] == "10:00"
    

class TestExtractMessageMultiline:
    def test_ios_multiline_continuation(self, parser):
        chat = textwrap.dedent("""\
            [01/01/24 10.00.00] Alice: Kej 1 - 3 done
            Kej 4- 6 done
            [01/01/24 10.05.00] Bob: Kejadian 1-3
        """)
        msgs = parser.extract_messages(chat, "iOS")
        assert msgs[0]["message"] == "Kej 1 - 3 done\nKej 4- 6 done"

    def test_android_multiline_continuation(self, parser):
        chat = textwrap.dedent("""\
            01/01/24, 10:00 - Alice: Kej 1 - 3 done
            Kej 4- 6 done
            01/01/24, 10:05 - Bob: Kejadian 1-3
        """)
        msgs = parser.extract_messages(chat, "Android")
        assert msgs[0]["message"] == "Kej 1 - 3 done\nKej 4- 6 done"
    
    def test_empty_chat_returns_empty_list(self, parser):
        assert parser.extract_messages("", "iOS") == []

class TestParseTimestamps:
    def test_ios_timestamps_parsed(self, parser):
        df = pd.DataFrame([{"date": "01/01/24", "time": "10.00.00"}])
        result = parser.parse_timestamps(df, "iOS")
        assert result.iloc[0].year == 2024
        assert result.iloc[0].month == 1
 
    def test_android_timestamps_parsed(self, parser):
        df = pd.DataFrame([{"date": "01/01/24", "time": "10:00"}])
        result = parser.parse_timestamps(df, "Android")
        assert result.iloc[0].year == 2024
        assert result.iloc[0].month == 1
 
    def test_invalid_timestamp_coerced_to_nat(self, parser):
        df = pd.DataFrame([{"date": "99/99/99", "time": "99.99.99"}])
        result = parser.parse_timestamps(df, "iOS")
        assert pd.isna(result.iloc[0])

IOS_FIXTURE  = textwrap.dedent("""\
        [01/01/24 10.00.00] ~Alice: Kejadian 1-3 done
        [01/01/24 10.05.00] Bob: Kejadian 4-6 ✅
        [01/01/24 14.00.00] ~Alice: continuing
        second line of Alice's message
        [01/01/24 14.15.00] Charlie: Kejadian 1-3 ya 😊
    """)

ANDROID_FIXTURE  = textwrap.dedent("""\
        01/01/24, 10:00 - Alice: Kejadian 1-3 done
        01/01/24, 10:05 - Bob: Kejadian 4-6 ✅
        01/01/24, 10:10 - Charlie: Kejadian 1-3 😊
        01/01/24, 10:15 - Messages and calls are end-to-end encrypted.
    """)

class TestParseChatFileIOS:
    @pytest.fixture
    def ios_file(self, tmp_path):
        f = tmp_path / "ios_file.txt"
        f.write_text(IOS_FIXTURE, encoding="utf-8")
        return str(f)
    
    def test_return_dataframe(self, parser, ios_file):
        df = parser.parse_chat_file(ios_file)
        assert isinstance(df, pd.DataFrame)
    
    def test_correct_columns(self, parser, ios_file):
        df = parser.parse_chat_file(ios_file)
        assert list(df.columns) == ["timestamp", "sender", "message"]
    
    def test_correct_row_count(self, parser, ios_file):
        df = parser.parse_chat_file(ios_file)
        assert len(df) == 4
    
    def test_timestamps_are_datetime(self, parser, ios_file):
        df = parser.parse_chat_file(ios_file)
        assert pd.api.types.is_datetime64_any_dtype(df["timestamp"])

    def test_sender_values(self, parser, ios_file):
        df = parser.parse_chat_file(ios_file)
        assert set(df["sender"].dropna()) == {"Alice", "Bob", "Charlie"}
    
    def test_multiline_message_merged(self, parser, ios_file):
        df = parser.parse_chat_file(ios_file)
        alice_msgs = df[df["sender"] == "Alice"]["message"].tolist()
        assert any("\n" in m for m in alice_msgs)

class TestParseChatFileAndroid:
    @pytest.fixture
    def android_file(self, tmp_path):
        f = tmp_path / "android_file.txt"
        f.write_text(ANDROID_FIXTURE, encoding="utf-8")
        return str(f)
    
    def test_return_dataframe(self, parser, android_file):
        df = parser.parse_chat_file(android_file)
        assert isinstance(df, pd.DataFrame)
    
    def test_correct_row_count(self, parser, android_file):
        df = parser.parse_chat_file(android_file)
        assert len(df) == 4
    
    def test_system_message_has_null_sender(self, parser, android_file):
        df = parser.parse_chat_file(android_file)
        assert df["sender"].isna().any()
    
    def test_timestamps_are_datetime(self, parser, android_file):
        df = parser.parse_chat_file(android_file)
        assert pd.api.types.is_datetime64_any_dtype(df["timestamp"])

class TestParseChatFileEdgeCases:
    def test_empty_file_returns_empty_dataframe(self, parser, tmp_path):
        f = tmp_path / "empty.txt"
        f.write_text("", encoding="utf-8")
        df = parser.parse_chat_file(str(f))
        assert df.empty
        assert list(df.columns) == ["timestamp", "sender", "message"]