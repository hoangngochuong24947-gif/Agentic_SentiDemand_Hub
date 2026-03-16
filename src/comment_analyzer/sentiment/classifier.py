"""Classification module for comment_analyzer.

Provides machine learning classifiers for sentiment classification.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.naive_bayes import MultinomialNB
from sklearn.svm import LinearSVC
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)


@dataclass
class ModelResults:
    """Container for model training results.

    Attributes:
        model: Trained model instance
        accuracy: Model accuracy on test set
        precision: Weighted precision score
        recall: Weighted recall score
        f1_score: Weighted F1 score
        confusion_matrix: Confusion matrix
        classification_report: Detailed classification report
        cross_val_scores: Cross-validation scores if performed
    """

    model: Any
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    confusion_matrix: np.ndarray
    classification_report: str
    cross_val_scores: Optional[np.ndarray] = None

    def summary(self) -> str:
        """Generate a summary of model performance."""
        lines = [
            "Model Performance Summary",
            "=" * 40,
            f"Accuracy:  {self.accuracy:.4f}",
            f"Precision: {self.precision:.4f}",
            f"Recall:    {self.recall:.4f}",
            f"F1 Score:  {self.f1_score:.4f}",
        ]
        if self.cross_val_scores is not None:
            lines.append(f"CV Mean:   {self.cross_val_scores.mean():.4f} (+/- {self.cross_val_scores.std():.4f})")
        return "\n".join(lines)


class Classifier:
    """Machine learning classifier for sentiment analysis.

    Supports Naive Bayes, SVM, and Logistic Regression with
    a unified interface for training and prediction.

    Example:
        >>> from comment_analyzer.sentiment.vectorizer import TFIDFVectorizer
        >>> vectorizer = TFIDFVectorizer()
        >>> X = vectorizer.fit_transform(texts)
        >>> y = ['positive', 'negative', 'positive', ...]

        >>> # Train Naive Bayes
        >>> clf = Classifier('naive_bayes')
        >>> results = clf.train(X, y)
        >>> print(results.summary())

        >>> # Make predictions
        >>> predictions = clf.predict(X_new)

        >>> # Train with cross-validation
        >>> results = clf.train(X, y, cross_validate=True, cv=5)
    """

    SUPPORTED_MODELS = ['naive_bayes', 'svm', 'logistic_regression']

    def __init__(
        self,
        model_type: str = 'naive_bayes',
        **model_params
    ):
        """Initialize the classifier.

        Args:
            model_type: Type of model to use.
                       Options: 'naive_bayes', 'svm', 'logistic_regression'.
            **model_params: Additional parameters for the model.

        Raises:
            ValueError: If model_type is not supported.
        """
        if model_type not in self.SUPPORTED_MODELS:
            raise ValueError(
                f"Invalid model_type: {model_type}. "
                f"Choose from {self.SUPPORTED_MODELS}"
            )

        self.model_type = model_type
        self.model_params = model_params
        self.model = self._create_model()
        self._is_trained = False

    def _create_model(self) -> Any:
        """Create the underlying model instance."""
        if self.model_type == 'naive_bayes':
            return MultinomialNB(
                alpha=self.model_params.get('alpha', 1.0)
            )
        elif self.model_type == 'svm':
            return LinearSVC(
                C=self.model_params.get('C', 1.0),
                max_iter=self.model_params.get('max_iter', 1000),
                random_state=self.model_params.get('random_state', 42),
            )
        elif self.model_type == 'logistic_regression':
            return LogisticRegression(
                C=self.model_params.get('C', 1.0),
                max_iter=self.model_params.get('max_iter', 1000),
                random_state=self.model_params.get('random_state', 42),
                n_jobs=-1,
            )

    def train(
        self,
        X,
        y,
        test_size: float = 0.2,
        cross_validate: bool = False,
        cv: int = 5,
        random_state: int = 42,
    ) -> ModelResults:
        """Train the classifier.

        Args:
            X: Feature matrix.
            y: Target labels.
            test_size: Fraction of data to use for testing.
            cross_validate: Whether to perform cross-validation.
            cv: Number of folds for cross-validation.
            random_state: Random seed for reproducibility.

        Returns:
            ModelResults containing training metrics and model.
        """
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state, stratify=y
        )

        # Train model
        self.model.fit(X_train, y_train)
        self._is_trained = True

        # Make predictions
        y_pred = self.model.predict(X_test)

        # Calculate metrics
        accuracy = accuracy_score(y_test, y_pred)
        precision = precision_score(y_test, y_pred, average='weighted', zero_division=0)
        recall = recall_score(y_test, y_pred, average='weighted', zero_division=0)
        f1 = f1_score(y_test, y_pred, average='weighted', zero_division=0)
        cm = confusion_matrix(y_test, y_pred)
        report = classification_report(y_test, y_pred, zero_division=0)

        # Cross-validation
        cv_scores = None
        if cross_validate:
            cv_scores = cross_val_score(self.model, X, y, cv=cv)

        return ModelResults(
            model=self.model,
            accuracy=accuracy,
            precision=precision,
            recall=recall,
            f1_score=f1,
            confusion_matrix=cm,
            classification_report=report,
            cross_val_scores=cv_scores,
        )

    def predict(self, X) -> np.ndarray:
        """Make predictions on new data.

        Args:
            X: Feature matrix.

        Returns:
            Array of predicted labels.

        Raises:
            ValueError: If model hasn't been trained.
        """
        if not self._is_trained:
            raise ValueError("Model must be trained before prediction")
        return self.model.predict(X)

    def predict_proba(self, X) -> Optional[np.ndarray]:
        """Get prediction probabilities.

        Args:
            X: Feature matrix.

        Returns:
            Array of prediction probabilities, or None if not supported.

        Raises:
            ValueError: If model hasn't been trained.
        """
        if not self._is_trained:
            raise ValueError("Model must be trained before prediction")

        # SVM doesn't support predict_proba
        if self.model_type == 'svm':
            return None

        return self.model.predict_proba(X)

    def get_feature_importance(
        self,
        feature_names: Optional[List[str]] = None
    ) -> List[Tuple[str, float]]:
        """Get feature importance/importance scores.

        Args:
            feature_names: List of feature names.

        Returns:
            List of (feature, importance) tuples sorted by importance.

        Raises:
            ValueError: If model hasn't been trained.
        """
        if not self._is_trained:
            raise ValueError("Model must be trained")

        if self.model_type == 'naive_bayes':
            # Use log probabilities as importance
            importance = np.abs(self.model.feature_log_prob_[1] - self.model.feature_log_prob_[0])
        elif self.model_type in ['svm', 'logistic_regression']:
            # Use coefficient magnitude
            if hasattr(self.model, 'coef_'):
                importance = np.abs(self.model.coef_[0])
            else:
                return []
        else:
            return []

        # Map to feature names
        if feature_names is None:
            feature_names = [f"feature_{i}" for i in range(len(importance))]

        feature_importance = list(zip(feature_names, importance))
        feature_importance.sort(key=lambda x: x[1], reverse=True)

        return feature_importance

    def save(self, path: str) -> None:
        """Save the trained model to disk.

        Args:
            path: Path to save the model.
        """
        import joblib
        joblib.dump({
            'model': self.model,
            'model_type': self.model_type,
            'model_params': self.model_params,
            'is_trained': self._is_trained,
        }, path)

    def load(self, path: str) -> None:
        """Load a trained model from disk.

        Args:
            path: Path to the saved model.
        """
        import joblib
        data = joblib.load(path)
        self.model = data['model']
        self.model_type = data['model_type']
        self.model_params = data['model_params']
        self._is_trained = data['is_trained']
