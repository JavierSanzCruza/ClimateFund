from __future__ import annotations

import re
import textwrap
from pathlib import Path
from typing import Dict, Tuple

import pandas as pd

from .config import ExperimentConfig
from .results_table import first_existing_file, find_latest_run_dir_with_metrics, latex_escape


def load_latest_run_outputs(cfg: ExperimentConfig):
    latest_run_dir, _ = find_latest_run_dir_with_metrics(cfg.run_dir)
    metrics_df = pd.read_csv(first_existing_file(latest_run_dir, ["metrics_df.csv", "metrics_final.csv", "metrics_checkpoint.csv"]))
    predictions_df = pd.read_csv(first_existing_file(latest_run_dir, ["predictions_df.csv", "predictions_final.csv", "predictions_checkpoint.csv"]))
    run_details_df = pd.read_csv(first_existing_file(latest_run_dir, ["run_details_df.csv", "run_details_final.csv", "run_details_checkpoint.csv"]))
    summary_path = first_existing_file(latest_run_dir, ["summary_df.csv", "summary_final.csv", "summary.csv"], required=False)
    if summary_path:
        summary_df = pd.read_csv(summary_path)
    else:
        numeric_cols = metrics_df.select_dtypes(include="number").columns.tolist()
        summary_df = metrics_df.groupby("run_name")[numeric_cols].mean().reset_index() if "run_name" in metrics_df.columns and numeric_cols else pd.DataFrame()
    qrels_path = cfg.table_dir / "qrels.csv"
    passages_path = cfg.table_dir / "passages.csv"
    qrels_df = pd.read_csv(qrels_path) if qrels_path.exists() else pd.DataFrame(columns=["qid", "docno"])
    passages_df = pd.read_csv(passages_path) if passages_path.exists() else pd.DataFrame(columns=["docno", "text", "project", "parent_docno"])
    questions_df = pd.read_csv(cfg.qa_dataset_path) if cfg.qa_dataset_path.exists() else pd.DataFrame()
    return latest_run_dir, {"metrics_df": metrics_df, "summary_df": summary_df, "predictions_df": predictions_df, "run_details_df": run_details_df, "qrels_df": qrels_df, "passages_df": passages_df, "questions_df": questions_df}


def safe_col(df, possible_names):
    for c in possible_names:
        if c in df.columns:
            return c
    return None


def find_metric_column(df, names):
    for n in names:
        if n in df.columns:
            return n
    return None


def select_examples(metrics_df: pd.DataFrame, n: int = 2):
    ndcg_col = find_metric_column(metrics_df, ["nDCG@10", "ndcg_cut_10", "nDCG@10_retrieval", "ndcg@10"])
    f1_col = find_metric_column(metrics_df, ["F1", "f1", "answer_f1", "token_f1", "F1Score", "f1_score"])
    bert_col = find_metric_column(metrics_df, ["BERTScore", "bertscore_f1", "bert_score", "bertscore"])
    metric = bert_col or f1_col or ndcg_col
    if metric is None:
        return {}
    run_name = metrics_df["run_name"].dropna().astype(str).iloc[0]
    df = metrics_df[metrics_df["run_name"].astype(str) == run_name].copy()
    return {"good_examples": df.sort_values(metric, ascending=False).head(n), "bad_examples": df.sort_values(metric, ascending=True).head(n)}


def get_top_retrieved(run_details_df: pd.DataFrame, passages_df: pd.DataFrame, run_name, qid, top_k=5):
    rows = run_details_df[(run_details_df["run_name"].astype(str) == str(run_name)) & (run_details_df["qid"].astype(str) == str(qid))].copy()
    if rows.empty:
        return rows
    if "rank" in rows.columns:
        rows = rows.sort_values("rank")
    rows = rows.head(top_k)
    if "text" not in rows.columns and not passages_df.empty:
        passage_cols = [c for c in ["docno", "text", "project", "parent_docno"] if c in passages_df.columns]
        rows = rows.merge(passages_df[passage_cols], on="docno", how="left", suffixes=("", "_passage"))
    return rows


def print_example(metrics_df, predictions_df, run_details_df, passages_df, run_name, qid, top_k=5):
    row_df = metrics_df[(metrics_df["run_name"].astype(str) == str(run_name)) & (metrics_df["qid"].astype(str) == str(qid))]
    pred_df = predictions_df[(predictions_df["run_name"].astype(str) == str(run_name)) & (predictions_df["qid"].astype(str) == str(qid))]
    if row_df.empty:
        print("No example found.")
        return
    row = row_df.iloc[0]
    pred = pred_df.iloc[0] if not pred_df.empty else row
    print("=" * 100)
    print("RUN:", run_name)
    print("QID:", qid)
    print("QUESTION:")
    print(textwrap.fill(str(pred.get("question", "")), width=110))
    print("\nGOLD ANSWER:")
    print(textwrap.fill(str(pred.get("gold_answer", "")), width=110))
    print("\nGENERATED ANSWER:")
    print(textwrap.fill(str(pred.get("generated_answer", "")), width=110))
    print("\nMETRICS:")
    for c in ["EM", "F1", "BERTScore", "nDCG@10"]:
        if c in row.index:
            print(f"  {c}: {row.get(c)}")
    print("\nTOP RETRIEVED PASSAGES:")
    top = get_top_retrieved(run_details_df, passages_df, run_name, qid, top_k)
    if top.empty:
        print("No retrieved passages found.")
    else:
        for _, r in top.iterrows():
            print("-" * 100)
            print(f"Rank {r.get('rank', '')} | docno={r.get('docno', '')} | project={r.get('project', '')}")
            print(textwrap.shorten(str(r.get("text", "")).replace("\n", " "), width=450, placeholder="..."))
    print("=" * 100)


def create_qualitative_examples(cfg: ExperimentConfig, top_k: int = 5, n: int = 2):
    latest_run_dir, data = load_latest_run_outputs(cfg)
    metrics_df = data["metrics_df"]
    examples = select_examples(metrics_df, n=n)
    out_dir = latest_run_dir / "qualitative_examples"
    out_dir.mkdir(parents=True, exist_ok=True)
    for label, df in examples.items():
        for _, r in df.iterrows():
            qid, run_name = r["qid"], r["run_name"]
            top = get_top_retrieved(data["run_details_df"], data["passages_df"], run_name, qid, top_k)
            text = f"% Qualitative example: {label}, {run_name}, {qid}\n"
            text += f"% Top retrieved passages: {len(top)}\n"
            for _, tr in top.iterrows():
                text += "% " + str(tr.get("docno", "")) + ": " + str(tr.get("text", ""))[:250].replace("\n", " ") + "\n"
            safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", f"{label}_{run_name}_{qid}")
            (out_dir / f"{safe_name}.tex").write_text(text, encoding="utf-8")
    return latest_run_dir, examples
