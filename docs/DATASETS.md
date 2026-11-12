# Dataset preparation (M1)

Implementation follows TECH_DOC 6.2/6.4 and SKILLS.md skill 3. This is an
offline corpus pipeline, never a storage path for live user messages. Only
privacy-reviewed, de-identified research corpora and reviewed synthetic data
may be supplied. The preparation command does not download data. The separate
source-audit command fetches official files in memory and persists only metadata.

## Inventory

Source files were fetched and audited in memory on 2026-11-09; no public
corpus text was saved. Actual source sizes, hashes and label counts are in
[DATASET_INVENTORY.json](DATASET_INVENTORY.json). The synthetic custom review
pack has been generated; human labels and approval remain pending. See
[DATA_REVIEW.md](DATA_REVIEW.md) for concrete review instructions. Published
approximate sizes below remain context, not measured training-set sizes.

| Source | Official source / license | Published size | Original labels -> project labels | Local status |
|---|---|---|---|---|
| UCI Roman Urdu | [UCI](https://archive.ics.uci.edu/dataset/458/roman+urdu+data+set), CC BY 4.0 | About 20k | Positive/Neutral -> normal; Negative and unknown labels excluded | Audited in memory; approved local input pending |
| RUHSOLD | [Authors' repository](https://github.com/haroonshakeel/roman_urdu_hate_speech), MIT | About 10k (TECH_DOC estimate) | 1/Normal -> normal; 0/Abusive-Offensive, 2/Religious Hate, 3/Sexism, 4/Profane-Untargeted -> abusive | Audited in memory; approved local input pending |
| SMS Spam Collection | [UCI](https://archive.ics.uci.edu/dataset/228/sms+spam+collection), CC BY 4.0 | UCI lists 5,574 | ham -> normal; spam -> scam | Audited in memory; approved local input pending |
| Custom Roman Urdu | Project authors; redistribution license not assigned | Target 400-600 scam + 300+ normal | normal/scam retained; other labels excluded | Draft review pack generated; human review pending |

RUHSOLD numeric meanings come from the authors'
[label definitions](https://github.com/haroonshakeel/roman_urdu_hate_speech/blob/main/label_definitions.txt).
The URL dataset belongs to the separate M6 URL pipeline and is not merged here.
Spam is only a proxy for scam, as prescribed by the spec; preserve the SMS source
for the later with/without-SMS ablation. Sentiment negative is never abusive.

## Input contract

Place approved files beneath `backend/data/raw/`:

```text
uci/Roman Urdu DataSet.csv
ruhsold/ruhsold.csv
sms/SMSSpamCollection
custom/custom_scam.csv
```

All files must be UTF-8 (UTF-8 BOM supported). Review and remove personal data
before placing files here; the loader does not claim automatic anonymization.
Do not use chat exports, transcripts, real phone numbers, CNICs or account IDs.

- UCI: original headerless CSV; columns 1 and 2 are text and sentiment.
  The optional third column is ignored. Do not add a header.
- RUHSOLD: reviewed **headered CSV export** with `text,label`. Adapt the
  authors' TSV files locally to these two named columns, preserving original
  numeric labels. Combine one task's partitions, not both tasks; retain the
  original dataset version and conversion notes in your local data inventory.
  This pipeline creates new project splits, not the original benchmark splits.
  Numeric 0 is abusive and 1 is normal. Named labels normal, offensive,
  abusive, hate, abusive/offensive, religious hate, sexism and
  profane/untargeted are also accepted. No arbitrary binary-label guessing.
- SMS: original headerless `label<TAB>text` format. Quotes are literal text.
- Custom: headered CSV with `text,label,theme,source,annotator`; retain review
  metadata in this local raw file. Follow SKILLS.md skill 4 for human review
  and Cohen's kappa. `source` in processed output is dataset identity
  (`custom`), not generation method or annotator identity.

The loaders drop null/blank text, trim outer whitespace and normalize label
case/whitespace. Missing and unknown labels are counted as unmapped and dropped.
They do not perform M2 text normalization, balancing or vectorization.

## Outputs and reproducibility

From `backend`, with the declared requirements installed:

```powershell
.\.venv\Scripts\Activate.ps1
python -m ml.data_prep
pytest -q
```

Optional `--raw-dir` and `--output-dir` accept explicit paths. Defaults resolve
relative to the script's backend directory, not the current working directory.
All four inputs are required; missing files fail without producing a partial
dataset. Existing named outputs are not overwritten, protecting frozen splits.
For an intentional new corpus version, use a new ignored output directory and
record the change before training. Do not repeatedly regenerate test splits.

1. Merge all sources and deduplicate exact **trimmed** text globally. Remove
   every row of text with conflicting labels, counting affected rows. For
   same-label duplicates prefer custom provenance so copies cannot leak out of
   its hold-out; otherwise retain deterministic alphabetical source precedence.
2. Reserve a stratified 20% of deduplicated custom rows as
   `custom_holdout.csv` (SKILLS.md skill 4). Both normal and scam must remain.
3. Save the remaining pool as `all.csv`, then stratify it into
   `train.csv`, `val.csv`, `test.csv` at 70/15/15 with `random_state=42`
   for both split stages. Integer rounding can slightly change percentages.
   `all.csv` is exactly the union of these three splits; it excludes hold-out.
4. Assert pairwise text disjointness for all four evaluation/training files.
   Fail if any requested split cannot preserve the input classes.
5. Save and print `counts.json`: loader input/empty/unmapped/retained counts,
   class counts by source before/after deduplication, conflict/duplicate row
   counts, and class/source counts for every split. Reports contain no text,
   original labels, annotator identifiers or phone numbers.

CSV columns are exactly `text,label,source,lang_hint`. Source IDs are
`uci,ruhsold,sms,custom`; language hints are `roman_urdu` or `en` and describe
the corpus, not per-row language detection. These approved offline text
artifacts stay local and must never be committed. The hold-out is also frozen;
do not tune on it or on test. No model evaluation is performed by preparation.

Tracked `.gitignore` rules now exclude raw data, processed data and
WhatsApp auth directories. This protection travels with clones; the existing
local exclusions remain redundant protection. Model joblib files are ignored.
Keep seeds, drafts, annotation sheets and approved text inside ignored data paths.

## Verification status and limits

Tests use only synthetic placeholders, covering label mappings, empty and
unknown rows, conflicts, cross-source duplicates, reproducibility, frozen
outputs, leakage assertions, small classes and the complete CLI. Those counts
are test data, not project dataset statistics. M1 is not complete until all
four reviewed corpora have been supplied, their actual inventory recorded,
and a production preparation run has generated the real counts.

Exact-text deduplication does not eliminate template-family or paraphrase
leakage. Record that limitation before interpreting model scores. Custom
human review, label agreement and dataset licensing obligations remain the
dataset owners' responsibilities.

## Generated inventory snapshot

Generated from DATASET_INVENTORY.json and the ignored review manifest;
these are pre-dedup source counts, not final training or evaluation counts.

| Source/partition | Rows | Normal mapped | Abusive mapped | Scam mapped |
|---|---:|---:|---:|---:|
| uci | 20229 | 14829 | 0 | 0 |
| sms | 5574 | 4827 | 0 | 747 |
| ruhsold/train | 7209 | 3851 | 3358 | 0 |
| ruhsold/validation | 801 | 428 | 373 | 0 |
| ruhsold/test | 2003 | 1070 | 933 | 0 |

Custom draft: 800 candidates, 500 scam and 300 normal,
80 seed families, 100 blind-review items.
Status: **awaiting human review**. No real-draft kappa or model metrics exist.

## M6 URL source
[UCI PhiUSIIL](https://archive.ics.uci.edu/dataset/967/phiusiil%2Bphishing%2Burl%2Bdataset), Prasad & Chandra (2024), CC BY 4.0. This separate binary dataset uses source label 0=phishing and 1=legitimate; training maps phishing to 1. Source archive and partition fingerprints: URL_DATASET_INVENTORY.json. Generated counts and metrics: URL_MODEL_RESULTS.json. URL strings and all source columns stay in memory; no source URLs are fetched. Only computed static lexical features are trained.
