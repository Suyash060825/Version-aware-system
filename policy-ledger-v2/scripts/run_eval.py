import os
import sys
import json
import time
import uuid
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app import create_app
from rag.chatbot.chat_service import answer

def run_eval():
    app = create_app("development")
    
    benchmark_file = "data/eval_benchmark.json"
    if not os.path.exists(benchmark_file):
        print(f"{benchmark_file} not found. Please run build_eval_benchmark.py first.")
        return
        
    with open(benchmark_file, "r") as f:
        queries = json.load(f)
        
    results = []
    total_latency = 0
    total_cost = 0
    EST_COST_PER_1K_TOKENS = 0.004
    
    with app.app_context():
        for q in queries:
            print(f"Evaluating: {q['query_text']}")
            start_time = time.time()
            session_id = str(uuid.uuid4())
            try:
                res = answer(
                    query=q['query_text'],
                    session_id=session_id,
                    user_role="Admin",
                    user_department=""
                )
            except Exception as e:
                res = {"answer": f"Error: {str(e)}", "usage": {}, "model": "error", "fallback": True}
                
            latency = time.time() - start_time
            total_latency += latency
            
            usage = res.get("usage", {})
            tokens = usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0)
            cost = (tokens / 1000) * EST_COST_PER_1K_TOKENS
            total_cost += cost
            
            results.append({
                "id": q["id"],
                "query": q["query_text"],
                "answer": res["answer"],
                "model": res.get("model", "unknown"),
                "latency_s": round(latency, 2),
                "cost_usd": cost,
                "fallback": res.get("fallback", False)
            })
            
    with open("data/eval_results.json", "w") as f:
        json.dump(results, f, indent=2)
        
    print("\n--- Evaluation Summary ---")
    print(f"Total Queries: {len(results)}")
    print(f"Average Latency: {total_latency/max(len(results), 1):.2f}s")
    print(f"Total Cost: ${total_cost:.4f}")

if __name__ == "__main__":
    run_eval()
