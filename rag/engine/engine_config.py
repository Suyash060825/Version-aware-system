"""
rag/engine/engine_config.py
Configuration dataclass for QueryEngine execution and ablation experiments.
"""
from dataclasses import dataclass
from config import Config

@dataclass
class EngineConfig:
    use_fact: bool = True
    use_qa: bool = True
    use_temporal_filter: bool = True
    use_rerank: bool = True
    use_confidence_gate: bool = True
    use_cache: bool = True
    use_nli: bool = getattr(Config, "USE_NLI", True)
    use_llm: bool = True
    rerank_top_k: int = getattr(Config, "RERANK_TOP_K", 3)
    min_evidence_score: float = 2.0
