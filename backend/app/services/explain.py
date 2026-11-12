"""Partial, exact linear-feature attribution for the ensemble's LR component."""

import re

import numpy as np

from app.services import classifier
from app.services.expert_rules import load_lexicon


def component_cues(text: str, label: str, limit: int = 3) -> list[str]:
    """Return positive word TF-IDF * LR coefficient terms, with lexicon masking."""
    try:
        outer = classifier.load_model(str(classifier.MODEL_PATH))
        cleaned = outer.named_steps["input"].transform([text])
        ensemble = outer.named_steps["classifier"]
        linear = ensemble.named_estimators_["lr"]
        matrix = linear[:-1].transform(cleaned).tocsr()
        estimator = linear.named_steps["classifier"]
        component_label = (
            ensemble.le_.transform([label])[0] if hasattr(ensemble, "le_") else label
        )
        class_index = list(estimator.classes_).index(component_label)
        names = linear.named_steps["features"].get_feature_names_out()
        indices = matrix.indices
        contributions = matrix.data * estimator.coef_[class_index, indices]
        result = []
        for rank in np.argsort(contributions)[::-1]:
            if contributions[rank] <= 0:
                break
            name = names[indices[rank]]
            if not name.startswith("word__"):
                continue
            term = name.removeprefix("word__")
            if (
                "token" in term
                or len(term) > 40
                or not re.fullmatch(r"[^\W\d_]+(?: [^\W\d_]+)?", term)
            ):
                continue
            for word in load_lexicon():
                term = re.sub(
                    r"(?<!\w)" + re.escape(word) + r"(?!\w)",
                    lambda match: match.group()[0] + "***",
                    term,
                    flags=re.IGNORECASE,
                )
            if term not in result:
                result.append(term)
            if len(result) == limit:
                break
        return result
    except (
        classifier.ModelUnavailableError,
        AttributeError,
        KeyError,
        ValueError,
        TypeError,
        IndexError,
    ):
        return []
