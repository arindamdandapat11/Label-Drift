from __future__ import annotations

import io
import csv
from pathlib import Path

import pandas as pd
from flask import Flask, jsonify, render_template, request

from src.analyze import build_reports
from src.classify import LocalClassifier
from src.io_utils import load_config
from src.run_experiment import classify_dataset

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.yaml"
MAX_UPLOAD_BYTES = 50 * 1024 * 1024

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES
classifier_cache: dict[tuple[str, int, float], LocalClassifier] = {}


def read_csv_upload(contents: bytes) -> pd.DataFrame:
    errors = []
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            text = contents.decode(encoding)
            try:
                delimiter = csv.Sniffer().sniff(text[:65536], delimiters=",;\t|").delimiter
            except csv.Error:
                delimiter = ","
            return pd.read_csv(io.StringIO(text), sep=delimiter)
        except (UnicodeDecodeError, pd.errors.ParserError) as error:
            errors.append(error)
    raise ValueError(f"Could not read this CSV. Check its encoding and formatting. ({errors[-1]})")


def json_records(frame: pd.DataFrame) -> list[dict]:
    clean = frame.astype(object).where(pd.notna(frame), None)
    return clean.to_dict(orient="records")


def get_classifier(config: dict) -> LocalClassifier:
    model = config["model"]
    key = (
        model["name"],
        int(model.get("max_new_tokens", 16)),
        float(model.get("temperature", 0.0)),
    )
    if key not in classifier_cache:
        classifier_cache[key] = LocalClassifier(
            model_name=key[0], max_new_tokens=key[1], temperature=key[2]
        )
    return classifier_cache[key]


@app.get("/")
def index():
    config = load_config(CONFIG_PATH)
    return render_template(
        "index.html",
        labels=", ".join(str(label) for label in config["labels"]),
        config_task="classify each text row using the categories provided",
        model_name=config["model"]["name"],
        prompts=config["prompts"],
    )


@app.post("/inspect")
def inspect_csv():
    upload = request.files.get("file")
    if upload is None or not upload.filename:
        return jsonify(error="Choose a CSV file first."), 400
    try:
        frame = read_csv_upload(upload.read())
        if frame.empty or len(frame.columns) == 0:
            return jsonify(error="This CSV has no rows or columns to analyze."), 400
        preview = frame.head(5).astype(object).where(pd.notna(frame.head(5)), None)
        label_column = next(
            (
                column
                for column in frame.columns
                if str(column).strip().lower() in {"gold", "label", "target", "category", "class"}
            ),
            None,
        )
        suggested_labels = []
        if label_column is not None:
            values = frame[label_column].dropna().astype(str).str.strip()
            unique_values = list(dict.fromkeys(value.lower() for value in values if value))
            if 2 <= len(unique_values) <= 20:
                suggested_labels = unique_values
        return jsonify(
            columns=[str(column) for column in frame.columns],
            rows=int(len(frame)),
            preview=preview.to_dict(orient="records"),
            suggested_labels=suggested_labels,
        )
    except (ValueError, pd.errors.EmptyDataError) as error:
        return jsonify(error=str(error)), 400


@app.post("/analyze")
def analyze_csv():
    upload = request.files.get("file")
    if upload is None or not upload.filename:
        return jsonify(error="Choose a CSV file first."), 400
    try:
        frame = read_csv_upload(upload.read())
        text_column = request.form.get("text_column", "")
        gold_column = request.form.get("gold_column", "")
        task_description = request.form.get("task_description", "").strip()
        labels = [label.strip().lower() for label in request.form.get("labels", "").split(",")]
        labels = list(dict.fromkeys(label for label in labels if label))

        if text_column not in frame.columns:
            return jsonify(error="Choose a valid text column."), 400
        if gold_column and gold_column not in frame.columns:
            return jsonify(error="Choose a valid gold-label column."), 400
        if len(labels) < 2:
            return jsonify(error="Enter at least two labels, separated by commas."), 400
        if not task_description:
            return jsonify(error="Describe what the text should be classified as."), 400

        dataset = frame.copy()
        dataset[text_column] = dataset[text_column].fillna("").astype(str).str.strip()
        dataset = dataset[dataset[text_column].ne("")].copy()
        if dataset.empty:
            return jsonify(error="The selected text column has no non-empty rows."), 400
        if gold_column:
            dataset["_gold"] = dataset[gold_column].fillna("").astype(str).str.strip().str.lower()
            dataset.loc[dataset["_gold"].eq(""), "_gold"] = pd.NA
        else:
            dataset["_gold"] = pd.NA

        config = load_config(CONFIG_PATH)
        config["labels"] = labels
        config["data"]["text_column"] = text_column
        config["data"]["task_description"] = task_description
        config["prompts"] = [
            {**prompt, "id": str(prompt.get("id", f"prompt_{index + 1}"))}
            for index, prompt in enumerate(config["prompts"])
        ]
        predictions = classify_dataset(get_classifier(config), dataset, config)
        reports = build_reports(
            predictions,
            labels=labels,
            gold_available=dataset["_gold"].notna().any(),
        )
        return jsonify(
            summary=reports["summary"].iloc[0].to_dict(),
            per_prompt=json_records(reports["per_prompt"]),
            wide=json_records(reports["wide"]),
            disagreements=json_records(reports["disagreements"]),
            predictions=json_records(predictions),
            model=config["model"]["name"],
        )
    except (ValueError, pd.errors.EmptyDataError) as error:
        return jsonify(error=str(error)), 400
    except Exception as error:
        app.logger.exception("CSV analysis failed")
        return jsonify(error=f"Analysis failed: {error}"), 500


@app.errorhandler(413)
def upload_too_large(_error):
    return jsonify(error="This file is over the 50 MB upload limit."), 413


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)