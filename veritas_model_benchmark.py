#!/usr/bin/env python3
"""
Veritas local Ollama model benchmark.
Measures API latency, generation tokens/sec, and a transparent keyword-based
answer score. The keyword score is a screening proxy, NOT a publication-grade
semantic accuracy metric. Review outputs manually before making research claims.
"""
import csv
import json
import time
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODELS = [
    "qwen2.5:3b",
    "llama3.2:3b",
    "qwen3:1.7b-q4_K_M",
    "phi4-mini:3.8b-q4_K_M",
    "qwen3:4b-q4_K_M",
]

# Synthetic policy evidence: all models receive exactly the same evidence.
POLICY = """
ACME ANNUAL LEAVE POLICY — Version 3.0
1. Eligible full-time employees receive 20 days of annual leave per calendar year.
2. Employees may carry over at most 5 unused annual-leave days into the next year.
3. Annual leave requests must be submitted at least 7 calendar days before the first day of leave.
4. A manager must approve or reject a request within 3 business days after submission.
5. Contractors are not eligible for annual leave under this policy.
6. This policy does not specify sick-leave entitlement.
7. Version 3.0 became effective on 1 January 2026 and supersedes Version 2.0.
"""

# Each case has required concepts. A simple proxy checks whether each concept
# appears in the answer (or a listed alternative). This cannot reliably judge
# nuanced correctness, so inspect the saved answers as well.
CASES = [
    {
        "id": "Q1", "question": "How many annual-leave days does an eligible full-time employee receive per calendar year?",
        "required": [["20"], ["days", "day"], ["annual leave", "annual-leave"]],
        "type": "answer",
    },
    {
        "id": "Q2", "question": "What is the maximum number of unused annual-leave days that can be carried over?",
        "required": [["5"], ["days", "day"], ["carry", "carried over", "carry over"]],
        "type": "answer",
    },
    {
        "id": "Q3", "question": "How far in advance must an employee submit an annual-leave request?",
        "required": [["7"], ["calendar days", "days"]],
        "type": "answer",
    },
    {
        "id": "Q4", "question": "How long does a manager have to approve or reject a leave request?",
        "required": [["3"], ["business days"]],
        "type": "answer",
    },
    {
        "id": "Q5", "question": "Are contractors eligible for annual leave under this policy?",
        "required": [["no", "not eligible", "ineligible"], ["contractor"]],
        "type": "answer",
    },
    {
        "id": "Q6", "question": "What is the effective date of Version 3.0?",
        "required": [["1 january 2026", "january 1, 2026", "2026-01-01"]],
        "type": "answer",
    },
    {
        "id": "Q7", "question": "Does this policy state how many sick-leave days employees receive? Answer only from the supplied evidence.",
        "required": [["not specify", "does not specify", "not stated", "doesn't specify", "insufficient information"]],
        "type": "abstain",
    },
    {
        "id": "Q8", "question": "A contractor requests 20 annual-leave days. According to this policy, are they eligible? Briefly explain.",
        "required": [["no", "not eligible", "ineligible"], ["contractor"]],
        "type": "answer",
    },
]

SYSTEM_INSTRUCTIONS = """
You are Veritas, an enterprise policy assistant. Answer only from the policy evidence.
Do not invent rules. If the policy does not contain the requested information, say so.
Keep the answer concise and cite the relevant numbered policy clause(s), for example [Clause 2].
"""

def call_ollama(model, prompt, num_predict=120):
    body = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "think": False,
        "keep_alive": "10m",
        "options": {"temperature": 0, "num_predict": num_predict},
    }
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        OLLAMA_URL, data=data, headers={"Content-Type": "application/json"}
    )
    start = time.perf_counter()
    with urllib.request.urlopen(req, timeout=600) as response:
        result = json.loads(response.read().decode("utf-8"))
    wall = time.perf_counter() - start
    eval_count = result.get("eval_count", 0) or 0
    eval_duration = result.get("eval_duration", 0) or 0  # nanoseconds
    tok_s = (eval_count / (eval_duration / 1e9)) if eval_duration else 0.0
    return result.get("response", "").strip(), wall, tok_s, eval_count, result

def keyword_score(answer, required_groups):
    text = answer.lower()
    matched = sum(1 for group in required_groups if any(term in text for term in group))
    return matched / max(len(required_groups), 1)

