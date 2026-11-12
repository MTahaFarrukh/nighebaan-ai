"""Serializable sklearn adapter with frozen lexical resources for inference."""

from __future__ import annotations

from collections.abc import Iterable

from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.utils.validation import check_is_fitted

from app.services import preprocess


class TextPreprocessor(TransformerMixin, BaseEstimator):
    """Snapshot configuration at fit time without storing training messages."""

    def __init__(
        self, *, normalize: bool = True, remove_stopwords: bool = False
    ) -> None:
        self.normalize = normalize
        self.remove_stopwords = remove_stopwords

    def fit(self, X: Iterable[str], y: object = None) -> TextPreprocessor:
        """Freeze resources; no corpus statistics or message contents are retained."""
        self.normalization_map_ = (
            preprocess.load_normalization_map() if self.normalize else {}
        )
        self.stopwords_ = (
            preprocess.load_stopwords() if self.remove_stopwords else frozenset()
        )
        return self

    def transform(self, X: Iterable[str]) -> list[str]:
        """Apply exactly the resource snapshot embedded in the fitted pipeline."""
        check_is_fitted(self, ["normalization_map_", "stopwords_"])
        return [
            preprocess.clean_text(
                text,
                normalize=self.normalize,
                remove_stopwords=self.remove_stopwords,
                normalization_map=self.normalization_map_,
                stopwords=self.stopwords_,
            )
            for text in X
        ]
