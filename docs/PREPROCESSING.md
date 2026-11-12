# M2 preprocessing

The shared implementation is `backend/app/services/preprocess.py`. Existing
analyzer callers continue to receive `cleaned` and `urls`; additional internal
metadata contains `script`, `urdu_ratio` and `features`. HTTP response schemas
are unchanged. Neither input text nor URLs are logged, saved or fetched.

## Order and options

1. NFKC normalization, whitespace normalization and removal of controls/format
   characters. Emoji ZWJ sequences retain their joiners until emoji tokenization.
2. Arabic/Urdu-script letter ratio, using all alphabetic letters as denominator.
   A ratio strictly greater than 0.3 selects `script=urdu`. Digits and punctuation
   do not affect this ratio. This detects script, not the Urdu language itself.
3. Extract URL candidates and features before lowercasing or destructive edits.
   URL casing, paths and query values are preserved in memory after the Unicode
   normalization step. Repeated occurrences are retained. Sentence delimiters
   are removed; balanced parentheses within URLs are retained.
4. Lowercase and tokenize entities. Emails are masked before URLs so their
   domains are not mistaken for links; amounts are masked before phone patterns
   so a long monetary value does not become a phone. Tokens are `emailtoken`,
   `urltoken`, `amounttoken`, `phonetoken`. Bare domains are static candidates,
   not proof of a valid domain or malicious intent. Fake phone placeholders
   `03XX-XXXXXXX` are supported alongside numeric phone-like sequences.
5. Emoji become `emojitoken`. Common pictographs, skin-tone modifiers, joined
   sequences, two-letter flags and keycaps are counted as sequence units. This
   is a lightweight Unicode-range implementation, not a complete Unicode emoji
   grapheme database; future/uncommon sequences may not be counted precisely.
6. Collapse runs of repeated letters to two. Digits are not collapsed.
7. Apply whole-token mappings from `normalization_map.json`. `normalize=False`
   disables this lexical step only; it is not the full raw-text ablation.
8. Replace punctuation/symbols with word boundaries, retaining Unicode letters,
   combining marks and digits. Collapse whitespace.
9. Optional stopword removal (`remove_stopwords=True`), disabled by default.
   The small Roman Urdu list preserves negation, urgency and financial cues.

The v1 normalization map is a manually specified starter vocabulary, not
learned from validation or test data. Ambiguous mappings such as `kia -> kya`
come from the project spec and can change meaning in some contexts. Tune only
using training/validation later. Urdu text remains in Urdu; Roman tokens in
mixed text can still be normalized. Full Urdu lexicon routing and transliteration
belong to M7 and are not implemented here. `script=urdu` is the routing signal,
not a claim that the current stub classifier understands Urdu script.

## Features

Features use Unicode-cleaned input before lowercasing/tokenization:

| Key | Definition |
|---|---|
| length | Unicode code-point count, including spaces |
| uppercase_ratio | Uppercase letters divided by all alphabetic letters |
| exclamation_count | Number of `!` characters |
| question_count | Number of `?` and Urdu `؟` characters |
| digit_ratio | Digit characters divided by total code points |
| has_url / url_count | Presence / occurrence count of static URL candidates |
| emoji_count | Number of recognized emoji sequences |

Empty denominators yield zero. Punctuation counts include punctuation within
URL/query text; they are raw surface counts, not semantic urgency judgments.

## Training/inference consistency

`app.services.text_transformer.TextPreprocessor` is the sklearn adapter for
the upcoming M3 pipeline. Its `fit` snapshots the normalization map and optional
stopwords without storing input messages; `transform` uses that snapshot.
Saving the complete pipeline therefore preserves lexical configuration even
if the resource files are later edited. Save this adapter with the vectorizer
and classifier, not just a callable that reloads external resource files.
Changes to Python preprocessing logic still require versioning/retraining.

Handcrafted features are exposed for subsequent experiments, not yet fed into
the stub classifier. The stub recognizes `urltoken` to preserve its previous
URL-only fallback probabilities. No real model has been trained here.

## Verification and limits

Run from `backend`:

```powershell
.venv/Scripts/python.exe -m pytest -q
```

`PREPROCESS_EXAMPLES.json` contains only invented examples and fake entities.
Tests verify each expected output, pipeline serialization/resource snapshots,
Unicode/script boundaries, entity overlap, emoji, features, opt-in stopwords,
repeatability and API compatibility. A tiny synthetic sklearn fit is solely an
integration test; it produces no project metrics or saved model.

Entity replacement is not a comprehensive anonymizer: names, addresses,
obfuscated identifiers and unusual number formats may remain. Do not persist
live inputs or raw URLs. No train/validation/test corpora were used for M2, and
no test-set evaluation occurred. Validation F1 comparisons and stopword ablations
remain pending until M3/M4 models exist.
