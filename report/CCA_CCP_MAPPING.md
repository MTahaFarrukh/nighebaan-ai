# CCA / CCP requirement mapping

The original teacher briefs (`AIES_CCA`, `AIES_CCP`) were not present in the
repository at report time. Headings follow `docs/TECH_DOC.md` sections 2 and 16,
which already map this project to those briefs. If the PDFs are added later,
compare this table before printing; do not invent extra course requirements.

| Course requirement (TECH_DOC §2) | Where the CCP report answers it |
|---|---|
| Real-world problem, clear I/O | Report §1 |
| 2+ datasets or 1 large | Report §2 |
| Pre-processing of noisy data | Report §4 |
| Diverse data types | Report §3 and §7 |
| Baseline + multiple AI approaches | Report §5 and §6 |
| Privacy / ethics | Report §8 |
| Visualization / interface | Report §7 |
| Network dependency of real-time monitoring | Report §7 (WhatsApp bridge + simulator) |
| CCP only: 10+ page technical report with methodology diagram | This `report/` folder; Figure 1 |

CCA deliverables in the spec are code plus visualization. CCP additionally
requires this report. Numbers in the report are copied from generated JSON/MD
under `docs/` and `backend/models/metrics.json`. They are not typed from memory.
