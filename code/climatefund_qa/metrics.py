from __future__ import annotations

import re
from collections import Counter
from typing import Dict, List

import numpy as np
import pandas as pd

ANSWER_NOT_ENOUGH_TEXT = "Not enough information."
BERTSCORE_RESCALE_WITH_BASELINE = True


def normalize_answer_text(x: str) -> str:
    if x is None:
        return ""
    try:
        if pd.isna(x):
            return ""
    except Exception:
        pass
    x = str(x).lower()
    x = re.sub(r"[^a-z0-9\s]", " ", x)
    x = re.sub(r"\s+", " ", x).strip()
    return x


def exact_match(prediction: str, gold: str) -> float:
    return float(normalize_answer_text(prediction) == normalize_answer_text(gold))


def token_f1(prediction: str, gold: str) -> float:
    pred_tokens = normalize_answer_text(prediction).split()
    gold_tokens = normalize_answer_text(gold).split()
    if not pred_tokens and not gold_tokens:
        return 1.0
    if not pred_tokens or not gold_tokens:
        return 0.0
    common = Counter(pred_tokens) & Counter(gold_tokens)
    num_same = sum(common.values())
    if num_same == 0:
        return 0.0
    precision = num_same / len(pred_tokens)
    recall = num_same / len(gold_tokens)
    return 2 * precision * recall / (precision + recall)


def answer_issue_flags(answer: str) -> Dict[str, bool]:
    a = "" if answer is None else str(answer).strip()
    low = a.lower()
    return {
        "is_empty": len(a) == 0,
        "is_not_enough_information": ANSWER_NOT_ENOUGH_TEXT.lower() in low,
        "is_very_short": len(a.split()) < 5,
    }


def compute_bertscore(predictions: List[str], references: List[str], enabled: bool = True) -> List[float]:
    if not enabled:
        return [float("nan")] * len(predictions)
    try:
        from bert_score import score as bert_score_fn
        _, _, f1 = bert_score_fn(predictions, references, lang="en", rescale_with_baseline=BERTSCORE_RESCALE_WITH_BASELINE)
        return [float(x) for x in f1.detach().cpu().numpy().tolist()]
    except Exception as e:
        print("BERTScore unavailable/failed; using NaN. Error:", e)
        return [float("nan")] * len(predictions)


def evaluate_predictions(predictions_df: pd.DataFrame, compute_bertscore_flag: bool = True) -> pd.DataFrame:
    rows = []
    preds = predictions_df["generated_answer"].fillna("").astype(str).tolist()
    refs = predictions_df["gold_answer"].fillna("").astype(str).tolist()
    bert_scores = compute_bertscore(preds, refs, enabled=compute_bertscore_flag)
    for i, row in predictions_df.reset_index(drop=True).iterrows():
        pred = str(row.get("generated_answer", ""))
        gold = str(row.get("gold_answer", ""))
        flags = answer_issue_flags(pred)
        rows.append({
            "run_name": row.get("run_name", ""),
            "qid": row.get("qid", ""),
            "retrieval_scope": row.get("retrieval_scope", row.get("scope", "")),
            "retriever": row.get("retriever", ""),
            "reranker": row.get("reranker", ""),
            "reader": row.get("reader", ""),
            "reader_display": row.get("reader_display", ""),
            "EM": exact_match(pred, gold),
            "F1": token_f1(pred, gold),
            "BERTScore": bert_scores[i],
            **flags,
        })
    return pd.DataFrame(rows)
