"""
rag/reranker/reranker.py — compatibility re-export shim.
Delegates to the authoritative rag.retrieval.reranker.
"""
from rag.retrieval.reranker import Qwen3Reranker, FlashRankReranker, MockReranker, get_reranker

__all__ = ["Qwen3Reranker", "FlashRankReranker", "MockReranker", "get_reranker"]
