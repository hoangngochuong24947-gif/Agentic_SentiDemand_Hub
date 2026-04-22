"""Tests for preprocessing modules."""

import pytest

from comment_analyzer.preprocessing.cleaner import TextCleaner
from comment_analyzer.preprocessing.filter import StopwordFilter
from comment_analyzer.preprocessing.segmenter import JiebaSegmenter, MultilingualSegmenter


class TestTextCleaner:
    """Tests for text cleaning helpers."""

    def test_basic_cleaning(self):
        cleaner = TextCleaner()
        result = cleaner.clean("Hello   world")
        assert "Hello" in result

    def test_url_removal(self):
        cleaner = TextCleaner(remove_urls=True)
        result = cleaner.clean("Check https://example.com now")
        assert "https://" not in result
        assert "example.com" not in result

    def test_email_removal(self):
        cleaner = TextCleaner(remove_emails=True)
        result = cleaner.clean("Contact test@example.com")
        assert "@" not in result

    def test_html_removal(self):
        cleaner = TextCleaner(remove_html=True)
        result = cleaner.clean("<b>Bold</b> text")
        assert "<b>" not in result
        assert "Bold" in result

    def test_none_input(self):
        cleaner = TextCleaner()
        assert cleaner.clean(None) == ""

    def test_punctuation_removal(self):
        cleaner = TextCleaner()
        result = cleaner.remove_punctuation("Hello, world! How are you?", keep_chinese=False)
        assert "," not in result
        assert "!" not in result
        assert "?" not in result


class TestJiebaSegmenter:
    """Tests for Chinese segmentation."""

    def test_basic_segmentation(self):
        segmenter = JiebaSegmenter(mode="precise")
        result = segmenter.segment("产品质量很好")
        assert isinstance(result, list)
        assert len(result) > 0

    def test_segmentation_modes(self):
        text = "中文分词测试"
        precise = JiebaSegmenter(mode="precise").segment(text)
        full = JiebaSegmenter(mode="full").segment(text)
        search = JiebaSegmenter(mode="search").segment(text)
        assert all(isinstance(result, list) for result in (precise, full, search))

    def test_invalid_mode(self):
        with pytest.raises(ValueError):
            JiebaSegmenter(mode="invalid")

    def test_empty_text(self):
        assert JiebaSegmenter().segment("") == []

    def test_segment_with_pos(self):
        result = JiebaSegmenter().segment_with_pos("产品质量")
        assert isinstance(result, list)
        assert all(isinstance(item, tuple) and len(item) == 2 for item in result)

    def test_extract_nouns(self):
        nouns = JiebaSegmenter().extract_nouns("产品质量很好")
        assert isinstance(nouns, list)

    def test_batch_segmentation(self):
        texts = ["第一句", "第二句", "第三句"]
        results = JiebaSegmenter().segment_batch(texts)
        assert len(results) == len(texts)

    def test_word_frequency(self):
        freq = JiebaSegmenter().get_word_freq(["测试测试", "测试"])
        assert isinstance(freq, dict)
        assert "测试" in freq


class TestStopwordFilter:
    """Tests for stopword filtering."""

    def test_basic_filtering(self):
        filter_ = StopwordFilter()
        words = ["的", "产品", "是", "很好"]
        result = filter_.filter(words)
        assert "的" not in result
        assert "是" not in result
        assert "产品" in result

    def test_extra_words(self):
        filter_ = StopwordFilter(extra_words=["特别"])
        result = filter_.filter(["特别", "好", "产品"])
        assert "特别" not in result

    def test_min_word_length(self):
        filter_ = StopwordFilter(min_word_length=2)
        result = filter_.filter(["a", "ab", "abc"])
        assert "a" not in result
        assert "ab" in result

    def test_add_and_remove_stopwords(self):
        filter_ = StopwordFilter()
        filter_.add_stopwords(["新增"])
        assert "新增" not in filter_.filter(["新增", "产品"])
        filter_.remove_stopwords(["的"])
        assert "的" in filter_.filter(["的", "产品"])

    def test_is_stopword(self):
        filter_ = StopwordFilter()
        assert filter_.is_stopword("的")
        assert not filter_.is_stopword("产品")

    def test_batch_filtering(self):
        filter_ = StopwordFilter()
        results = filter_.filter_batch([["的", "产品"], ["是", "很好"]])
        assert len(results) == 2

    def test_get_stopwords(self):
        stopwords = StopwordFilter().get_stopwords()
        assert isinstance(stopwords, set)
        assert "的" in stopwords

    def test_save_stopwords(self, tmp_path):
        save_path = tmp_path / "stopwords.txt"
        StopwordFilter().save_stopwords(save_path)
        assert save_path.exists()

    def test_hybrid_strategy_keeps_non_stopwords(self, tmp_path):
        stopwords_file = tmp_path / "stopwords.txt"
        stopwords_file.write_text("服务\n", encoding="utf-8")
        filter_ = StopwordFilter(
            stopwords_path=stopwords_file,
            extra_words=["特删"],
            strategy="hybrid",
        )
        result = filter_.filter(["好", "服务", "产品", "特删"])
        assert "服务" not in result
        assert "特删" not in result
        assert "产品" in result


class TestMultilingualSegmenter:
    """Tests for Korean-aware segmentation."""

    def test_korean_regex_fallback(self):
        segmenter = MultilingualSegmenter(language="ko", backend="regex")
        result = segmenter.segment("배송은 빨랐고 품질도 좋았어요")
        assert isinstance(result, list)
        assert "배송은" in result or "배송" in result
