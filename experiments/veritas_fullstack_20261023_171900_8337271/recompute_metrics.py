# Independent Metric Recomputation Script for veritas_fullstack_20261023_171900_8337271
import json, numpy as np

with open("query_results.jsonl") as f:
    records = [json.loads(line) for line in f if line.strip()]

total = len(records)
correct = sum(1 for r in records if r["answer_correctness"])
f1s = [r["token_f1"] for r in records]
latencies = [r["latency_ms"] for r in records]
llm_invoked = sum(1 for r in records if r["llm_used"])
llm_eligible = sum(1 for r in records if r["llm_eligible"])

print(f"Total Queries: {total}")
print(f"Accuracy: {correct / total * 100:.2f}% ({correct}/{total})")
print(f"Mean Token F1: {np.mean(f1s):.4f}")
print(f"P50 Latency: {np.percentile(latencies, 50):.2f} ms")
print(f"P95 Latency: {np.percentile(latencies, 95):.2f} ms")
print(f"LLM Invocations: {llm_invoked}/{llm_eligible} ({llm_invoked / llm_eligible * 100 if llm_eligible else 0:.1f}%)")
