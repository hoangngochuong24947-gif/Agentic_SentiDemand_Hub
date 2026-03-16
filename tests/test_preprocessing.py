"""Tests for preprocessing modules."""

import pytest

from comment_analyzer.preprocessing.cleaner import TextCleaner
from comment_analyzer.preprocessing.segmenter import JiebaSegmenter
from comment_analyzer.preprocessing.filter import StopwordFilter


class TestTextCleaner:
    """Tests for TextCleaner."""

    def test_basic_cleaning(self):
        cleaner = TextCleaner()
        text = "Hello World ！ "
        result = cleaner.clean(text)
        assert result == "Hello World ！"

    def test_url_removal(self):
        cleaner = TextCleaner(remove_urls=True)
        text = "Check https://example.com and http://test.org here"
        result = cleaner.clean(text)
        assert "https://" not in result
        assert "http://" not in result
        assert "example.com" not in result

    def test_email_removal(self):
        cleaner = TextCleaner(remove_emails=True)
        text = "Contact test@example.com for info"
        result = cleaner.clean(text)
        assert "test@example.com" not in result
        assert "@" not in result

    def test_html_removal(self):
        cleaner = TextCleaner(remove_html=True)
        text = "<b>Bold</b> and <i>italic</i> text"
        result = cleaner.clean(text)
        assert "<b>" not in result
        assert "</b>" not in result
        assert "Bold" in result

    def test_whitespace_normalization(self):
        cleaner = TextCleaner(normalize_whitespace=True, remove_extra_spaces=True)
        text = "Too   many     spaces\tand\ttabs"
        result = cleaner.clean(text)
        assert "  " not in result

    def test_none_input(self):
        cleaner = TextCleaner()
        result = cleaner.clean(None)
        assert result == ""

    def test_punctuation_removal(self):
        cleaner = TextCleaner()
        text = "Hello, world! How are you?"
        result = cleaner.remove_punctuation(text, keep_chinese=False)
        assert "," not in result
        assert "!" not in result
        assert "?" not in result


class TestJiebaSegmenter:
    """Tests for JiebaSegmenter."""

    def test_basic_segmentation(self):
        segmenter = JiebaSegmenter(mode='precise')
        text = "产品质量很好"
        result = segmenter.segment(text)
        assert isinstance(result, list)
        assert len(result) > 0

    def test_segmentation_modes(self):
        text = "中文分词测试"

        precise = JiebaSegmenter(mode='precise')
        full = JiebaSegmenter(mode='full')
        search = JiebaSegmenter(mode='search')

        precise_result = precise.segment(text)
        full_result = full.segment(text)
        search_result = search.segment(text)

        assert all(isinstance(r, list) for r in [precise_result, full_result, search_result])

    def test_invalid_mode(self):
        with pytest.raises(ValueError):
            JiebaSegmenter(mode='invalid')

    def test_empty_text(self):
        segmenter = JiebaSegmenter()
        result = segmenter.segment("")
        assert result == []

    def test_segment_with_pos(self):
        segmenter = JiebaSegmenter()
        text = "产品质量"
        result = segmenter.segment_with_pos(text)
        assert isinstance(result, list)
        assert all(isinstance(item, tuple) and len(item) == 2 for item in result)

    def test_noun_extraction(self):
        segmenter = JiebaSegmenter()
        text = "产品质量很好"
        nouns = segmenter.extract_nouns(text)
        assert isinstance(nouns, list)

    def test_batch_segmentation(self):
        segmenter = JiebaSegmenter()
        texts = ["第一句", "第二句", "第三句"]
        results = segmenter.segment_batch(texts)
        assert len(results) == len(texts)
        assert all(isinstance(r, list) for r in results)

    def test_word_frequency(self):
        segmenter = JiebaSegmenter()
        texts = ["测试测试", "测试"]
        freq = segmenter.get_word_freq(texts)
        assert isinstance(freq, dict)
        assert "测试" in freq


class TestStopwordFilter:
    """Tests for StopwordFilter."""

    def test_basic_filtering(self):
        filter_ = StopwordFilter()
        words = ["的", "产品", "是", "好"]
        result = filter_.filter(words)
        assert "的" not in result
        assert "是" not in result
        assert "产品" in result
        assert "好" in result

    def test_extra_words(self):
        filter_ = StopwordFilter(extra_words=["特别"])
        words = ["特别", "好", "产品"]
        result = filter_.filter(words)
        assert "特别" not in result

    def test_min_word_length(self):
        filter_ = StopwordFilter(min_word_length=2)
        words = ["a", "ab", "abc"]
        result = filter_.filter(words)
        assert "a" not in result
        assert "ab" in result

    def test_add_stopwords(self):
        filter_ = StopwordFilter()
        filter_.add_stopwords(["新增"])
        words = ["新增", "产品"]
        result = filter_.filter(words)
        assert "新增" not in result

    def test_remove_stopwords(self):
        filter_ = StopwordFilter()
        filter_.remove_stopwords(["的"])
        words = ["的", "产品"]
        result = filter_.filter(words)
        assert "的" in result

    def test_is_stopword(self):
        filter_ = StopwordFilter()
        assert filter_.is_stopword("的")
        assert not filter_.is_stopword("产品")

    def test_batch_filtering(self):
        filter_ = StopwordFilter()
        word_lists = [["的", "产品"], ["是", "好"]]
        results = filter_.filter_batch(word_lists)
        assert len(results) == len(word_lists)

    def test_get_stopwords(self):
        filter_ = StopwordFilter()
        stopwords = filter_.get_stopwords()
        assert isinstance(stopwords, set)
        assert "的" in stopwords

    def test_save_stopwords(self, tmp_path):
        filter_ = StopwordFilter()
        save_path = tmp_path / "test_stopwords.txt"
        filter_.save_stopwords(save_path)
        assert save_path.exists()
