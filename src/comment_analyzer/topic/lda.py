"""LDA topic modeling module for comment_analyzer.

Provides Latent Dirichlet Allocation (LDA) for topic discovery in comments.
"""

from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from gensim import corpora
from gensim.models import LdaModel as GensimLdaModel
from gensim.models.coherencemodel import CoherenceModel


class LDAModel:
    """Latent Dirichlet Allocation (LDA) topic model.

    Discovers latent topics in a corpus of text using LDA.

    Example:
        >>> lda = LDAModel(num_topics=5)
        >>> documents = [['产品', '质量', '好'], ['服务', '态度', '不错'], ...]
        >>> topics = lda.fit_transform(documents)
        >>> for topic in topics:
        ...     print(topic['words'][:5])

        >>> # Get topic distribution for new document
        >>> doc_topics = lda.get_document_topics(['质量', '很好', '满意'])
    """

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
        """Initialize the LDA model.

        Args:
            num_topics: Number of topics to discover.
            passes: Number of passes through the corpus during training.
            iterations: Maximum number of iterations through the corpus.
            alpha: Document-topic prior. 'symmetric', 'asymmetric', 'auto', or float.
            eta: Topic-word prior. 'symmetric', 'auto', or float.
            random_state: Random seed for reproducibility.
            minimum_probability: Minimum probability threshold for topics.
        """
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

    def fit(self, documents: List[List[str]]) -> "LDAModel":
        """Fit the LDA model to the documents.

        Args:
            documents: List of documents, where each document is a list of words.

        Returns:
            Self for method chaining.
        """
        # Create dictionary
        self.dictionary = corpora.Dictionary(documents)

        # Filter extremes (optional but recommended)
        self.dictionary.filter_extremes(no_below=2, no_above=0.9)

        # Create corpus (bag-of-words)
        self.corpus = [self.dictionary.doc2bow(doc) for doc in documents]

        # Set random state for gensim
        np.random.seed(self.random_state)

        # Create and train LDA model
        self.model = GensimLdaModel(
            corpus=self.corpus,
            id2word=self.dictionary,
            num_topics=self.num_topics,
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
        """Fit the model and return topic representations.

        Args:
            documents: List of documents, where each document is a list of words.

        Returns:
            List of topic dictionaries with 'id', 'words', and 'weights' keys.
        """
        self.fit(documents)
        return self.get_topics()

    def get_topics(self) -> List[Dict[str, Any]]:
        """Get the discovered topics.

        Returns:
            List of topic dictionaries. Each dictionary contains:
            - 'id': Topic ID
            - 'words': List of (word, weight) tuples
            - 'weight': Overall topic weight

        Raises:
            ValueError: If model hasn't been fitted.
        """
        if not self._is_fitted:
            raise ValueError("Model must be fitted before getting topics")

        topics = []
        for topic_id in range(self.num_topics):
            # Get topic words
            topic_terms = self.model.show_topic(topic_id, topn=20)

            # Calculate topic weight (proportion in corpus)
            topic_weight = sum(
                prob for doc in self.corpus
                for t, prob in self.model.get_document_topics(doc)
                if t == topic_id
            ) / len(self.corpus)

            topics.append({
                'id': topic_id,
                'words': topic_terms,
                'weight': topic_weight,
            })

        # Sort by weight
        topics.sort(key=lambda x: x['weight'], reverse=True)

        return topics

    def get_document_topics(self, document: List[str]) -> List[Tuple[int, float]]:
        """Get topic distribution for a single document.

        Args:
            document: List of words in the document.

        Returns:
            List of (topic_id, probability) tuples.

        Raises:
            ValueError: If model hasn't been fitted.
        """
        if not self._is_fitted:
            raise ValueError("Model must be fitted")

        bow = self.dictionary.doc2bow(document)
        return self.model.get_document_topics(bow)

    def transform(self, documents: List[List[str]]) -> List[List[Tuple[int, float]]]:
        """Get topic distributions for multiple documents.

        Args:
            documents: List of documents.

        Returns:
            List of topic distribution lists.

        Raises:
            ValueError: If model hasn't been fitted.
        """
        if not self._is_fitted:
            raise ValueError("Model must be fitted")

        results = []
        for doc in documents:
            bow = self.dictionary.doc2bow(doc)
            topics = self.model.get_document_topics(bow)
            results.append(topics)

        return results

    def get_coherence_score(
        self,
        documents: List[List[str]],
        coherence: str = 'c_v'
    ) -> float:
        """Calculate topic coherence score.

        Args:
            documents: List of documents.
            coherence: Coherence measure ('c_v', 'u_mass', 'c_uci', 'c_npmi').

        Returns:
            Coherence score.

        Raises:
            ValueError: If model hasn't been fitted.
        """
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
        """Get top words for a specific topic.

        Args:
            topic_id: ID of the topic.
            topn: Number of top words to return.

        Returns:
            List of (word, weight) tuples.

        Raises:
            ValueError: If model hasn't been fitted.
        """
        if not self._is_fitted:
            raise ValueError("Model must be fitted")

        return self.model.show_topic(topic_id, topn=topn)

    def find_dominant_topic(self, document: List[str]) -> Tuple[int, float]:
        """Find the dominant topic for a document.

        Args:
            document: List of words.

        Returns:
            Tuple of (topic_id, probability) for the dominant topic.
        """
        topics = self.get_document_topics(document)
        if not topics:
            return (-1, 0.0)
        return max(topics, key=lambda x: x[1])
