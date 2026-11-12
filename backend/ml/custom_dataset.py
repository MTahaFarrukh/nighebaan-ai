"""Build synthetic review packs and promote only completed human annotations."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd
from sklearn.metrics import cohen_kappa_score

THEMES = (
    "prize",
    "bank",
    "wallet",
    "government",
    "job",
    "courier",
    "loan",
    "investment",
    "group",
    "relative",
)
PREFIXES = (
    "",
    "Salam, ",
    "Assalam o alaikum, ",
    "Ek baat suno: ",
    "Zara dekhein: ",
    "Aap ke liye message: ",
    "Hello ji, ",
    "Ye baat parh lein: ",
    "Ji suniye, ",
    "Ek update hai: ",
)


def read_csv(path: Path) -> pd.DataFrame:
    """Read review data without disclosing parser details."""
    try:
        return pd.read_csv(path, dtype=str, keep_default_na=False).fillna("")
    except (OSError, ValueError, UnicodeError):
        raise ValueError("Review CSV cannot be read.") from None


def build_pack(seeds_path: Path, directory: Path) -> dict[str, object]:
    """Expand LLM-authored seeds into an explicitly unreviewed candidate set."""
    seeds = json.loads(seeds_path.read_text(encoding="utf-8"))
    if set(seeds) != set(THEMES):
        raise ValueError("Seed file must contain the ten specified themes.")
    rows = []
    for theme in THEMES:
        if set(seeds[theme]) != {"normal", "scam"}:
            raise ValueError("Each theme needs normal and scam seeds.")
        for label, expected in (("scam", 5), ("normal", 3)):
            templates = seeds[theme][label]
            if len(templates) != expected or any(
                not isinstance(t, str) or not t.strip() for t in templates
            ):
                raise ValueError("Each theme needs five scam and three normal seeds.")
            for index, template in enumerate(templates):
                family = f"{theme}-{label}-{index}"
                for prefix in PREFIXES:
                    text = prefix + template.strip()
                    rows.append(
                        {
                            "id": hashlib.sha256(text.encode()).hexdigest()[:16],
                            "text": text,
                            "label": label,
                            "theme": theme,
                            "family_id": family,
                            "source": "llm_assisted",
                            "annotator": "",
                        }
                    )
    frame = pd.DataFrame(rows)
    if frame["text"].duplicated().any() or frame["id"].duplicated().any():
        raise ValueError("Duplicate candidates; revise the seeds.")
    files = (
        "custom_scam.draft.csv",
        "review_all.csv",
        "reviewer_a.csv",
        "reviewer_b.csv",
        "manifest.json",
    )
    if any((directory / name).exists() for name in files):
        raise ValueError("Review pack already exists; use a new directory.")
    # Stratify the blind sample by theme before any project split exists.
    sample = frame.groupby("theme", sort=True).sample(n=10, random_state=42)
    blind = (
        sample[["id", "text"]].sample(frac=1, random_state=42).reset_index(drop=True)
    )
    for column in ("label", "reviewer"):
        blind[column] = ""
    review = frame[["id", "text", "theme", "family_id"]].copy()
    for column in ("label", "privacy_ok", "reviewer"):
        review[column] = ""
    directory.mkdir(parents=True, exist_ok=True)
    frame.to_csv(directory / files[0], index=False)
    review.to_csv(directory / files[1], index=False)
    for name in files[2:4]:
        blind.to_csv(directory / name, index=False)
    report = {
        "status": "awaiting_human_review",
        "rows": len(frame),
        "class_counts": frame["label"].value_counts().to_dict(),
        "theme_counts": frame["theme"].value_counts().to_dict(),
        "families": int(frame["family_id"].nunique()),
        "blind_sample_rows": len(blind),
        "draft_sha256": hashlib.sha256((directory / files[0]).read_bytes()).hexdigest(),
        "sample_ids": blind["id"].tolist(),
        "seeds_sha256": hashlib.sha256(seeds_path.read_bytes()).hexdigest(),
        "generation": "LLM-authored seeds expanded with ten shared prefixes; not independent examples",
    }
    (directory / files[4]).write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return report


def validate_reviews(frame: pd.DataFrame, ids: set[str], *, privacy: bool) -> None:
    """Require a complete, uniquely identified annotation table."""
    columns = {"id", "label", "reviewer"} | ({"privacy_ok"} if privacy else set())
    if not columns.issubset(frame.columns):
        raise ValueError("Review columns are missing.")
    if frame["id"].duplicated().any() or set(frame["id"]) != ids:
        raise ValueError("Review IDs are missing, duplicated or unexpected.")
    if not frame["label"].isin(["normal", "scam"]).all():
        raise ValueError("Every item requires a human normal/scam label.")
    if not frame["reviewer"].str.fullmatch(r"reviewer_[A-Za-z0-9_-]+").all():
        raise ValueError("Use anonymous reviewer IDs such as reviewer_a.")
    if privacy and not frame["privacy_ok"].eq("yes").all():
        raise ValueError("Every item requires privacy_ok=yes after human inspection.")


def promote(directory: Path, output: Path) -> dict[str, object]:
    """Compute independent agreement and export all-item adjudicated labels."""
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    draft_path = directory / "custom_scam.draft.csv"
    if hashlib.sha256(draft_path.read_bytes()).hexdigest() != manifest["draft_sha256"]:
        raise ValueError("Draft changed; create a new review pack.")
    draft = read_csv(draft_path)
    review = read_csv(directory / "review_all.csv")
    validate_reviews(review, set(draft["id"]), privacy=True)
    samples = [read_csv(directory / f"reviewer_{name}.csv") for name in ("a", "b")]
    for sample in samples:
        validate_reviews(sample, set(manifest["sample_ids"]), privacy=False)
        if sample["reviewer"].nunique() != 1:
            raise ValueError("Each independent sample must have exactly one reviewer.")
    if samples[0]["reviewer"].iloc[0] == samples[1]["reviewer"].iloc[0]:
        raise ValueError("Two distinct human reviewers are required.")
    reference = draft.set_index("id")["text"]
    for table in [review, *samples]:
        if (
            "text" not in table
            or not table["text"].eq(table["id"].map(reference)).all()
        ):
            raise ValueError("Review text changed; revise seeds and create a new pack.")
    left, right = [sample.set_index("id").sort_index()["label"] for sample in samples]
    if len(set(left) | set(right)) < 2:
        raise ValueError("Agreement requires more than one observed class.")
    kappa = float(cohen_kappa_score(left, right))
    accepted = (
        draft.drop(columns=["label", "annotator"])
        .merge(review[["id", "label", "reviewer"]], on="id", validate="one_to_one")
        .rename(columns={"reviewer": "annotator"})
    )
    counts = accepted["label"].value_counts().to_dict()
    if not 400 <= counts.get("scam", 0) <= 600 or counts.get("normal", 0) < 300:
        raise ValueError("Reviewed labels do not meet the spec's class-count targets.")
    if output.exists() or output.with_suffix(".review.json").exists():
        raise ValueError("Approved output exists; it will not be overwritten.")
    report = {
        "status": "human_reviewed",
        "rows": len(accepted),
        "class_counts": counts,
        "cohens_kappa": kappa,
        "sample_rows": len(left),
        "sample_disagreements": int(left.ne(right).sum()),
        "draft_sha256": manifest["draft_sha256"],
        "review_sha256": hashlib.sha256(
            (directory / "review_all.csv").read_bytes()
        ).hexdigest(),
        "adjudication": "review_all.csv contains final labels after human discussion",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    accepted[["text", "label", "theme", "source", "annotator"]].to_csv(
        output, index=False
    )
    report["approved_sha256"] = hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix(".review.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return report


def main() -> None:
    """Expose draft and promotion commands without printing example content."""
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build")
    build.add_argument("--seeds", type=Path, required=True)
    build.add_argument("--directory", type=Path, required=True)
    approve = commands.add_parser("promote")
    approve.add_argument("--directory", type=Path, required=True)
    approve.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = (
            build_pack(args.seeds, args.directory)
            if args.command == "build"
            else promote(args.directory, args.output)
        )
    except (ValueError, OSError, KeyError, TypeError):
        parser.exit(
            1,
            "Custom dataset operation failed; check schema, review completion and output paths.\n",
        )
    print(
        json.dumps(
            {key: value for key, value in result.items() if key != "sample_ids"},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
