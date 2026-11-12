"""Synthetic ablation isolation and raw-text recovery checks."""

import pandas as pd
import pytest
from ml.evaluate import make_pipeline, variant_inputs


def test_raw_mode_has_no_preprocessing() -> None:
    assert "preprocess" not in make_pipeline("raw_both", 1).named_steps
    assert (
        make_pipeline("no_lexical_normalization", 1).named_steps["preprocess"].normalize
        is False
    )
    assert (
        make_pipeline("with_stopwords_removed", 1)
        .named_steps["preprocess"]
        .remove_stopwords
        is True
    )


def test_feature_views() -> None:
    assert [
        name
        for name, _ in make_pipeline("word_only", 1)
        .named_steps["features"]
        .transformer_list
    ] == ["word"]
    assert [
        name
        for name, _ in make_pipeline("char_only", 1)
        .named_steps["features"]
        .transformer_list
    ] == ["char"]


def test_original_mapping_and_sms_isolation() -> None:
    frame = pd.DataFrame(
        {
            "text": ["acha", "placeholder", "otp", "sms text"],
            "label": ["normal", "abusive", "scam", "normal"],
            "source": ["uci", "ruhsold", "custom", "sms"],
        }
    )
    raw = {(row.source, row.text): row.text.upper() + "!" for row in frame.itertuples()}
    X, y, V, vy = variant_inputs("raw_both", frame, frame, raw)
    assert X[0] == "ACHA!" and V[0] == "ACHA!"
    X, y, V, vy = variant_inputs("without_sms", frame, frame, raw)
    assert len(X) == 3 and len(V) == 4 and "sms text" in V
    assert set(y) == {"normal", "abusive", "scam"}
    assert vy == frame.label.tolist()


def test_missing_original_fails_instead_of_using_cleaned_text() -> None:
    frame = pd.DataFrame(
        {
            "text": ["a", "b", "c"],
            "label": ["normal", "abusive", "scam"],
            "source": ["uci", "ruhsold", "custom"],
        }
    )
    with pytest.raises(KeyError):
        variant_inputs("raw_both", frame, frame, {})


def test_original_lookup_keeps_first_source_representative(monkeypatch) -> None:
    import hashlib

    from ml.train_preliminary import load_public

    payload = b"ACCHA!,Positive\nachha,Neutral\n"
    monkeypatch.setattr("ml.train_preliminary.fetch", lambda url: payload)
    inventory = {
        "sources": [
            {
                "source": "uci",
                "url": "https://example.com",
                "member_sha256": hashlib.sha256(payload).hexdigest(),
                "encoding": "utf-8",
            }
        ]
    }
    lookup = {}
    frame = load_public(inventory, raw_lookup=lookup)
    assert frame.text.tolist() == ["acha", "acha"]
    assert lookup[("uci", "acha")] == "ACCHA!"


def test_lexical_ablation_preserves_entity_cleaning() -> None:
    from ml.train_preliminary import sanitize

    assert sanitize("ACHHA @demo_handle", normalize=False) == "achha handletoken"
    assert sanitize("ACHHA @demo_handle") == "acha handletoken"
