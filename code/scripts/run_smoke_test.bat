@echo off
python -m climatefund_qa.cli status
python -m climatefund_qa.cli prepare
python -m climatefund_qa.cli indexes --retrievers bm25 --rebuild
python -m climatefund_qa.cli run --retrievers bm25 --rerankers none --readers extractive_fallback --max-questions 3 --no-bertscore
python -m climatefund_qa.cli table
