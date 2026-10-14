# Prompt wording study

Same classification objective, six differently worded prompts, one local open-source Hugging Face model. The question: **does changing only the wording change the predicted label?**

No paid APIs. Default model: [`google/flan-t5-base`](https://huggingface.co/google/flan-t5-base).

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

The first run downloads the model from Hugging Face into the local cache.

## Your dataset

The CLI accepts a CSV with a text column. Set the task description, text column, optional gold-label column, and categories in `config.yaml`:

```csv
id,text,label
1,example sentence,positive
```

Then point `config.yaml` at it:

```yaml
data:
  path: data/dataset.csv
  text_column: text
  gold_column: label   # or null if you have no gold labels
  task_description: sentiment of a product review
labels:
  - positive
  - negative
  - neutral
```

Change `labels` and `task_description` to match your task (spam/ham, topics, emotion, and so on). Prompt templates use `{task}`, `{labels}`, and `{text}`.

A tiny sentiment sample lives in `data/sample.csv` so you can run the pipeline before your file is ready.

## Run

```powershell
python -m src.run_experiment --config config.yaml --output results
```

## Interface

Launch the local CSV workbench:

```powershell
python -m src.app
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000), drop in any text-bearing CSV, choose the text column, describe the classification task, and set its categories. A gold-label column is optional; selecting one also reports per-prompt accuracy. The workbench compares every row across the prompts in `config.yaml` and provides predictions, label shifts, per-prompt metrics, and CSV exports. The first run downloads and loads the model into memory; later runs reuse it. Uploaded files are processed locally and are limited to 50 MB.

## What to look at

| File | Meaning |
| --- | --- |
| `results/summary.csv` | Flip rate: share of examples where prompts did not all pick the same label |
| `results/wide.csv` | One row per example, one column per prompt |
| `results/disagreements.csv` | Only the examples where wording changed the decision |
| `results/pairwise.csv` | Agreement and Cohen's kappa between every prompt pair |
| `results/per_prompt.csv` | Unknown-output rate, and accuracy if gold labels exist |
| `results/predictions.csv` | Raw model text plus parsed label |

If `flip_rate` is above 0, wording changed at least some decisions even though the task and labels were identical.

## Notes

- Decoding is greedy (`temperature: 0.0`) so sampling noise is not the cause of flips.
- Swap `model.name` for any other local Transformers checkpoint, for example `google/flan-t5-small` or `Qwen/Qwen2.5-0.5B-Instruct`.
- Edit or add entries under `prompts:` in `config.yaml` to test more phrasings.
