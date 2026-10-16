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
import logging
from typing import Optional, List, Dict, Any

from models import Policy, PolicyVersion, PolicyStatus
from rag.engine.query_result import QueryResult
from rag.engine.evidence_pack import EvidencePack
from rag.engine.query_scope import QueryScope
from rag.engine.engine_config import EngineConfig
from rag.cache.semantic_cache import get_cache
from rag.embeddings.embedder import get_embedder
from rag.router.query_router import QueryRouter
from rag.router.intent_classifier import Intent
from rag.router.complexity_classifier import ComplexityLevel
from rag.facts.fact_resolver import FactResolver
from rag.qa.qa_matcher import QAMatcher
from rag.retrieval.hybrid import HybridRetriever
from rag.retrieval.reranker import get_reranker
from rag.authorization.evidence_filter import EvidenceFilter, get_evidence_filter
from rag.verification.confidence import ConfidenceEngine
from rag.verification.entailment import EntailmentVerifier, get_entailment_verifier
from rag.verification.citation_validator import CitationValidator
from rag.versions.resolver import VersionResolver
from rag.versions.diff_engine import PolicyDiffEngine
from rag.generation.qwen import QwenLocalProvider
from rag.generation.prompts import STREAMING_POLICY_GROUNDING_PROMPT, build_streaming_qa_prompt

logger = logging.getLogger("rag.engine.query_engine")

def verify_numeric_grounding(answer: str, chunks: List[Dict[str, Any]]) -> bool:
    """
    Verifies that numerical figures, percentages, or metrics mentioned in the answer
    are grounded in the retrieved chunks, preventing hallucinated numbers.
    """
    if not answer or not chunks:
        return True
    raw_nums = set(re.findall(r"\b\d+(?:\.\d+)?%?\b", answer))
    if not raw_nums:
        return True
    context = " ".join([c.get("text", "") for c in chunks])
    ctx_nums = set(re.findall(r"\b\d+(?:\.\d+)?%?\b", context))
    for num in raw_nums:
        if num in ctx_nums or num in ("1", "2"):
            continue
        if num.endswith("%") and num[:-1] in ctx_nums:
            continue
        return False
    return True

