"""rag/chatbot/citations.py"""

def build_citations(chunks: list[dict]) -> list[dict]:
    seen, citations = set(), []
    for c in chunks:
        pid = c.get("policy_id")
        pname = (c.get("policy_name") or "").strip().lower()
        sec = (c.get("section") or "General").strip().lower()
        ver = str(c.get("version") or "1.0").strip().lower().lstrip("v")
        key = (pid if pid else pname, ver, sec)
        if key not in seen:
            seen.add(key)
            citations.append({
                "policy_name": (c.get("policy_name") or "Unknown").strip(),
                "version": str(c.get("version") or "1.0").strip(),
                "section": (c.get("section") or "General").strip(),
                "page": c.get("page", "N/A"),
                "department": c.get("department", ""),
                "policy_id": c.get("policy_id", ""),
                "relevance_score": round(float(c.get("rerank_score", c.get("score", 0)) or 0), 3),
            })
    return citations


def format_citations_text(citations: list[dict]) -> str:
    if not citations:
        return ""
    lines = ["\n\n**Sources:**"]
    for i, c in enumerate(citations, 1):
        lines.append(
            f"{i}. **{c['policy_name']}** v{c['version']} — "
            f"Section: {c['section']}"
            + (f", Page {c['page']}" if c['page'] and c['page'] != "None" else "")
        )
    return "\n".join(lines)
