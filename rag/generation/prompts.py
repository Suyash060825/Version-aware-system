"""
rag/generation/prompts.py
Strict, structured generation prompts for factual policy grounding, version diffs, and complex reasoning.
"""
from typing import Optional

SYSTEM_POLICY_GROUNDING_PROMPT = """You are an Enterprise Policy Assistant.
Answer the user's question using ONLY the provided authoritative policy evidence.
Do NOT fabricate rules, policies, numbers, or exceptions.
If the evidence does not contain the answer, respond with "INSUFFICIENT_EVIDENCE".
In the "answer" field, always cite the specific section (e.g., "Section 4.2 of the Leave Policy states...").
Never say just "the policy says" without naming the section.

Always output ONLY valid JSON. No markdown fences, no explanation outside the JSON.
Example: {"answer": "Section 3.1 of the Annual Leave Policy states that employees are entitled to 21 days of annual leave per year.", "reasoning_summary": "Section 3.1 states 21 days.", "used_evidence_ids": ["chunk-1"], "needs_clarification": false}
"""

STREAMING_POLICY_GROUNDING_PROMPT = """You are an Enterprise Policy Assistant.
Answer the user's question directly, clearly, and concisely based ONLY on the provided authoritative policy evidence.
Do NOT fabricate rules, numbers, or exceptions.
If the evidence does not contain the answer, emit only "INSUFFICIENT_EVIDENCE", do not invent an answer.
Do not output JSON, markdown tags, or boilerplate; output the direct natural answer."""

def build_grounded_qa_prompt(query: str, evidence_chunks: list) -> str:
    context_blocks = []
    for i, c in enumerate(evidence_chunks):
        cid = c.get("chunk_id") or c.get("id") or f"chunk-{i+1}"
        sec = c.get("section") or c.get("section_path") or "Policy Section"
        pname = c.get("policy_name") or "Policy"
        ver = str(c.get("version") or "1.0").lstrip("v")
        status = "Active" if c.get("is_active", True) else "Superseded"
        status_label = f" ({status})" if status == "Active" else ""
        text = c.get("text", "").strip()[:700]
        context_blocks.append(f"[{cid}] [Policy: {pname} | Version: v{ver}{status_label} | Section: {sec}]:\n{text}")

    context_str = "\n\n".join(context_blocks)
    
    return f"""Context:
{context_str}

User Question:
{query}

JSON Response:"""

def build_streaming_qa_prompt(query: str, evidence_chunks: list) -> str:
    context_blocks = []
    for i, c in enumerate(evidence_chunks):
        cid = c.get("chunk_id") or c.get("id") or f"chunk-{i+1}"
        sec = c.get("section") or c.get("section_path") or "Policy Section"
        pname = c.get("policy_name") or "Policy"
        ver = c.get("version") or "1.0"
        text = c.get("text", "").strip()[:700]
        context_blocks.append(f"[{pname} v{ver} - Section: {sec}]:\n{text}")

    context_str = "\n\n".join(context_blocks)
    return f"""Authoritative Policy Evidence:
{context_str}

User Question:
{query}

Direct Answer:"""

def build_comparison_prompt(policy_name: str, v1_num: str, v1_text: str, v2_num: str, v2_text: str, diff_summary: Optional[str] = None) -> str:
    if diff_summary:
        return f"""Compare Policy '{policy_name}' Version {v1_num} vs Version {v2_num}.
Synthesize the key changes, additions, and removals clearly and concisely based on the following pre-computed structural diff:

{diff_summary}

Summary of changes:"""

    return f"""Compare Policy '{policy_name}' Version {v1_num} vs Version {v2_num}.
Summarize the key changes, additions, and removals clearly and concisely.

Version {v1_num}:
{v1_text[:700]}

Version {v2_num}:
{v2_text[:700]}

Summary of changes:"""
