from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
from tqdm import tqdm

from src.analyze import build_reports, write_reports
from src.classify import LocalClassifier, parse_label
from src.io_utils import load_config, load_dataset, render_prompt


def make_classifier(config: dict) -> LocalClassifier:
    model_cfg = config["model"]
    return LocalClassifier(
        model_name=model_cfg["name"],
        max_new_tokens=int(model_cfg.get("max_new_tokens", 16)),
        temperature=float(model_cfg.get("temperature", 0.0)),
    )


def classify_text(classifier: LocalClassifier, text: str, config: dict) -> list[dict]:
    labels = [str(item).lower() for item in config["labels"]]
    results = []
    for prompt in config["prompts"]:
        filled = render_prompt(
            prompt["template"],
            text=text,
            labels=labels,
            task=config.get("data", {}).get("task_description", "text classification"),
        )
        raw = classifier.generate(filled)
        parsed = parse_label(raw, labels)
        results.append(
            {
                "prompt_id": prompt["id"],
                "prompt_description": prompt.get("description", ""),
                "prompt": filled,
                "raw_output": raw,
                "parsed_label": parsed,
            }
        )
    return results


def classify_dataset(classifier: LocalClassifier, dataset: pd.DataFrame, config: dict) -> pd.DataFrame:
    labels = [str(item).lower() for item in config["labels"]]
    text_col = config["data"]["text_column"]
    rows = []
    example_id_col = "id" if "id" in dataset.columns else None
    for row_index, row in tqdm(dataset.iterrows(), total=len(dataset), desc="examples"):
        example_id = row[example_id_col] if example_id_col else row_index
        text = row[text_col]
        gold = row["_gold"]
        for result in classify_text(classifier, text, config):
            rows.append(
                {
                    "example_id": example_id,
                    "text": text,
                    "gold": gold if pd.notna(gold) else pd.NA,
                    "prompt_id": result["prompt_id"],
                    "prompt_description": result["prompt_description"],
                    "raw_output": result["raw_output"],
                    "parsed_label": result["parsed_label"],
                }
            )
    return pd.DataFrame(rows)


def run(config_path: str, output_dir: str) -> None:
    config = load_config(config_path)
    labels = [str(item).lower() for item in config["labels"]]
    dataset = load_dataset(config)
    gold_available = dataset["_gold"].notna().any()
    classifier = make_classifier(config)
    predictions = classify_dataset(classifier, dataset, config)
    reports = build_reports(predictions, labels=labels, gold_available=gold_available)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(out / "predictions.csv", index=False)
    write_reports(reports, out)

    summary = reports["summary"].iloc[0]
    print(f"Model: {config['model']['name']}")
    print(f"Examples: {summary['n_examples']}  Prompts: {summary['n_prompts']}")
    print(f"Wording changed the decision on {summary['flip_rate']:.1%} of examples")
    print(f"All prompts agreed on {summary['full_agreement_rate']:.1%} of examples")
    print(f"Mean pairwise agreement: {summary['mean_pairwise_agreement']:.1%}")
    print(f"Wrote reports to {out.resolve()}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the same classification task with differently worded prompts."
    )
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--output", default="results")
    args = parser.parse_args()
    run(args.config, args.output)


if __name__ == "__main__":
    main()
