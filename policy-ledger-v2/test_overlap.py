import re
prompt = """RETRIEVED POLICY CHUNKS:
<policy_chunk id="pol2_vv2.0_c1" index="1" policy="Leave Policy" version="v2.0" section="1. Annual Leave" page="None" department="Human Resources">
24 days paid annual leave per calendar year, accrued at 2 days/month.
</policy_chunk>

USER QUESTION: How many paid leave days do I get?
"""
excerpts_match = re.search(r"(?:POLICY EXCERPTS|RETRIEVED POLICY CHUNKS):\s*(.*?)\s*(?:QUESTION|USER QUESTION):", prompt, re.DOTALL)
question_match = re.search(r"(?:QUESTION|USER QUESTION):\s*(.*?)(?:\n\n|$)", prompt, re.DOTALL)

STOP_WORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "in", "on", "at", "to", "for", "from", "of", "with", "by", "what", "which",
    "who", "whom", "this", "that", "these", "those", "and", "or", "but", "it", "how"
}
q_tokens = set(w for w in re.findall(r"[a-z0-9]+", question_match.group(1).lower()) if w not in STOP_WORDS)
print("Q_Tokens:", q_tokens)

raw_excerpts = excerpts_match.group(1)
raw_excerpts = re.sub(r"</?policy_chunk[^>]*>", "---", raw_excerpts)
blocks = raw_excerpts.split("---")

best_score = 0
best_sentence = ""
for block in blocks:
    lines = block.strip().split("\n")
    body = "\n".join(lines[2:]) if len(lines) > 2 and lines[0].strip().startswith("[Excerpt") else block
    sentences = re.split(r"(?<=[.!?])\s+", body.strip())
    for s in sentences:
        if not s.strip(): continue
        s_tokens = set(re.findall(r"[a-z0-9]+", s.lower()))
        overlap = len(q_tokens & s_tokens)
        print(f"Sentence: {s!r}, Tokens: {s_tokens}, Overlap: {overlap} ({q_tokens & s_tokens})")
        if overlap > best_score:
            best_score = overlap
            best_sentence = s

print("Best Score:", best_score)
print("Best Sentence:", best_sentence)
