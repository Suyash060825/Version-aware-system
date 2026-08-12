import os
import sys
import json
import random
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app import create_app
from models import SearchHistory

def build_benchmark():
    app = create_app("development")
    with app.app_context():
        queries = SearchHistory.query.all()
        # Mix of answered, unanswered, and diff keywords
        answered = [q for q in queries if q.answered]
        unanswered = [q for q in queries if not q.answered]
        diff_keywords = ["changed", "used to", "previous version", "difference between", "compare", "diff"]
        diff_queries = [q for q in queries if any(k in (q.query_text or "").lower() for k in diff_keywords)]
        
        selected = set()
        for q in random.sample(diff_queries, min(10, len(diff_queries))): selected.add(q)
        for q in random.sample(unanswered, min(15, len(unanswered))): selected.add(q)
        for q in random.sample(answered, min(25, len(answered))): selected.add(q)
        
        remaining = list(set(queries) - selected)
        while len(selected) < 50 and remaining:
            c = random.choice(remaining)
            selected.add(c)
            remaining.remove(c)
                
        out = [{"id": q.id, "query_text": q.query_text} for q in list(selected)[:50]]
        os.makedirs("data", exist_ok=True)
        with open("data/eval_benchmark.json", "w") as f:
            json.dump(out, f, indent=2)
        print(f"Exported {len(out)} queries to data/eval_benchmark.json")

if __name__ == "__main__":
    build_benchmark()
