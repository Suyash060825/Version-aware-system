"""
rag/compiler/compilation_manifest.py
Structured compilation manifest recording exact build provenance, model versions, and artifact counts.
"""
import json
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, Any, Optional

@dataclass
class CompilationManifest:
    policy_id: int
    version_id: int
    document_hash: str
    compiler_version: str
    parser_version: str
    embedding_model: str
    embedding_version: str
    reranker_model: str
    chunk_count: int
    fact_count: int
    entity_count: int
    question_count: int
    validated_answer_count: int
    compiled_at: str

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "CompilationManifest":
        data = json.loads(json_str)
        return cls(**data)
