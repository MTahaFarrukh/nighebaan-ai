# Preliminary baseline run

Command from backend:
`.venv/Scripts/python.exe -m ml.train_preliminary --output models/nb_preliminary_001`

The runner verifies the exact official corpus bytes against docs/DATASET_INVENTORY.json.
It downloads into memory, tokenizes identifiers/entities in memory, maps only specified labels,
deduplicates cleaned text globally, and splits with seed 42. No public corpus text CSVs are saved.
The custom draft is human-unverified. Only one representative per template family is used,
then 20% of the retained custom subset is held out. Remaining text uses 70/15/15 splits.
Only train and validation are passed to the trainer. Test and custom hold-out are not evaluated.
Hashes of partition membership permit subsequent reconstruction against pinned source bytes.

This is a preliminary experiment, not completion of reviewed M1 or final evaluation.
Entity regexes do not prove anonymization; original/cleaned public text remains in memory only.
Learned model vocabularies are local research artifacts and must not be committed or published.
Upstream licenses and label definitions remain as documented in DATASETS.md.

Output: nb_baseline.joblib, metrics.json, validation_metrics.json, label_map.json,
experiments.csv, run_metadata.json, data_manifest.json. Input hashes now describe canonical
DataFrame CSV serialization in memory, not necessarily exact bytes of input files.
The classifier API is still a stub until explicit integration work is completed.
M4 comparisons must reconstruct the SAME partitions and verify membership hashes, not invent
new splits or evaluate test. Full reviewed-data results remain separate from this run.
