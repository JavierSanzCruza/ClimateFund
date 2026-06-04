from __future__ import annotations

import json
import math
import pickle
import shutil
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import numpy as np
import pandas as pd

from .config import ExperimentConfig, safe_project_id
from .utils import clean_text

DUMMY_DOC_PREFIX = "__dummy__"


def bm25_index_exists(index_path: Path) -> bool:
    index_path = Path(index_path)
    return index_path.exists() and (index_path / "bm25_index.pkl").exists()


def e5_index_exists(index_path: Path) -> bool:
    index_path = Path(index_path)
    return index_path.exists() and ((index_path / "e5_index.faiss").exists() or (index_path / "e5_embeddings.npy").exists())


def _tokenize(text: str) -> List[str]:
    import re
    return re.findall(r"[a-zA-Z0-9]+", clean_text(text).lower())


class SimpleBM25Index:
    """Small BM25 implementation so CMD works even when PyTerrier is unavailable."""
    def __init__(self, passages_df: pd.DataFrame, k1: float = 1.2, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.passages_df = passages_df.reset_index(drop=True).copy()
        self.docnos = self.passages_df["docno"].astype(str).tolist()
        self.tokens = [_tokenize(t) for t in self.passages_df["text"].fillna("")]
        self.doc_lens = np.array([len(t) for t in self.tokens], dtype=np.float32)
        self.avgdl = float(self.doc_lens.mean()) if len(self.doc_lens) else 0.0
        self.tfs = [Counter(toks) for toks in self.tokens]
        df = Counter()
        for toks in self.tokens:
            df.update(set(toks))
        n = len(self.tokens)
        self.idf = {term: math.log(1 + (n - freq + 0.5) / (freq + 0.5)) for term, freq in df.items()}

    def search(self, query: str, k: int = 50) -> pd.DataFrame:
        q_terms = _tokenize(query)
        scores = np.zeros(len(self.tokens), dtype=np.float32)
        if not q_terms or len(self.tokens) == 0:
            return self.passages_df.head(0).copy()
        for term in q_terms:
            idf = self.idf.get(term, 0.0)
            if idf == 0.0:
                continue
            for i, tf in enumerate(self.tfs):
                f = tf.get(term, 0)
                if f == 0:
                    continue
                denom = f + self.k1 * (1 - self.b + self.b * self.doc_lens[i] / max(self.avgdl, 1e-6))
                scores[i] += idf * (f * (self.k1 + 1)) / denom
        top_idx = np.argsort(-scores)[:k]
        top_idx = [i for i in top_idx if scores[i] > 0]
        out = self.passages_df.iloc[top_idx].copy()
        out["score"] = [float(scores[i]) for i in top_idx]
        out["rank"] = np.arange(1, len(out) + 1)
        return out.reset_index(drop=True)


def build_bm25_index(passages_df: pd.DataFrame, index_path: Path, rebuild: bool = False) -> SimpleBM25Index:
    index_path = Path(index_path)
    if rebuild and index_path.exists():
        shutil.rmtree(index_path)
    index_path.mkdir(parents=True, exist_ok=True)
    if bm25_index_exists(index_path) and not rebuild:
        return load_bm25_index(index_path)
    idx = SimpleBM25Index(passages_df)
    with open(index_path / "bm25_index.pkl", "wb") as f:
        pickle.dump(idx, f)
    return idx


def load_bm25_index(index_path: Path) -> SimpleBM25Index:
    with open(Path(index_path) / "bm25_index.pkl", "rb") as f:
        return pickle.load(f)


class E5Index:
    def __init__(self, passages_df: pd.DataFrame, model_name: str = "intfloat/e5-base-v2"):
        from sentence_transformers import SentenceTransformer
        self.passages_df = passages_df.reset_index(drop=True).copy()
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)
        texts = ["passage: " + str(t) for t in self.passages_df["text"].fillna("").tolist()]
        emb = self.model.encode(texts, normalize_embeddings=True, show_progress_bar=True)
        self.embeddings = np.asarray(emb, dtype="float32")

    def search(self, query: str, k: int = 50) -> pd.DataFrame:
        q = self.model.encode(["query: " + query], normalize_embeddings=True)
        q = np.asarray(q, dtype="float32")
        scores = self.embeddings @ q[0]
        top_idx = np.argsort(-scores)[:k]
        out = self.passages_df.iloc[top_idx].copy()
        out["score"] = [float(scores[i]) for i in top_idx]
        out["rank"] = np.arange(1, len(out) + 1)
        return out.reset_index(drop=True)


def build_e5_index(passages_df: pd.DataFrame, index_path: Path, rebuild: bool = False) -> E5Index:
    index_path = Path(index_path)
    if rebuild and index_path.exists():
        shutil.rmtree(index_path)
    index_path.mkdir(parents=True, exist_ok=True)
    if e5_index_exists(index_path) and not rebuild:
        return load_e5_index(index_path)
    idx = E5Index(passages_df)
    idx.passages_df.to_csv(index_path / "passages.csv", index=False)
    np.save(index_path / "e5_embeddings.npy", idx.embeddings)
    (index_path / "model_name.txt").write_text(idx.model_name, encoding="utf-8")
    return idx


