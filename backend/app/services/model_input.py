"""Frozen outer cleaning used by the preliminary research model."""

from __future__ import annotations

import re
from collections.abc import Iterable

from sklearn.base import BaseEstimator, TransformerMixin

from app.services.preprocess import clean_text, normalize_unicode


class ModelInputSanitizer(TransformerMixin, BaseEstimator):
    """Match preliminary sanitize() using the fitted model's lexical snapshot."""

    def __init__(self, normalization_map: dict[str, str]) -> None:
        self.normalization_map = normalization_map

    def fit(self, X: Iterable[str], y: object = None) -> ModelInputSanitizer:
        """No learned statistics or input storage."""
        return self

    def transform(self, X: Iterable[str]) -> list[str]:
        """Apply the exact outer normalization order used for training data."""
        result = []
        for text in X:
            text = normalize_unicode(text)
            text = re.sub(r"(?<!\w)@[\w]+", " handletoken ", text)
            text = re.sub(r"\d(?:[\s().+/-]*\d){5,}", " phonetoken ", text)
            result.append(clean_text(text, normalization_map=self.normalization_map))
        return result
