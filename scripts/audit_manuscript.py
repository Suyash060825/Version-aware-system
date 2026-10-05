import json
import re
import csv

def audit():
    with open("Veritas_IEEE.log", "r") as f:
        log = f.read()

    undefined_cits = re.findall(r"Citation `([^`]+)' on page \d+ undefined", log)
    undefined_refs = re.findall(r"Reference `([^`]+)' on page \d+ undefined", log)
    latex_errors = re.findall(r"^! .*", log, re.M)

    print("=== LATEX COMPILATION AUDIT ===")
    print("Errors:", len(latex_errors))
    print("Undefined citations:", undefined_cits)
    print("Undefined references:", undefined_refs)

    with open("Veritas_IEEE.tex", "r") as f:
        tex = f.read()

    print("\n=== MARKDOWN & HTML AUDIT ===")
    print("Double asterisks (**):", tex.count("**"))
    print("Double underscores (__):", tex.count("__"))
    print("HTML entities (&#x):", tex.count("&#x"))

    print("\n=== TARGET WORDING AUDIT ===")
    wording_checks = [
        ("prior to reranking and neural context assembly", "prior to reranking and neural context assembly" in tex),
        ("NO prior to retrieval", "prior to retrieval" not in tex),
        ("comparable version-selection accuracy", "comparable version-selection accuracy" in tex),
        ("Version Resolution Rate (All Queries)", "Version Resolution Rate (All Queries)" in tex),
        ("Version Acc.\\ (Answered Queries)", "Version Acc.\\ (Answered Queries)" in tex),
        ("Cryptographic compilation eliminates unnecessary re-embedding", "Cryptographic compilation eliminates unnecessary re-embedding" in tex),
        ("100.0% authorization/scope decision correctness", r"100.0\% authorization/scope decision correctness" in tex),
        ("In this pilot set, no contradiction pair was misclassified as entailment", "In this pilot set, no contradiction pair was misclassified as entailment" in tex),
        ("indicates that most emitted citations correspond to authoritative evidence", "indicates that most emitted citations correspond to authoritative evidence" in tex)
    ]

    for label, passed in wording_checks:
        status = "PASS" if passed else "FAIL"
        print(f"[{status}] {label}")

    with open("results/eval_summary.json", "r") as f:
        local_eval = json.load(f)

    with open("results/gemini/eval_summary.json", "r") as f:
        gemini_eval = json.load(f)

    def load_accuracy_csv(path):
        data = {}
        with open(path, "r") as f:
            reader = csv.reader(f)
            header = next(reader)
            for row in reader:
                if len(row) >= 3:
                    data[row[0].strip()] = (row[1].strip(), row[2].strip())
        return data

    local_acc = load_accuracy_csv("results/answer_accuracy.csv")
    gemini_acc = load_accuracy_csv("results/gemini/answer_accuracy.csv")

    print("\n=== NUMERICAL AUDIT (Local) ===")
    print(f"Exact match: {local_acc.get('Exact / Fully Correct Answers', ('', ''))[1]}")
    print(f"Partially correct: {local_acc.get('Partially Correct Answers', ('', ''))[1]}")
    print(f"Refusal acc: {local_acc.get('Abstained Correctly (Adversarial/Security)', ('', ''))[1]}")
    print(f"Token F1: {local_acc.get('Mean Token F1 Score', ('', ''))[1]}")
    print(f"Citation precision: {local_acc.get('Citation Precision', ('', ''))[1]}")
    print(f"Citation recall: {local_acc.get('Citation Recall', ('', ''))[1]}")
    print(f"Citation F1: {local_acc.get('Citation F1', ('', ''))[1]}")
    print(f"Latency P50: {local_eval['metrics']['latency_p50_ms']} ms")
    print(f"Latency P95: {local_eval['metrics']['latency_p95_ms']} ms")

    print("\n=== NUMERICAL AUDIT (Gemini) ===")
    print(f"Exact match: {gemini_acc.get('Exact / Fully Correct Answers', ('', ''))[1]}")
    print(f"Partially correct: {gemini_acc.get('Partially Correct Answers', ('', ''))[1]}")
    print(f"Refusal acc: {gemini_acc.get('Abstained Correctly (Adversarial/Security)', ('', ''))[1]}")
    print(f"Token F1: {gemini_acc.get('Mean Token F1 Score', ('', ''))[1]}")
    print(f"Citation precision: {gemini_acc.get('Citation Precision', ('', ''))[1]}")
    print(f"Citation recall: {gemini_acc.get('Citation Recall', ('', ''))[1]}")
    print(f"Citation F1: {gemini_acc.get('Citation F1', ('', ''))[1]}")
    print(f"Latency P50: {gemini_eval['metrics']['latency_p50_ms']} ms")
    print(f"Latency P95: {gemini_eval['metrics']['latency_p95_ms']} ms")

if __name__ == "__main__":
    audit()
