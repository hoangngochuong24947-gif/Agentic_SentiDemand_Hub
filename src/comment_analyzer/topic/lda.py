"""LDA topic modeling helpers."""

from typing import Any, Dict, List, Tuple

import numpy as np
from gensim import corpora
from gensim.models import LdaModel as GensimLdaModel
from gensim.models.coherencemodel import CoherenceModel


class LDAModel:
    """Wrapper around gensim LDA with safer defaults for tiny corpora."""

    def __init__(
        self,
        num_topics: int = 5,
        passes: int = 15,
        iterations: int = 100,
        alpha: str = "auto",
        eta: str = "auto",
        random_state: int = 42,
        minimum_probability: float = 0.01,
    ):
        self.num_topics = num_topics
        self.passes = passes
        self.iterations = iterations
        self.alpha = alpha
        self.eta = eta
        self.random_state = random_state
        self.minimum_probability = minimum_probability

        self.model = None
        self.dictionary = None
        self.corpus = None
        self._is_fitted = False
        self._effective_num_topics = num_topics

    def fit(self, documents: List[List[str]]) -> "LDAModel":
        self.dictionary = corpora.Dictionary(documents)
        if len(self.dictionary) == 0:
            raise ValueError("Cannot fit LDA on empty documents")

        if len(documents) >= 5 and len(self.dictionary) > self.num_topics:
            self.dictionary.filter_extremes(no_below=2, no_above=0.9)
        else:
            self.dictionary.filter_extremes(no_below=1, no_above=1.0)

        if len(self.dictionary) == 0:
            self.dictionary = corpora.Dictionary(documents)

        self.corpus = [self.dictionary.doc2bow(doc) for doc in documents]
        if not any(self.corpus):
            raise ValueError("Cannot fit LDA on documents with no remaining tokens")

        self._effective_num_topics = max(1, min(self.num_topics, len(self.dictionary)))

        np.random.seed(self.random_state)
        self.model = GensimLdaModel(
            corpus=self.corpus,
            id2word=self.dictionary,
            num_topics=self._effective_num_topics,
            passes=self.passes,
            iterations=self.iterations,
            alpha=self.alpha,
            eta=self.eta,
            random_state=self.random_state,
            minimum_probability=self.minimum_probability,
        )

        self._is_fitted = True
        return self

    def fit_transform(self, documents: List[List[str]]) -> List[Dict[str, Any]]:
        self.fit(documents)
        return self.get_topics()

    def get_topics(self) -> List[Dict[str, Any]]:
        if not self._is_fitted:
            raise ValueError("Model must be fitted before getting topics")

        topics = []
        for topic_id in range(self._effective_num_topics):
            topic_terms = self.model.show_topic(topic_id, topn=20)
            topic_weight = sum(
                prob
                for doc in self.corpus
                for t, prob in self.model.get_document_topics(doc)
                if t == topic_id
            ) / len(self.corpus)
            topics.append({"id": topic_id, "words": topic_terms, "weight": topic_weight})

        topics.sort(key=lambda item: item["weight"], reverse=True)
        return topics

    def get_document_topics(self, document: List[str]) -> List[Tuple[int, float]]:
        if not self._is_fitted:
            raise ValueError("Model must be fitted")

        bow = self.dictionary.doc2bow(document)
        return self.model.get_document_topics(bow)

    def transform(self, documents: List[List[str]]) -> List[List[Tuple[int, float]]]:
        if not self._is_fitted:
            raise ValueError("Model must be fitted")

        results = []
        for doc in documents:
            bow = self.dictionary.doc2bow(doc)
            results.append(self.model.get_document_topics(bow))
        return results

    def get_coherence_score(self, documents: List[List[str]], coherence: str = "c_v") -> float:
        if not self._is_fitted:
            raise ValueError("Model must be fitted")

        coherence_model = CoherenceModel(
            model=self.model,
            texts=documents,
            dictionary=self.dictionary,
            coherence=coherence,
        )
        return coherence_model.get_coherence()

    def get_topic_words(self, topic_id: int, topn: int = 10) -> List[Tuple[str, float]]:
        if not self._is_fitted:
            raise ValueError("Model must be fitted")
        return self.model.show_topic(topic_id, topn=topn)

    def find_dominant_topic(self, document: List[str]) -> Tuple[int, float]:
        topics = self.get_document_topics(document)
        if not topics:
            return (-1, 0.0)
        return max(topics, key=lambda item: item[1])
