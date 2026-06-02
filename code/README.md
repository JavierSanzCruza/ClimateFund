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

We describe here how to run the code. TODO

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

