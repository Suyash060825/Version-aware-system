import re
prompt = """RETRIEVED POLICY CHUNKS:
<policy_chunk id="pol2_vv2.0_c1" index="1" policy="Leave Policy" version="v2.0" section="1. Annual Leave" page="None" department="Human Resources">
24 days paid annual leave per calendar year, accrued at 2 days/month.
</policy_chunk>

USER QUESTION: How many paid leave days do I get?

INSTRUCTION: Answer the question strictly using the policy chunks above. If not found, reply with: "I couldn't find this information in the available policies."
"""

excerpts_match = re.search(r"(?:POLICY EXCERPTS|RETRIEVED POLICY CHUNKS):\s*(.*?)\s*(?:QUESTION|USER QUESTION):", prompt, re.DOTALL)
question_match = re.search(r"(?:QUESTION|USER QUESTION):\s*(.*?)(?:\n\n|$)", prompt, re.DOTALL)

print("Excerpts Match:", bool(excerpts_match))
print("Question Match:", bool(question_match))
if question_match:
    print("Question:", repr(question_match.group(1)))
