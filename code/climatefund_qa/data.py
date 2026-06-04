from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd
from pypdf import PdfReader

from .config import ExperimentConfig
from .utils import (
    clean_docno,
    clean_text,
    clean_text_without_project_codes,
    infer_project_id_from_filename,
    normalize_project_id,
    normalize_scope,
    parse_source_projects,
)

REQUIRED_DOC_COLUMNS = ["docno", "project", "filename", "text_filename", "text"]
REQUIRED_PASSAGE_COLUMNS = ["docno", "text", "project", "filename", "parent_docno", "passage_id"]
EXCLUDED_DISCOVERY_DIR_NAMES = {"rag_experiment_artifacts", "indexes", "retrieval_indexes", ".ipynb_checkpoints", "__pycache__"}


def _is_excluded_path(path: Path) -> bool:
    parts = {p.lower() for p in Path(path).parts}
    return any(name.lower() in parts for name in EXCLUDED_DISCOVERY_DIR_NAMES)


def _dedupe_paths(paths: List[Path]) -> List[Path]:
    seen, out = set(), []
    for p in paths:
        p = Path(p)
        key = str(p.resolve()) if p.exists() else str(p)
        if key not in seen:
            out.append(p)
            seen.add(key)
    return out


def discover_document_files(cfg: ExperimentConfig) -> List[Path]:
    """Find PDF files, with TXT fallback, using the same discovery style as the notebook."""
    candidates: List[Path] = []
    for root in cfg.document_search_roots:
        root = Path(root)
        if root.exists():
            candidates.extend(root.rglob("*.pdf"))
    candidates = [p for p in _dedupe_paths(candidates) if not _is_excluded_path(p)]

    if candidates:
        return candidates

    if cfg.allow_text_document_fallback and cfg.text_document_dir.exists():
        txts = [p for p in cfg.text_document_dir.rglob("*.txt") if not _is_excluded_path(p)]
        return _dedupe_paths(txts)

    return []


