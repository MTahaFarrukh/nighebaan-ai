"""Synthetic LR attribution and URL augmentation integrity checks."""

from types import SimpleNamespace

from app.services import explain
from ml.url_robustness import benign_variant
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import FeatureUnion, Pipeline


def test_actual_linear_component_cues_masked(monkeypatch):
    texts = [
        "otp prize",
        "otp prize money",
        "syntheticbadword rude",
        "syntheticbadword angry",
        "salam friend",
        "hello friend",
    ]
    labels = ["scam", "scam", "abusive", "abusive", "normal", "normal"]
    linear = Pipeline(
        [
            ("features", FeatureUnion([("word", TfidfVectorizer())])),
            ("classifier", LogisticRegression(random_state=42)),
        ]
    ).fit(texts, labels)
    outer = SimpleNamespace(
        named_steps={
            "input": SimpleNamespace(transform=lambda rows: rows),
            "classifier": SimpleNamespace(named_estimators_={"lr": linear}),
        }
    )
    monkeypatch.setattr(explain.classifier, "load_model", lambda path: outer)
    monkeypatch.setattr(explain, "load_lexicon", lambda: ("syntheticbadword",))
    assert "otp" in explain.component_cues("otp prize", "scam")
    cues = explain.component_cues("syntheticbadword", "abusive")
    assert cues == ["s***"]
    assert explain.component_cues("98765432", "scam") == []


def test_unavailable_attribution_does_not_break_analysis(monkeypatch):
    monkeypatch.setattr(explain.classifier, "load_model", lambda path: object())
    assert explain.component_cues("synthetic", "normal") == []


def test_augmentation_preserves_origin_and_is_deterministic():
    from urllib.parse import urlsplit

    source = "https://example.com/"
    values = [benign_variant(source, index) for index in range(100)]
    assert values == [benign_variant(source, index) for index in range(100)]
    assert all(
        urlsplit(value).netloc == "example.com" and urlsplit(value).scheme == "https"
        for value in values
    )
    assert len({urlsplit(value).path for value in values}) > 80
    assert any(urlsplit(value).query for value in values)
    heldout = [benign_variant(source, index, validation=True) for index in range(100)]
    assert not set(values) & set(heldout)


def test_voting_encoded_classes(monkeypatch):
    from sklearn.ensemble import VotingClassifier

    linear = Pipeline(
        [
            ("features", FeatureUnion([("word", TfidfVectorizer())])),
            ("classifier", LogisticRegression(random_state=42)),
        ]
    )
    ensemble = VotingClassifier([("lr", linear)], voting="soft").fit(
        [
            "otp prize",
            "otp money",
            "rude angry",
            "rude loud",
            "hello friend",
            "salam friend",
        ],
        ["scam", "scam", "abusive", "abusive", "normal", "normal"],
    )
    outer = SimpleNamespace(
        named_steps={
            "input": SimpleNamespace(transform=lambda rows: rows),
            "classifier": ensemble,
        }
    )
    monkeypatch.setattr(explain.classifier, "load_model", lambda path: outer)
    assert "otp" in explain.component_cues("otp prize", "scam")


def test_www_variant_preserves_path_scheme_and_credentials():
    from ml.url_robustness import without_www

    assert (
        without_www("https://www.example.com/demo?q=1")
        == "https://example.com/demo?q=1"
    )
    assert without_www("http://www.example.com:8080/") == "http://example.com:8080/"
    assert (
        without_www("https://www.user@example.com/") == "https://www.user@example.com/"
    )
    assert without_www("https://wwwx.example.com/") == "https://wwwx.example.com/"
