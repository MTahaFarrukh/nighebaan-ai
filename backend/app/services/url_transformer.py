"""Serializable stateless feature extraction shared by training and serving."""

from __future__ import annotations

import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin

from app.services.url_features import FEATURE_NAMES, extract_url_features


class URLFeatureTransformer(TransformerMixin, BaseEstimator):
    """Fit stores no URLs, domains or vocabularies."""

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        rows = [extract_url_features(url) for url in X]
        return np.asarray([[float(row[key]) for key in FEATURE_NAMES] for row in rows])
