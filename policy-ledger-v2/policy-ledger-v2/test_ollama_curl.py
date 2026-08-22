import requests
import json

prompt = """RETRIEVED POLICY CHUNKS:
<policy_chunk id="pol2_vv2.0_c1" index="1" policy="Leave Policy" version="v2.0" section="1. Annual Leave" page="None" department="Human Resources">
24 days paid annual leave per calendar year, accrued at 2 days/month.
</policy_chunk>

<policy_chunk id="pol2_vv2.0_c2" index="2" policy="Leave Policy" version="v2.0" section="2. Sick Leave" page="None" department="Human Resources">
12 days paid sick leave per year. Medical certificate needed for 2+ consecutive days.
</policy_chunk>

USER QUESTION: How many paid leave days do I get?

INSTRUCTION: Answer the question strictly using the policy chunks above. If not found, reply with: "I couldn't find this information in the available policies."
"""

messages = [
    {"role": "system", "content": "You are a helpful HR assistant. Answer strictly based on chunks. Cite with [Policy: Leave Policy, Section: 1. Annual Leave]."},
    {"role": "user", "content": prompt}
]

payload = {
    "model": "llama3.2:3b-instruct-q4_K_M",
    "messages": messages,
    "stream": False,
    "options": {
        "temperature": 0.2
    }
}

resp = requests.post("http://localhost:11434/api/chat", json=payload)
print(resp.json().get("message", {}).get("content"))