def load_e5_index(index_path: Path) -> E5Index:
    from sentence_transformers import SentenceTransformer
    index_path = Path(index_path)
    obj = E5Index.__new__(E5Index)
    obj.passages_df = pd.read_csv(index_path / "passages.csv")
    obj.embeddings = np.load(index_path / "e5_embeddings.npy")
    obj.model_name = (index_path / "model_name.txt").read_text(encoding="utf-8").strip()
    obj.model = SentenceTransformer(obj.model_name)
    return obj


def build_global_indexes(cfg: ExperimentConfig, passages_df: pd.DataFrame, retrievers: Iterable[str] = ("bm25", "e5"), rebuild: bool = False) -> Dict[str, object]:
    out = {}
    retrievers = [r.lower() for r in retrievers]
    if "bm25" in retrievers:
        out["bm25"] = build_bm25_index(passages_df, cfg.bm25_passage_index, rebuild=rebuild or cfg.rebuild_bm25_passage_index)
    if "e5" in retrievers:
        out["e5"] = build_e5_index(passages_df, cfg.e5_passage_index, rebuild=rebuild or cfg.rebuild_e5_passage_index)
    return out


def build_project_indexes(cfg: ExperimentConfig, passages_df: pd.DataFrame, retrievers: Iterable[str] = ("bm25", "e5"), rebuild: bool = False) -> Dict[str, Dict[str, object]]:
    """Build per-project indexes just like the notebook's by_project indexes."""
    out = {"bm25": {}, "e5": {}}
    if "project" not in passages_df.columns:
        return out
    for project, group in passages_df.groupby(passages_df["project"].astype(str).str.lower().str.strip()):
        if not project or project == "nan":
            continue
        if "bm25" in retrievers:
            out["bm25"][project] = build_bm25_index(group, cfg.project_bm25_index_path(project), rebuild=rebuild or cfg.rebuild_bm25_passage_index)
        if "e5" in retrievers:
            out["e5"][project] = build_e5_index(group, cfg.project_e5_index_path(project), rebuild=rebuild or cfg.rebuild_e5_passage_index)
    return out


def build_indexes(cfg: ExperimentConfig, passages_df: pd.DataFrame, retrievers: Iterable[str] = ("bm25", "e5"), rebuild: bool = False) -> Dict[str, object]:
    """Notebook step: create global + per-project BM25/E5 indexes."""
    cfg.make_dirs()
    global_indexes = build_global_indexes(cfg, passages_df, retrievers, rebuild=rebuild)
    project_indexes = build_project_indexes(cfg, passages_df, retrievers, rebuild=rebuild)
    return {"global": global_indexes, "by_project": project_indexes}


def load_indexes(cfg: ExperimentConfig, retrievers: Iterable[str] = ("bm25", "e5"), passages_df: Optional[pd.DataFrame] = None) -> Dict[str, object]:
    """Load existing global + discovered per-project indexes."""
    out = {"global": {}, "by_project": {"bm25": {}, "e5": {}}}
    retrievers = [r.lower() for r in retrievers]
    if "bm25" in retrievers and bm25_index_exists(cfg.bm25_passage_index):
        out["global"]["bm25"] = load_bm25_index(cfg.bm25_passage_index)
    if "e5" in retrievers and e5_index_exists(cfg.e5_passage_index):
        out["global"]["e5"] = load_e5_index(cfg.e5_passage_index)

    projects = []
    if passages_df is not None and "project" in passages_df.columns:
        projects = sorted(passages_df["project"].dropna().astype(str).str.lower().str.strip().unique())
    elif cfg.project_index_dir.exists():
        projects = [p.name for p in cfg.project_index_dir.iterdir() if p.is_dir()]

    for project in projects:
        if "bm25" in retrievers and bm25_index_exists(cfg.project_bm25_index_path(project)):
            out["by_project"]["bm25"][project] = load_bm25_index(cfg.project_bm25_index_path(project))
        if "e5" in retrievers and e5_index_exists(cfg.project_e5_index_path(project)):
            out["by_project"]["e5"][project] = load_e5_index(cfg.project_e5_index_path(project))
    return out


def load_or_build_indexes(cfg: ExperimentConfig, passages_df: pd.DataFrame, retrievers: Iterable[str] = ("bm25", "e5"), rebuild: bool = False) -> Dict[str, object]:
    if rebuild:
        return build_indexes(cfg, passages_df, retrievers=retrievers, rebuild=True)
    loaded = load_indexes(cfg, retrievers=retrievers, passages_df=passages_df)
    missing = [r for r in retrievers if r not in loaded["global"]]
    if missing:
        built = build_indexes(cfg, passages_df, retrievers=missing, rebuild=False)
        loaded["global"].update(built["global"])
        for r, d in built["by_project"].items():
            loaded["by_project"].setdefault(r, {}).update(d)
    return loaded
