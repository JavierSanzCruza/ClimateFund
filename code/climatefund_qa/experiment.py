from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import pandas as pd
from tqdm.auto import tqdm

from .config import ExperimentConfig, RunSpec
from .data import prepare_tables
from .indexes import load_or_build_indexes
from .metrics import evaluate_predictions
from .readers import get_reader, reader_display_name
from .retrieval import retrieve_for_question
from .utils import clear_cuda, normalize_scope, parse_source_projects


def is_connection_error(e: Exception) -> bool:
    msg = str(e).lower()
    patterns = ["connection error", "connectionerror", "connection refused", "connection reset", "connect timeout", "read timeout", "api key", "unauthorized", "forbidden", "missing"]
    return any(p in msg for p in patterns)


def make_run_specs(retrievers: Iterable[str], rerankers: Iterable[str], readers: Iterable[str]) -> List[RunSpec]:
    return [RunSpec(r, rr, rd) for r in retrievers for rr in rerankers for rd in readers]


def _gold_answer(row) -> str:
    for c in ["answer", "gold_answer", "reference_answer"]:
        if c in row and pd.notna(row[c]):
            return str(row[c])
    return ""


def run_single_configuration(cfg: ExperimentConfig, qa_df: pd.DataFrame, passages_df: pd.DataFrame, indexes: Dict[str, object], run_spec: RunSpec, output_dir: Path, compute_bertscore_flag: Optional[bool] = None):
    compute_bertscore_flag = cfg.compute_bertscore if compute_bertscore_flag is None else compute_bertscore_flag
    run_name = run_spec.run_name
    print("\nRunning:", run_name)

    try:
        reader = get_reader(run_spec.reader, final_context_k=cfg.final_context_k)
    except Exception as e:
        print("Reader unavailable; skipping run:", run_name, "|", e)
        failed_df = pd.DataFrame([{"run_name": run_name, "qid": "ALL", "stage": "reader_init", "error": str(e)}])
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), failed_df

    prediction_rows, run_rows, failed_rows = [], [], []

    for _, qrow in tqdm(qa_df.iterrows(), total=len(qa_df), desc=run_name):
        qid = str(qrow.get("qid", ""))
        question = str(qrow.get("question", ""))
        scope = normalize_scope(qrow.get("scope", "cross_projects"))
        source_projects = parse_source_projects(qrow.get("source_projects_norm", qrow.get("source_projects", "")))
        try:
            contexts = retrieve_for_question(cfg, qrow, run_spec.retriever, run_spec.reranker, indexes, passages_df)
            answer = reader.answer(question, contexts)
            for _, crow in contexts.iterrows():
                d = crow.to_dict()
                d.update({
                    "run_name": run_name,
                    "retrieval_scope": scope,
                    "source_projects": " | ".join(source_projects),
                    "reader": run_spec.reader,
                    "reader_display": reader_display_name(run_spec.reader),
                })
                run_rows.append(d)
            prediction_rows.append({
                "run_name": run_name,
                "qid": qid,
                "question": question,
                "gold_answer": _gold_answer(qrow),
                "generated_answer": answer,
                "retrieval_scope": scope,
                "source_projects": " | ".join(source_projects),
                "retriever": run_spec.retriever,
                "reranker": run_spec.reranker,
                "reader": run_spec.reader,
                "reader_display": reader_display_name(run_spec.reader),
            })
        except Exception as e:
            failed_rows.append({"run_name": run_name, "qid": qid, "stage": "question", "error": str(e)})
            if is_connection_error(e):
                print("Connection/API-like error; continuing to next question/run:", e)
        finally:
            clear_cuda()

    predictions_df = pd.DataFrame(prediction_rows)
    run_details_df = pd.DataFrame(run_rows)
    failed_df = pd.DataFrame(failed_rows)
    metrics_df = evaluate_predictions(predictions_df, compute_bertscore_flag) if not predictions_df.empty else pd.DataFrame()

    # Save per-run files like the notebook.
    for name, df in [("predictions", predictions_df), ("run_details", run_details_df), ("metrics", metrics_df), ("failed", failed_df)]:
        df.to_csv(output_dir / f"{run_name}__{name}.csv", index=False)

    return predictions_df, run_details_df, metrics_df, failed_df


def run_experiment(cfg: ExperimentConfig, retrievers: Optional[List[str]] = None, rerankers: Optional[List[str]] = None, readers: Optional[List[str]] = None, max_questions: Optional[int] = None, rebuild_indexes: bool = False, compute_bertscore_flag: Optional[bool] = None):
    tables = prepare_tables(cfg)
    qa_df = tables["qa_df"].copy()
    passages_df = tables["passages_df"].copy()
    if max_questions is None:
        max_questions = cfg.max_questions
    if max_questions is not None:
        qa_df = qa_df.head(int(max_questions)).copy()

    retrievers = retrievers or cfg.retrievers
    rerankers = rerankers or cfg.rerankers
    readers = readers or cfg.readers
    indexes = load_or_build_indexes(cfg, passages_df, retrievers=retrievers, rebuild=rebuild_indexes)

    run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = cfg.run_dir / f"run_{run_timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)
    print("Output directory:", output_dir)

    all_predictions, all_run_details, all_metrics, all_failed = [], [], [], []
    specs = make_run_specs(retrievers, rerankers, readers)

    for spec in specs:
        pred, details, metrics, failed = run_single_configuration(cfg, qa_df, passages_df, indexes, spec, output_dir, compute_bertscore_flag)
        all_predictions.append(pred)
        all_run_details.append(details)
        all_metrics.append(metrics)
        all_failed.append(failed)

        pd.concat(all_predictions, ignore_index=True).to_csv(output_dir / "predictions_checkpoint.csv", index=False)
        pd.concat(all_run_details, ignore_index=True).to_csv(output_dir / "run_details_checkpoint.csv", index=False)
        pd.concat(all_metrics, ignore_index=True).to_csv(output_dir / "metrics_checkpoint.csv", index=False)
        pd.concat(all_failed, ignore_index=True).to_csv(output_dir / "failed_checkpoint.csv", index=False)

    predictions_final = pd.concat(all_predictions, ignore_index=True) if all_predictions else pd.DataFrame()
    run_details_final = pd.concat(all_run_details, ignore_index=True) if all_run_details else pd.DataFrame()
    metrics_final = pd.concat(all_metrics, ignore_index=True) if all_metrics else pd.DataFrame()
    failed_final = pd.concat(all_failed, ignore_index=True) if all_failed else pd.DataFrame()

    # Save notebook-compatible and final names.
    predictions_final.to_csv(output_dir / "predictions_final.csv", index=False)
    predictions_final.to_csv(output_dir / "predictions_df.csv", index=False)
    run_details_final.to_csv(output_dir / "run_details_final.csv", index=False)
    run_details_final.to_csv(output_dir / "run_details_df.csv", index=False)
    metrics_final.to_csv(output_dir / "metrics_final.csv", index=False)
    metrics_final.to_csv(output_dir / "metrics_df.csv", index=False)
    failed_final.to_csv(output_dir / "failed_final.csv", index=False)
    failed_final.to_csv(output_dir / "failed_df.csv", index=False)

    return {"output_dir": output_dir, "predictions_df": predictions_final, "run_details_df": run_details_final, "metrics_df": metrics_final, "failed_df": failed_final}
