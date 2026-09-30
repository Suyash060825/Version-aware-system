import requests
import re
import json
import sys

s = requests.Session()
resp = s.get("http://localhost:5000/auth/login")
csrf = re.search(r'name="csrf_token" value="(.*?)"', resp.text).group(1)

login = s.post("http://localhost:5000/auth/login", data={"csrf_token": csrf, "email": "admin@company.com", "password": "Admin@1234"})

api_csrf_match = re.search(r'meta name="csrf-token" content="(.*?)"', login.text)
api_csrf = api_csrf_match.group(1) if api_csrf_match else csrf

queries = {
    "normal": "What is the work from home policy?",
    "structured": "What is the maximum expense limit?",
    "qa": "How do I reset my password?",
    "semantic": "I need to take time off for being sick, what are the rules?",
    "temporal": "What was the travel policy in 2022?",
    "repeated_cache_test": "What is the work from home policy?"
}

for name, q in queries.items():
    print(f"\n--- Testing {name} query ---")
    payload = {"query": q}
    chat_resp = s.post("http://localhost:5000/rag/api/chat", json=payload, headers={"X-CSRFToken": api_csrf})
    print("Status:", chat_resp.status_code)
    try:
        res = chat_resp.json()
        print("Answer:", res.get("answer", "")[:100].replace("\n", " "))
        print("Citations:", len(res.get("citations", [])))
        print("Cache Hit:", res.get("cache_hit"))
        print("NLI Used:", res.get("llm_used", "Unknown"))
    except:
        print("Failed JSON.")
