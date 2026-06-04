from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Optional

import pandas as pd

from .config import ExperimentConfig, RunSpec, create_config
from .data import prepare_tables
from .experiment import run_experiment
from .indexes import build_indexes, load_indexes, load_or_build_indexes
from .readers import get_reader
from .retrieval import retrieve_for_question, retrieve_no_reranker, retrieve_with_reranker


def step_status(cfg: ExperimentConfig) -> None:
    cfg.make_dirs()
    cfg.print_diagnostics()


def step_prepare_tables(cfg: ExperimentConfig):
    return prepare_tables(cfg)


def step_build_indexes(cfg: ExperimentConfig, passages_df: pd.DataFrame, retrievers: Iterable[str] = ("bm25", "e5"), rebuild: bool = False):
    return build_indexes(cfg, passages_df, retrievers=retrievers, rebuild=rebuild)


def step_load_indexes(cfg: ExperimentConfig, retrievers: Iterable[str] = ("bm25", "e5"), passages_df: Optional[pd.DataFrame] = None):
    return load_indexes(cfg, retrievers=retrievers, passages_df=passages_df)


def step_load_or_build_indexes(cfg: ExperimentConfig, passages_df: pd.DataFrame, retrievers: Iterable[str] = ("bm25", "e5"), rebuild: bool = False):
    return load_or_build_indexes(cfg, passages_df, retrievers=retrievers, rebuild=rebuild)


def step_retrieve(cfg: ExperimentConfig, question: str, indexes, passages_df: pd.DataFrame, retriever: str = "bm25", reranker: str = "none", scope: str = "cross_projects", source_projects: Optional[List[str]] = None):
    qrow = {"qid": "manual", "question": question, "scope": scope, "source_projects": " | ".join(source_projects or [])}
    return retrieve_for_question(cfg, qrow, retriever, reranker, indexes, passages_df)


def step_read_answer(cfg: ExperimentConfig, question: str, contexts: pd.DataFrame, reader: str = "extractive_fallback") -> str:
    r = get_reader(reader, final_context_k=cfg.final_context_k)
    return r.answer(question, contexts)


def step_run_experiment(cfg: ExperimentConfig, retrievers=None, rerankers=None, readers=None, max_questions=None, rebuild_indexes=False, compute_bertscore_flag=None):
    return run_experiment(cfg, retrievers=retrievers, rerankers=rerankers, readers=readers, max_questions=max_questions, rebuild_indexes=rebuild_indexes, compute_bertscore_flag=compute_bertscore_flag)