def read_pdf_text(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    pages = []
    for page in reader.pages:
        try:
            pages.append(page.extract_text() or "")
        except Exception:
            pages.append("")
    return clean_text("\n".join(pages))


def load_source_documents(cfg: ExperimentConfig) -> pd.DataFrame:
    """Load PDFs/TXT source documents into docs_df."""
    files = discover_document_files(cfg)
    if not files:
        raise FileNotFoundError(
            "No PDF/TXT source documents found. Checked: "
            + ", ".join(str(p) for p in cfg.document_search_roots)
        )

    rows = []
    cfg.text_dir.mkdir(parents=True, exist_ok=True)

    for path in files:
        path = Path(path)
        project = infer_project_id_from_filename(path)
        docno = clean_docno(path.stem)
        if path.suffix.lower() == ".pdf":
            text = read_pdf_text(path)
        else:
            text = path.read_text(encoding="utf-8", errors="ignore")
            text = clean_text(text)

        text_filename = f"{docno}.txt"
        (cfg.text_dir / text_filename).write_text(text, encoding="utf-8")
        rows.append({
            "docno": docno,
            "project": project,
            "filename": path.name,
            "text_filename": text_filename,
            "text": text,
        })

    docs_df = pd.DataFrame(rows, columns=REQUIRED_DOC_COLUMNS)
    docs_df["project"] = docs_df["project"].astype(str).str.lower().str.strip()
    docs_df["text"] = docs_df["text"].fillna("").map(clean_text_without_project_codes)
    return docs_df


def split_into_passages(docs_df: pd.DataFrame, cfg: ExperimentConfig) -> pd.DataFrame:
    """Notebook-style sliding window passage creation without requiring PyTerrier."""
    rows = []
    for _, d in docs_df.iterrows():
        words = str(d.get("text", "")).split()
        if not words:
            continue
        passage_id = 0
        step = max(1, cfg.passage_stride_words)
        size = max(1, cfg.passage_size_words)
        for start in range(0, len(words), step):
            window = words[start:start + size]
            if not window:
                break
            text = clean_text(" ".join(window))
            if len(text) < cfg.min_passage_chars:
                continue
            docno = clean_docno(f"{d['docno']}_p{passage_id:04d}")
            rows.append({
                "docno": docno,
                "text": text,
                "project": str(d.get("project", "")).lower().strip(),
                "filename": d.get("filename", ""),
                "parent_docno": d.get("docno", ""),
                "passage_id": passage_id,
            })
            passage_id += 1
            if start + size >= len(words):
                break
    return pd.DataFrame(rows, columns=REQUIRED_PASSAGE_COLUMNS)


def load_or_build_document_tables(cfg: ExperimentConfig) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Build/load docs.csv and passages.csv, mirroring the notebook flow."""
    cfg.make_dirs()
    docs_path = cfg.table_dir / "documents.csv"
    passages_path = cfg.table_dir / "passages.csv"

    if cfg.allow_passages_table_only and passages_path.exists() and not cfg.rebuild_passage_table:
        passages_df = pd.read_csv(passages_path)
        docs_df = pd.read_csv(docs_path) if docs_path.exists() else pd.DataFrame(columns=REQUIRED_DOC_COLUMNS)
        return docs_df, passages_df

    if docs_path.exists() and not cfg.rebuild_document_tables:
        docs_df = pd.read_csv(docs_path)
    else:
        if not cfg.source_documents_available:
            raise FileNotFoundError("source_documents_available=False but documents.csv must be rebuilt or loaded.")
        docs_df = load_source_documents(cfg)
        docs_df.to_csv(docs_path, index=False)

    if passages_path.exists() and not cfg.rebuild_passage_table:
        passages_df = pd.read_csv(passages_path)
    else:
        passages_df = split_into_passages(docs_df, cfg)
        passages_df.to_csv(passages_path, index=False)

    docs_df["project"] = docs_df.get("project", "").astype(str).str.lower().str.strip()
    passages_df["project"] = passages_df.get("project", "").astype(str).str.lower().str.strip()
    passages_df["docno"] = passages_df["docno"].astype(str)
    return docs_df, passages_df


def load_qa_dataset(cfg: ExperimentConfig) -> pd.DataFrame:
    path = cfg.qa_dataset_path
    if not path.exists():
        candidates = list(cfg.dataset_dir.glob("*.csv")) + list(cfg.project_root.glob("*.csv"))
        candidates = [p for p in candidates if not _is_excluded_path(p)]
        if candidates:
            print("QA_DATASET_PATH was not found. Using discovered dataset:", candidates[0])
            path = candidates[0]
        else:
            raise FileNotFoundError(f"QA dataset not found: {path}")

    if path.suffix.lower() in [".xlsx", ".xls"]:
        qa_df = pd.read_excel(path, sheet_name=cfg.sheet_name)
    else:
        qa_df = pd.read_csv(path)

    if "qid" not in qa_df.columns:
        qa_df = qa_df.copy()
        qa_df["qid"] = [f"q{i:04d}" for i in range(len(qa_df))]

    qa_df["qid"] = qa_df["qid"].astype(str)
    if "scope" in qa_df.columns:
        qa_df["scope"] = qa_df["scope"].map(normalize_scope)
    else:
        qa_df["scope"] = "cross_projects"

    if "source_projects" in qa_df.columns:
        qa_df["source_projects_norm"] = qa_df["source_projects"].map(lambda x: " | ".join(parse_source_projects(x)))
    else:
        qa_df["source_projects"] = ""
        qa_df["source_projects_norm"] = ""

    return qa_df


def prepare_tables(cfg: ExperimentConfig) -> Dict[str, pd.DataFrame]:
    """Notebook step wrapper: documents/passages + QA dataset."""
    docs_df, passages_df = load_or_build_document_tables(cfg)
    qa_df = load_qa_dataset(cfg)
    print("Documents:", len(docs_df))
    print("Passages:", len(passages_df))
    print("Questions:", len(qa_df))
    return {"docs_df": docs_df, "passages_df": passages_df, "qa_df": qa_df}
