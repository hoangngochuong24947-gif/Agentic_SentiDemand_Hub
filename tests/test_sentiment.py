"""Tests for sentiment analysis modules."""

import numpy as np
import pytest

from comment_analyzer.sentiment.labeler import SentimentLabeler
from comment_analyzer.sentiment.vectorizer import TFIDFVectorizer
from comment_analyzer.sentiment.classifier import Classifier, ModelResults


class TestSentimentLabeler:
    """Tests for SentimentLabeler."""

    def test_snownlp_labeling(self):
        labeler = SentimentLabeler(method='snownlp')
        # Positive text
        result = labeler.label("这个产品非常好，很满意！")
        assert result in ['positive', 'negative', 'neutral']

    def test_invalid_method(self):
        with pytest.raises(ValueError):
            SentimentLabeler(method='invalid')

    def test_get_score(self):
        labeler = SentimentLabeler()
        score = labeler.get_score("这个产品很好")
        assert 0 <= score <= 1

    def test_empty_text(self):
        labeler = SentimentLabeler()
        result = labeler.label("")
        assert result in ['positive', 'negative', 'neutral']

    def test_batch_labeling(self):
        labeler = SentimentLabeler()
        texts = ["很好", "很差", "一般"]
        results = labeler.label_batch(texts)
        assert len(results) == len(texts)
        assert all(r in ['positive', 'negative', 'neutral'] for r in results)

    def test_rating_labeling(self):
        labeler = SentimentLabeler()
        ratings = [5.0, 4.0, 3.0, 2.0, 1.0]
        results = labeler.label_from_rating(ratings, max_rating=5.0)
        assert len(results) == len(ratings)
        assert results[0] == 'positive'  # 5/5
        assert results[-1] == 'negative'  # 1/5

    def test_distribution(self):
        labeler = SentimentLabeler()
        labels = ['positive', 'negative', 'positive', 'neutral', 'positive']
        dist = labeler.get_sentiment_distribution(labels)
        assert 'positive' in dist
        assert 'negative' in dist
        assert dist['positive']['count'] == 3


class TestTFIDFVectorizer:
    """Tests for TFIDFVectorizer."""

    def test_basic_vectorization(self):
        vectorizer = TFIDFVectorizer(max_features=100)
        texts = ["产品质量好", "服务不错", "物流很快"]
        X = vectorizer.fit_transform(texts)
        assert X.shape[0] == len(texts)
        assert X.shape[1] <= 100

    def test_fit_and_transform(self):
        vectorizer = TFIDFVectorizer()
        texts = ["产品质量好", "服务不错"]
        vectorizer.fit(texts)
        X = vectorizer.transform(texts)
        assert X.shape[0] == len(texts)

    def test_not_fitted_error(self):
        vectorizer = TFIDFVectorizer()
        with pytest.raises(ValueError):
            vectorizer.transform(["test"])

    def test_get_feature_names(self):
        vectorizer = TFIDFVectorizer()
        texts = ["产品质量好", "服务不错"]
        vectorizer.fit_transform(texts)
        features = vectorizer.get_feature_names()
        assert isinstance(features, list)
        assert len(features) > 0

    def test_get_vocabulary(self):
        vectorizer = TFIDFVectorizer()
        texts = ["产品质量好"]
        vectorizer.fit_transform(texts)
        vocab = vectorizer.get_vocabulary()
        assert isinstance(vocab, dict)

    def test_get_idf_scores(self):
        vectorizer = TFIDFVectorizer()
        texts = ["产品质量好", "服务不错"]
        vectorizer.fit_transform(texts)
        idf = vectorizer.get_idf_scores()
        assert isinstance(idf, dict)
        assert all(isinstance(v, (int, float)) for v in idf.values())

    def test_get_top_features(self):
        vectorizer = TFIDFVectorizer()
        texts = ["产品质量好，质量很好"]
        vectorizer.fit(["产品质量好，质量很好", "服务不错"])
        top = vectorizer.get_top_features("产品质量好", top_n=5)
        assert len(top) <= 5
        assert all(isinstance(t, tuple) and len(t) == 2 for t in top)


class TestClassifier:
    """Tests for Classifier."""

    def test_naive_bayes_training(self):
        vectorizer = TFIDFVectorizer(max_features=100)
        texts = ["产品很好"] * 10 + ["产品很差"] * 10 + ["产品一般"] * 10
        X = vectorizer.fit_transform(texts)
        y = ['positive'] * 10 + ['negative'] * 10 + ['neutral'] * 10

        clf = Classifier('naive_bayes')
        results = clf.train(X, y)
        assert isinstance(results, ModelResults)
        assert 0 <= results.accuracy <= 1

    def test_svm_training(self):
        vectorizer = TFIDFVectorizer(max_features=100)
        texts = ["很好"] * 10 + ["很差"] * 10
        X = vectorizer.fit_transform(texts)
        y = ['positive'] * 10 + ['negative'] * 10

        clf = Classifier('svm')
        results = clf.train(X, y)
        assert isinstance(results, ModelResults)

    def test_logistic_regression_training(self):
        vectorizer = TFIDFVectorizer(max_features=100)
        texts = ["很好"] * 10 + ["很差"] * 10
        X = vectorizer.fit_transform(texts)
        y = ['positive'] * 10 + ['negative'] * 10

        clf = Classifier('logistic_regression')
        results = clf.train(X, y)
        assert isinstance(results, ModelResults)

    def test_invalid_model_type(self):
        with pytest.raises(ValueError):
            Classifier('invalid_model')

    def test_prediction(self):
        vectorizer = TFIDFVectorizer(max_features=100)
        texts = ["很好"] * 10 + ["很差"] * 10
        X = vectorizer.fit_transform(texts)
        y = ['positive'] * 10 + ['negative'] * 10

        clf = Classifier('naive_bayes')
        clf.train(X, y)

        X_test = vectorizer.transform(["很好", "很差"])
        predictions = clf.predict(X_test)
        assert len(predictions) == 2

    def test_not_trained_error(self):
        clf = Classifier('naive_bayes')
        with pytest.raises(ValueError):
            clf.predict([1, 2, 3])

    def test_feature_importance(self):
        vectorizer = TFIDFVectorizer(max_features=50)
        texts = ["产品质量好"] * 10 + ["服务很差"] * 10
        X = vectorizer.fit_transform(texts)
        y = ['positive'] * 10 + ['negative'] * 10

        clf = Classifier('naive_bayes')
        clf.train(X, y)

        importance = clf.get_feature_importance(vectorizer.get_feature_names())
        assert isinstance(importance, list)

    def test_model_results_summary(self):
        results = ModelResults(
            model=None,
            accuracy=0.85,
            precision=0.84,
            recall=0.83,
            f1_score=0.835,
            confusion_matrix=np.array([[10, 2], [3, 15]]),
            classification_report="Test report",
        )
        summary = results.summary()
        assert "Accuracy" in summary
        assert "0.85" in summary
