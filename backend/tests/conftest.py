"""Small synthetic classifier fixture for API tests independent of local models."""

import numpy as np
import pytest
from app.services import classifier


@pytest.fixture
def fake_text_model(monkeypatch):
    class SyntheticModel:
        classes_ = np.array(["normal", "abusive", "scam"])

        def predict_proba(self, texts):
            return np.array([[0.2, 0.1, 0.7]])

    monkeypatch.setattr(classifier, "load_model", lambda path: SyntheticModel())


@pytest.fixture(autouse=True)
def isolated_history(tmp_path, monkeypatch):
    from app.services import history

    monkeypatch.setattr(history, "DB_PATH", tmp_path / "alerts.sqlite3")
