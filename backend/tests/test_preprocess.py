"""M2 tests use only invented text, reserved domains and fake identifiers."""

import json
import pickle
from pathlib import Path

import pytest
from app.main import app
from app.services.preprocess import (
    clean_text,
    collapse_repeated_letters,
    extract_features,
    extract_urls,
    load_normalization_map,
    load_stopwords,
    normalize_spelling,
    normalize_unicode,
    preprocess,
    remove_punctuation,
    replace_entities,
    urdu_script_ratio,
)
from app.services.text_transformer import TextPreprocessor
from fastapi.testclient import TestClient
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline


@pytest.mark.parametrize(
    "source,expected",
    [
        ("ACHHA accha achaa", "acha acha acha"),
        ("nhi nahin naheen", "nahi nahi nahi"),
        ("kia kyaa kyaaaa", "kya kya kya"),
        ("yaaaar ye to fraaud hai!!!", "yaar ye to fraud hai"),
        ("FURAN paise bhjo", "foran paisay bhejo"),
        ("ＨＥＬＬＯ\t\n acha\u200b", "hello acha"),
        ("o\u200dtp o\u0000tp", "otp otp"),
        ("", ""),
        (" \n\t", ""),
        ("!??...", ""),
    ],
)
def test_normalization_examples(source: str, expected: str) -> None:
    assert clean_text(source) == expected


def test_unicode_controls_and_emoji_joiner() -> None:
    assert normalize_unicode("Ａ\tB\r\nC\u202e\x00") == "A B  C"
    assert normalize_unicode("👩🏽‍💻") == "👩🏽‍💻"
    assert normalize_unicode("o\u200dtp") == "otp"


def test_urls_preserve_case_path_and_balanced_parentheses() -> None:
    text = "Visit (HTTPS://Example.com/AbC?Code=X), www.example.org! example.pk/a(b)."
    assert extract_urls(text) == [
        "HTTPS://Example.com/AbC?Code=X",
        "www.example.org",
        "example.pk/a(b)",
    ]
    result = preprocess(text)
    assert result["urls"] == extract_urls(text)
    assert result["cleaned"].count("urltoken") == 3


def test_emails_are_not_urls_and_repeats_are_counted() -> None:
    text = "demo.user@example.com example.com example.com/path"
    result = preprocess(text)
    assert result["urls"] == ["example.com", "example.com/path"]
    assert result["cleaned"] == "emailtoken urltoken urltoken"
    assert result["features"]["url_count"] == 2


@pytest.mark.parametrize(
    "source,expected",
    [
        ("03XX-XXXXXXX", "phonetoken"),
        ("+00 (000) 000-0000", "phonetoken"),
        ("Rs. 100000000", "amounttoken"),
        ("PKR 5,000", "amounttoken"),
        ("2 lakh", "amounttoken"),
        ("500 rupay", "amounttoken"),
        ("demo@example.com", "emailtoken"),
        ("https://example.com/pay?amount=500", "urltoken"),
    ],
)
def test_entity_tokens(source: str, expected: str) -> None:
    assert clean_text(source) == expected


def test_entity_helpers_keep_ordinary_numbers_and_words() -> None:
    assert replace_entities("room 42 kal") == "room 42 kal"
    assert collapse_repeated_letters("yaaaar 0000 !!!") == "yaar 0000 !!!"
    assert (
        normalize_spelling("nhi achha achhai", {"nhi": "nahi", "achha": "acha"})
        == "nahi acha achhai"
    )
    assert remove_punctuation("acha/nahi_OTP، ٹھیک؟") == "acha nahi OTP ٹھیک"


@pytest.mark.parametrize("emoji", ["😀", "❤️", "👩🏽‍💻", "🇵🇰", "1️⃣", "👍🏽"])
def test_emoji_sequences_are_single_units(emoji: str) -> None:
    result = preprocess(f"acha {emoji}!")
    assert result["cleaned"] == "acha emojitoken"
    assert result["features"]["emoji_count"] == 1


def test_features_are_computed_before_cleaning() -> None:
    text = "OTP 42!!?"
    features = extract_features(text)
    assert features == {
        "length": 9,
        "uppercase_ratio": 1.0,
        "exclamation_count": 2,
        "question_count": 1,
        "digit_ratio": 2 / 9,
        "has_url": False,
        "url_count": 0,
        "emoji_count": 0,
    }
    assert preprocess(text)["features"] == features
    assert extract_features("")["digit_ratio"] == 0
    assert extract_features("!!!")["uppercase_ratio"] == 0


