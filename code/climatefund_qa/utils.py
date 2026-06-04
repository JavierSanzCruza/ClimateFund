from __future__ import annotations

import gc
import re
from pathlib import Path
from typing import List, Optional

import pandas as pd


def clean_text(text: str) -> str:
    if text is None:
        return ""
    try:
        if pd.isna(text):
            return ""
    except Exception:
        pass
    text = str(text).replace("\x00", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def clean_docno(docno: str) -> str:
    docno = str(docno).replace("%p", "_p")
    docno = re.sub(r"[^a-zA-Z0-9_\-.]+", "_", docno)
    return docno.strip("_")


def normalize_project_id(x) -> Optional[str]:
    if x is None:
        return None
    try:
        if pd.isna(x):
            return None
    except Exception:
        pass
    x = str(x).strip().lower()
    m = re.search(r"\bfp\s*0*([0-9]+)\b", x, flags=re.I)
    if m:
        return f"fp{int(m.group(1)):03d}"
    m = re.search(r"\bfpm\s*0*([0-9]+)\b", x, flags=re.I)
    if m:
        return f"fp{int(m.group(1)):03d}"
    cleaned = clean_docno(x).lower()
    return cleaned if cleaned else None


def infer_project_id_from_filename(path_or_name) -> str:
    name = Path(path_or_name).stem.lower()
    project = normalize_project_id(name)
    return project or clean_docno(name).lower()


def parse_source_projects(x) -> List[str]:
    if x is None:
        return []
    try:
        if pd.isna(x):
            return []
    except Exception:
        pass
    parts = re.split(r"\s*\|\s*|\s*,\s*|\s*;\s*", str(x))
    out = []
    for p in parts:
        n = normalize_project_id(p)
        if n and n not in out:
            out.append(n)
    return out


def normalize_scope(x: str) -> str:
    x = str(x).lower().strip()
    if x in ["single", "single_project", "single-project", "single project"]:
        return "single_project"
    if x in ["cross", "cross_project", "cross_projects", "cross-project", "cross project"]:
        return "cross_projects"
    return x


def clean_text_without_project_codes(text):
    if text is None:
        return ""
    text = str(text)
    pattern = re.compile(r"\b[A-Z]{2,10}[-_ ]?\d{1,6}\b|\b[A-Z]{2,10}[-_][A-Z0-9]{2,10}\b")
    text = pattern.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip()


def clear_cuda():
    gc.collect()
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            try:
                torch.cuda.ipc_collect()
            except Exception:
                pass
    except Exception:
        pass
