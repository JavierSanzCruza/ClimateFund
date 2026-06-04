from __future__ import annotations

import os
from typing import Dict, Any

import pandas as pd


def build_context(contexts: pd.DataFrame, final_context_k: int = 5) -> str:
    blocks = []
    if contexts is None:
        return ""
    for i, (_, row) in enumerate(contexts.head(final_context_k).iterrows(), start=1):
        text = str(row.get("text", ""))
        docno = str(row.get("docno", ""))
        project = str(row.get("project", ""))
        blocks.append(f"[Context {i}] docno={docno} project={project}\n{text}")
    return "\n\n".join(blocks)


class ExtractiveFallbackReader:
    """Offline reader for smoke tests. Returns the first retrieved passage snippet."""
    reader_id = "extractive_fallback"
    reader_display = "Extractive fallback"

    def __init__(self, final_context_k: int = 5):
        self.final_context_k = final_context_k

    def answer(self, question: str, contexts: pd.DataFrame) -> str:
        if contexts is None or len(contexts) == 0:
            return "Not enough information."
        text = str(contexts.iloc[0].get("text", "")).strip()
        if not text:
            return "Not enough information."
        return text[:900]


class OpenAICompatibleReader:
    def __init__(self, reader_id: str, model_name: str, api_key_env: str, base_url: str | None = None, reader_display: str | None = None, final_context_k: int = 5):
        from openai import OpenAI
        self.reader_id = reader_id
        self.model_name = model_name
        self.reader_display = reader_display or model_name
        self.final_context_k = final_context_k
        api_key = os.environ.get(api_key_env)
        if not api_key:
            raise ValueError(f"Missing API key environment variable: {api_key_env}")
        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self.client = OpenAI(**kwargs)

    def answer(self, question: str, contexts: pd.DataFrame) -> str:
        context = build_context(contexts, self.final_context_k)
        prompt = f"""Answer the question using only the evidence below.
If the answer is not supported by the evidence, say: Not enough information.

Evidence:
{context}

Question: {question}
Answer:"""
        resp = self.client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        return resp.choices[0].message.content.strip()


class HuggingFaceTransformersReader:
    def __init__(self, reader_id: str, model_name: str, api_key_env: str = "HF_TOKEN", reader_display: str | None = None, final_context_k: int = 5):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        self.reader_id = reader_id
        self.model_name = model_name
        self.reader_display = reader_display or model_name
        self.final_context_k = final_context_k
        hf_token = os.environ.get(api_key_env)
        if not hf_token:
            raise ValueError(f"Missing Hugging Face token: {api_key_env}")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name, token=hf_token)
        self.model = AutoModelForCausalLM.from_pretrained(model_name, token=hf_token, torch_dtype=torch.bfloat16, device_map="auto")

    def answer(self, question: str, contexts: pd.DataFrame) -> str:
        context = build_context(contexts, self.final_context_k)
        prompt = f"""Answer the question using only the evidence below.
If the answer is not supported by the evidence, say: Not enough information.

Evidence:
{context}

Question: {question}
Answer:"""
        inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=4096).to(self.model.device)
        output = self.model.generate(**inputs, max_new_tokens=256, do_sample=False)
        text = self.tokenizer.decode(output[0], skip_special_tokens=True)
        return text[len(prompt):].strip() if text.startswith(prompt) else text.strip()


READER_CONFIGS: Dict[str, Dict[str, Any]] = {
    "extractive_fallback": {"type": "fallback", "display": "Extractive fallback"},
    "openai_gpt_4o_mini": {"type": "openai", "model": "gpt-4o-mini", "api_key_env": "OPENAI_API_KEY", "display": "OpenAI GPT-4o mini"},
    "openai_gpt_4_1_mini": {"type": "openai", "model": "gpt-4.1-mini", "api_key_env": "OPENAI_API_KEY", "display": "OpenAI GPT-4.1 mini"},
    "gpt-5.4-mini-2026-03-17": {"type": "openai", "model": "gpt-5.4-mini-2026-03-17", "api_key_env": "OPENAI_API_KEY", "display": "OpenAI GPT-5.4 mini"},
    "ida_qwen_2_5_72b": {"type": "ida", "model": "qwen2.5-72b-instruct", "api_key_env": "IDA_LLM_API_KEY", "display": "Qwen 2.5 72B Instruct"},
    "ida_qwen_2_5_7b": {"type": "ida", "model": "qwen2.5-7b-instruct", "api_key_env": "IDA_LLM_API_KEY", "display": "Qwen 2.5 7B Instruct"},
    "llama-3.3-70b-instruct": {"type": "ida", "model": "llama-3.3-70b-instruct", "api_key_env": "IDA_LLM_API_KEY", "display": "Llama 3.3 70B Instruct"},
    "hf_mistral_7b_instruct_v03": {"type": "hf", "model": "mistralai/Mistral-7B-Instruct-v0.3", "api_key_env": "HF_TOKEN", "display": "Mistral 7B Instruct v0.3"},
}


def get_reader(reader_id: str, final_context_k: int = 5):
    reader_id = str(reader_id).strip()
    cfg = READER_CONFIGS.get(reader_id)
    if cfg is None:
        raise ValueError(f"Unknown reader: {reader_id}. Available: {sorted(READER_CONFIGS)}")
    if cfg["type"] == "fallback":
        return ExtractiveFallbackReader(final_context_k=final_context_k)
    if cfg["type"] == "openai":
        return OpenAICompatibleReader(reader_id, cfg["model"], cfg["api_key_env"], None, cfg["display"], final_context_k)
    if cfg["type"] == "ida":
        base_url = os.environ.get("IDA_LLM_BASE_URL", "http://api.terrier.org/v1")
        return OpenAICompatibleReader(reader_id, cfg["model"], cfg["api_key_env"], base_url, cfg["display"], final_context_k)
    if cfg["type"] == "hf":
        return HuggingFaceTransformersReader(reader_id, cfg["model"], cfg["api_key_env"], cfg["display"], final_context_k)
    raise ValueError(f"Unsupported reader type: {cfg['type']}")


def reader_display_name(reader_id: str) -> str:
    return READER_CONFIGS.get(reader_id, {}).get("display", reader_id)