def main():
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_csv = Path(f"veritas_model_benchmark_{stamp}.csv")
    out_json = Path(f"veritas_model_benchmark_{stamp}.json")
    rows = []
    summary = []

    print("Veritas Ollama benchmark")
    print(f"Models: {len(MODELS)} | Questions/model: {len(CASES)}")
    print("A warm-up request is sent to each model before its scored questions.")
    print("Keep this terminal open; first-time model loading may take a while.\n")

    for model in MODELS:
        print(f"\n=== {model} ===")
        try:
            # Warm-up, excluded from scores (model-load cost is not the main measure).
            call_ollama(
                model,
                f"{SYSTEM_INSTRUCTIONS}\n\nEvidence:\n{POLICY}\n\nQuestion: In one sentence, state the carry-over limit.",
                num_predict=48,
            )
        except (urllib.error.URLError, TimeoutError, Exception) as e:
            print(f"ERROR: could not run model: {e}")
            rows.append({
                "model": model, "question_id": "ERROR", "question": "",
                "latency_seconds": "", "tokens_per_second": "", "eval_tokens": "",
                "proxy_score": "", "answer": f"ERROR: {e}",
            })
            continue

        latencies = []
        speeds = []
        scores = []
        for case in CASES:
            prompt = (
                f"{SYSTEM_INSTRUCTIONS}\n\n"
                f"POLICY EVIDENCE:\n{POLICY}\n\n"
                f"QUESTION ({case['id']}): {case['question']}\n"
                "Give a concise answer and cite the clause number(s)."
            )
            try:
                answer, latency, tok_s, eval_count, raw = call_ollama(model, prompt)
                score = keyword_score(answer, case["required"])
                latencies.append(latency)
                if tok_s:
                    speeds.append(tok_s)
                scores.append(score)
                row = {
                    "model": model,
                    "question_id": case["id"],
                    "question": case["question"],
                    "case_type": case["type"],
                    "latency_seconds": round(latency, 3),
                    "tokens_per_second": round(tok_s, 2),
                    "eval_tokens": eval_count,
                    "proxy_score": round(score, 3),
                    "answer": answer,
                    "prompt_eval_ms": round((raw.get("prompt_eval_duration", 0) or 0) / 1e6, 2),
                    "generation_ms": round((raw.get("eval_duration", 0) or 0) / 1e6, 2),
                    "load_ms": round((raw.get("load_duration", 0) or 0) / 1e6, 2),
                }
                rows.append(row)
                print(f"{case['id']} | {latency:6.2f}s | {tok_s:5.1f} tok/s | proxy {score:.0%}")
                print(f"   {answer[:220].replace(chr(10), ' ')}")
            except Exception as e:
                print(f"{case['id']} ERROR: {e}")
                rows.append({
                    "model": model, "question_id": case["id"], "question": case["question"],
                    "latency_seconds": "", "tokens_per_second": "", "eval_tokens": "",
                    "proxy_score": "", "answer": f"ERROR: {e}",
                })

        summary.append({
            "model": model,
            "questions_completed": len(scores),
            "mean_latency_seconds": round(sum(latencies) / len(latencies), 3) if latencies else None,
            "mean_tokens_per_second": round(sum(speeds) / len(speeds), 2) if speeds else None,
            "mean_keyword_proxy_score": round(sum(scores) / len(scores), 3) if scores else None,
        })

    # CSV includes individual model answers for manual inspection.
    fields = sorted({key for row in rows for key in row.keys()})
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    out_json.write_text(json.dumps({"summary": summary, "results": rows}, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\n\n=== SUMMARY (lower latency is better; higher proxy score is better) ===")
    print(f"{'MODEL':32} {'AVG SEC':>8} {'TOK/S':>8} {'PROXY':>8}")
    for item in sorted(summary, key=lambda x: x["mean_latency_seconds"] if x["mean_latency_seconds"] is not None else 999999):
        print(f"{item['model']:32} {str(item['mean_latency_seconds']):>8} {str(item['mean_tokens_per_second']):>8} {str(item['mean_keyword_proxy_score']):>8}")
    print(f"\nSaved detailed CSV:  {out_csv.resolve()}")
    print(f"Saved full JSON:     {out_json.resolve()}")
    print("\nNOTE: The keyword proxy is only a quick screening signal. Manually review answers")
    print("and score correctness, citations, version handling, and abstention before using")
    print("any results in a paper. This test uses synthetic evidence, not your full Veritas suite.")

if __name__ == "__main__":
    main()