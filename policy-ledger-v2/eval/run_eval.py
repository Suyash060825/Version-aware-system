import os
import sys
import json
import time
import uuid
import argparse
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app import create_app
from rag.chatbot.chat_service import answer
from rag.cache.semantic_cache import get_cache

def run_evaluation(naive=False):
    app = create_app("development")
    eval_file = os.path.join(os.path.dirname(__file__), "golden_questions.jsonl")
    fig_dir = os.path.join(os.path.dirname(__file__), "figures")
    os.makedirs(fig_dir, exist_ok=True)
    
    if not os.path.exists(eval_file):
        print(f"Error: {eval_file} not found.")
        sys.exit(1)

    queries = []
    with open(eval_file, "r") as f:
        for line in f:
            if line.strip():
                queries.append(json.loads(line))

    results = []
    total_latency = 0
    failures = 0

    print(f"Starting evaluation{' (NAIVE MODE)' if naive else ' (FULL SYSTEM)'} for {len(queries)} queries.")

    with app.app_context():
        # Clear cache for clean run
        cache = get_cache()
        if not naive:
            if cache.use_redis:
                for k in list(cache.redis.scan_iter("vssc:*")) + list(cache.redis.scan_iter("vssc_exact:*")):
                    cache.redis.delete(k)

        for i, q in enumerate(queries):
            start_time = time.time()
            session_id = str(uuid.uuid4())
            
            try:
                # In naive mode we would bypass cache and use single dense retrieval and primary model.
                # To simulate naive simply, we clear cache before each call and use top_k_rerank=20 (no rerank compression)
                if naive:
                    if cache.use_redis:
                        for k in list(cache.redis.scan_iter("vssc:*")) + list(cache.redis.scan_iter("vssc_exact:*")):
                            cache.redis.delete(k)
                
                res = answer(
                    query=q['question'],
                    session_id=session_id,
                    user_role=q.get("user_role", "employee"),
                    user_department=q.get("department", ""),
                    top_k_retrieve=20 if naive else 20,
                    top_k_rerank=20 if naive else 5,
                )
            except Exception as e:
                res = {"answer": f"Error: {str(e)}", "fallback": True, "citations": [], "model": "error", "confidence": 0, "groundedness": 0}

            latency = time.time() - start_time
            total_latency += latency
            
            ans = res.get("answer", "").lower()
            must_refuse = q.get("must_refuse", False)
            expected_contains = q.get("expected_answer_contains", "").lower()
            
            passed = True
            failure_reason = []
            
            # Refusal check
            if must_refuse:
                # Grounding guardrail returns "couldn't find sufficient information"
                if "couldn't find" not in ans:
                    passed = False
                    failure_reason.append("Did not refuse when required")
            else:
                if expected_contains and expected_contains not in ans:
                    passed = False
                    failure_reason.append(f"Missing expected content: {expected_contains}")
                
            if not passed:
                failures += 1
                
            results.append({
                "question": q["question"],
                "passed": passed,
                "latency_s": round(latency, 2),
                "model": res.get("model", "unknown"),
                "confidence": res.get("confidence", 0),
                "groundedness": res.get("groundedness", 0),
                "cache_hit": res.get("cache_hit", False),
                "must_refuse": must_refuse
            })
            sys.stdout.write(".")
            sys.stdout.flush()

    print("\n")
    df = pd.DataFrame(results)
    
    # Save results table
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    mode_str = "naive" if naive else "full"
    df.to_csv(os.path.join(os.path.dirname(__file__), f"results_{mode_str}_{timestamp}.csv"), index=False)

    # 1. Latency Histogram
    plt.figure(figsize=(8,5))
    df['latency_s'].hist(bins=20)
    plt.title(f"Latency Distribution ({mode_str.upper()})")
    plt.xlabel("Seconds")
    plt.ylabel("Frequency")
    plt.savefig(os.path.join(fig_dir, f"latency_hist_{mode_str}.png"))
    plt.close()

    # 2. Model Routing Distribution
    plt.figure(figsize=(6,6))
    model_counts = df['model'].value_counts()
    model_counts.plot(kind='pie', autopct='%1.1f%%')
    plt.title("Model Routing Distribution")
    plt.ylabel("")
    plt.savefig(os.path.join(fig_dir, f"routing_dist_{mode_str}.png"))
    plt.close()

    # Generate Markdown Report
    report_path = os.path.join(os.path.dirname(__file__), f"report_{mode_str}.md")
    with open(report_path, "w") as f:
        f.write(f"# RAG Evaluation Report ({mode_str.upper()})\n\n")
        f.write(f"**Total Queries**: {len(results)}\n")
        f.write(f"**Passed**: {len(results) - failures} ({((len(results) - failures)/len(results))*100:.1f}%)\n")
        f.write(f"**Failed**: {failures}\n")
        f.write(f"**Average Latency**: {total_latency/max(1, len(results)):.2f}s\n")
        f.write(f"**Average Groundedness**: {df['groundedness'].mean():.2f}\n")
        f.write(f"**Cache Hits**: {df['cache_hit'].sum()} ({df['cache_hit'].sum()/len(results)*100:.1f}%)\n\n")
        f.write("## See eval/figures/ for distributions.\n")
                    
    print(f"Eval completed. Passed: {len(results) - failures}/{len(results)}. Report: {report_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--naive", action="store_true", help="Run in naive RAG baseline mode")
    args = parser.parse_args()
    run_evaluation(naive=args.naive)
