from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class ExperimentConfig:
    """Main configuration, kept close to the original notebook variables."""

    project_root: Path
    code_dir: Optional[Path] = None
    dataset_dir: Optional[Path] = None

    # Input names/folders
    dataset_filename: str = "climatefund_qa.csv"
    documents_dirname: str = "documents"
    sheet_name: int | str = 0

    # Output/index folders
    artifact_dirname: str = "rag_experiment_artifacts"
    index_dirname: str = "indexes"

    # Passage/sliding-window parameters
    sliding_text_attr: str = "text"
    sliding_prepend_attr: Optional[str] = None
    passage_size_words: int = 180
    passage_stride_words: int = 60
    min_passage_chars: int = 20

    # Rebuild switches
    rebuild_document_tables: bool = True
    rebuild_passage_table: bool = True
    rebuild_bm25_passage_index: bool = True
    rebuild_e5_passage_index: bool = True
    source_documents_available: bool = True
    allow_text_document_fallback: bool = True
    allow_passages_table_only: bool = True

    # Experiment grid
    retrievers: List[str] = field(default_factory=lambda: ["bm25", "e5"])
    rerankers: List[str] = field(default_factory=lambda: ["none", "t5"])
    readers: List[str] = field(default_factory=lambda: ["extractive_fallback"])

    # Retrieval/generation
    retrieve_k: int = 50
    rerank_input_k: int = 20
    final_context_k: int = 5
    single_use_source_project_filter: bool = True
    max_questions: Optional[int] = None
    compute_bertscore: bool = True

    # Reader defaults
    ida_llm_base_url: str = "http://api.terrier.org/v1"

    def __post_init__(self):
        self.project_root = Path(self.project_root).expanduser().resolve()
        if self.code_dir is None:
            self.code_dir = self.project_root / "code"
        else:
            self.code_dir = Path(self.code_dir).expanduser().resolve()
        if self.dataset_dir is None:
            self.dataset_dir = self.project_root / "dataset"
        else:
            self.dataset_dir = Path(self.dataset_dir).expanduser().resolve()

    @property
    def base_dir(self) -> Path:
        """Compatibility with the notebook's BASE_DIR name."""
        return self.project_root

    @property
    def pdf_dir(self) -> Path:
        return self.dataset_dir / self.documents_dirname

    @property
    def document_search_roots(self) -> List[Path]:
        return [
            self.pdf_dir,
            self.dataset_dir / "pdfs",
            self.dataset_dir / "PDFs",
            self.dataset_dir / "funding_proposals",
            self.dataset_dir / "proposals",
            self.dataset_dir,
        ]

    @property
    def text_document_dir(self) -> Path:
        return self.dataset_dir / "text_documents"

    @property
    def qa_dataset_path(self) -> Path:
        return self.dataset_dir / self.dataset_filename

    @property
    def artifact_dir(self) -> Path:
        return self.project_root / self.artifact_dirname

    @property
    def text_dir(self) -> Path:
        return self.artifact_dir / "texts"

    @property
    def table_dir(self) -> Path:
        return self.artifact_dir / "tables"

    @property
    def run_dir(self) -> Path:
        return self.artifact_dir / "runs"

    @property
    def index_dir(self) -> Path:
        return self.project_root / self.index_dirname

    @property
    def bm25_passage_index(self) -> Path:
        return self.index_dir / "dest.bm25"

    @property
    def e5_passage_index(self) -> Path:
        return self.index_dir / "dest.e5.flex"

    @property
    def project_index_dir(self) -> Path:
        return self.index_dir / "by_project"

    def project_bm25_index_path(self, project: str) -> Path:
        return self.project_index_dir / safe_project_id(project) / "dest.bm25"

    def project_e5_index_path(self, project: str) -> Path:
        return self.project_index_dir / safe_project_id(project) / "dest.e5.flex"

    def make_dirs(self) -> None:
        for p in [self.text_dir, self.table_dir, self.run_dir, self.index_dir, self.project_index_dir]:
            p.mkdir(parents=True, exist_ok=True)

    def print_diagnostics(self) -> None:
        print("PROJECT_ROOT:", self.project_root, "| exists =", self.project_root.exists())
        print("CODE_DIR:", self.code_dir, "| exists =", self.code_dir.exists())
        print("DATASET_DIR:", self.dataset_dir, "| exists =", self.dataset_dir.exists())
        print("QA_DATASET_PATH:", self.qa_dataset_path, "| exists =", self.qa_dataset_path.exists())
        print("DOCUMENT_DIR:", self.pdf_dir, "| exists =", self.pdf_dir.exists())
        print("INDEX_DIR:", self.index_dir, "| exists =", self.index_dir.exists())
        print("BM25 index:", self.bm25_passage_index, "| exists =", self.bm25_passage_index.exists())
        print("E5 index:", self.e5_passage_index, "| exists =", self.e5_passage_index.exists())
        print("ARTIFACT_DIR:", self.artifact_dir, "| exists =", self.artifact_dir.exists())

        if self.project_root.exists():
            print("\nPROJECT_ROOT children:")
            for child in sorted(self.project_root.iterdir()):
                kind = "dir" if child.is_dir() else "file"
                print(f"  - {child.name} ({kind})")

        if self.dataset_dir.exists():
            print("\nDATASET_DIR children:")
            for child in sorted(self.dataset_dir.iterdir()):
                kind = "dir" if child.is_dir() else "file"
                print(f"  - {child.name} ({kind})")


def safe_project_id(project) -> str:
    import re
    project = str(project).strip().lower()
    return re.sub(r"[^a-zA-Z0-9_\-]+", "_", project)


def create_config(project_root: str | Path | None = None, **kwargs) -> ExperimentConfig:
    """Create config for UOG layout: UOG/code and UOG/dataset."""
    if project_root is None:
        cwd = Path.cwd().resolve()
        # If running from UOG/code, use parent UOG. Otherwise use cwd.
        project_root = cwd.parent if cwd.name.lower() == "code" else cwd
    cfg = ExperimentConfig(project_root=Path(project_root), **kwargs)
    cfg.make_dirs()
    return cfg


@dataclass
class RunSpec:
    retriever: str
    reranker: str
    reader: str

    @property
    def run_name(self) -> str:
        return f"{self.retriever}__{self.reranker}__{self.reader}"