class QueryEngine:
    def __init__(self, config: Optional[EngineConfig] = None):
        self.config = config or EngineConfig()
        self.router = QueryRouter()
        self.fact_resolver = FactResolver()
        self.qa_matcher = QAMatcher()
        self.hybrid_retriever = HybridRetriever()
        self.reranker = get_reranker()
        self.evidence_filter = get_evidence_filter()
        self.confidence_engine = ConfidenceEngine()
        self.entailment_verifier = get_entailment_verifier()
        self.citation_validator = CitationValidator()
        self.version_resolver = VersionResolver()
        self.diff_engine = PolicyDiffEngine()
        self.llm = QwenLocalProvider()
        self.cache = get_cache()
        self.embedder = get_embedder()

    def answer(self, query: str, user=None, session_id: str = None) -> QueryResult:
        t_start = time.time()
        
        # 1. Normalize Query & Fast Authorization Scope
        normalized_query = self.router.normalize(query)
        allowed_pids = self.evidence_filter.get_allowed_policy_ids(user)

        # Fast temporal cues check (avoids 15 regex patterns for common queries)
        is_diff = bool(re.search(r"\bv\d+\s*(?:and|vs|versus|to|\-)\s*v\d+\b", normalized_query, re.I))
        has_temporal_cue = is_diff or bool(re.search(r"\b(?:in\s+20\d\d|as\s+of|before\s+|after\s+|between\s+|since\s+|until\s+|during\s+|historical|previous|prior|old\s+version|v\d+)\b", normalized_query, re.I))

        temporal_context = self.version_resolver.resolve_temporal_context(normalized_query, user) if has_temporal_cue else None
        scope = QueryScope.from_user(user, temporal_context, allowed_policy_ids=allowed_pids)

        # 1.5 Scoped Cache Lookup (L1 Exact Hash -> L2 Semantic Vector)
        cached = None
        q_emb = None
        if self.config.use_cache:
            cached = self.cache.get(query=normalized_query, scope=scope, is_diff_query=is_diff)
            if not cached:
                q_emb = self.embedder.embed_query(normalized_query)
                cached = self.cache.get(query_embedding=q_emb, scope=scope, is_diff_query=is_diff)

        if cached:
            cits = cached.get("citations", [])
            return QueryResult(
                answer=cached["answer"],
                route="CACHE_HIT",
                confidence=cached.get("confidence", 0.95),
                citations=cits,
                policy_versions=[str(cits[0]["version"])] if cits and "version" in cits[0] else [],
                latency_ms=(time.time() - t_start) * 1000,
                llm_used=False,
                retrieval_count=cached.get("chunks_used", 0),
                reranker_used=False,
                abstained=False
            )

        # If cache missed and embedding was not yet computed, compute now
        if q_emb is None:
            q_emb = self.embedder.embed_query(normalized_query)

        # 1.6 Classify Route on Cache Miss
        intent, complexity, route_name, meta = self.router.route(normalized_query)
        if temporal_context is None and (route_name in ("TEMPORAL_COMPARISON", "TEMPORAL") or intent in (Intent.TEMPORAL, Intent.COMPARISON)):
            temporal_context = self.version_resolver.resolve_temporal_context(normalized_query, user)
            scope = QueryScope.from_user(user, temporal_context, allowed_policy_ids=allowed_pids)
            is_diff = (route_name == "TEMPORAL_COMPARISON")

        # 2. Level 0: Fast Structured Fact Path
        if self.config.use_fact:
            fact_res = self.fact_resolver.try_resolve(normalized_query, scope=scope, temporal=temporal_context, user=user)
            if fact_res.found and fact_res.answer:
                cits = self.citation_validator.enrich_only(fact_res.citations)
                if self.config.use_cache:
                    self.cache.put(q_emb, fact_res.answer, cits, 1, scope=scope, confidence=fact_res.confidence, is_diff_query=is_diff, query=normalized_query)
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

        # 3. Level 1: Precomputed Canonical QA Fast Path (checked reliably when enabled)
        if self.config.use_qa and not is_diff:
            qa_match = self.qa_matcher.match(normalized_query, q_emb, scope=scope, threshold=0.80)
            
            if qa_match:
                pol = qa_match.get("policy")
                ver = qa_match.get("version")
                # Authoritative entity authorization check if loaded
                is_auth = True
                conf_ok = True
                temp_ok = True
                if pol:
                    is_auth = self.evidence_filter.is_authorized_for_policy(scope, pol)
                    conf_ok = pol.confidentiality in scope.allowed_confidentiality
                if ver:
                    temp_ok = (not scope.target_date) or ver.is_valid_for_date(scope.target_date)

                if is_auth and conf_ok and temp_ok:
                    cits = self.citation_validator.enrich_only(qa_match["citations"])
                    if cits:
                        if self.config.use_cache:
                            self.cache.put(q_emb, qa_match["answer"], cits, 1, scope=scope, confidence=qa_match["confidence"], is_diff_query=is_diff, query=normalized_query)
                        return QueryResult(
                            answer=qa_match["answer"],
                            route="FAST_PATH_COMPILED_QA",
                            confidence=qa_match["confidence"],
                            citations=cits,
                            policy_versions=[str(cits[0]["version"])],
                            latency_ms=(time.time() - t_start) * 1000,
                            llm_used=False,
                            retrieval_count=1,
                            reranker_used=False,
                            abstained=False
                        )

        # 4. Level 3: Version Comparison Path (Strictly Authorized & Scalable)
        temporal_meta = meta.get("temporal", {})
        if temporal_meta.get("is_comparison") and temporal_meta.get("version_v1") and temporal_meta.get("version_v2"):
            v1_num = temporal_meta["version_v1"]
            v2_num = temporal_meta["version_v2"]

            # Scalable candidate lookup: query only relevant/authorized policies
            if temporal_context and temporal_context.policy_id:
                p_query = Policy.query.filter(Policy.id == temporal_context.policy_id)
            elif scope.allowed_policy_ids is not None:
                p_query = Policy.query.filter(Policy.id.in_(scope.allowed_policy_ids))
            else:
                p_query = Policy.query.filter(Policy.status == PolicyStatus.ACTIVE)

            candidate_policies = p_query.all()
            for p in candidate_policies:
                if p.title.lower() in normalized_query.lower() or any(w in p.title.lower() for w in normalized_query.lower().split() if len(w) > 3):
                    # SECURITY REQUIREMENT 4: Enforce authorization BEFORE loading comparison versions or computing diff
                    if not self.evidence_filter.is_authorized_for_policy(scope, p):
                        continue

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
                            
                        cits = self.citation_validator.enrich_only([
                            {"policy_id": p.id, "version_id": v1.id, "policy_name": p.title, "version": str(v1.version_num), "section": "Version Comparison", "page": 1},
                            {"policy_id": p.id, "version_id": v2.id, "policy_name": p.title, "version": str(v2.version_num), "section": "Version Comparison", "page": 1},
                        ])
                        diff_clauses = len(diff_res.get("added_clauses", [])) + len(diff_res.get("removed_clauses", [])) + len(diff_res.get("changed_clauses", []))
                        comparison_evidence_score = 0.85 if diff_clauses > 0 else 0.80

                        if self.config.use_cache:
                            self.cache.put(q_emb, diff_summary, cits, 2, scope=scope, confidence=comparison_evidence_score, is_diff_query=True, query=normalized_query)
                        return QueryResult(
                            answer=diff_summary,
                            route="TEMPORAL_COMPARISON",
                            confidence=comparison_evidence_score,
                            citations=cits,
                            policy_versions=[str(v1.version_num), str(v2.version_num)],
                            latency_ms=(time.time() - t_start) * 1000,
                            llm_used=False,
                            retrieval_count=2,
                            reranker_used=False,
                            abstained=False
                        )

        # 5. Hybrid Retrieval (Dense + Sparse BM25) with Pre-filtering
        filters = {}
        if scope.allowed_policy_ids is not None:
            if len(scope.allowed_policy_ids) == 0:
                return QueryResult.abstained("I could not find sufficient authoritative evidence in the applicable policies.", (time.time() - t_start) * 1000)
            if temporal_context and temporal_context.policy_id:
                if temporal_context.policy_id not in scope.allowed_policy_ids:
                    return QueryResult.abstained("I could not find sufficient authoritative evidence in the applicable policies.", (time.time() - t_start) * 1000)
                filters["policy_id"] = temporal_context.policy_id
            else:
                filters["policy_id"] = list(scope.allowed_policy_ids)
        elif temporal_context and temporal_context.policy_id:
            filters["policy_id"] = temporal_context.policy_id

        if self.config.use_temporal_filter:
            if scope.target_date:
                from datetime import datetime, time as dt_time
                target_ts = int(datetime.combine(scope.target_date, dt_time.min).timestamp())
                filters["valid_from_ts"] = {"$lte": target_ts}
                filters["valid_to_ts"] = {"$gte": target_ts}
            elif not has_temporal_cue and not is_diff:
                filters["is_active"] = True

        raw_candidates = self.hybrid_retriever.search(normalized_query, filters=filters, top_k=25, query_embedding=q_emb)
        
        # 6. Authorization Filtering using unified QueryScope
        authorized_candidates = self.evidence_filter.filter_chunks(raw_candidates, scope)
        
        if not authorized_candidates:
            return QueryResult.abstained("I could not find sufficient authoritative evidence in the applicable policies.", (time.time() - t_start) * 1000)

        # 7. CrossEncoder Precision Reranking
        if self.config.use_rerank:
            ranked = self.reranker.rank(normalized_query, authorized_candidates, top_k=min(len(authorized_candidates), self.config.rerank_top_k))
            score_type = "rerank_prob"
        else:
            ranked = authorized_candidates[:min(len(authorized_candidates), self.config.rerank_top_k)]
            score_type = "rrf"

        if not ranked:
            ranked = authorized_candidates[:8]
            score_type = "rrf"

        # 8. Multi-Factor Confidence Scoring
        evidence = EvidencePack(
            query=normalized_query,
            route="HYBRID_RAG",
            chunks=ranked,
            scores=[c.get("rerank_score", c.get("hybrid_score", 0.5)) for c in ranked],
            score_type=score_type
        )
        
        conf = self.confidence_engine.score(normalized_query, evidence)
        if self.config.use_confidence_gate and conf.abstain:
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
        citations = self.citation_validator.validate_and_enrich(raw_cits, scope=scope)

        # 9. Answer Generation: Grounded Evidence Extraction vs Local LLM
        top_text = ranked[0].get("text", "").strip()
        top_section = ranked[0].get("section") or ranked[0].get("section_path") or "Policy"

        llm_used = False
        final_answer = None

        # Try LLM generation first when available
        if self.llm.health_check():
            try:
                llm_output = self.llm.generate_grounded_answer(normalized_query, ranked[:3])
                if llm_output and llm_output.get("answer") and "INSUFFICIENT_EVIDENCE" not in llm_output.get("answer", ""):
                    ans_candidate = llm_output["answer"]
                    if verify_numeric_grounding(ans_candidate, ranked[:3]):
                        if self.config.use_nli:
                            is_grounded, entail_score = self.entailment_verifier.verify(ans_candidate, ranked[:3])
                        else:
                            is_grounded = True
                        if is_grounded:
                            final_answer = ans_candidate
                            llm_used = True
            except Exception as e:
                logger.warning(f"Local LLM inference encountered error: {e}. Falling back to deterministic grounded extraction.")

        if not final_answer:
            # Deterministic evidence extraction: must be verified as answer-bearing
            sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', top_text) if len(s.strip()) > 15]
            q_words = set(re.findall(r"\b[a-z0-9]+\b", normalized_query.lower())) - {"what", "when", "where", "which", "who", "whom", "how", "why", "does", "have", "policy", "the", "for", "and", "can", "are", "get", "with", "from", "that", "this", "our", "you", "your", "will", "shall", "is"}
            
            best_sentence = None
            best_score = 0
            for s in sentences:
                s_words = set(re.findall(r"\b[a-z0-9]+\b", s.lower()))
                overlap = len(q_words & s_words)
                if overlap > best_score:
                    best_score = overlap
                    best_sentence = s

            # Require at least 2 distinct content word matches for evidence bearing
            if best_sentence and best_score >= 2:
                policy_name = citations[0]["policy_name"] if citations else "Policy"
                version_num = citations[0]["version"] if citations else "1.0"
                final_answer = f"According to the {policy_name} (v{version_num}, {top_section}):\n{best_sentence}"
            else:
                # If cannot extract verified answer-bearing sentence and no LLM grounding, abstain safely
                return QueryResult.abstained("I could not find sufficient authoritative evidence to answer this specific question.", (time.time() - t_start) * 1000)

        # Cache successful verified answer preserving exact confidence score
        if self.config.use_cache:
            self.cache.put(q_emb, final_answer, citations, len(ranked), scope=scope, model="qwen3", confidence=conf.value, is_diff_query=is_diff, query=normalized_query)

        return QueryResult(
            answer=final_answer,
            route="HYBRID_RAG",
            confidence=conf.value,
            citations=citations,
            policy_versions=[str(citations[0]["version"])] if citations else [],
            latency_ms=(time.time() - t_start) * 1000,
            llm_used=llm_used,
            retrieval_count=len(ranked),
            reranker_used=self.config.use_rerank,
            abstained=False
        )

    def stream_answer(self, query: str, user=None, session_id: str = None):
        """
        True streaming generator yielding token events in real time and final result metadata for SSE.
        """
        t_start = time.time()
        
        # 1. Normalize Query & Fast Authorization Scope
        normalized_query = self.router.normalize(query)
        allowed_pids = self.evidence_filter.get_allowed_policy_ids(user)

        # Fast temporal cues check
        is_diff = bool(re.search(r"\bv\d+\s*(?:and|vs|versus|to|\-)\s*v\d+\b", normalized_query, re.I))
        has_temporal_cue = is_diff or bool(re.search(r"\b(?:in\s+20\d\d|as\s+of|before\s+|after\s+|between\s+|since\s+|until\s+|during\s+|historical|previous|prior|old\s+version|v\d+)\b", normalized_query, re.I))

        temporal_context = self.version_resolver.resolve_temporal_context(normalized_query, user) if has_temporal_cue else None
        scope = QueryScope.from_user(user, temporal_context, allowed_policy_ids=allowed_pids)

        # 1.5 Scoped Cache Lookup (L1 Exact Hash -> L2 Semantic Vector)
        cached = None
        q_emb = None
        if self.config.use_cache:
            cached = self.cache.get(query=normalized_query, scope=scope, is_diff_query=is_diff)
            if not cached:
                q_emb = self.embedder.embed_query(normalized_query)
                cached = self.cache.get(query_embedding=q_emb, scope=scope, is_diff_query=is_diff)

        if cached:
            cits = cached.get("citations", [])
            words = cached["answer"].split(" ")
            for i, word in enumerate(words):
                chunk = word if i == len(words) - 1 else word + " "
                yield {"type": "token", "token": chunk}
            conf_val = cached.get("confidence", 0.95)
            yield {
                "type": "done",
                "result": {
                    "answer": cached["answer"],
                    "citations": cits,
                    "confidence": conf_val * 100 if conf_val <= 1.0 else conf_val,
                    "route": "CACHE_HIT",
                    "llm_used": False,
                    "latency_ms": (time.time() - t_start) * 1000,
                    "fallback": False,
                    "model": "semantic-cache"
                }
            }
            return

        # If cache missed and embedding was not yet computed, compute now
        if q_emb is None:
            q_emb = self.embedder.embed_query(normalized_query)

        # 1.6 Classify Route on Cache Miss
        intent, complexity, route_name, meta = self.router.route(normalized_query)
        if temporal_context is None and (route_name in ("TEMPORAL_COMPARISON", "TEMPORAL") or intent in (Intent.TEMPORAL, Intent.COMPARISON)):
            temporal_context = self.version_resolver.resolve_temporal_context(normalized_query, user)
            scope = QueryScope.from_user(user, temporal_context, allowed_policy_ids=allowed_pids)
            is_diff = (route_name == "TEMPORAL_COMPARISON")

        # 2. Level 0: Fast Structured Fact Path
        if self.config.use_fact:
            fact_res = self.fact_resolver.try_resolve(normalized_query, scope=scope, temporal=temporal_context, user=user)
            if fact_res.found and fact_res.answer:
                cits = self.citation_validator.enrich_only(fact_res.citations)
                if self.config.use_cache:
                    self.cache.put(q_emb, fact_res.answer, cits, 1, scope=scope, confidence=fact_res.confidence, is_diff_query=is_diff, query=normalized_query)
                words = fact_res.answer.split(" ")
                for i, word in enumerate(words):
                    chunk = word if i == len(words) - 1 else word + " "
                    yield {"type": "token", "token": chunk}
                yield {
                    "type": "done",
                    "result": {
                        "answer": fact_res.answer,
                        "citations": cits,
                        "confidence": fact_res.confidence * 100,
                        "route": "FAST_PATH_FACT",
                        "llm_used": False,
                        "latency_ms": (time.time() - t_start) * 1000,
                        "fallback": False,
                        "model": "fact-engine"
                    }
                }
                return

        # 3. Level 1: Precomputed Canonical QA Fast Path
        if self.config.use_qa and not is_diff:
            qa_match = self.qa_matcher.match(normalized_query, q_emb, scope=scope, threshold=0.80)
            
            if qa_match:
                pol = qa_match.get("policy")
                ver = qa_match.get("version")
                is_auth = True
                conf_ok = True
                temp_ok = True
                if pol:
                    is_auth = self.evidence_filter.is_authorized_for_policy(scope, pol)
                    conf_ok = pol.confidentiality in scope.allowed_confidentiality
                if ver:
                    temp_ok = (not scope.target_date) or ver.is_valid_for_date(scope.target_date)

                if is_auth and conf_ok and temp_ok:
                    cits = self.citation_validator.enrich_only(qa_match["citations"])
                    if cits:
                        if self.config.use_cache:
                            self.cache.put(q_emb, qa_match["answer"], cits, 1, scope=scope, confidence=qa_match["confidence"], is_diff_query=is_diff, query=normalized_query)
                        words = qa_match["answer"].split(" ")
                        for i, word in enumerate(words):
                            chunk = word if i == len(words) - 1 else word + " "
                            yield {"type": "token", "token": chunk}
                        yield {
                            "type": "done",
                            "result": {
                                "answer": qa_match["answer"],
                                "citations": cits,
                                "confidence": qa_match["confidence"] * 100,
                                "route": "FAST_PATH_COMPILED_QA",
                                "llm_used": False,
                                "latency_ms": (time.time() - t_start) * 1000,
                                "fallback": False,
                                "model": "precompiled-qa"
                            }
                        }
                        return

        # 4. Level 3: Version Comparison Path (Strictly Authorized & Scalable)
        temporal_meta = meta.get("temporal", {})
        if temporal_meta.get("is_comparison") and temporal_meta.get("version_v1") and temporal_meta.get("version_v2"):
            v1_num = temporal_meta["version_v1"]
            v2_num = temporal_meta["version_v2"]

            # Scalable candidate lookup: query only relevant/authorized policies
            if temporal_context and temporal_context.policy_id:
                p_query = Policy.query.filter(Policy.id == temporal_context.policy_id)
            elif scope.allowed_policy_ids is not None:
                p_query = Policy.query.filter(Policy.id.in_(scope.allowed_policy_ids))
            else:
                p_query = Policy.query.filter(Policy.status == PolicyStatus.ACTIVE)

            candidate_policies = p_query.all()
            for p in candidate_policies:
                if p.title.lower() in normalized_query.lower() or any(w in p.title.lower() for w in normalized_query.lower().split() if len(w) > 3):
                    # SECURITY: Enforce authorization BEFORE loading comparison versions or computing diff
                    if not self.evidence_filter.is_authorized_for_policy(scope, p):
                        continue

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
                            
                        cits = self.citation_validator.enrich_only([
                            {"policy_id": p.id, "version_id": v1.id, "policy_name": p.title, "version": str(v1.version_num), "section": "Version Comparison", "page": 1},
                            {"policy_id": p.id, "version_id": v2.id, "policy_name": p.title, "version": str(v2.version_num), "section": "Version Comparison", "page": 1},
                        ])

                        diff_clauses = len(diff_res.get("added_clauses", [])) + len(diff_res.get("removed_clauses", [])) + len(diff_res.get("changed_clauses", []))
                        comparison_evidence_score = 85.0 if diff_clauses > 0 else 80.0

                        if self.config.use_cache:
                            self.cache.put(q_emb, diff_summary, cits, 2, scope=scope, confidence=comparison_evidence_score / 100.0, is_diff_query=True, query=normalized_query)

                        words = diff_summary.split(" ")
                        for i, word in enumerate(words):
                            chunk = word if i == len(words) - 1 else word + " "
                            yield {"type": "token", "token": chunk}
                        yield {
                            "type": "done",
                            "result": {
                                "answer": diff_summary,
                                "citations": cits,
                                "confidence": comparison_evidence_score,
                                "route": "TEMPORAL_COMPARISON",
                                "llm_used": False,
                                "latency_ms": (time.time() - t_start) * 1000,
                                "fallback": False,
                                "model": "diff-engine"
                            }
                        }
                        return

        # 5. Hybrid Retrieval (Dense + Sparse BM25) with Pre-filtering
        filters = {}
        if scope.allowed_policy_ids is not None:
            if len(scope.allowed_policy_ids) == 0:
                refusal = "I could not find sufficient authoritative evidence in the applicable policies."
                yield {"type": "token", "token": refusal}
                yield {
                    "type": "done",
                    "result": {
                        "answer": refusal,
                        "citations": [],
                        "confidence": 0,
                        "route": "REFUSAL",
                        "llm_used": False,
                        "latency_ms": (time.time() - t_start) * 1000,
                        "fallback": True,
                        "model": "retrieval-filter"
                    }
                }
                return
            if temporal_context and temporal_context.policy_id:
                if temporal_context.policy_id not in scope.allowed_policy_ids:
                    refusal = "I could not find sufficient authoritative evidence in the applicable policies."
                    yield {"type": "token", "token": refusal}
                    yield {
                        "type": "done",
                        "result": {
                            "answer": refusal,
                            "citations": [],
                            "confidence": 0,
                            "route": "REFUSAL",
                            "llm_used": False,
                            "latency_ms": (time.time() - t_start) * 1000,
                            "fallback": True,
                            "model": "retrieval-filter"
                        }
                    }
                    return
                filters["policy_id"] = temporal_context.policy_id
            else:
                filters["policy_id"] = list(scope.allowed_policy_ids)
        elif temporal_context and temporal_context.policy_id:
            filters["policy_id"] = temporal_context.policy_id

        if self.config.use_temporal_filter:
            if scope.target_date:
                from datetime import datetime, time as dt_time
                target_ts = int(datetime.combine(scope.target_date, dt_time.min).timestamp())
                filters["valid_from_ts"] = {"$lte": target_ts}
                filters["valid_to_ts"] = {"$gte": target_ts}
            elif not has_temporal_cue and not is_diff:
                filters["is_active"] = True

        raw_candidates = self.hybrid_retriever.search(normalized_query, filters=filters, top_k=25, query_embedding=q_emb)
        
        # 6. Authorization Filtering using unified QueryScope
        authorized_candidates = self.evidence_filter.filter_chunks(raw_candidates, scope)
        
        if not authorized_candidates:
            refusal = "I could not find sufficient authoritative evidence in the applicable policies."
            yield {"type": "token", "token": refusal}
            yield {
                "type": "done",
                "result": {
                    "answer": refusal,
                    "citations": [],
                    "confidence": 0,
                    "route": "REFUSAL",
                    "llm_used": False,
                    "latency_ms": (time.time() - t_start) * 1000,
                    "fallback": True,
                    "model": "retrieval-filter"
                }
            }
            return

        # 7. CrossEncoder Precision Reranking
        if self.config.use_rerank:
            ranked = self.reranker.rank(normalized_query, authorized_candidates, top_k=min(len(authorized_candidates), self.config.rerank_top_k))
            score_type = "rerank_prob"
        else:
            ranked = authorized_candidates[:min(len(authorized_candidates), self.config.rerank_top_k)]
            score_type = "rrf"

        if not ranked:
            ranked = authorized_candidates[:8]
            score_type = "rrf"

        # 8. Multi-Factor Confidence Scoring
        evidence = EvidencePack(
            query=normalized_query,
            route="HYBRID_RAG",
            chunks=ranked,
            scores=[c.get("rerank_score", c.get("hybrid_score", 0.5)) for c in ranked],
            score_type=score_type
        )
        
        conf = self.confidence_engine.score(normalized_query, evidence)
        if self.config.use_confidence_gate and conf.abstain:
            refusal = "I could not find sufficient authoritative evidence in the applicable policies."
            yield {"type": "token", "token": refusal}
            yield {
                "type": "done",
                "result": {
                    "answer": refusal,
                    "citations": [],
                    "confidence": conf.value * 100,
                    "route": "ABSTAIN",
                    "llm_used": False,
                    "latency_ms": (time.time() - t_start) * 1000,
                    "fallback": True,
                    "model": "confidence-gate"
                }
            }
            return

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
        citations = self.citation_validator.validate_and_enrich(raw_cits, scope=scope)

        # 9. Real-time Streaming Generation
        llm_used = False
        full_answer = ""
        
        if complexity >= ComplexityLevel.LEVEL_2_RETRIEVAL and self.llm.health_check():
            try:
                prompt = build_streaming_qa_prompt(normalized_query, ranked[:3])
                for token in self.llm.stream(prompt, system_prompt=STREAMING_POLICY_GROUNDING_PROMPT):
                    if token:
                        full_answer += token
                        yield {"type": "token", "token": token}
                
                if full_answer.strip() and verify_numeric_grounding(full_answer, ranked[:3]):
                    llm_used = True
                else:
                    full_answer = ""
            except Exception as e:
                full_answer = ""

        if not full_answer.strip():
            # Deterministic clean extraction: extract the most relevant sentence from the top chunk
            top_text = ranked[0].get("text", "").strip()
            top_section = ranked[0].get("section") or ranked[0].get("section_path") or "Policy"
            sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', top_text) if len(s.strip()) > 15]
            q_words = set(re.findall(r"\b[a-z0-9]+\b", normalized_query.lower())) - {"what", "when", "where", "which", "who", "whom", "how", "why", "does", "have", "policy", "the", "for", "and", "can", "are", "get", "with", "from", "that", "this", "our", "you", "your", "will", "shall", "is"}
            
            best_sentence = None
            best_score = 0
            for s in sentences:
                s_words = set(re.findall(r"\b[a-z0-9]+\b", s.lower()))
                overlap = len(q_words & s_words)
                if overlap > best_score:
                    best_score = overlap
                    best_sentence = s

            if best_sentence and best_score >= 2:
                policy_name = citations[0]["policy_name"] if citations else "Policy"
                version_num = citations[0]["version"] if citations else "1.0"
                full_answer = f"According to the {policy_name} (v{version_num}, {top_section}):\n{best_sentence}"
                
                words = full_answer.split(" ")
                for i, word in enumerate(words):
                    chunk = word if i == len(words) - 1 else word + " "
                    yield {"type": "token", "token": chunk}
            else:
                refusal = "I could not find sufficient authoritative evidence to answer this specific question."
                yield {"type": "token", "token": refusal}
                yield {
                    "type": "done",
                    "result": {
                        "answer": refusal,
                        "citations": [],
                        "confidence": 0,
                        "route": "ABSTAIN",
                        "llm_used": False,
                        "latency_ms": (time.time() - t_start) * 1000,
                        "fallback": True,
                        "model": "deterministic-rag"
                    }
                }
                return

        # Cache successful verified answer preserving confidence score
        if self.config.use_cache:
            self.cache.put(q_emb, full_answer, citations, len(ranked), scope=scope, model="qwen3" if llm_used else "deterministic-rag", confidence=conf.value, is_diff_query=is_diff, query=normalized_query)

        yield {
            "type": "done",
            "result": {
                "answer": full_answer,
                "citations": citations,
                "confidence": conf.value * 100,
                "route": "HYBRID_RAG",
                "llm_used": llm_used,
                "latency_ms": (time.time() - t_start) * 1000,
                "fallback": False,
                "model": "qwen3" if llm_used else "deterministic-rag"
            }
        }

_ENGINE = None
def get_query_engine(config: Optional[EngineConfig] = None) -> QueryEngine:
    global _ENGINE
    if config is not None:
        return QueryEngine(config=config)
    if _ENGINE is None:
        _ENGINE = QueryEngine()
    return _ENGINE
