import os
import sys
import json
import time
import uuid
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app import create_app
from rag.engine.query_engine import get_query_engine

def run_eval():
    app = create_app("development")
    
    benchmark_file = "data/benchmarks/benchmark_test.json"
    if not os.path.exists(benchmark_file):
        benchmark_file = "data/eval_benchmark.json"
        
    if not os.path.exists(benchmark_file):
        print(f"{benchmark_file} not found. Running reproducible evaluation...")
        import subprocess
        subprocess.run([sys.executable, "scripts/run_reproducible_eval.py"])
        return
        
    with open(benchmark_file, "r") as f:
        queries = json.load(f)
        
    results = []
    total_latency = 0
    total_cost = 0
    EST_COST_PER_1K_TOKENS = 0.004
    
    with app.app_context():
        engine = get_query_engine()
        for q in queries:
            q_text = q.get("query") or q.get("query_text")
            print(f"Evaluating: {q_text}")
            start_time = time.time()
            session_id = str(uuid.uuid4())
            try:
                res = engine.answer(
                    query=q_text,
                    session_id=session_id
                )
                answer_text = res.answer
                model_name = res.model or "qwen3"
                is_fallback = res.abstained
                route = res.route
            except Exception as e:
                answer_text = f"Error: {str(e)}"
                model_name = "error"
                is_fallback = True
                route = "ERROR"
                
            latency = time.time() - start_time
            total_latency += latency
            cost = 0.0 if not getattr(res, "llm_used", False) else 0.0008
            total_cost += cost
            
            results.append({
                "id": q.get("id"),
                "query": q_text,
                "answer": answer_text,
                "model": model_name,
                "route": route,
                "latency_ms": round(latency * 1000, 2),
                "cost_usd": cost,
                "fallback": is_fallback
            })
            
    with open("results/eval_results.json", "w") as f:
        json.dump(results, f, indent=2)
        
    print("\n--- Evaluation Summary ---")
    print(f"Total Queries: {len(results)}")
    print(f"Average Latency: {total_latency/max(len(results), 1):.4f}s ({(total_latency*1000)/max(len(results), 1):.2f}ms)")
    print(f"Total Cost: ${total_cost:.4f}")

if __name__ == "__main__":
    run_eval()
