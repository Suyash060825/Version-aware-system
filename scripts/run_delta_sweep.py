"""
scripts/run_delta_sweep.py
E1: Multi-delta incremental compiler sweep.
Tests the incremental knowledge compiler at δ = 0, 1, 10%, 30%, 50%
modification rates against a full FAISS QA index + BM25 rebuild baseline.
Reports time, re-indexed chunks, speedup vs. full rebuild at each delta level.
"""
import os
import sys
import csv
import time
import hashlib
import numpy as np

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app import create_app
from models import PolicyChunkV2
from rag.compiler.incremental import IncrementalCompiler
from rag.compiler.document_ir import ChunkIR
from rag.retrieval.sparse import PersistentBM25Index
from rag.engine.query_engine import get_query_engine


def make_chunk_ir(c, modified=False, suffix=""):
    text = c.text + (f" [DELTA_MOD_{suffix}]" if modified else "")
    # Use the same hash format as structure_extractor.py: sha256 of raw text bytes
    h = hashlib.sha256(text.encode()).hexdigest()
    return ChunkIR(
        chunk_id=c.chunk_id,
        policy_id=c.policy_id,
        version_id=c.version_id,
        section_path=c.section_path or "General",
        text=text,
        page=c.page or 1,
        paragraph_num=c.paragraph_num or 1,
        text_hash=h,
        char_count=len(text)
    )


def run_delta_sweep():
    app = create_app("development")
    os.makedirs("results", exist_ok=True)

    with app.app_context():
        engine = get_query_engine()
        sparse = PersistentBM25Index()
        sparse.rebuild_from_db()
        qa_index = engine.qa_matcher.index

        # Use Policy 1 (Remote Work Policy), version 1 as the delta reference
        p1_chunks = PolicyChunkV2.query.filter_by(policy_id=1, version_id=1).all()
        N_policy = len(p1_chunks)
        N_total = PolicyChunkV2.query.count()
        print(f"[Delta Sweep] Full corpus: {N_total} chunks total | Policy 1, v1: {N_policy} chunks")

        # Measure FULL CORPUS rebuild baseline: FAISS QA index + BM25 (3 runs, take median)
        rebuild_times = []
        for _ in range(3):
            t0 = time.time()
            qa_index.rebuild_from_db()
            sparse.rebuild_from_db()
            rebuild_times.append((time.time() - t0) * 1000)
        full_rebuild_ms = float(np.median(rebuild_times))
        print(f"[Delta Sweep] Full corpus rebuild baseline (FAISS QA + BM25, {N_total} chunks, median of 3): {full_rebuild_ms:.2f} ms")

        # Delta levels: (label, num_modified_chunks)
        delta_levels = [
            ("0 chunks (0.0% / Hash No-Op)", 0),
            ("1 chunk (16.67% of policy)", 1),
            ("3 chunks (50.00% of policy)", 3),
        ]

        rows = []
        inc_compiler = IncrementalCompiler()

        for label, n_modified in delta_levels:
            # Build new chunk set: modify first n_modified of p1_chunks, keep rest unchanged
            new_chunk_irs = []
            for i, c in enumerate(p1_chunks):
                new_chunk_irs.append(make_chunk_ir(c, modified=(i < n_modified), suffix=str(i)))

            # Run incremental diff 3 times, take median
            inc_times = []
            for _ in range(3):
                t0 = time.time()
                diff_res = inc_compiler.diff_versions(new_chunk_irs, previous_version_id=1)
                changed_data = [
                    {"chunk_id": c.chunk_id, "text": c.text, "section": c.section_path, "page": c.page}
                    for c in diff_res.changed_chunks + diff_res.added_chunks
                ]
                if changed_data:
                    sparse.update_policy_version(1, 1, changed_data)
                inc_times.append((time.time() - t0) * 1000)

            inc_ms = float(np.median(inc_times))
            speedup = full_rebuild_ms / max(0.1, inc_ms)
            re_indexed = len(diff_res.changed_chunks) + len(diff_res.added_chunks)
            unchanged = len(diff_res.unchanged_chunks)

            rows.append([
                label,
                n_modified,
                round(inc_ms, 2),
                round(full_rebuild_ms, 2),
                re_indexed,
                unchanged,
                round(speedup, 2),
            ])
            print(f"  δ={label}: inc={inc_ms:.2f}ms, speedup={speedup:.1f}×, re-indexed={re_indexed}, unchanged={unchanged}")

        with open("results/incremental_delta_sweep.csv", "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Delta Level", "Modified Chunks (|Δ|)",
                "Incremental Time (ms)", "Full Rebuild Time (ms)",
                "Re-Indexed Chunks", "Unchanged Chunks", "Speedup (×)"
            ])
            for r in rows:
                writer.writerow(r)

        print(f"\n[Delta Sweep] Results saved → results/incremental_delta_sweep.csv")
        return rows


if __name__ == "__main__":
    run_delta_sweep()
