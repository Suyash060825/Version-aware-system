"""
rag/generation/prompts.py
Strict, structured generation prompts for factual policy grounding, version diffs, and complex reasoning.
"""

SYSTEM_POLICY_GROUNDING_PROMPT = """You are an Enterprise Policy Assistant.
Answer the user's question using ONLY the provided authoritative policy evidence.
Do NOT fabricate rules, policies, numbers, or exceptions.
If the evidence does not contain the answer, respond with "INSUFFICIENT_EVIDENCE".

Always output your response as valid JSON with the following structure:
{
  "answer": "Clear, concise direct answer based only on the evidence.",
  "reasoning_summary": "Brief summary of how the policy supports the answer.",
  "used_evidence_ids": ["list of chunk_id strings used"],
  "needs_clarification": false
}
"""

STREAMING_POLICY_GROUNDING_PROMPT = """You are an Enterprise Policy Assistant.
Answer the user's question directly, clearly, and concisely based ONLY on the provided authoritative policy evidence.
Do NOT fabricate rules, numbers, or exceptions.
If the evidence does not contain the answer, state clearly that the policy does not specify this information.
Do not output JSON, markdown tags, or boilerplate; output the direct natural answer."""

def build_grounded_qa_prompt(query: str, evidence_chunks: list) -> str:
    context_blocks = []
    for i, c in enumerate(evidence_chunks):
        cid = c.get("chunk_id") or c.get("id") or f"chunk-{i+1}"
        sec = c.get("section") or c.get("section_path") or "Policy Section"
        text = c.get("text", "").strip()
        context_blocks.append(f"[{cid}] ({sec}):\n{text}")

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
        text = c.get("text", "").strip()
        context_blocks.append(f"[{pname} v{ver} - Section: {sec}]:\n{text}")

    context_str = "\n\n".join(context_blocks)
    return f"""Authoritative Policy Evidence:
{context_str}

User Question:
{query}

Direct Answer:"""

def build_comparison_prompt(policy_name: str, v1_num: str, v1_text: str, v2_num: str, v2_text: str) -> str:
    return f"""Compare Policy '{policy_name}' Version {v1_num} vs Version {v2_num}.
Summarize the key changes, additions, and removals clearly and concisely.

Version {v1_num}:
{v1_text}

Version {v2_num}:
{v2_text}

Summary of changes:"""
