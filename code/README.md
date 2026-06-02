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

We describe here...



## Results

## 

¦ Model configuration ¦¦ Single project ¦¦ Cross-project ¦¦
------------------------------------------------------------
¦ Retriever ¦ Reranker ¦ Reader ¦ F1 ¦ BERTScore ¦ F1 ¦ BERTScore ¦
¦ BM25 ¦ None ¦ Mistral 7B Instruct v0.3 ¦ 0.243 ¦ 0.232 ¦ 0.111 ¦ 0.084
