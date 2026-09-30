import json

with open("results/final_benchmark_metrics.json") as f:
    metrics = json.load(f)

md = []
md.append("### 3. Metric Tables")
md.append("#### A. Version Selection")
md.append(f"- Overall Benchmark Metric: {metrics['version_selection']['overall']}")
md.append(f"- Numeric-Version-Only Metric: {metrics['version_selection']['numeric_only']}")

md.append("#### B. Answer Quality")
md.append(f"- Strict Exact Match: {metrics['answer_quality']['strict_exact_match']}")
md.append(f"- Token F1 Avg: {metrics['answer_quality']['token_f1_avg']:.4f}")
md.append(f"- Correct Abstentions: {metrics['answer_quality']['correct_abstentions']}")
md.append(f"- Incorrect Answers: {metrics['answer_quality']['incorrect_answers']}")
md.append(f"- Incorrect Refusals: {metrics['answer_quality']['incorrect_refusals']}")

md.append("#### C. Retrieval")
md.append("*(Not fully implemented in evaluator, assumed 0 for now pending retrieval IDs)*")

md.append("#### D. Citation Quality")
md.append("*(Pending strict citation extraction)*")

md.append("#### E. Latency Distribution")
md.append(f"- P50 Latency: {metrics['latency'].get('P50', 0):.4f}s")
md.append(f"- P95 Latency: {metrics['latency'].get('P95', 0):.4f}s")
for route, lats in metrics['latency']['route'].items():
    if lats:
        avg = sum(lats)/len(lats)
        md.append(f"- {route} Route Avg Latency: {avg:.4f}s")

md.append("#### F. Runtime Behavior")
md.append(f"- Ollama Timeouts: {metrics['runtime']['timeouts']}")
md.append(f"- Other Errors: {metrics['runtime']['other_errors']}")

md.append("### 7. Category Breakdown")
for cat, stats in metrics["categories"].items():
    md.append(f"**{cat}**")
    md.append(f"- Total: {stats['total']}")
    md.append(f"- Correct Version: {stats['correct_version']}")
    md.append(f"- Correct Answer: {stats['correct_answer']}")
    md.append(f"- Abstained: {stats['abstained']}")

with open("results/final_markdown_report.md", "w") as f:
    f.write("\n".join(md))

print("Markdown generated.")
