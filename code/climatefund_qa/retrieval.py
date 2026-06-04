from __future__ import annotations

from typing import Dict, Iterable, List, Optional

import numpy as np
import pandas as pd

from .config import ExperimentConfig
from .rerankers import get_reranker
from .utils import normalize_scope, parse_source_projects


def make_passage_lookup(passages_df: pd.DataFrame) -> pd.DataFrame:
    passage_lookup = passages_df.drop(columns=[c for c in ["norm_text"] if c in passages_df.columns], errors="ignore").copy()
    passage_lookup["docno"] = passage_lookup["docno"].astype(str)
    if "project" in passage_lookup.columns:
        passage_lookup["project"] = passage_lookup["project"].astype(str).str.lower().str.strip()
    return passage_lookup


def _attach_passage_text(results: pd.DataFrame, passages_df: pd.DataFrame) -> pd.DataFrame:
    if results is None or len(results) == 0:
        return pd.DataFrame()
    out = results.copy()
    if "text" not in out.columns:
        cols = [c for c in ["docno", "text", "project", "filename", "parent_docno", "passage_id"] if c in passages_df.columns]
        out = out.merge(passages_df[cols], on="docno", how="left", suffixes=("", "_passage"))
    return out


def select_index_for_question(cfg: ExperimentConfig, indexes: Dict[str, object], retriever: str, scope: str, source_projects: List[str]):
    """Single-project questions use per-project index; cross-project questions use global index."""
    retriever = retriever.lower().strip()
    scope = normalize_scope(scope)
    if scope == "single_project" and cfg.single_use_source_project_filter and source_projects:
        project = source_projects[0]
        project_index = indexes.get("by_project", {}).get(retriever, {}).get(project)
        if project_index is not None:
            return project_index, project
    return indexes.get("global", {}).get(retriever), None


def retrieve_no_reranker(cfg: ExperimentConfig, query: str, retriever: str, indexes: Dict[str, object], passages_df: pd.DataFrame, scope: str = "cross_projects", source_projects: Optional[List[str]] = None, top_k: Optional[int] = None) -> pd.DataFrame:
    top_k = top_k or cfg.final_context_k
    source_projects = source_projects or []
    idx, project_used = select_index_for_question(cfg, indexes, retriever, scope, source_projects)
    if idx is None:
        raise ValueError(f"No index loaded for retriever={retriever}, scope={scope}, project={source_projects}")
    results = idx.search(query, k=cfg.retrieve_k)
    results = _attach_passage_text(results, passages_df)
    results["retriever"] = retriever
    results["reranker"] = "none"
    results["project_index_used"] = project_used or "global"
    return results.head(top_k).reset_index(drop=True)


def retrieve_with_reranker(cfg: ExperimentConfig, query: str, retriever: str, reranker_name: str, indexes: Dict[str, object], passages_df: pd.DataFrame, scope: str = "cross_projects", source_projects: Optional[List[str]] = None, top_k: Optional[int] = None) -> pd.DataFrame:
    top_k = top_k or cfg.final_context_k
    source_projects = source_projects or []
    idx, project_used = select_index_for_question(cfg, indexes, retriever, scope, source_projects)
    if idx is None:
        raise ValueError(f"No index loaded for retriever={retriever}, scope={scope}, project={source_projects}")
    results = idx.search(query, k=cfg.retrieve_k)
    results = _attach_passage_text(results, passages_df)
    reranker = get_reranker(reranker_name, rerank_input_k=cfg.rerank_input_k)
    reranked = reranker.rerank(results, query=query, top_k=top_k)
    reranked = _attach_passage_text(reranked, passages_df)
    reranked["retriever"] = retriever
    reranked["reranker"] = reranker_name
    reranked["project_index_used"] = project_used or "global"
    return reranked.reset_index(drop=True)


def retrieve_for_question(cfg: ExperimentConfig, question_row, retriever: str, reranker: str, indexes: Dict[str, object], passages_df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(question_row, pd.Series):
        question = str(question_row.get("question", ""))
        qid = str(question_row.get("qid", "q0"))
        scope = str(question_row.get("scope", "cross_projects"))
        source_projects = parse_source_projects(question_row.get("source_projects_norm", question_row.get("source_projects", "")))
    elif isinstance(question_row, dict):
        question = str(question_row.get("question", ""))
        qid = str(question_row.get("qid", "q0"))
        scope = str(question_row.get("scope", "cross_projects"))
        source_projects = parse_source_projects(question_row.get("source_projects_norm", question_row.get("source_projects", "")))
    else:
        question = str(question_row)
        qid = "q0"
        scope = "cross_projects"
        source_projects = []

    if str(reranker).lower().strip() in ["none", "no", "no_reranker"]:
        out = retrieve_no_reranker(cfg, question, retriever, indexes, passages_df, scope, source_projects, cfg.final_context_k)
    else:
        out = retrieve_with_reranker(cfg, question, retriever, reranker, indexes, passages_df, scope, source_projects, cfg.final_context_k)
    out["qid"] = qid
    out["query"] = question
    return out
