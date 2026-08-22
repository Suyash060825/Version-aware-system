"""
rag/engine/query_engine.py
Master Query Inference Engine orchestrating the multi-tier adaptive architecture:
Level 0: Fast Deterministic Fact Engine (<1ms)
Level 1: Precomputed Canonical QA ANN Index (<5ms)
Level 2: Adaptive Hybrid Retrieval + Reranking (<50ms)
Level 3: Deterministic Version Diff & Temporal Engine
Level 4: Local Small LLM Reasoning + Entailment Verification
"""
import time
import re
from typing import Optional, List, Dict, Any
from rag.engine.query_result import QueryResult
from rag.engine.evidence_pack import EvidencePack
from rag.router.query_router import QueryRouter
from rag.router.complexity_classifier import ComplexityLevel
from rag.facts.fact_resolver import FactResolver
from rag.qa.qa_matcher import QAMatcher
from rag.retrieval.hybrid import HybridRetriever
from rag.retrieval.reranker import get_reranker
from rag.authorization.evidence_filter import EvidenceFilter
from rag.verification.confidence import ConfidenceEngine
from rag.verification.entailment import EntailmentVerifier
from rag.verification.citation_validator import CitationValidator
from rag.versions.resolver import VersionResolver
from rag.versions.diff_engine import PolicyDiffEngine
from rag.generation.qwen import QwenLocalProvider

