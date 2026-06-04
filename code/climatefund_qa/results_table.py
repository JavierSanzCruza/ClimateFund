from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional

import numpy as np
import pandas as pd
from pandas.errors import EmptyDataError

from .config import ExperimentConfig


def safe_read_csv(path, default_columns=None):
    path = Path(path)
    if default_columns is None:
        default_columns = []
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame(columns=default_columns)
    try:
        return pd.read_csv(path)
    except EmptyDataError:
        return pd.DataFrame(columns=default_columns)


def first_existing_file(folder, filenames, required=True):
    folder = Path(folder)
    for filename in filenames:
        path = folder / filename
        if path.exists() and path.stat().st_size > 0:
            return path
    if required:
        existing = [p.name for p in folder.iterdir()] if folder.exists() else []
        raise FileNotFoundError(
            f"Could not find any of these files in:\n{folder}\n\nTried:\n"
            + "\n".join(f"- {x}" for x in filenames)
            + "\n\nExisting files:\n"
            + "\n".join(f"- {x}" for x in existing)
        )
    return None


def find_latest_run_dir_with_metrics(run_root: Path):
    run_root = Path(run_root)
    run_dirs = sorted([p for p in run_root.iterdir() if p.is_dir()])
    for candidate_dir in reversed(run_dirs):
        candidate_metrics_path = first_existing_file(candidate_dir, ["metrics_df.csv", "metrics_final.csv", "metrics_checkpoint.csv"], required=False)
        if candidate_metrics_path is None:
            continue
        try:
            test_df = pd.read_csv(candidate_metrics_path, nrows=1)
            if not test_df.empty:
                return candidate_dir, candidate_metrics_path
        except EmptyDataError:
            continue
    raise ValueError(f"No run folder with a readable metrics file was found in {run_root}.")


def load_latest_metrics_and_failures(cfg: ExperimentConfig):
    latest_run_dir, metrics_path = find_latest_run_dir_with_metrics(cfg.run_dir)
    failed_path = first_existing_file(latest_run_dir, ["failed_df.csv", "failed_final.csv", "failed_checkpoint.csv"], required=False)
    metrics_df = safe_read_csv(metrics_path)
    failed_df = safe_read_csv(failed_path, ["run_name", "qid", "stage", "error"]) if failed_path else pd.DataFrame(columns=["run_name", "qid", "stage", "error"])
    return latest_run_dir, metrics_df, failed_df


def apply_optional_filters(metrics_df: pd.DataFrame, failed_df: Optional[pd.DataFrame] = None, table_retrievers=None, table_rerankers=None, table_readers=None) -> pd.DataFrame:
    metrics_for_table = metrics_df.copy()
    for col in ["run_name", "retriever", "reranker", "reader", "reader_display", "retrieval_scope", "qid"]:
        if col not in metrics_for_table.columns:
            metrics_for_table[col] = ""
    if failed_df is None:
        failed_df = pd.DataFrame(columns=["run_name", "qid"])

    num_questions = metrics_for_table["qid"].astype(str).nunique()
    fully_failed_runs = []
    if not failed_df.empty and {"run_name", "qid"}.issubset(failed_df.columns):
        failed_summary = failed_df.dropna(subset=["run_name", "qid"]).groupby("run_name")["qid"].nunique().reset_index(name="num_failed")
        fully_failed_runs = failed_summary.loc[failed_summary["num_failed"] >= num_questions, "run_name"].tolist()
    if fully_failed_runs:
        metrics_for_table = metrics_for_table[~metrics_for_table["run_name"].isin(fully_failed_runs)].copy()

    metrics_for_table["retriever"] = metrics_for_table["retriever"].astype(str).str.lower().str.strip()
    metrics_for_table["reranker"] = metrics_for_table["reranker"].astype(str).str.lower().str.strip()
    metrics_for_table["reader"] = metrics_for_table["reader"].astype(str).str.strip()
    metrics_for_table["reader_display"] = metrics_for_table["reader_display"].fillna(metrics_for_table["reader"]).astype(str).str.strip()
    metrics_for_table["retrieval_scope"] = metrics_for_table["retrieval_scope"].astype(str).str.lower().str.strip()

    if table_retrievers is not None:
        vals = [str(x).lower().strip() for x in table_retrievers]
        metrics_for_table = metrics_for_table[metrics_for_table["retriever"].isin(vals)].copy()
    if table_rerankers is not None:
        vals = [str(x).lower().strip() for x in table_rerankers]
        metrics_for_table = metrics_for_table[metrics_for_table["reranker"].isin(vals)].copy()
    if table_readers is not None:
        vals = [str(x).strip() for x in table_readers]
        metrics_for_table = metrics_for_table[metrics_for_table["reader"].isin(vals)].copy()

    if metrics_for_table.empty:
        raise ValueError("No rows left after filtering. Check retrievers/rerankers/readers.")
    return metrics_for_table


def normalize_scope_for_table(x):
    x = str(x).lower().strip()
    if x in ["single", "single_project", "single-project", "single project"]:
        return "single"
    if x in ["cross", "cross_project", "cross_projects", "cross-project", "cross project"]:
        return "cross"
    return x


