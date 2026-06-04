from __future__ import annotations

import argparse
from pathlib import Path

from .config import create_config
from .credentials import load_credentials, credential_status
from .pipeline import step_build_indexes, step_load_indexes, step_prepare_tables, step_retrieve, step_run_experiment, step_status
from .qualitative import create_qualitative_examples
from .results_table import create_and_save_main_results


def build_parser():
    p = argparse.ArgumentParser(description="ClimateFund QA modular pipeline")
    p.add_argument("--project-root", default=None, help="Project root containing code/ and dataset/. Defaults to parent if running from code/.")
    p.add_argument("--dataset-filename", default="climatefund_qa.csv")
    p.add_argument("--credentials", default=None, help="Optional credentials.env path")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("status")
    sub.add_parser("prepare")

    p_idx = sub.add_parser("indexes")
    p_idx.add_argument("--retrievers", nargs="+", default=["bm25", "e5"])
    p_idx.add_argument("--rebuild", action="store_true")

    p_ret = sub.add_parser("retrieve")
    p_ret.add_argument("--question", required=True)
    p_ret.add_argument("--retriever", default="bm25")
    p_ret.add_argument("--reranker", default="none")
    p_ret.add_argument("--scope", default="cross_projects")
    p_ret.add_argument("--source-projects", nargs="*", default=[])

    p_run = sub.add_parser("run")
    p_run.add_argument("--retrievers", nargs="+", default=["bm25"])
    p_run.add_argument("--rerankers", nargs="+", default=["none"])
    p_run.add_argument("--readers", nargs="+", default=["extractive_fallback"])
    p_run.add_argument("--max-questions", type=int, default=None)
    p_run.add_argument("--rebuild-indexes", action="store_true")
    p_run.add_argument("--no-bertscore", action="store_true")

    p_table = sub.add_parser("table")
    p_table.add_argument("--retrievers", nargs="+", default=None)
    p_table.add_argument("--rerankers", nargs="+", default=None)
    p_table.add_argument("--readers", nargs="+", default=None)

    p_q = sub.add_parser("qualitative")
    p_q.add_argument("--top-k", type=int, default=5)
    p_q.add_argument("--n", type=int, default=2)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.credentials:
        load_credentials([args.credentials])
    else:
        load_credentials()

    cfg = create_config(project_root=args.project_root, dataset_filename=args.dataset_filename)

    if args.command == "status":
        step_status(cfg)
        print("Credential status:", credential_status())
    elif args.command == "prepare":
        step_prepare_tables(cfg)
    elif args.command == "indexes":
        tables = step_prepare_tables(cfg)
        step_build_indexes(cfg, tables["passages_df"], retrievers=args.retrievers, rebuild=args.rebuild)
    elif args.command == "retrieve":
        tables = step_prepare_tables(cfg)
        indexes = step_build_indexes(cfg, tables["passages_df"], retrievers=[args.retriever], rebuild=False)
        results = step_retrieve(cfg, args.question, indexes, tables["passages_df"], retriever=args.retriever, reranker=args.reranker, scope=args.scope, source_projects=args.source_projects)
        print(results[[c for c in ["rank", "docno", "project", "score", "text"] if c in results.columns]].to_string(max_colwidth=120))
    elif args.command == "run":
        out = step_run_experiment(cfg, retrievers=args.retrievers, rerankers=args.rerankers, readers=args.readers, max_questions=args.max_questions, rebuild_indexes=args.rebuild_indexes, compute_bertscore_flag=not args.no_bertscore)
        print("Saved run to:", out["output_dir"])
    elif args.command == "table":
        out_dir, table, latex = create_and_save_main_results(cfg, args.retrievers, args.rerankers, args.readers)
        print(table.to_string(index=False))
        print("Saved table to:", out_dir)
    elif args.command == "qualitative":
        out_dir, examples = create_qualitative_examples(cfg, top_k=args.top_k, n=args.n)
        print("Saved qualitative examples to:", out_dir / "qualitative_examples")


if __name__ == "__main__":
    main()