class QueryEngine:
    def __init__(self):
        self.router = QueryRouter()
        self.fact_resolver = FactResolver()
        self.qa_matcher = QAMatcher()
        self.hybrid_retriever = HybridRetriever()
        self.reranker = get_reranker()
        self.evidence_filter = EvidenceFilter()
        self.confidence_engine = ConfidenceEngine()
        self.entailment_verifier = EntailmentVerifier()
        self.citation_validator = CitationValidator()
        self.version_resolver = VersionResolver()
        self.diff_engine = PolicyDiffEngine()
        self.llm = QwenLocalProvider()

    def answer(self, query: str, user=None, session_id: str = None) -> QueryResult:
        t_start = time.time()
        
        # 1. Normalize Query & Classify Route
        normalized_query = self.router.normalize(query)
        intent, complexity, route_name, meta = self.router.route(normalized_query)
        temporal_context = self.version_resolver.resolve_temporal_context(normalized_query, user)

        # 2. Level 0: Fast Structured Fact Path
        fact_res = self.fact_resolver.try_resolve(normalized_query, temporal=temporal_context)
        if fact_res.found and fact_res.answer:
            cits = self.citation_validator.validate_and_enrich(fact_res.citations)
            return QueryResult(
                answer=fact_res.answer,
                route="FAST_PATH_FACT",
                confidence=fact_res.confidence,
                citations=cits,
                policy_versions=[str(cits[0]["version"])] if cits else [],
                latency_ms=(time.time() - t_start) * 1000,
                llm_used=False,
                retrieval_count=1,
                reranker_used=False,
                abstained=False
            )

        # 3. Level 1: Precomputed Canonical QA Fast Path
        if complexity <= ComplexityLevel.LEVEL_1_COMPILED_QA:
            from rag.embeddings.embedder import get_embedder
            embedder = get_embedder()
            q_emb = embedder.embed_query(normalized_query)
            qa_match = self.qa_matcher.match(normalized_query, q_emb, threshold=0.78)
            
            if qa_match:
                cits = self.citation_validator.validate_and_enrich(qa_match["citations"])
                # Authorization check on matched QA
                allowed_cits = [c for c in cits if self.evidence_filter.is_authorized_for_policy(user, type('Obj', (), {'id': c['policy_id'], 'status': 'active', 'department_id': None})())]
                if allowed_cits or not user or user.is_admin():
                    return QueryResult(
                        answer=qa_match["answer"],
                        route="FAST_PATH_COMPILED_QA",
                        confidence=qa_match["confidence"],
                        citations=cits,
                        policy_versions=[str(cits[0]["version"])] if cits else [],
                        latency_ms=(time.time() - t_start) * 1000,
                        llm_used=False,
                        retrieval_count=1,
                        reranker_used=False,
                        abstained=False
                    )

        # 4. Level 3: Version Comparison Path
        temporal_meta = meta.get("temporal", {})
        if temporal_meta.get("is_comparison") and temporal_meta.get("version_v1") and temporal_meta.get("version_v2"):
            v1_num = temporal_meta["version_v1"]
            v2_num = temporal_meta["version_v2"]
            from models import Policy, PolicyVersion
            policies = Policy.query.all()
            for p in policies:
                if p.title.lower() in normalized_query.lower() or any(w in p.title.lower() for w in normalized_query.lower().split() if len(w) > 3):
                    v1 = PolicyVersion.query.filter(PolicyVersion.policy_id == p.id, (PolicyVersion.version_num == float(v1_num)) | (PolicyVersion.version_label.ilike(f"%{v1_num}%"))).first()
                    v2 = PolicyVersion.query.filter(PolicyVersion.policy_id == p.id, (PolicyVersion.version_num == float(v2_num)) | (PolicyVersion.version_label.ilike(f"%{v2_num}%"))).first()
                    if v1 and v2:
                        diff_res = self.diff_engine.compute_diff(v1.content or "", v2.content or "")
                        v1_label = v1.version_label or f"v{v1.version_num}"
                        v2_label = v2.version_label or f"v{v2.version_num}"
                        diff_summary = f"Comparison of {p.title} {v1_label} vs {v2_label}:\n"
                        if diff_res.get("added_clauses"):
                            diff_summary += f"\n- Added ({len(diff_res['added_clauses'])} clauses): " + "; ".join(diff_res['added_clauses'][:3])
                        if diff_res.get("removed_clauses"):
                            diff_summary += f"\n- Removed ({len(diff_res['removed_clauses'])} clauses): " + "; ".join(diff_res['removed_clauses'][:3])
                        if diff_res.get("changed_clauses"):
                            diff_summary += f"\n- Modified ({len(diff_res['changed_clauses'])} clauses): " + "; ".join(diff_res['changed_clauses'][:3])
                        if not diff_res.get("added_clauses") and not diff_res.get("removed_clauses") and not diff_res.get("changed_clauses"):
                            diff_summary += "\nNo structural text differences detected between these two versions."
                            
                        cits = self.citation_validator.validate_and_enrich([
                            {"policy_id": p.id, "version_id": v1.id, "policy_name": p.title, "version": str(v1.version_num), "section": "Version Comparison", "page": 1},
                            {"policy_id": p.id, "version_id": v2.id, "policy_name": p.title, "version": str(v2.version_num), "section": "Version Comparison", "page": 1},
                        ])
                        return QueryResult(
                            answer=diff_summary,
                            route="TEMPORAL_COMPARISON",
                            confidence=0.95,
                            citations=cits,
                            policy_versions=[str(v1.version_num), str(v2.version_num)],
                            latency_ms=(time.time() - t_start) * 1000,
                            llm_used=False,
                            retrieval_count=2,
                            reranker_used=False,
                            abstained=False
                        )

        # 5. Hybrid Retrieval (Dense + Sparse BM25)
        filters = {}
        if temporal_context.policy_id:
            filters["policy_id"] = str(temporal_context.policy_id)

        raw_candidates = self.hybrid_retriever.search(normalized_query, filters=filters, top_k=50)
        
        # 6. Authorization Filtering
        authorized_candidates = self.evidence_filter.filter_chunks(raw_candidates, user)
        
        if not authorized_candidates:
            return QueryResult.abstained("I could not find sufficient authoritative evidence in the applicable policies.", (time.time() - t_start) * 1000)

        # 7. CrossEncoder Precision Reranking
        ranked = self.reranker.rank(normalized_query, authorized_candidates, top_k=8)
        if not ranked:
            ranked = authorized_candidates[:8]

        # 8. Multi-Factor Confidence Scoring
        evidence = EvidencePack(
            query=normalized_query,
            route="HYBRID_RAG",
            chunks=ranked,
            scores=[c.get("rerank_score", c.get("hybrid_score", 0.5)) for c in ranked]
        )
        
        conf = self.confidence_engine.score(normalized_query, evidence)
        if conf.abstain:
            return QueryResult.abstained("I could not find sufficient authoritative evidence in the applicable policies.", (time.time() - t_start) * 1000)

        # Build clean citations
        raw_cits = []
        for c in ranked[:3]:
            raw_cits.append({
                "chunk_id": c.get("chunk_id") or c.get("id"),
                "policy_id": c.get("policy_id"),
                "version_id": c.get("version_id"),
                "policy_name": c.get("policy_name", "Policy"),
                "version": c.get("version", "1.0"),
                "section": c.get("section") or c.get("section_path") or "General",
                "page": c.get("page", 1)
            })
        citations = self.citation_validator.validate_and_enrich(raw_cits)

        # 9. Answer Generation: Deterministic vs Local LLM
        # If query is simple and top chunk has high relevance, extract concise statement
        top_text = ranked[0].get("text", "").strip()
        top_section = ranked[0].get("section") or ranked[0].get("section_path") or "Policy"

        # Check if local Ollama LLM is available for complex reasoning
        llm_used = False
        final_answer = None

        if complexity >= ComplexityLevel.LEVEL_2_RETRIEVAL and self.llm.health_check():
            try:
                llm_output = self.llm.generate_grounded_answer(normalized_query, ranked[:3])
                if llm_output and llm_output.get("answer") and "INSUFFICIENT_EVIDENCE" not in llm_output.get("answer", ""):
                    # Grounding verification with EntailmentVerifier
                    is_grounded, entail_score = self.entailment_verifier.verify(llm_output["answer"], ranked[:3])
                    if is_grounded:
                        final_answer = llm_output["answer"]
                        llm_used = True
            except Exception as e:
                pass

        if not final_answer:
            # Deterministic clean extraction: extract the most relevant sentence from the top chunk
            sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', top_text) if len(s.strip()) > 15]
            q_words = set(re.findall(r"\b[a-z0-9]+\b", normalized_query.lower())) - {"what", "is", "the", "policy", "for", "and", "can", "how"}
            
            best_sentence = sentences[0] if sentences else top_text
            best_score = -1
            for s in sentences:
                s_words = set(re.findall(r"\b[a-z0-9]+\b", s.lower()))
                overlap = len(q_words & s_words)
                if overlap > best_score:
                    best_score = overlap
                    best_sentence = s

            policy_name = citations[0]["policy_name"] if citations else "Policy"
            version_num = citations[0]["version"] if citations else "1.0"
            final_answer = f"According to the {policy_name} (v{version_num}, {top_section}):\n{best_sentence}"

        return QueryResult(
            answer=final_answer,
            route="HYBRID_RAG",
            confidence=conf.value,
            citations=citations,
            policy_versions=[str(citations[0]["version"])] if citations else [],
            latency_ms=(time.time() - t_start) * 1000,
            llm_used=llm_used,
            retrieval_count=len(ranked),
            reranker_used=True,
            abstained=False
        )

    def stream_answer(self, query: str, user=None, session_id: str = None):
        """
        Streaming generator yielding token events and final result metadata for SSE.
        """
        t_start = time.time()
        # Compute answer via fast-path / hybrid engine
        res = self.answer(query, user=user, session_id=session_id)
        
        # Tokenize answer by words to deliver streaming cadence
        words = res.answer.split(" ")
        for i, word in enumerate(words):
            chunk = word if i == len(words) - 1 else word + " "
            yield {"type": "token", "token": chunk}

        # Deliver final result payload with citations, confidence, and route info
        yield {
            "type": "done",
            "result": {
                "answer": res.answer,
                "citations": res.citations,
                "confidence": res.confidence * 100,
                "route": res.route,
                "llm_used": res.llm_used,
                "latency_ms": (time.time() - t_start) * 1000,
                "fallback": res.abstained,
                "model": "qwen3" if res.llm_used else "deterministic-rag"
            }
        }

_ENGINE = None
def get_query_engine() -> QueryEngine:
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = QueryEngine()
    return _ENGINE
