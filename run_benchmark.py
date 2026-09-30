import requests
import json
import time
import sys
import re
import os

from collections import defaultdict

BENCHMARK_FILE = "data/benchmarks/benchmark_test.json"
OUTPUT_RAW = "results/final_benchmark_raw.json"
BASE_URL = "http://localhost:5000"

os.makedirs("results", exist_ok=True)

with open(BENCHMARK_FILE) as f:
    queries = json.load(f)

users = [
    "admin@company.com",
    "hr@company.com",
    "legal.counsel@company.com",
    "ciso@company.com",
    "eng.lead@company.com",
    "employee@company.com",
    "fin.analyst@company.com",
    "ops.manager@company.com",
    "sales.exec@company.com",
    "mkt.specialist@company.com"
]
password = os.getenv("BENCHMARK_PASSWORD", os.getenv("DEFAULT_ADMIN_PASSWORD", "Admin@1234"))

sessions = []
for u in users:
    s = requests.Session()
    resp = s.get(f"{BASE_URL}/auth/login")
    csrf_match = re.search(r'name="csrf_token" value="(.*?)"', resp.text)
    if csrf_match:
        login_resp = s.post(f"{BASE_URL}/auth/login", data={
            "csrf_token": csrf_match.group(1),
            "email": u,
            "password": password
        })
        api_csrf_match = re.search(r'meta name="csrf-token" content="(.*?)"', login_resp.text)
        api_csrf = api_csrf_match.group(1) if api_csrf_match else csrf_match.group(1)
        s.headers.update({"X-CSRFToken": api_csrf})
        sessions.append(s)

print(f"Initialized {len(sessions)} sessions.")

results = []
for i, item in enumerate(queries):
    start_time = time.time()
    s = sessions[i % len(sessions)] # Round-robin
    try:
        chat_resp = s.post(f"{BASE_URL}/rag/api/chat", json={"query": item["query"]}, timeout=120)
        end_time = time.time()
        
        if chat_resp.status_code == 429:
            print(f"Rate limited at query {i}. Sleeping 20s...")
            time.sleep(20)
            start_time = time.time()
            chat_resp = s.post(f"{BASE_URL}/rag/api/chat", json={"query": item["query"]}, timeout=120)
            end_time = time.time()

        latency = end_time - start_time
        status_code = chat_resp.status_code
        if status_code == 200:
            results.append({
                "item": item,
                "latency_sec": latency,
                "status": status_code,
                "response": chat_resp.json(),
                "error": None
            })
        else:
            results.append({
                "item": item,
                "latency_sec": latency,
                "status": status_code,
                "response": None,
                "error": chat_resp.text[:200]
            })
    except Exception as e:
        results.append({
            "item": item,
            "latency_sec": time.time() - start_time,
            "status": None,
            "response": None,
            "error": str(e)
        })
    
    if (i + 1) % 10 == 0:
        print(f"Processed {i + 1}/{len(queries)} queries...")

with open(OUTPUT_RAW, "w") as f:
    json.dump(results, f, indent=2)

print(f"Benchmark raw results saved to {OUTPUT_RAW}")