def make_main_results_table(metrics_for_table: pd.DataFrame) -> pd.DataFrame:
    required = ["retrieval_scope", "retriever", "reranker", "reader", "reader_display", "qid", "F1", "EM", "BERTScore"]
    missing = [c for c in required if c not in metrics_for_table.columns]
    if missing:
        raise ValueError(f"metrics_df is missing required columns: {missing}")
    df = metrics_for_table.copy()
    df["scope_norm"] = df["retrieval_scope"].map(normalize_scope_for_table)
    for c in ["EM", "F1", "BERTScore"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    summary = df.groupby(["retriever", "reranker", "reader", "reader_display", "scope_norm"], dropna=False).agg(questions=("qid", "nunique"), EM=("EM", "mean"), F1=("F1", "mean"), BERTScore=("BERTScore", "mean")).reset_index()
    wide = summary.pivot_table(index=["retriever", "reranker", "reader", "reader_display"], columns="scope_norm", values=["EM", "F1", "BERTScore"], aggfunc="mean").reset_index()
    wide.columns = [" ".join([str(x) for x in col if str(x) != ""]).strip() for col in wide.columns]
    main = wide.rename(columns={"EM single": "Single EM", "F1 single": "Single F1", "BERTScore single": "Single BERTScore", "EM cross": "Cross EM", "F1 cross": "Cross F1", "BERTScore cross": "Cross BERTScore"})
    expected = ["Single EM", "Single F1", "Single BERTScore", "Cross EM", "Cross F1", "Cross BERTScore"]
    for c in expected:
        if c not in main.columns:
            main[c] = np.nan
    retriever_labels = {"bm25": "BM25", "e5": "E5"}
    reranker_labels = {"none": "None", "t5": "T5"}
    main["Retriever"] = main["retriever"].map(retriever_labels).fillna(main["retriever"])
    main["Reranker"] = main["reranker"].map(reranker_labels).fillna(main["reranker"])
    main["Reader"] = main["reader_display"].fillna(main["reader"])
    final = main[["Retriever", "Reranker", "Reader"] + expected].copy()
    for c in expected:
        final[c] = pd.to_numeric(final[c], errors="coerce").round(3)
    return final


def latex_escape(text):
    if pd.isna(text):
        return ""
    text = str(text)
    for old, new in {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}.items():
        text = text.replace(old, new)
    return text


def fmt_metric(x):
    return "--" if pd.isna(x) else f"{float(x):.3f}"


def make_main_results_latex(df: pd.DataFrame) -> str:
    lines = [r"\begin{table*}[t]", r"\centering", r"\small", r"\setlength{\tabcolsep}{4.0pt}", r"\renewcommand{\arraystretch}{1.12}", r"\caption{Retrieval-augmented question answering results for each retriever, reranker, and reader model on single-project and cross-project questions.}", r"\label{tab:main_results}", r"\begin{tabular}{lllcccccc}", r"\toprule"]
    lines.append(r"\multicolumn{3}{c}{\textbf{Retriever--Reranker--Reader Configuration}} & \multicolumn{3}{c}{\textbf{Single project}} & \multicolumn{3}{c}{\textbf{Cross-project}} \\")
    lines += [r"\cmidrule(lr){1-3}", r"\cmidrule(lr){4-6}", r"\cmidrule(lr){7-9}", r"\textbf{Retriever} & \textbf{Reranker} & \textbf{Reader} & \textbf{EM} & \textbf{F1} & \textbf{BERTScore} & \textbf{EM} & \textbf{F1} & \textbf{BERTScore} \\", r"\midrule"]
    for _, row in df.iterrows():
        lines.append(latex_escape(row["Retriever"]) + " & " + latex_escape(row["Reranker"]) + " & " + latex_escape(row["Reader"]) + " & " + fmt_metric(row["Single EM"]) + " & " + fmt_metric(row["Single F1"]) + " & " + fmt_metric(row["Single BERTScore"]) + " & " + fmt_metric(row["Cross EM"]) + " & " + fmt_metric(row["Cross F1"]) + " & " + fmt_metric(row["Cross BERTScore"]) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table*}"]
    return "\n".join(lines)


def create_and_save_main_results(cfg: ExperimentConfig, table_retrievers=None, table_rerankers=None, table_readers=None):
    latest_run_dir, metrics_df, failed_df = load_latest_metrics_and_failures(cfg)
    filtered = apply_optional_filters(metrics_df, failed_df, table_retrievers, table_rerankers, table_readers)
    table = make_main_results_table(filtered)
    latex = make_main_results_latex(table)
    table.to_csv(latest_run_dir / "main_results_table.csv", index=False)
    table.to_csv(latest_run_dir / "main_results_table_final.csv", index=False)
    (latest_run_dir / "main_results_table.tex").write_text(latex, encoding="utf-8")
    (latest_run_dir / "main_results_table_final.tex").write_text(latex, encoding="utf-8")
    return latest_run_dir, table, latex
