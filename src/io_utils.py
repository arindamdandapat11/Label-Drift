from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml


def load_config(path: str | Path) -> dict:
    with Path(path).open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def format_labels(labels: list[str]) -> str:
    if len(labels) == 1:
        return labels[0]
    if len(labels) == 2:
        return f"{labels[0]} or {labels[1]}"
    return ", ".join(labels[:-1]) + f", or {labels[-1]}"


def render_prompt(
    template: str,
    text: str,
    labels: list[str],
    task: str = "text classification",
) -> str:
    return template.format(text=text, labels=format_labels(labels), task=task).strip()


def load_dataset(config: dict) -> pd.DataFrame:
    data_cfg = config["data"]
    path = Path(data_cfg["path"])
    if not path.exists():
        raise FileNotFoundError(
            f"Dataset not found: {path}. Put your CSV there or update data.path in config.yaml."
        )

    frame = pd.read_csv(path)
    text_col = data_cfg["text_column"]
    if text_col not in frame.columns:
        raise ValueError(f"Column {text_col!r} missing. Found: {list(frame.columns)}")

    frame = frame.copy()
    frame[text_col] = frame[text_col].astype(str)
    gold_col = data_cfg.get("gold_column")
    if gold_col in (None, "null", ""):
        frame["_gold"] = pd.NA
    elif gold_col not in frame.columns:
        raise ValueError(f"Gold column {gold_col!r} missing. Found: {list(frame.columns)}")
    else:
        frame["_gold"] = frame[gold_col].astype(str).str.strip().str.lower()
    return frame
