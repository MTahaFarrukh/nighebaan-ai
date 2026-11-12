# M4 preliminary comparison

Run from backend:
`.venv/Scripts/python.exe -u -m ml.train_improved --output models/m4_preliminary_001`

Sources and every split membership must match the NB baseline manifest. Public text
remains in memory. Test and custom hold-out are reconstructed for integrity checks
only and never passed to predict, fit, calibration, search or model selection.

- Logistic regression: balanced class weights; C in [0.5, 2].
- Linear SVM: balanced class weights; C in [0.5, 2]. Best training-CV pipeline
  calibrated using three shuffled stratified training folds, seed 42.
- Random forest: balanced class weights; 80 trees; max_depth in [30, unlimited].
- Every search uses five shuffled stratified training folds, seed 42, macro-F1.
  Entire preprocessing/vectorizer pipeline is inside CV, so vocabularies and IDF
  statistics are fitted independently for each fold.
- TF-IDF limits: 15k word features and 25k char features. The NB baseline was
  uncapped, so this is a practical model comparison, not an isolated classifier ablation.
- Top two individual validation models form an equal-weight soft-voting ensemble.
  The final model is whichever has highest validation macro-F1, including NB.

Each completed family saves a .joblib and .json checkpoint. The same command
resumes finished families only when runner/configuration/partition metadata match.
Do not edit preprocessing or runner files during the run. Single-family search
interrupted before a checkpoint must be repeated. No corpus cache is persisted.

The run directory contains experiments.csv with training-CV scores for every
candidate. Its validation field refers to the selected estimator in that model
family (not separate validation evaluation of each parameter candidate).
Metrics include per-class precision/recall/F1, confusion matrix, macro ROC-AUC OVR,
accuracy and batch prediction time per item. SVM probability calibration changes
its final classifier relative to the uncalibrated search scorer.

All results are preliminary and human-unverified. Do not interpret them as
production safety or real-world performance. Custom data uses only one item per
seed family. No ablation results exist yet; the metrics ablations array remains empty.
API model loading and final promotion are separate pending work after comparison.

## Completed preliminary comparison

Generated from models/m4_preliminary_001/metrics.json. Validation only.

| Model | Macro-F1 | Scam recall |
|---|---:|---:|
| nb_baseline | 0.3924 | 0.0206 |
| lr | 0.9263 | 0.9485 |
| svm | 0.9325 | 0.9072 |
| rf | 0.9115 | 0.8866 |
| voting_ensemble | 0.9367 | 0.9381 |
