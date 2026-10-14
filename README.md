```text
 ____  ____   ___  __  __ ____ _____   __        _____  ____  ____ ___ _   _  ____
|  _ \|  _ \ / _ \|  \/  |  _ \_   _|  \ \      / / _ \|  _ \|  _ \_ _| \ | |/ ___|
| |_) | |_) | | | | |\/| | |_) || |     \ \ /\ / / | | | |_) | | | | ||  \| | |  _
|  __/|  _ <| |_| | |  | |  __/ | |      \ V  V /| |_| |  _ <| |_| | || |\  | |_| |
|_|   |_| \_\\___/|_|  |_|_|    |_|       \_/\_/  \___/|_| \_\____/___|_| \_|\____|

            >>>  S T U D Y   //   W I T H O U T   A   S I N G L E   A P I   K E Y  <<<
```

> 🛰️ **`SYSTEM QUERY`** Does changing *only the wording* change the predicted label?

Same classification objective. Six differently worded prompts. One local open-source Hugging Face model. Zero paid APIs. Greedy decoding, so any flip you see comes from the words alone, not from sampling noise. 🧪

**🤖 Default model:** [`google/flan-t5-base`](https://huggingface.co/google/flan-t5-base)

---

## `01` 🎯 Mission Parameters

| Parameter | Value |
| --- | --- |
| 🎯 Objective | Measure how prompt phrasing alone shifts model decisions |
| ✍️ Prompts under test | 6 phrasings of one identical task |
| 💻 Inference | Fully local, runs on your machine |
| 🧊 Decoding | Greedy (`temperature: 0.0`) |
| 💸 Cost | $0 |

---

## `//` ⚡ Powered By

<p align="center">
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/Hugging%20Face-FFD21E?style=for-the-badge&logo=huggingface&logoColor=black" alt="Hugging Face" />
  <img src="https://img.shields.io/badge/Transformers-FF6F00?style=for-the-badge&logo=huggingface&logoColor=white" alt="Transformers" />
  <img src="https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white" alt="Flask" />
  <img src="https://img.shields.io/badge/PowerShell-5391FE?style=for-the-badge&logo=powershell&logoColor=white" alt="PowerShell" />
  <img src="https://img.shields.io/badge/YAML-CB171E?style=for-the-badge&logo=yaml&logoColor=white" alt="YAML" />
</p>

---

## `//` 🗂️ Project Structure

```text
prompt-wording-study/
├── config.yaml              # model, data, labels, and prompt templates
├── requirements.txt         # Python dependencies
├── data/
│   ├── sample.csv           # tiny sentiment sample for a first run
│   └── dataset.csv          # your own CSV (id, text, label)
├── src/
│   ├── run_experiment.py    # CLI: runs every prompt over every row
│   └── app.py               # local CSV workbench (Flask)
└── results/                 # generated outputs
    ├── summary.csv          # flip rate
    ├── wide.csv             # one column per prompt
    ├── disagreements.csv    # examples where wording changed the label
    ├── pairwise.csv         # agreement + Cohen's kappa
    ├── per_prompt.csv       # unknown rate, accuracy if gold labels exist
    └── predictions.csv      # raw model text + parsed label
```

---

## `02` 🚀 Boot Sequence

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

> 📥 **Note:** The first run downloads the model from Hugging Face into your local cache.

---

## `03` 📂 Load Your Dataset

Feed the system a CSV with a text column:

```csv
id,text,label
1,example sentence,positive
```

Then point `config.yaml` at it. Set the task description, text column, optional gold-label column, and categories:

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

Change `labels` and `task_description` to match your mission: spam/ham, topics, emotion, and so on. Prompt templates use `{task}`, `{labels}`, and `{text}`.

A tiny sentiment sample lives in `data/sample.csv`, so you can run the full pipeline before your own file is ready. ✅

---

## `04` ▶️ Execute

```powershell
python -m src.run_experiment --config config.yaml --output results
```

---

## `05` 🖥️ Launch the Interface

Spin up the local CSV workbench:

```powershell
python -m src.app
```

Open **[http://127.0.0.1:5000](http://127.0.0.1:5000)** and:

1. 📤 Drop in any text-bearing CSV
2. 🔤 Choose the text column
3. 📝 Describe the classification task and set its categories
4. 🏷️ *(Optional)* Select a gold-label column to also get per-prompt accuracy

The workbench compares every row across the prompts in `config.yaml` and delivers predictions, label shifts, per-prompt metrics, and CSV exports.

- ⏳ The first run downloads and loads the model into memory. Later runs reuse it.
- 🔒 Everything is processed locally. Uploaded files are limited to **50 MB**.

---

## `06` 📡 Telemetry Output

| File | Signal |
| --- | --- |
| 📊 `results/summary.csv` | **Flip rate**: share of examples where prompts did not all pick the same label |
| 📋 `results/wide.csv` | One row per example, one column per prompt |
| ⚠️ `results/disagreements.csv` | Only the examples where wording changed the decision |
| 🤝 `results/pairwise.csv` | Agreement and Cohen's kappa between every prompt pair |
| 📈 `results/per_prompt.csv` | Unknown-output rate, and accuracy if gold labels exist |
| 💬 `results/predictions.csv` | Raw model text plus parsed label |

### 🔍 Reading the signal

```text
flip_rate == 0   ->  wording had no effect on any decision
flip_rate  > 0   ->  wording changed at least some decisions,
                     even though the task and labels were identical
```

---

## `07` 🛠️ Configuration Notes

- 🧊 **Deterministic by design.** Decoding is greedy (`temperature: 0.0`), so sampling noise is not the cause of flips.
- 🔄 **Swap the engine.** Change `model.name` to any other local Transformers checkpoint, for example `google/flan-t5-small` or `Qwen/Qwen2.5-0.5B-Instruct`.
- ➕ **Expand the experiment.** Edit or add entries under `prompts:` in `config.yaml` to test more phrasings.

---

```text
[ END OF TRANSMISSION ] 🛸
```
