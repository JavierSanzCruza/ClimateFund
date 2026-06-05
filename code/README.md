# ClimateFund: An Annotated Dataset of Climate Mitigation Projects for Supporting Question Answering <a name="description"></a>

## Authors <a name="authors"></a>
- Javier Sanz-Cruzado Puig, University of Glasgow (javier.sanz-cruzadopuig@glasgow.ac.uk)
- Miruna Clinciu, University of Glasgow (miruna-adriana.clinciu@glasgow.ac.uk)
- Richard McCreadie, University of Glasgow (richard.mccreadie@glasgow.ac.uk)
- Craig Macdonald, University of Glasgow (craig.macdonald@glasgow.ac.uk)
- Iadh Ounis, University of Glasgow (iadh.ounis@glasgow.ac.uk)

## Repository contents <a name="file-structure"></a>
The code is organized as follows:

- **documents/:** Collection of the Green Climate Fund (GCF) funding proposals annotated in the dataset.
  - **documents/FPXXX.pdf:** Each of the documents, defined by its GCF project identifier (FP+Number).
- **climatefund.json:** JSON file containing the annotations of projects. Format is described below in ...
- **climatefund_qa.csv:** CSV file containing 500 question-answer pairs (ClimateFund-QA). Format is described below in ...
- **LICENSE:** A copy of the MPL-2.0 License.

## Running the experiments


### Install

```bash
pip install -r requirements.txt
```

For a quick smoke test without API keys, use `extractive_fallback` as the reader.

### Command-line flow

```bash
python -m climatefund_qa.cli status
python -m climatefund_qa.cli prepare
python -m climatefund_qa.cli indexes --retrievers bm25 --rebuild
python -m climatefund_qa.cli retrieve --question "What is the project objective?" --retriever bm25 --reranker none
python -m climatefund_qa.cli run --retrievers bm25 --rerankers none --readers extractive_fallback --max-questions 3 --no-bertscore
python -m climatefund_qa.cli table
python -m climatefund_qa.cli qualitative --top-k 5
```

For Windows, if you are not inside `UOG/code`, pass the root explicitly:

```bat
python -m climatefund_qa.cli --project-root C:\Users\mirun\Desktop\your_folder status
```

### Jupyter usage

Open `notebooks/run_modular_notebook_flow.ipynb`.

The notebook calls the same functions used by the command line:

- `step_prepare_tables`
- `step_build_indexes`
- `step_load_indexes`
- `step_retrieve`
- `step_read_answer`
- `step_run_experiment`

## Credentials

Copy `credentials.env.example` to `credentials.env` and add keys there. The code loads it automatically.

Do not commit `credentials.env` to GitHub.

## Google Colab notebook option


This repository contains a Google Colab notebook for running the ClimateFund question-answering experiment using multiple LLMs.

## Notebook

Open the notebook in Google Colab:

[Open in Colab](https://colab.research.google.com/github/JavierSanzCruza/ClimateFund/blob/main/code/climatefund_qa_experiment_google_colab.ipynb)

## Setup

Before running the notebook, add your API keys in Google Colab Secrets.

In Colab, open:

```text
Secrets → Add new secret
```

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

