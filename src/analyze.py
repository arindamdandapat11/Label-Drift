from __future__ import annotations

from itertools import combinations
from pathlib import Path

import pandas as pd
from sklearn.metrics import accuracy_score, cohen_kappa_score


def build_reports(predictions: pd.DataFrame, labels: list[str], gold_available: bool) -> dict[str, pd.DataFrame]:
    prompt_ids = list(predictions["prompt_id"].unique())
    wide = predictions.pivot_table(
        index="example_id",
        columns="prompt_id",
        values="parsed_label",
        aggfunc="first",
    )
    gold = predictions.drop_duplicates("example_id").set_index("example_id")["gold"]
    wide = wide.join(gold.rename("gold"))

    n_unique = wide[prompt_ids].nunique(axis=1)
    wide["n_unique_labels"] = n_unique
    wide["all_agree"] = n_unique == 1
    wide["majority_label"] = wide[prompt_ids].mode(axis=1)[0]
    wide["wording_changed_decision"] = ~wide["all_agree"]

    pair_rows = []
    for left, right in combinations(prompt_ids, 2):
        same = (wide[left] == wide[right]).mean()
        kappa = cohen_kappa_score(wide[left], wide[right], labels=labels + ["unknown"])
        pair_rows.append(
            {
                "prompt_a": left,
                "prompt_b": right,
                "agreement": round(float(same), 4),
                "cohen_kappa": round(float(kappa), 4),
            }
        )
    pairwise = pd.DataFrame(pair_rows)

    per_prompt = []
    for prompt_id in prompt_ids:
        subset = predictions[predictions["prompt_id"] == prompt_id]
        row = {
            "prompt_id": prompt_id,
            "unknown_rate": round(float((subset["parsed_label"] == "unknown").mean()), 4),
        }
        if gold_available:
            valid = subset[subset["gold"].notna()]
            row["accuracy"] = round(float(accuracy_score(valid["gold"], valid["parsed_label"])), 4)
        per_prompt.append(row)

    summary = pd.DataFrame(
        [
            {
                "n_examples": int(wide.shape[0]),
                "n_prompts": len(prompt_ids),
                "flip_rate": round(float(wide["wording_changed_decision"].mean()), 4),
                "full_agreement_rate": round(float(wide["all_agree"].mean()), 4),
                "mean_pairwise_agreement": round(float(pairwise["agreement"].mean()), 4) if not pairwise.empty else 1.0,
            }
        ]
    )

    disagreements = wide[wide["wording_changed_decision"]].reset_index()
    return {
        "wide": wide.reset_index(),
        "pairwise": pairwise,
        "per_prompt": pd.DataFrame(per_prompt),
        "summary": summary,
        "disagreements": disagreements,
    }


def write_reports(reports: dict[str, pd.DataFrame], output_dir: str | Path) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    for name, frame in reports.items():
        frame.to_csv(output / f"{name}.csv", index=False)
