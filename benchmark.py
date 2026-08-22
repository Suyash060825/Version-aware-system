import time
from app import create_app
from models import db
from rag.qa.qa_matcher import QAMatcher
from rag.retrieval.hybrid import HybridRetriever
from rag.embeddings.embedder import get_embedder

def run_benchmarks():
    app = create_app("development")
    with app.app_context():
        embedder = get_embedder()
        
        qa = QAMatcher()
        hybrid = HybridRetriever()
        
        query = "How many days of annual leave?"
        emb = embedder.embed_query(query)
        
        # Warmup
        qa.match(query, emb)
        hybrid.search(query, top_k=50)
        
        # Benchmark QA
        t0 = time.perf_counter()
        qa_match = qa.match(query, emb)
        t1 = time.perf_counter()
        print(f"QAMatcher latency: {(t1-t0)*1000:.2f} ms")
        
        # Benchmark Hybrid
        t0 = time.perf_counter()
        candidates = hybrid.search(query, top_k=50)
        t1 = time.perf_counter()
        print(f"HybridRetriever latency: {(t1-t0)*1000:.2f} ms")

if __name__ == "__main__":
    run_benchmarks()
