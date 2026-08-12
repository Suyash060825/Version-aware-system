import os
import sys
import json
import time
import uuid

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app import create_app
from rag.chatbot.chat_service import answer

def run_evaluation():
    app = create_app("development")
    eval_file = os.path.join(os.path.dirname(__file__), "golden_questions.jsonl")
    
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

    with app.app_context():
        for i, q in enumerate(queries):
            print(f"Evaluating [{i+1}/{len(queries)}]: {q['question']}")
            start_time = time.time()
            session_id = str(uuid.uuid4())
            
            try:
                res = answer(
                    query=q['question'],
                    session_id=session_id,
                    user_role=q.get("user_role", "employee"),
                    user_department=q.get("department", "")
                )
            except Exception as e:
                res = {"answer": f"Error: {str(e)}", "fallback": True, "citations": []}

            latency = time.time() - start_time
            total_latency += latency
            
            ans = res.get("answer", "").lower()
            must_refuse = q.get("must_refuse", False)
            expected_contains = q.get("expected_answer_contains", "").lower()
            
            passed = True
            failure_reason = []
            
            if must_refuse:
                if "couldn't find this information" not in ans:
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
                "answer": ans,
                "passed": passed,
                "failure_reason": failure_reason,
                "latency_s": round(latency, 2),
                "model": res.get("model", "unknown")
            })

    report_path = os.path.join(os.path.dirname(__file__), "report.md")
    with open(report_path, "w") as f:
        f.write("# RAG Evaluation Report\n\n")
        f.write(f"**Total Queries**: {len(results)}\n")
        f.write(f"**Passed**: {len(results) - failures}\n")
        f.write(f"**Failed**: {failures}\n")
        f.write(f"**Average Latency**: {total_latency/max(1, len(results)):.2f}s\n\n")
        
        f.write("## Failures\n")
        if failures == 0:
            f.write("None! 🎉\n")
        else:
            for r in results:
                if not r["passed"]:
                    f.write(f"- **Q**: {r['question']}\n")
                    f.write(f"  - **A**: {r['answer']}\n")
                    f.write(f"  - **Reasons**: {', '.join(r['failure_reason'])}\n")
                    
    print(f"\nEval completed. Passed: {len(results) - failures}/{len(results)}. Report written to {report_path}")
    
    if failures > 0:
        print("Build failed due to evaluation failures.")
        sys.exit(1)

if __name__ == "__main__":
    run_evaluation()
