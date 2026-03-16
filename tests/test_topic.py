"""Tests for topic modeling modules."""

import pytest

from comment_analyzer.topic.keywords import KeywordExtractor
from comment_analyzer.topic.lda import LDAModel


class TestKeywordExtractor:
    """Tests for KeywordExtractor."""

    def test_basic_extraction(self):
        extractor = KeywordExtractor(top_k=10)
        texts = ["产品质量好 服务不错"] * 5 + ["物流很快 包装很好"] * 5
        keywords = extractor.extract(texts)
        assert isinstance(keywords, list)
        assert len(keywords) <= 10
        assert all(isinstance(k, tuple) and len(k) == 2 for k in keywords)

    def test_invalid_method(self):
        with pytest.raises(ValueError):
            KeywordExtractor(method='invalid')

    def test_document_keywords(self):
        extractor = KeywordExtractor()
        texts = ["产品质量好", "服务不错"]
        extractor.extract(texts)

        doc_keywords = extractor.extract_for_document("产品质量")
        assert isinstance(doc_keywords, list)

    def test_not_fitted_error(self):
        extractor = KeywordExtractor()
        with pytest.raises(ValueError):
            extractor.extract_for_document("test")

    def test_batch_extraction(self):
        extractor = KeywordExtractor()
        texts = ["产品质量好", "服务不错"]
        results = extractor.extract_batch(texts)
        assert len(results) == len(texts)

    def test_word_frequency(self):
        extractor = KeywordExtractor()
        texts = ["测试 测试 内容", "测试 其他"]
        freq = extractor.get_word_frequency(texts)
        assert isinstance(freq, list)
        assert freq[0][0] == "测试"


class TestLDAModel:
    """Tests for LDAModel."""

    def test_basic_lda(self):
        model = LDAModel(num_topics=2, passes=5)
        documents = [
            ["产品", "质量", "很好"],
            ["服务", "态度", "不错"],
            ["物流", "速度", "快"],
            ["质量", "一般"],
            ["服务", "很好"],
        ]
        topics = model.fit_transform(documents)
        assert isinstance(topics, list)
        assert len(topics) > 0

    def test_fit_and_get_topics(self):
        model = LDAModel(num_topics=2, passes=5)
        documents = [
            ["产品", "质量"],
            ["服务", "态度"],
        ]
        model.fit(documents)
        topics = model.get_topics()
        assert isinstance(topics, list)
        assert all('id' in t for t in topics)
        assert all('words' in t for t in topics)

    def test_not_fitted_error(self):
        model = LDAModel()
        with pytest.raises(ValueError):
            model.get_topics()

    def test_document_topics(self):
        model = LDAModel(num_topics=2, passes=5)
        documents = [
            ["产品", "质量"],
            ["服务", "态度"],
        ]
        model.fit(documents)

        topics = model.get_document_topics(["产品", "质量"])
        assert isinstance(topics, list)
        assert all(isinstance(t, tuple) and len(t) == 2 for t in topics)

    def test_transform(self):
        model = LDAModel(num_topics=2, passes=5)
        documents = [
            ["产品", "质量"],
            ["服务", "态度"],
        ]
        model.fit(documents)

        results = model.transform([["产品"], ["服务"]])
        assert len(results) == 2

    def test_find_dominant_topic(self):
        model = LDAModel(num_topics=2, passes=5)
        documents = [
            ["产品", "质量", "产品", "质量"],
            ["服务", "态度"],
        ]
        model.fit(documents)

        topic_id, prob = model.find_dominant_topic(["产品", "质量"])
        assert isinstance(topic_id, int)
        assert 0 <= prob <= 1

    def test_get_topic_words(self):
        model = LDAModel(num_topics=2, passes=5)
        documents = [["产品", "质量"], ["服务", "态度"]]
        model.fit(documents)

        words = model.get_topic_words(0, topn=5)
        assert isinstance(words, list)
        assert len(words) <= 5
