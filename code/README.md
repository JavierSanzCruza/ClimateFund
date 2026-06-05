# ClimateFund: An Annotated Dataset of Climate Mitigation Projects for Supporting Question Answering <a name="description"></a>

## Authors <a name="authors"></a>
- Javier Sanz-Cruzado Puig, University of Glasgow (javier.sanz-cruzadopuig@glasgow.ac.uk)
- Miruna Clinciu, University of Glasgow (miruna-adriana.clinciu@glasgow.ac.uk)
- Richard McCreadie, University of Glasgow (richard.mccreadie@glasgow.ac.uk)
- Craig Macdonald, University of Glasgow (craig.macdonald@glasgow.ac.uk)
- Iadh Ounis, University of Glasgow (iadh.ounis@glasgow.ac.uk)

## Repository contents <a name="file-structure"></a>
The code is organized as follows:


```text
code/
├── climatefund_qa/                         # Python package with the modular QA pipeline
│   ├── __init__.py
│   ├── cli.py                              # Command-line interface: status, prepare, indexes, retrieve, run, table, qualitative
│   ├── config.py                           # Paths, defaults, experiment settings, index locations
│   ├── credentials.py                      # Loads API keys from credentials.env / environment variables
│   ├── data.py                             # Loads PDFs/TXT files, builds document and passage tables, loads QA CSV
│   ├── experiment.py                       # Runs the full grid of retriever/reranker/reader combinations
│   ├── indexes.py                          # Builds and loads BM25 and E5 indexes
│   ├── metrics.py                          # Exact match, token F1, BERTScore, answer-quality flags
│   ├── pipeline.py                         # Thin wrapper functions used by the CLI and notebook
│   ├── qualitative.py                      # Selects and saves example outputs for manual inspection
│   ├── readers.py                          # Extractive fallback, OpenAI-compatible, LLMHOST, and Hugging Face readers
│   ├── rerankers.py                        # No reranker and MonoT5 reranker
│   ├── results_table.py                    # Builds final results tables and LaTeX tables
│   ├── retrieval.py                        # Runs retrieval and attaches passage text/evidence
│   └── utils.py                            # Text cleaning, project ID normalisation, helper functions
│
├── dataset/                                # Input data folder
│   ├── climatefund_qa.csv                  # Question-answer dataset, or another CSV passed by --dataset-filename
│   ├── documents/                          # Preferred location for source PDFs
│   ├── pdfs/                               # Also searched for PDFs
│   ├── PDFs/                               # Also searched for PDFs
│   ├── funding_proposals/                  # Also searched for PDFs
│   ├── proposals/                          # Also searched for PDFs
│   └── text_documents/                     # TXT fallback if no PDFs are found
│
├── notebooks/
│   └── run_modular_notebook_flow.ipynb     # Notebook version of the same pipeline that was used to run via Google Colab
│
├── scripts/
│   ├── run_smoke_test.sh                   # Linux/macOS smoke-test commands
│   └── run_smoke_test.bat                  # Windows smoke-test commands
│
├── README.md
├── requirements.txt
└── credentials.env.example
```



Generated folders are created after running the pipeline:

```text
code/
├── rag_experiment_artifacts/
│   ├── texts/                              # Extracted document text
│   ├── tables/                             # Prepared tables and final result tables
│   └── runs/                               # Timestamped experiment runs
└── indexes/
    ├── dest.bm25                           # Global BM25 index
    ├── dest.e5.flex                        # Global E5 index
    └── by_project/                         # Per-project indexes
```

---

## Pipeline overview

The pipeline has seven stages:

1. **Check setup**: verify paths, dataset location, output folders, and credentials.
2. **Prepare data**: read the QA CSV and convert project documents into passages.
3. **Build indexes**: create BM25 and/or E5 indexes for retrieval.
4. **Test retrieval**: retrieve passages for one question before running a full experiment.
5. **Run experiments**: evaluate combinations of retrievers, rerankers, and readers.
6. **Create tables**: aggregate metrics into report-ready CSV and LaTeX tables.
7. **Inspect examples**: export qualitative examples for manual analysis.

```text
QA CSV + project documents
        ↓
prepare document and passage tables
        ↓
build BM25/E5 indexes
        ↓
retrieve evidence passages
        ↓
optional reranking
        ↓
reader generates answer
        ↓
metrics, result tables, and qualitative examples
```

---

## Installation

Run the following commands from the `code/` directory, i.e. the folder that contains `climatefund_qa/`.

```bash
python -m venv .venv
```

Activate the environment.

Linux/macOS:

