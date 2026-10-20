import time
import statistics
from app import create_app
from rag.qa.qa_matcher import QAMatcher
from rag.retrieval.hybrid import HybridRetriever
from rag.retrieval.sparse import PersistentBM25Index
from rag.retrieval.dense import DenseRetriever
from rag.embeddings.embedder import get_embedder
from rag.engine.query_engine import get_query_engine

def run_benchmarks():
    app = create_app("testing")
    with app.app_context():
        embedder = get_embedder()
        qa = QAMatcher()
        hybrid = HybridRetriever()
        sparse = PersistentBM25Index()
        dense = DenseRetriever()
        engine = get_query_engine()
        
        test_queries = [
            "How many days of annual leave?",
            "What is the remote work policy?",
            "What is the daily meal per diem reimbursement?",
            "What was the internet allowance in 2022?",
            "Compare version 1.0 vs version 2.0"
        ]

        print("=" * 60)
        print("VERITAS PERFORMANCE BENCHMARK & LATENCY INSTRUMENTATION")
        print("=" * 60)

        # 1. Cold Start Execution
        t_cold_start = time.perf_counter()
        _ = engine.answer(test_queries[0])
        cold_latency = (time.perf_counter() - t_cold_start) * 1000
        print(f"Cold-Start End-to-End Latency: {cold_latency:.2f} ms\n")

        # 2. Stage-level Benchmarking (20 iterations each)
        dense_times = []
        sparse_times = []
        hybrid_times = []
        qa_times = []
        e2e_warm_times = []

        for q in test_queries * 4:
            # Dense
            t0 = time.perf_counter()
            _ = dense.search(q, top_k=50)
            dense_times.append((time.perf_counter() - t0) * 1000)

            # Sparse BM25
            t0 = time.perf_counter()
            _ = sparse.get_scores(q)
            sparse_times.append((time.perf_counter() - t0) * 1000)

            # Hybrid
            t0 = time.perf_counter()
            _ = hybrid.search(q, top_k=50)
            hybrid_times.append((time.perf_counter() - t0) * 1000)

            # QA Matcher
            emb = embedder.embed_query(q)
            t0 = time.perf_counter()
            _ = qa.match(q, emb)
            qa_times.append((time.perf_counter() - t0) * 1000)

            # End-to-End Warm
            t0 = time.perf_counter()
            _ = engine.answer(q)
            e2e_warm_times.append((time.perf_counter() - t0) * 1000)

        def report_stats(name, samples):
            p50 = statistics.median(samples)
            sorted_s = sorted(samples)
            p95_idx = int(len(sorted_s) * 0.95)
            p95 = sorted_s[min(p95_idx, len(sorted_s) - 1)]
            print(f"{name:30s} | P50: {p50:6.2f} ms | P95: {p95:6.2f} ms | Min: {min(samples):6.2f} ms | Max: {max(samples):6.2f} ms")

        print("Stage-Level Latency Breakdown:")
        print("-" * 60)
        report_stats("1. Dense Retrieval (Chroma)", dense_times)
        report_stats("2. Sparse Retrieval (BM25)", sparse_times)
        report_stats("3. Hybrid Retrieval", hybrid_times)
        report_stats("4. Fast-Path QAMatcher", qa_times)
        report_stats("5. End-to-End Query (Warm)", e2e_warm_times)
        print("=" * 60)

if __name__ == "__main__":
    run_benchmarks()
