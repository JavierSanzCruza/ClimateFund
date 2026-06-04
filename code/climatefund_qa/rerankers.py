from __future__ import annotations

import numpy as np
import pandas as pd


class NoReranker:
    name = "none"

    def rerank(self, results: pd.DataFrame, query: str, top_k: int) -> pd.DataFrame:
        out = results.copy() if results is not None else pd.DataFrame()
        if len(out) == 0:
            return out
        out["reranker"] = self.name
        out["rerank_score"] = out["score"] if "score" in out.columns else 0.0
        out = out.sort_values("rerank_score", ascending=False).head(top_k).reset_index(drop=True)
        out["rank"] = np.arange(1, len(out) + 1)
        return out


class MonoT5Reranker:
    name = "t5"

    def __init__(self, model_name: str = "castorini/monot5-base-msmarco", batch_size: int = 2, rerank_input_k: int = 20):
        self.rerank_input_k = rerank_input_k
        from pyterrier_t5 import MonoT5ReRanker
        try:
            self.model = MonoT5ReRanker(model=model_name, batch_size=batch_size)
        except TypeError:
            self.model = MonoT5ReRanker()

    def rerank(self, results: pd.DataFrame, query: str, top_k: int) -> pd.DataFrame:
        if results is None or len(results) == 0:
            return pd.DataFrame()
        inp = results.copy().head(self.rerank_input_k)
        inp["query"] = query
        if "qid" not in inp.columns:
            inp["qid"] = "q0"
        try:
            out = self.model.transform(inp)
        except Exception as e:
            print("MonoT5 failed; returning original ranking. Error:", e)
            return NoReranker().rerank(results, query, top_k)
        out["reranker"] = self.name
        if "score" in out.columns:
            out["rerank_score"] = out["score"]
        out = out.sort_values("rerank_score", ascending=False).head(top_k).reset_index(drop=True)
        out["rank"] = np.arange(1, len(out) + 1)
        return out


def get_reranker(name: str, rerank_input_k: int = 20):
    name = str(name).lower().strip()
    if name in ["none", "no", "no_reranker"]:
        return NoReranker()
    if name in ["t5", "monot5", "mono_t5"]:
        return MonoT5Reranker(rerank_input_k=rerank_input_k)
    raise ValueError(f"Unknown reranker: {name}")
