"""
rag/compiler/incremental.py
Incremental compiler diffing chunk hashes across policy versions to avoid redundant recomputations.
"""
import hashlib
from typing import List, Dict, Set, Tuple
from dataclasses import dataclass
from rag.compiler.document_ir import ChunkIR
from models import PolicyChunkV2

@dataclass
class IncrementalDiff:
    unchanged_chunks: List[ChunkIR]
    changed_chunks: List[ChunkIR]
    added_chunks: List[ChunkIR]
    deleted_chunk_ids: List[str]

class IncrementalCompiler:
    def diff_versions(self, new_chunks: List[ChunkIR], previous_version_id: int) -> IncrementalDiff:
        old_chunks = PolicyChunkV2.query.filter_by(version_id=previous_version_id).all()
        old_by_hash = {c.text_hash: c for c in old_chunks}
        old_by_id = {c.chunk_id: c for c in old_chunks}

        unchanged = []
        changed = []
        added = []
        matched_old_ids = set()

        for chunk in new_chunks:
            if chunk.text_hash in old_by_hash:
                unchanged.append(chunk)
                matched_old_ids.add(old_by_hash[chunk.text_hash].chunk_id)
            elif chunk.chunk_id in old_by_id:
                changed.append(chunk)
                matched_old_ids.add(chunk.chunk_id)
            else:
                added.append(chunk)

        deleted_ids = [cid for cid in old_by_id if cid not in matched_old_ids]

        return IncrementalDiff(
            unchanged_chunks=unchanged,
            changed_chunks=changed,
            added_chunks=added,
            deleted_chunk_ids=deleted_ids
        )

def compute_chunk_hash(text: str, model_name: str = "", model_version: str = "") -> str:
    content = f"{text.strip()}|{model_name}|{model_version}"
    return hashlib.sha256(content.encode()).hexdigest()
