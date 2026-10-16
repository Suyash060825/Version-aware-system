"""
rag/engine/engine_config.py
Configuration dataclass for QueryEngine execution and ablation experiments.
"""
from dataclasses import dataclass

@dataclass
class EngineConfig:
    use_fact: bool = True
    use_qa: bool = True
    use_temporal_filter: bool = True
    use_rerank: bool = True
    use_confidence_gate: bool = True
    use_cache: bool = True
    use_nli: bool = False  # Disabled by default in production per audit (CPU latency blocker)
    rerank_top_k: int = 15
    min_evidence_score: float = 2.0
