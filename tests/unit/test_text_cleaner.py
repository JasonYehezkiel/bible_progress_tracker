from preprocessing.text_cleaner import clean_text, normalize_whitespace, remove_invisible_chars

class TestRemoveInvisibleChars:
    def test_empty_string(self):
        assert remove_invisible_chars("") == ""
    
    def test_remove_lrm(self):
        assert remove_invisible_chars("Hello\u200EWorld") == "HelloWorld"
    
    def test_remove_rlm(self):
        assert remove_invisible_chars("Hello\u200FWorld") == "HelloWorld"
    
    def test_remove_bom(self):
        assert remove_invisible_chars("\uFEFFhello") == "hello"
    
    def test_remove_zwsp(self):
        assert remove_invisible_chars("he\u200Bllo") == "hello"
    
    def test_remove_zwnj(self):
        assert remove_invisible_chars("he\u200Cllo") == "hello"
    
    def test_remove_zwj(self):
        assert remove_invisible_chars("he\u200Dllo") == "hello"
    
    def test_remove_lre_rle(self):
        assert remove_invisible_chars("he\u202Allo\u202B") == "hello"
    
    def test_remove_multiple_markers_in_one_string(self):
        text = "\uFEFF[01/01/24\u200E 10.00.00] Alice: hi"
        result = remove_invisible_chars(text)
        assert "\uFFEFF" not in result
        assert "\u200E" not in result
        assert "Alice: hi" in result
    
    def test_preserves_newlines(self):
        assert "\n" in remove_invisible_chars("Line1\nLine2")
    
    def test_preserves_tabs(self):
        assert "\t" in remove_invisible_chars("Column1\tColumn2")
    
    def test_plain_text_unchanged(self):
        text = "Kejadian 1-3"
        assert remove_invisible_chars(text) == text

class TestNormalizeWhitespace:
    def test_collapses_multiple_spaces(self):
        assert normalize_whitespace("hello    world") == "hello world"
    
    def test_preserves_single_space(self):
        assert normalize_whitespace("hello world") == "hello world"
    
    def test_strips_each_line(self):
        assert normalize_whitespace("  hello  \n  world  ") == "hello\nworld"
    
    def test_removes_leading_newlines(self):
        result = normalize_whitespace("\n\nhello")
        assert not result.startswith("\n")
    
    def test_removes_trailing_newlines(self):
        result = normalize_whitespace("hello\n\n")
        assert not result.endswith("\n")
    
    def test_preserves_internal_newlines(self):
        result = normalize_whitespace("Line1\nLine2\nLine3")
        assert result.count("\n") == 2
    
    def test_tabs_within_lines_not_collapsed(self):
        result = normalize_whitespace("hello\t\tworld")
        assert result == "hello world"
    
    def test_empty_string(self):
        assert normalize_whitespace("") == ""


class TestCleanText:
    def test_empty_string(self):
        assert clean_text("") == ""

    def test_none_equivalent_empty(self):
        assert clean_text("") == ""
    
    def test_removes_invisible_and_normalizes_spaces(self):
        text = "\uFEFFhello\u200E   world"
        result = clean_text(text)
        assert result == "hello world"
    
    def test_realistic_whatsapp_line(self):
        line = "\uFEFF[01/01/24\u200E 10.00.00] ~Alice: Kejadian 1-3 done"
        result = clean_text(line)
        assert result.startswith("[01/01/24")
        assert "\uFFEFF" not in result
        assert "\u200E" not in result
    
    def test_multiline_preserved(self):
        text = "line one\nline two"
        assert "\n" in clean_text(text)
    
    def test_plain_text_unchanged(self):
        text = "Kejadian 1-3"
        assert clean_text(text) == text