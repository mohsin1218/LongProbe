# CLI Reference

LongProbe provides a rich, user-friendly Command Line Interface built with **Typer** and styled with **Rich**. It offers colored tables, progress spinner overlays, regression logs, and interactive UI utilities.

---

## Command Overview

| Command | Description |
|---------|-------------|
| [`longprobe init`](#longprobe-init) | Initialize starting configuration files. |
| [`longprobe check`](#longprobe-check) | Run retrieval quality tests against your Golden Set. |
| [`longprobe diff`](#longprobe-diff) | Compare current performance against a saved baseline. |
| [`longprobe explain`](#longprobe-explain) | *New:* Diagnose and troubleshoot a retrieval regression. |
| [`longprobe edit`](#longprobe-edit) | *New:* Open the interactive Terminal UI to edit your Golden Set. |
| [`longprobe baseline save`](#longprobe-baseline-save) | Save current run as a baseline snapshot. |
| [`longprobe baseline list`](#longprobe-baseline-list) | List all saved baselines. |
| [`longprobe baseline delete`](#longprobe-baseline-delete) | Delete a saved baseline snapshot. |
| [`longprobe watch`](#longprobe-watch) | Re-run tests automatically on changes. |
| [`longprobe capture`](#longprobe-capture) | Build golden questions interactively by querying your retriever. |
| [`longprobe generate`](#longprobe-generate) | Auto-generate golden questions from local documents using an LLM. |

---

## Core Commands

### `longprobe init`
Initialize starter files in the current working directory.

```bash
longprobe init
```

**Creates:**
* `longprobe.yaml` - Base retriever and scorer configuration.
* `goldens.yaml` - Pre-filled sample golden question set.
* `.longprobe/` - Database directory to store baselines.

---

### `longprobe check`
Query your retriever with all golden questions, evaluate matches, and print results.

```bash
longprobe check [OPTIONS]
```

**Options:**
* `-g, --goldens PATH`: Path to your golden questions YAML. (Default: `goldens.yaml`)
* `-c, --config PATH`: Path to your config file. (Default: `longprobe.yaml`)
* `-k, --top-k INTEGER`: Override the default `top_k` retrieved chunks.
* `-t, --threshold FLOAT`: Override the default recall threshold globally.
* `--tag TEXT`: Only run questions with this tag (can be passed multiple times).
* `-o, --output TEXT`: Output format. Options: `table`, `json`, `github`. (Default: `table`)

---

### `longprobe diff`
Run checks and show an exact comparison/difference against a saved baseline.

```bash
longprobe diff [OPTIONS]
```

**Options:**
* `-b, --baseline TEXT`: Label of the baseline to compare against. (Default: `latest`)
* `-g, --goldens PATH`: Path to your golden questions YAML. (Default: `goldens.yaml`)
* `-c, --config PATH`: Path to your config file. (Default: `longprobe.yaml`)
* `--tag TEXT`: Only run questions with this tag.

---

## 🛠️ Diagnostic & TUI Tools

### `longprobe explain`
Diagnose why a specific golden question failed or degraded. It runs an **extended top-k search** (searching deeper into the index) to track down missing chunks, detects "interlopers" that pushed correct answers out of rank, and provides a clear recommendation.

```bash
longprobe explain QUESTION_ID [OPTIONS]
```

**Arguments:**
* `QUESTION_ID`: The ID of the golden question to troubleshoot (e.g. `q1`).

**Options:**
* `-b, --baseline TEXT`: The baseline label to trace rank shifts against. (Default: `latest`)
* `--extended-top-k INTEGER`: How deep to search to find where missing chunks went. (Default: `20`)
* `-g, --goldens PATH`: Path to golden questions YAML.
* `-c, --config PATH`: Path to config YAML.

**Example Output:**
```
🔍 Explain: q1
   Question: "What is the refund policy?"
   Status: ⚠️ REGRESSION (Recall: 50%)

   Missing Chunks:
     • "30-day money-back guarantee" (was in baseline) — found at rank 8

   Current Top-5 Results (Interlopers?):
     [1] score=0.902 | Unrelated return shipping guidelines
     [2] score=0.880 | Promo policy details

   💡 Recommendation:
      Some missing chunks were found further down the ranking. Consider increasing top_k or improving the embedding index.
```

---

### `longprobe edit`
Launch the terminal-native **Textual TUI** to manage and edit your Golden Question set without leaving the terminal.

```bash
longprobe edit [OPTIONS]
```

**Options:**
* `-g, --goldens PATH`: Path to golden questions YAML to edit. (Default: `goldens.yaml`)

**TUI Hotkeys:**
* `Ctrl + S`: Save changes to `goldens.yaml`
* `Ctrl + N`: Create a new golden question
* `Ctrl + D`: Delete the selected golden question
* `q`: Quit the editor

---

## Baseline Management

### `longprobe baseline save`
Run checks and save the report as a named baseline.

```bash
longprobe baseline save [OPTIONS]
```

**Options:**
* `-l, --label TEXT`: Name for the baseline. (Default: `latest`)
* `-g, --goldens PATH`: Path to your golden questions.
* `-c, --config PATH`: Path to your config.

---

### `longprobe baseline list`
Display a table of all saved baselines stored in your local database.

```bash
longprobe baseline list [OPTIONS]
```

**Options:**
* `--db-path PATH`: Custom path to the SQLite baseline database.

---

### `longprobe baseline delete`
Remove a saved baseline snapshot.

```bash
longprobe baseline delete --label LABEL [OPTIONS]
```

**Options:**
* `-l, --label TEXT`: Label of the baseline to delete. *(Required)*
* `--db-path PATH`: Custom path to the SQLite baseline database.

---

## Utility Commands

### `longprobe watch`
Continuously watch the golden-set file and automatically re-run checks whenever a change is saved.

```bash
longprobe watch [OPTIONS]
```

**Options:**
* `-i, --interval FLOAT`: Polling interval in seconds. (Default: `2.0`)
* `-g, --goldens PATH`: Path to golden questions YAML.
* `-c, --config PATH`: Path to config YAML.

---

### `longprobe capture`
Build a golden question set interactively by querying your active retriever and selecting which retrieved chunks are correct answers.

```bash
longprobe capture [OPTIONS]
```

**Options:**
* `-q, --question TEXT`: Specific question to capture (can pass multiple times).
* `-Q, --questions-file PATH`: Text file containing one question per line.
* `-k, --top-k INTEGER`: Top-k chunks to retrieve per question. (Default: `5`)
* `-m, --match-mode TEXT`: Match mode to apply to the question. (Default: `"text"`)
* `--auto`: Trust the retriever and automatically save all results without prompting.

---

### `longprobe generate`
Generate high-quality golden questions automatically from local document collections using an LLM.

```bash
longprobe generate PATH [OPTIONS]
```

**Arguments:**
* `PATH`: File or folder containing documents to process.

**Options:**
* `-n, --num-questions INTEGER`: Number of questions to generate (Default: config file setting)
* `-o, --output PATH`: Path to write the questions YAML (prints to console if not set)
* `--provider TEXT`: LLM provider to override config (e.g. `openai`, `anthropic`, `gemini`, `ollama`)
* `--model TEXT`: LLM model to override config (e.g. `gpt-4o-mini`, `claude-3-haiku-20240307`)
* `--auto-capture`: Instantly query the retriever with generated questions to build a live golden set.
* `-g, --goldens PATH`: Golden questions YAML output path if using `--auto-capture`.
* `-m, --match-mode TEXT`: Match mode for auto-captured questions (`id`, `text`, or `semantic`).