def test_urdu_routing_and_boundary_preserve_script() -> None:
    assert urdu_script_ratio("abc123!?") == 0
    assert urdu_script_ratio("ابجabcdefg") == pytest.approx(0.3)
    assert preprocess("ابجabcdefg")["script"] == "roman_or_other"
    assert preprocess("ابجدabcdef")["script"] == "urdu"
    result = preprocess("یہ پیغام ہے، OTP نہیں دینا؟")
    assert result["script"] == "urdu"
    assert "نہیں" in result["cleaned"]
    assert result["features"]["question_count"] == 1


def test_options_and_negation_preservation() -> None:
    assert clean_text("achha nhi", normalize=False) == "achha nhi"
    assert clean_text("ye acha hai") == "ye acha hai"
    assert (
        clean_text("ye acha hai nahi mat OTP", remove_stopwords=True)
        == "acha nahi mat otp"
    )
    assert (
        not {"nahi", "nahin", "na", "mat", "otp", "foran", "paisay"} & load_stopwords()
    )


def test_resource_map_is_stable_and_whole_token() -> None:
    mapping = load_normalization_map()
    assert all(key != value for key, value in mapping.items())
    assert all(clean_text(value) == value for value in mapping.values())
    assert normalize_spelling("achhai", mapping) == "achhai"
    assert clean_text("hey chai kiya") == "hey chai kiya"


def test_repeatability_and_no_input_output(capsys: pytest.CaptureFixture[str]) -> None:
    source = "FURAN example.com/Case?demo=yes 03XX-XXXXXXX 😃!!"
    first = preprocess(source)
    assert preprocess(source) == first
    first["urls"].clear()
    assert preprocess(source)["urls"]
    assert capsys.readouterr() == ("", "")


def test_pipeline_can_serialize_shared_preprocessor() -> None:
    # This is a synthetic integration test, not project training/evaluation.
    model = Pipeline(
        [
            ("preprocess", TextPreprocessor()),
            ("tfidf", TfidfVectorizer(lowercase=False)),
            ("nb", MultinomialNB()),
        ]
    )
    model.fit(
        ["acha din hai", "theek hai", "otp foran bhejo", "inaam paise bhejo"],
        ["normal", "normal", "scam", "scam"],
    )
    loaded = pickle.loads(pickle.dumps(model))
    assert (
        loaded.predict(["achha din hy"]).tolist()
        == model.predict(["achha din hy"]).tolist()
    )


def test_transformer_freezes_resources_without_storing_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transformer = TextPreprocessor(remove_stopwords=True).fit(
        ["synthetic private sentinel"]
    )
    loaded = pickle.loads(pickle.dumps(transformer))
    monkeypatch.setattr(
        "app.services.preprocess.load_normalization_map", lambda: {"achha": "changed"}
    )
    monkeypatch.setattr(
        "app.services.preprocess.load_stopwords", lambda: frozenset({"acha"})
    )
    assert loaded.transform(["achha hai"]) == ["acha"]
    assert "sentinel" not in repr(vars(loaded))


def test_existing_api_uses_normalized_cues_and_url_without_echo() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/analyze/text",
        json={"text": "FURAN OTP bhjo HTTPS://Example.com/UniqueCase"},
    )
    assert response.status_code == 200
    assert {"R01", "R03", "R05"}.issubset(
        response.json()["rule_flags"]
    )
    assert "UniqueCase" not in response.text
    assert "cleaned" not in response.json()


def test_url_only_text_uses_probability_distribution() -> None:
    client = TestClient(app)
    result = client.post(
        "/api/analyze/text", json={"text": "https://example.com"}
    ).json()
    assert sum(result["probabilities"].values()) == pytest.approx(1.0)


def test_documented_examples_match_implementation() -> None:
    path = Path(__file__).resolve().parents[2] / "docs" / "PREPROCESS_EXAMPLES.json"
    for row in json.loads(path.read_text(encoding="utf-8")):
        assert clean_text(row["input"]) == row["expected"]


pytestmark = pytest.mark.usefixtures("fake_text_model")