```bash
source .venv/bin/activate
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Check that the CLI works:

```bash
python -m climatefund_qa.cli --project-root . status
```

---

## Dataset setup

By default, the QA file should be placed here:

```text
dataset/climatefund_qa.csv
```

The recommended CSV columns are:

| Column | Description |
|---|---|
| `qid` | Unique question ID. If missing, IDs are generated automatically. |
| `question` | Question to answer. |
| `answer` | Gold/reference answer used for evaluation. |
| `scope` | Retrieval scope, usually `cross_projects` or `single_project`. |
| `source_projects` | Project IDs for single-project retrieval. |

The code is flexible about answer column names and also checks common alternatives such as `gold_answer` and `reference_answer`.

Project documents should be placed in one of these folders:

```text
dataset/documents/
dataset/pdfs/
dataset/PDFs/
dataset/funding_proposals/
dataset/proposals/
```

If PDFs are not available, TXT files can be placed in:

```text
dataset/text_documents/
```

To use a different QA file inside `dataset/`, pass `--dataset-filename`:

```bash
python -m climatefund_qa.cli --project-root . --dataset-filename climatefund_qa_v2.csv prepare
```

---

## Credentials

No API keys are needed for the offline smoke test if you use:

```text
--readers extractive_fallback
--rerankers none
```

Model-based readers require credentials. Create a local credentials file:

```bash
cp credentials.env.example credentials.env
```

Then add the keys you need:

```text
OPENAI_API_KEY=...
LLM_API_KEY=...
HF_TOKEN=...
```

Do not commit `credentials.env` to GitHub.

---

## Quick start

Use this sequence for the first successful run:

```bash
python -m climatefund_qa.cli --project-root . status
python -m climatefund_qa.cli --project-root . prepare
python -m climatefund_qa.cli --project-root . indexes --retrievers bm25 --rebuild
python -m climatefund_qa.cli --project-root . retrieve --question "What is the project objective?" --retriever bm25 --reranker none
python -m climatefund_qa.cli --project-root . run --retrievers bm25 --rerankers none --readers extractive_fallback --max-questions 3 --no-bertscore
python -m climatefund_qa.cli --project-root . table
python -m climatefund_qa.cli --project-root . qualitative --top-k 5
```

This uses BM25 retrieval, no reranking, the offline fallback reader, only three questions, and no BERTScore. It is the fastest way to confirm that the full pipeline works.

---

## Step-by-step run guide

### 1. Check paths and credentials

```bash
python -m climatefund_qa.cli --project-root . status
```

This prints the resolved project, dataset, index, and artifact paths. Run this first if the code cannot find the dataset or documents.

---

### 2. Prepare the dataset and passages

```bash
python -m climatefund_qa.cli --project-root . prepare
```

This command:

- loads the QA CSV;
- extracts text from PDFs or TXT files;
- creates document and passage tables.

Main outputs:

```text
rag_experiment_artifacts/texts/*.txt
rag_experiment_artifacts/tables/documents.csv
rag_experiment_artifacts/tables/passages.csv
```

---

### 3. Build retrieval indexes

Build BM25 only:

```bash
python -m climatefund_qa.cli --project-root . indexes --retrievers bm25 --rebuild
```

Build E5 only:

```bash
python -m climatefund_qa.cli --project-root . indexes --retrievers e5 --rebuild
```

Build both:

```bash
python -m climatefund_qa.cli --project-root . indexes --retrievers bm25 e5 --rebuild
```

Use `--rebuild` when you want to recreate indexes from scratch. Without it, existing indexes are reused when possible.

---

### 4. Test retrieval for one question

```bash
python -m climatefund_qa.cli --project-root . retrieve \
  --question "What is the project objective?" \
  --retriever bm25 \
  --reranker none
```

Try E5 retrieval:

```bash
python -m climatefund_qa.cli --project-root . retrieve \
  --question "What is the project objective?" \
  --retriever e5 \
  --reranker none
```

Try MonoT5 reranking:

```bash
python -m climatefund_qa.cli --project-root . retrieve \
  --question "What is the project objective?" \
  --retriever bm25 \
  --reranker t5
```

For single-project retrieval, add project IDs:

```bash
python -m climatefund_qa.cli --project-root . retrieve \
  --question "What is the project objective?" \
  --retriever bm25 \
  --reranker none \
  --scope single_project \
  --source-projects project_001 project_002
```

Use retrieval testing before a large run to check that the returned passages are relevant.

---

### 5. Run an experiment

Small smoke test:

```bash
python -m climatefund_qa.cli --project-root . run \
  --retrievers bm25 \
  --rerankers none \
  --readers extractive_fallback \
  --max-questions 3 \
  --no-bertscore
```

Larger offline run:

```bash
python -m climatefund_qa.cli --project-root . run \
  --retrievers bm25 e5 \
  --rerankers none t5 \
  --readers extractive_fallback \
  --no-bertscore
```

Run with an OpenAI reader:

```bash
python -m climatefund_qa.cli --project-root . run \
  --retrievers bm25 \
  --rerankers none \
  --readers openai_gpt_4o_mini \
  --max-questions 10
```

Run with an LLMHOST-hosted reader:

```bash
python -m climatefund_qa.cli --project-root . run \
  --retrievers bm25 \
  --rerankers none \
  --readers LLMHOST_qwen_2_5_72b \
  --max-questions 10
```

Each run creates a timestamped folder under:

```text
rag_experiment_artifacts/runs/
```

---

### 6. Build the result table

```bash
python -m climatefund_qa.cli --project-root . table
```

This reads the latest run and writes summary tables to:

```text
rag_experiment_artifacts/tables/
```

Typical outputs:

```text
main_results_table.csv
main_results_table.tex
```

---

### 7. Export qualitative examples

```bash
python -m climatefund_qa.cli --project-root . qualitative --top-k 5
```

This saves examples containing the question, gold answer, predicted answer, metrics, and retrieved passages. Use these files to manually inspect where the pipeline succeeds or fails.

---

## Command options

Global options can be used before any subcommand:

| Option | Default | Description |
|---|---|---|
| `--project-root` | auto-detected | Folder containing `dataset/`, `indexes/`, and `rag_experiment_artifacts/`. Use `.` from the `code/` folder. |
| `--dataset-filename` | `climatefund_qa.csv` | QA CSV file inside `dataset/`. |
| `--credentials` | `credentials.env` if present | Optional path to a credentials file. |

Common experiment options:

| Option | Description |
|---|---|
| `--retrievers bm25 e5` | Select one or more first-stage retrievers. |
| `--rerankers none t5` | Select one or more rerankers. |
| `--readers extractive_fallback ...` | Select one or more answer generators. |
| `--max-questions N` | Limit the run to the first `N` questions. Useful for testing. |
| `--rebuild-indexes` | Rebuild indexes before running an experiment. |
| `--no-bertscore` | Skip BERTScore for faster runs. |

---

## Supported components

### Retrievers

| ID | Description | Best use |
|---|---|---|
| `bm25` | Lexical retrieval over passage text. | Fast smoke tests and strong baseline. |
| `e5` | Dense retrieval using E5-style embeddings. | Semantic retrieval experiments. |

### Rerankers

| ID | Description |
|---|---|
| `none` | Keep the first-stage retrieval order. |
| `t5` | MonoT5 reranking. Aliases: `monot5`, `mono_t5`. |

### Readers

| ID | Credential | Description |
|---|---|---|
| `extractive_fallback` | None | Offline fallback reader that returns an evidence snippet. |
| `openai_gpt_4o_mini` | `OPENAI_API_KEY` | OpenAI-compatible reader using GPT-4o mini. |
| `openai_gpt_4_1_mini` | `OPENAI_API_KEY` | OpenAI-compatible reader using GPT-4.1 mini. |
| `gpt-5.4-mini-2026-03-17` | `OPENAI_API_KEY` | OpenAI-compatible reader using the configured model name. |
| `LLMHOST_qwen_2_5_72b` | `LLMHOST_LLM_API_KEY` | LLMHOST-hosted Qwen 2.5 72B reader. |
| `LLMHOST_qwen_2_5_7b` | `LLMHOST_LLM_API_KEY` | LLMHOST-hosted Qwen 2.5 7B reader. |
| `llama-3.3-70b-instruct` | `LLMHOST_LLM_API_KEY` | LLMHOST-hosted Llama 3.3 70B reader. |
| `hf_mistral_7b_instruct_v03` | `HF_TOKEN` | Hugging Face Mistral 7B Instruct reader. |

---

## Outputs

Each experiment creates a folder like:

```text
rag_experiment_artifacts/runs/run_YYYYMMDD_HHMMSS/
```

For each configuration, for example `bm25__none__extractive_fallback`, the pipeline writes:

```text
bm25__none__extractive_fallback__predictions.csv
bm25__none__extractive_fallback__run_details.csv
bm25__none__extractive_fallback__metrics.csv
bm25__none__extractive_fallback__failed.csv
```

The run folder also contains combined checkpoint and final files:

```text
predictions_final.csv
run_details_final.csv
metrics_final.csv
failed_final.csv
```

| File type | Contains |
|---|---|
| `predictions*.csv` | Questions, gold answers, predicted answers, and run configuration. |
| `run_details*.csv` | Retrieved passages, ranks, scores, projects, and evidence text. |
| `metrics*.csv` | Exact match, token F1, BERTScore if enabled, and answer-quality flags. |
| `failed*.csv` | Failed questions/configurations and error messages. |
| `main_results_table.*` | Aggregated result tables created by `table`. |
| `qualitative_examples/` | Human-readable examples created by `qualitative`. |

---

## Notebook option

The notebook version is available at:

```text
notebooks/run_modular_notebook_flow.ipynb
```

It follows the same order as the CLI:

1. create the config;
2. check status;
3. prepare tables;
4. build/load indexes;
5. test retrieval;
6. run experiments;
7. create result tables and qualitative examples.

If running in Google Colab, add API keys using Colab Secrets before using model-based readers.

---

## Troubleshooting

### `QA dataset not found`

Check that the file exists at:

```text
dataset/climatefund_qa.csv
```

or pass a different filename:

```bash
python -m climatefund_qa.cli --project-root . --dataset-filename your_file.csv prepare
```

### `No PDF/TXT source documents found`

Place documents in one of the supported folders, then rerun `prepare`:

```bash
python -m climatefund_qa.cli --project-root . prepare
```

### The CLI is using the wrong folder

Run:

```bash
python -m climatefund_qa.cli --project-root . status
```

Use `--project-root .` when running from the GitHub `code/` directory.

### A model reader fails because of missing credentials

First verify the offline flow:

```bash
python -m climatefund_qa.cli --project-root . run \
  --retrievers bm25 \
  --rerankers none \
  --readers extractive_fallback \
  --max-questions 3 \
  --no-bertscore
```

Then add the required key to `credentials.env`.

### MonoT5 or BERTScore is slow

Disable them while testing:

```bash
python -m climatefund_qa.cli --project-root . run \
  --retrievers bm25 \
  --rerankers none \
  --readers extractive_fallback \
  --no-bertscore
```

### Start from scratch

Linux/macOS:

```bash
rm -rf rag_experiment_artifacts indexes
```

Windows PowerShell:

```powershell
Remove-Item -Recurse -Force rag_experiment_artifacts, indexes
```

Then rerun `prepare` and `indexes`.

---
## Current benchmark

## Single-project questions

| Retriever | Reranker | Reader | F1 | BERTScore | 
|-----------|----------|--------|----|-----------|
| BM25 | None | Mistral 7B Instruct v0.3 | 0.243 | 0.232 |
| BM25 | MonoT5 | Mistral 7B Instruct v0.3 | 0.279 | 0.265 |
| E5 | None | Mistral 7B Instruct v0.3 | 0.243 | 0.227 |
| E5 | MonoT5 | Mistral 7B Instruct v0.3 | 0.268 | 0.256 |
| BM25 | None | Llama 3.3 70B Instruct | 0.166 | 0.280 |
| BM25 | MonoT5 | Llama 3.3 70B Instruct | 0.198 | 0.296 |
| E5 | None | Llama 3.3 70B Instruct | 0.164 | 0.276 |
| E5 | MonoT5 | Llama 3.3 70B Instruct | 0.192 | 0.283 |
| BM25 | None | OpenAI GPT-5.4 mini | 0.197 | 0.319 |
| BM25 | MonoT5 | OpenAI GPT-5.4 mini | 0.237 | 0.350 |
| E5 | None | OpenAI GPT-5.4 mini | 0.194 | 0.316 |
| E5 | MonoT5 | OpenAI GPT-5.4 mini | 0.210 | 0.328 |

## Cross-project questions

| Retriever | Reranker | Reader | F1 | BERTScore | 
|-----------|----------|--------|----|-----------|
| BM25 | None | Mistral 7B Instruct v0.3 | 0.111 | 0.084 |
| BM25 | MonoT5 | Mistral 7B Instruct v0.3 | 0.111 | 0.084 |
| E5 | None | Mistral 7B Instruct v0.3 | 0.105 | 0.079 |
| E5 | MonoT5 | Mistral 7B Instruct v0.3 | 0.107 | 0.083 |
| BM25 | None | Llama 3.3 70B Instruct | 0.129 | 0.217 |
| BM25 | MonoT5 | Llama 3.3 70B Instruct | 0.150 | 0.224 |
| E5 | None | Llama 3.3 70B Instruct | 0.151 | 0.220 |
| E5 | MonoT5 | Llama 3.3 70B Instruct | 0.163 | 0.215 |
| BM25 | None | OpenAI GPT-5.4 mini | 0.147 | 0.252 |
| BM25 | MonoT5 | OpenAI GPT-5.4 mini | 0.174 | 0.265 |
| E5 | None | OpenAI GPT-5.4 mini | 0.158 | 0.256 |
| E5 | MonoT5 | OpenAI GPT-5.4 mini | 0.187 | 0.266 |

