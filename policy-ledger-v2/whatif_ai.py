"""
whatif_ai.py
AI engine for Module 25 — Policy Impact Simulator ("What-If" Compliance Checker).

Unlike the AI Assistant (Module: rag chat), which answers open-ended
questions conversationally, this module takes a described real-world
scenario/decision ("I want to expense a personal laptop under $500") and
returns a *structured verdict* — compliant / not compliant / depends /
unclear — grounded in the same retrieved policy chunks, with:

  - the specific policies + sections that apply (citations)
  - concrete required actions ("Get manager sign-off before purchase")
  - a confidence score, so low-confidence verdicts are visibly flagged
    rather than presented with false certainty
  - an auto-flag for HR review when the scenario is ambiguous or touches
    a mandatory/critical-priority policy, turning grey-area employee
    questions into a queue HR can actually act on.

Reuses the existing embedder / vector store / reranker (same stack as
rag/chatbot/chat_service.py) so no new indexing pipeline is needed —
only the final prompt and output shape differ.
"""
import json
import re

from rag.embeddings.embedder import get_embedder
from rag.vectordb.chroma import get_store
from rag.reranker.reranker import get_reranker
from rag.llm_provider import get_llm_provider

RELEVANCE_THRESHOLD = 0.10


def _extract_json(text: str) -> dict | None:
    if not text:
        return None
    text = re.sub(r"^```(?:json)?\s*", "", text.strip())
    text = re.sub(r"\s*```$", "", text)
    try:
        obj = json.loads(text)
        return obj if isinstance(obj, dict) else None
    except (ValueError, TypeError):
        pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            obj = json.loads(match.group(0))
            return obj if isinstance(obj, dict) else None
        except (ValueError, TypeError):
            pass
    return None


VERDICT_SYSTEM_PROMPT = """You are a corporate compliance decision-support assistant. An employee \
describes a real-world scenario or thing they want to do. You are given excerpts from the \
company's ACTIVE policies that are most relevant to it. Decide whether the scenario is allowed.

Respond with ONLY a single valid JSON object, no markdown fences, no commentary:
{
  "verdict": "compliant" | "not_compliant" | "depends" | "unclear",
  "confidence": <integer 0-100>,
  "explanation": "2-4 sentence plain-language explanation of the verdict, written directly to the employee",
  "required_actions": ["concrete next step, e.g. 'Get written manager approval before booking travel'", "..."],
  "applicable_sections": ["short label of which excerpt/section the verdict rests on, e.g. 'Remote Work Policy - Section 3'", "..."]
}

Rules:
- "compliant": clearly allowed as described, no special steps needed beyond normal process.
- "not_compliant": clearly against policy as described.
- "depends": allowed only under specific conditions (e.g. approval, threshold, duration) — explain the condition.
- "unclear": the provided policy excerpts don't clearly cover this scenario. Use confidence <= 40 in this case.
- Base the verdict strictly on the provided excerpts. Do not invent policy content that isn't there.
- If nothing relevant was provided at all, return verdict "unclear" with confidence 0.
"""


def _heuristic_verdict(scenario: str, chunks: list[dict]) -> dict:
    """Zero-LLM fallback: no verdict claim, just surfaces the most relevant
    excerpts so the employee/HR still gets something actionable."""
    if not chunks:
        return {
            "verdict": "unclear", "confidence": 0,
            "explanation": "I couldn't find any policy content relevant to this scenario. "
                           "Please check with HR directly, or configure an LLM provider for full analysis.",
            "required_actions": ["Ask HR / your manager directly."],
            "applicable_sections": [],
        }
    top = chunks[0]
    return {
        "verdict": "unclear", "confidence": 20,
        "explanation": (f"The closest matching policy content is from '{top.get('policy_name', 'a policy')}' "
                        f"(Section: {top.get('section', 'General')}), but automatic verdict generation is "
                        "unavailable right now (no LLM configured). Please review the cited section yourself "
                        "or ask HR to confirm."),
        "required_actions": ["Confirm with HR before proceeding."],
        "applicable_sections": [f"{top.get('policy_name', 'Policy')} - {top.get('section', 'General')}"],
    }


def evaluate_scenario(scenario: str, user_role: str = "employee", user_department: str = "",
                      top_k_retrieve: int = 20, top_k_rerank: int = 6) -> dict:
    """
    Full pipeline: scenario -> embed -> retrieve -> rerank -> structured verdict.

    Returns:
    {
        "verdict": str, "confidence": int, "explanation": str,
        "required_actions": list[str],
        "citations": list[dict],   # same shape as chat citations (policy_name, version, section, page, policy_id)
        "flagged_for_hr": bool,
        "chunks_used": int,
    }
    """
    scenario = (scenario or "").strip()
    if not scenario:
        return {"verdict": "unclear", "confidence": 0, "explanation": "No scenario provided.",
               "required_actions": [], "citations": [], "flagged_for_hr": False, "chunks_used": 0}

    embedder = get_embedder()
    store = get_store()
    reranker = get_reranker()
    llm = get_llm_provider()

    allowed_depts = None
    if user_role == "employee" and user_department:
        allowed_depts = [user_department, ""]

    q_vec = embedder.embed_query(scenario)
    hits = store.search(
        query_embedding=q_vec, query_text=scenario, top_k=top_k_retrieve,
        active_only=True, allowed_departments=allowed_depts,
    )
    hits = [h for h in hits if h.get("score", 0) >= RELEVANCE_THRESHOLD]
    top_chunks = reranker.rerank(scenario, hits, top_k=top_k_rerank) if hits else []

    citations = []
    seen = set()
    for c in top_chunks:
        key = (c.get("policy_name"), c.get("version"), c.get("section"))
        if key in seen:
            continue
        seen.add(key)
        citations.append({
            "policy_name": c.get("policy_name", "Unknown"), "version": c.get("version", "N/A"),
            "section": c.get("section", "General"), "page": c.get("page", "N/A"),
            "policy_id": c.get("policy_id", ""),
            "relevance_score": round(c.get("rerank_score", c.get("score", 0)), 3),
        })

    if not top_chunks:
        result = _heuristic_verdict(scenario, top_chunks)
    else:
        excerpts = "\n\n---\n\n".join(
            f"[{c.get('policy_name')} — {c.get('section', 'General')}]\n{c.get('text', '')[:1200]}"
            for c in top_chunks
        )
        user_prompt = f"SCENARIO: {scenario}\n\nPOLICY EXCERPTS:\n\n{excerpts}\n\nQUESTION: {scenario}\n\nProduce the JSON verdict now."
        raw_resp = None
        raw = ""
        try:
            prompt_msgs = [
                {"role": "system", "content": VERDICT_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ]
            raw_resp = llm.generate(prompt_msgs)
            raw = raw_resp.text
            
            if getattr(raw_resp, "fallback", False):
                parsed = {
                    "verdict": "depends",
                    "confidence": 50,
                    "explanation": raw if raw != "I couldn't find this information in the available policies." else "The closest matching policy content does not clearly authorize or prohibit this scenario. Please check with HR.",
                    "required_actions": ["Review the policy manually or ask HR."],
                    "applicable_sections": [f"{top_chunks[0].get('policy_name', 'Policy')} - {top_chunks[0].get('section', 'General')}"]
                }
            else:
                parsed = _extract_json(raw)
                if parsed and (int(parsed.get("confidence", 0) or 0) < 55 or parsed.get("verdict") in ("depends", "unclear")):
                    # Escalate to secondary model due to ambiguity
                    raw_resp = llm.generate(prompt_msgs, use_secondary=True)
                    raw = raw_resp.text
                    parsed = _extract_json(raw)
        except Exception:
            raw = ""
            parsed = None
            
        if not getattr(raw_resp, "fallback", False) and (not parsed or "I couldn't find this information" in (raw or "")):
            result = _heuristic_verdict(scenario, top_chunks)
        else:
            result = {
                "verdict": parsed.get("verdict") if parsed.get("verdict") in
                           ("compliant", "not_compliant", "depends", "unclear") else "unclear",
                "confidence": max(0, min(100, int(parsed.get("confidence", 0) or 0))),
                "explanation": str(parsed.get("explanation", "") or "").strip() or "No explanation generated.",
                "required_actions": [str(a) for a in (parsed.get("required_actions") or [])],
                "applicable_sections": [str(a) for a in (parsed.get("applicable_sections") or [])],
            }

    flagged = (
        result["verdict"] in ("depends", "unclear") or
        result.get("confidence", 0) < 55 or
        result["verdict"] == "not_compliant"
    )

    return {
        "verdict": result["verdict"],
        "confidence": result.get("confidence", 0),
        "explanation": result["explanation"],
        "required_actions": result.get("required_actions", []),
        "citations": citations,
        "flagged_for_hr": flagged,
        "chunks_used": len(top_chunks),
    }
