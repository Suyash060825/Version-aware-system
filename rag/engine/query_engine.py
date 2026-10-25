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
from typing import Optional, List, Dict, Any, Set, Tuple

from models import Policy, PolicyVersion, PolicyStatus
from rag import metrics
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
from rag.authorization.evidence_filter import get_evidence_filter
from rag.verification.confidence import ConfidenceEngine
from rag.verification.entailment import get_entailment_verifier
from rag.verification.citation_validator import CitationValidator
from rag.versions.resolver import VersionResolver
from rag.versions.diff_engine import PolicyDiffEngine
from rag.generation.qwen import QwenLocalProvider, get_qwen_provider
from rag.generation.prompts import STREAMING_POLICY_GROUNDING_PROMPT, build_streaming_qa_prompt

logger = logging.getLogger("rag.engine.query_engine")

_IS_DIFF_RE = re.compile(
    r"\b(?:version\s+|v)?(\d+(?:\.\d+)?)\s*(?:and|vs|versus|to|\-)\s*(?:version\s+|v)?(\d+(?:\.\d+)?)\b",
    re.I
)

def _is_valid_diff_query(query: str) -> bool:
    for m in _IS_DIFF_RE.finditer(query):
        v1_raw = m.group(1)
        v2_raw = m.group(2)
        full = m.group(0).lower()
        if len(v1_raw) == 4 and len(v2_raw) == 4 and not ("v" in full or "version" in full):
            continue
        return True
    return False
_HAS_TEMPORAL_CUE_RE = re.compile(
    r"\b(?:in\s+20\d\d|back\s+in\s+20\d\d|as\s+of|before\s+|after\s+|between\s+|since\s+|until\s+|during\s+|historical|previous|prior|old\s+version|v\d+|version\s+\d+)\b",
    re.I
)
_NUM_RE = re.compile(r"\b\d+(?:\.\d+)?%?\b")
_YEAR_RE = re.compile(r"^(?:19|20)\d{2}$")
_STOPWORDS = {
    "what", "when", "where", "which", "who", "whom", "how", "why", "does",
    "have", "policy", "the", "for", "and", "can", "are", "get", "with",
    "from", "that", "this", "our", "you", "your", "will", "shall", "is", "under"
}

DEFAULT_REFUSAL_MESSAGE = "I could not find sufficient authoritative evidence in the applicable policies."

def extract_grounding_numbers(chunks: List[Dict[str, Any]]) -> Set[str]:
    """Precompute set of numerical tokens across context chunks in a single pass."""
    if not chunks:
        return set()
    context = " ".join([c.get("text", "") for c in chunks])
    return set(_NUM_RE.findall(context))

def verify_numeric_grounding(answer: str, chunks_or_ctx_nums: Any) -> bool:
    """
    Verifies that numerical figures, percentages, or metrics mentioned in the answer
    are grounded in the retrieved chunks or precomputed ctx_nums set, preventing hallucinated numbers.
    """
    if not answer:
        return True
    raw_nums = set(_NUM_RE.findall(answer))
    if not raw_nums:
        return True
    if isinstance(chunks_or_ctx_nums, (set, frozenset)):
        ctx_nums = chunks_or_ctx_nums
    else:
        ctx_nums = extract_grounding_numbers(chunks_or_ctx_nums)
    for num in raw_nums:
        if num in ctx_nums:
            continue
        num_clean = num.rstrip('%')
        if _YEAR_RE.match(num_clean) or (num_clean.isdigit() and int(num_clean) in range(0, 10)):
            continue
        if num.endswith("%") and num[:-1] in ctx_nums:
            continue
        return False
    return True

_GENERIC_WORDS = {
    "limit", "policy", "rules", "guidelines", "procedure", "allowed", "permitted",
    "employee", "company", "days", "year", "time", "standard", "work", "general"
}

def _extract_best_evidence_context(
    normalized_query: str,
    ranked: List[Dict[str, Any]],
    citations: List[Dict[str, Any]]
) -> Optional[str]:
    """
    Multi-sentence contextual evidence synthesis across top ranked chunks.
    Unified single source of truth across answer() and stream_answer().
    """
    if not ranked:
        return None
    top_section = ranked[0].get("section") or ranked[0].get("section_path") or "Policy"
    top_text = ranked[0].get("text", "").strip()
    q_words = set(re.findall(r"\b[a-z0-9]+\b", normalized_query.lower())) - _STOPWORDS

    if not q_words:
        return None

    # Guard against ungrounded / underspecified queries (F16 Safe Abstention)
    substantive_q_words = q_words - _GENERIC_WORDS
    if not substantive_q_words:
        return None

    scored_candidates = []
    for rc in ranked[:5]:
        chunk_text = rc.get("text", "").strip()
        chunk_sec = rc.get("section") or rc.get("section_path") or "Policy"
        policy_title_words = set(re.findall(r"\b[a-z0-9]+\b", str(rc.get("policy_name", "")).lower())) - _STOPWORDS
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', chunk_text) if len(s.strip()) > 15]
        for s_idx, s in enumerate(sentences):
            s_words = set(re.findall(r"\b[a-z0-9]+\b", s.lower()))
            overlap = len(q_words & s_words)
            if overlap >= 1:
                # Substantive scoring: weight question words not in the policy title higher than title word repetition
                substantive_overlap = len(substantive_q_words & s_words)
                total_score = substantive_overlap * 3 + overlap
                scored_candidates.append((total_score, substantive_overlap, rc, chunk_sec, s_idx, s, sentences))

    if scored_candidates:
        scored_candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
        top_score, top_sub, best_chunk, best_sec, best_idx, best_sent, all_sents = scored_candidates[0]

        # If question had substantive keywords, require at least one substantive keyword match
        if substantive_q_words and top_sub == 0 and len(q_words) > 1:
            return None

        # Reorder citations so winning chunk citation is first
        winning_pid = best_chunk.get("policy_id")
        winning_sec = best_chunk.get("section") or best_chunk.get("section_path")
        for idx, cit in enumerate(citations):
            if cit.get("policy_id") == winning_pid and (cit.get("section") == winning_sec or not winning_sec):
                if idx > 0:
                    citations.insert(0, citations.pop(idx))
                break

        start_i = max(0, best_idx - 1)
        end_i = min(len(all_sents), best_idx + 2)
        context_paragraph = " ".join(all_sents[start_i:end_i])

        policy_name = best_chunk.get("policy_name") or (citations[0]["policy_name"] if citations else "Policy")
        version_raw = best_chunk.get("version") or (citations[0]["version"] if citations else "1.0")
        version_num = str(version_raw).lstrip("v")

        # Multi-part question evidence synthesis across distinct chunks/sections
        top_chunk_words = set(re.findall(r"\b[a-z0-9]+\b", context_paragraph.lower()))
        uncovered = q_words - top_chunk_words
        if len(uncovered) >= 2:
            for cand in scored_candidates[1:]:
                cand_chunk, cand_sec, cand_idx, cand_sent, cand_sents = cand[2], cand[3], cand[4], cand[5], cand[6]
                cand_sent_words = set(re.findall(r"\b[a-z0-9]+\b", cand_sent.lower()))
                if cand_chunk != best_chunk and len(uncovered & cand_sent_words) >= 1:
                    s_i = max(0, cand_idx - 1)
                    e_i = min(len(cand_sents), cand_idx + 2)
                    sec_context = " ".join(cand_sents[s_i:e_i])
                    sec_pname = cand_chunk.get("policy_name") or (citations[1]["policy_name"] if len(citations) > 1 else "Policy")
                    sec_vraw = cand_chunk.get("version") or (citations[1]["version"] if len(citations) > 1 else "1.0")
                    sec_vnum = str(sec_vraw).lstrip("v")
                    return f"According to the {policy_name} (v{version_num}, {best_sec}):\n{context_paragraph}\n\nAdditionally, according to {sec_pname} (v{sec_vnum}, {cand_sec}):\n{sec_context}"

        return f"According to the {policy_name} (v{version_num}, {best_sec}):\n{context_paragraph}"
    elif top_text and q_words and substantive_q_words:
        top_words = set(re.findall(r"\b[a-z0-9]+\b", top_text.lower()))
        if len(substantive_q_words & top_words) >= 1:
            policy_name = citations[0]["policy_name"] if citations else "Policy"
            version_raw = citations[0]["version"] if citations else "1.0"
            version_num = str(version_raw).lstrip("v")
            return f"According to the {policy_name} (v{version_num}, {top_section}):\n{top_text}"
    return None


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
        self.llm = get_qwen_provider()
        self.cache = get_cache()
        self.embedder = get_embedder()

    def _build_retrieval_filters(
        self,
        scope: QueryScope,
        temporal_context: Any,
        has_temporal_cue: bool,
        is_diff: bool,
        normalized_query: str = "",
        q_emb: Optional[List[float]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Builds authorization and temporal pre-filters for hybrid retrieval.
        Returns None if authorization is impossible (fail-closed).
        Uses semantic policy title identification (FIX 1) to eliminate false substring anchors.
        """
        filters: Dict[str, Any] = {}
        if scope.allowed_policy_ids is not None:
            if len(scope.allowed_policy_ids) == 0:
                return None
            if temporal_context and temporal_context.policy_id:
                if temporal_context.policy_id not in scope.allowed_policy_ids:
                    return None
                filters["policy_id"] = temporal_context.policy_id
            else:
                matched_pid = None
                if q_emb is None and normalized_query:
                    q_emb = self.embedder.embed_query(normalized_query)
                if q_emb is not None:
                    from rag.engine.policy_title_index import get_policy_title_index
                    title_idx = get_policy_title_index()
                    top_pid, top_sim = title_idx.find_top_policy_similarity(q_emb)
                    if top_sim > 0.75 and top_pid is not None:
                        if top_pid in scope.allowed_policy_ids:
                            matched_pid = top_pid
                        else:
                            return None  # Explicit request for unauthorized policy -> fail closed
                if matched_pid is not None:
                    filters["policy_id"] = matched_pid
                else:
                    filters["policy_id"] = list(scope.allowed_policy_ids)
        elif temporal_context and temporal_context.policy_id:
            filters["policy_id"] = temporal_context.policy_id
        else:
            if q_emb is None and normalized_query:
                q_emb = self.embedder.embed_query(normalized_query)
            if q_emb is not None:
                from rag.engine.policy_title_index import get_policy_title_index
                title_idx = get_policy_title_index()
                top_pid, top_sim = title_idx.find_top_policy_similarity(q_emb)
                if top_sim > 0.75 and top_pid is not None:
                    filters["policy_id"] = top_pid

        if self.config.use_temporal_filter:
            if scope.target_date:
                from datetime import datetime, time as dt_time
                target_ts = int(datetime.combine(scope.target_date, dt_time.min).timestamp())
                filters["valid_from_ts"] = {"$lte": target_ts}
                filters["valid_to_ts"] = {"$gte": target_ts}
            elif scope.requested_version:
                # Version-specific filter: pin to exact requested version label or number
                ver_clean = str(scope.requested_version).lower().lstrip("v")
                filters["version_num"] = float(ver_clean) if ver_clean.replace(".", "", 1).isdigit() else scope.requested_version
            elif not has_temporal_cue and not is_diff:
                filters["is_active"] = True

        return filters

    def _retrieve_and_rank(
        self,
        normalized_query: str,
        q_emb: List[float],
        scope: QueryScope,
        filters: Dict[str, Any],
        is_fallthrough: bool = False
    ) -> Optional[Tuple[List[Dict[str, Any]], str, Any, List[Dict[str, Any]]]]:
        """
        Shared retrieval, authorization filtering, cross-encoder reranking,
        confidence scoring, and citation extraction.
        Returns (ranked_chunks, score_type, conf, citations) or None if evidence absent.
        """
        # FIX 7: Adaptive top_k scaling
        if scope.allowed_policy_ids is not None:
            effective_top_k = min(50, max(20, len(scope.allowed_policy_ids) * 15))
        else:
            effective_top_k = 50

        t_search0 = time.perf_counter()
        with metrics.RETRIEVAL_LATENCY.time():
            raw_candidates = self.hybrid_retriever.search(normalized_query, filters=filters, top_k=effective_top_k, query_embedding=q_emb)
        t_search_ms = (time.perf_counter() - t_search0) * 1000

        pre_filter_count = len(raw_candidates)
        authorized_candidates = self.evidence_filter.filter_chunks(raw_candidates, scope)
        if len(authorized_candidates) < 5:
            logger.warning("Fewer than 5 authorized candidates (%d); re-querying with top_k=100", len(authorized_candidates))
            t_search_re0 = time.perf_counter()
            with metrics.RETRIEVAL_LATENCY.time():
                raw_candidates = self.hybrid_retriever.search(normalized_query, filters=filters, top_k=100, query_embedding=q_emb)
            t_search_ms += (time.perf_counter() - t_search_re0) * 1000
            pre_filter_count = len(raw_candidates)
            authorized_candidates = self.evidence_filter.filter_chunks(raw_candidates, scope)

        post_filter_count = len(authorized_candidates)
        if not authorized_candidates:
            self._last_retrieval_stats = {
                "pre_filter_count": pre_filter_count,
                "post_filter_count": 0,
                "post_rerank_count": 0,
                "pre_filter_chunk_ids": [c.get("chunk_id") or c.get("id") for c in raw_candidates if (c.get("chunk_id") or c.get("id"))],
                "authorized_chunk_ids": [],
                "post_rerank_chunk_ids": [],
                "timing_hybrid_retrieve_ms": t_search_ms,
                "timing_rerank_ms": 0.0,
                "timing_confidence_score_ms": 0.0
            }
            return None

        # FIX 7: Reduce rerank_top_k from 8 to 5 for Tier-0/Tier-1 fallthrough
        target_rerank_k = 5 if is_fallthrough else self.config.rerank_top_k

        t_rerank0 = time.perf_counter()
        if self.config.use_rerank:
            with metrics.RERANK_LATENCY.time():
                ranked = self.reranker.rank(normalized_query, authorized_candidates, top_k=min(len(authorized_candidates), target_rerank_k))
            score_type = "rerank_prob"
        else:
            ranked = authorized_candidates[:min(len(authorized_candidates), target_rerank_k)]
            score_type = "rrf"

        if not ranked:
            ranked = authorized_candidates[:target_rerank_k]
            score_type = "rrf"
        t_rerank_ms = (time.perf_counter() - t_rerank0) * 1000

        post_rerank_count = len(ranked)

        evidence = EvidencePack(
            query=normalized_query,
            route="HYBRID_RAG",
            chunks=ranked,
            scores=[c.get("rerank_score", c.get("hybrid_score", 0.5)) for c in ranked],
            score_type=score_type
        )
        t_conf0 = time.perf_counter()
        conf = self.confidence_engine.score(normalized_query, evidence)
        t_conf_ms = (time.perf_counter() - t_conf0) * 1000

        self._last_retrieval_stats = {
            "pre_filter_count": pre_filter_count,
            "post_filter_count": post_filter_count,
            "post_rerank_count": post_rerank_count,
            "pre_filter_chunk_ids": [c.get("chunk_id") or c.get("id") for c in raw_candidates if (c.get("chunk_id") or c.get("id"))],
            "authorized_chunk_ids": [c.get("chunk_id") or c.get("id") for c in authorized_candidates if (c.get("chunk_id") or c.get("id"))],
            "post_rerank_chunk_ids": [c.get("chunk_id") or c.get("id") for c in ranked if (c.get("chunk_id") or c.get("id"))],
            "timing_hybrid_retrieve_ms": t_search_ms,
            "timing_rerank_ms": t_rerank_ms,
            "timing_confidence_score_ms": t_conf_ms
        }

        # Build clean citations deduplicated by (policy_id, section)
        seen_cit_keys = set()
        raw_cits = []
        for c in ranked:
            p_id = c.get("policy_id")
            try:
                p_id_int = int(p_id) if p_id is not None else None
            except (ValueError, TypeError):
                p_id_int = None
            if not p_id_int or p_id_int <= 0:
                continue
            sec = c.get("section") or c.get("section_path") or "General"
            cit_key = (p_id_int, sec)
            if cit_key in seen_cit_keys:
                continue
            seen_cit_keys.add(cit_key)
            raw_cits.append({
                "chunk_id": c.get("chunk_id") or c.get("id"),
                "policy_id": p_id_int,
                "version_id": c.get("version_id"),
                "policy_name": c.get("policy_name", "Policy"),
                "version": c.get("version", "1.0"),
                "section": sec,
                "page": c.get("page", 1)
            })
            if len(raw_cits) >= 5:
                break
        citations = self.citation_validator.validate_and_enrich(raw_cits, scope=scope)

        return ranked, score_type, conf, citations

    def _run_version_comparison(
        self,
        normalized_query: str,
        meta: Dict[str, Any],
        temporal_context: Any,
        scope: QueryScope,
        q_emb: Optional[List[float]] = None
    ) -> Optional[Tuple[str, List[Dict[str, Any]], float, List[str]]]:
        """
        Shared Level 3 version comparison execution across answer() and stream_answer().
        Returns (diff_summary, citations, confidence_score, policy_versions) or None.
        """
        temporal_meta = meta.get("temporal", {})
        v1_num = temporal_meta.get("version_v1")
        v2_num = temporal_meta.get("version_v2")

        if not (v1_num and v2_num):
            t_query = getattr(temporal_context, "temporal_query", None)
            if t_query and getattr(t_query, "comparison_versions", None) and len(t_query.comparison_versions) >= 2:
                v1_num = t_query.comparison_versions[0]
                v2_num = t_query.comparison_versions[1]
            else:
                for m in _IS_DIFF_RE.finditer(normalized_query):
                    c1, c2 = m.group(1), m.group(2)
                    full = m.group(0).lower()
                    if len(c1) == 4 and len(c2) == 4 and not ("v" in full or "version" in full):
                        continue
                    v1_num, v2_num = c1, c2
                    break

        if not (v1_num and v2_num):
            return None

        if temporal_context and temporal_context.policy_id:
            p_query = Policy.query.filter(Policy.id == temporal_context.policy_id)
        elif scope.allowed_policy_ids is not None:
            p_query = Policy.query.filter(Policy.id.in_(scope.allowed_policy_ids))
        else:
            p_query = Policy.query.filter(Policy.status == PolicyStatus.ACTIVE)

        candidate_policies = p_query.all()
        q_lower = normalized_query.lower()
        q_words = set(re.findall(r"\b[a-z0-9]+\b", q_lower)) - _STOPWORDS

        scored_policies = []
        for p in candidate_policies:
            p_title_lower = p.title.lower()
            p_title_words = set(re.findall(r"\b[a-z0-9]+\b", p_title_lower)) - _STOPWORDS
            overlap = len(q_words & p_title_words)
            if p_title_lower in q_lower:
                overlap += 10
            if overlap > 0:
                scored_policies.append((overlap, p))

        scored_policies.sort(key=lambda x: x[0], reverse=True)

        for _, p in scored_policies:
            if not self.evidence_filter.is_authorized_for_policy(scope, p):
                continue

            try:
                v1_float = float(v1_num)
            except (ValueError, TypeError):
                v1_float = None
            try:
                v2_float = float(v2_num)
            except (ValueError, TypeError):
                v2_float = None

            v1_cond = PolicyVersion.version_label.ilike(f"%{v1_num}%")
            if v1_float is not None:
                v1_cond = (PolicyVersion.version_num == v1_float) | v1_cond
            v1 = PolicyVersion.query.filter(PolicyVersion.policy_id == p.id, v1_cond).first()

            v2_cond = PolicyVersion.version_label.ilike(f"%{v2_num}%")
            if v2_float is not None:
                v2_cond = (PolicyVersion.version_num == v2_float) | v2_cond
            v2 = PolicyVersion.query.filter(PolicyVersion.policy_id == p.id, v2_cond).first()

            if v1 and v2:
                diff_res = self.diff_engine.compute_diff(v1.content or "", v2.content or "", version_a_id=v1.id, version_b_id=v2.id)
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

                return diff_summary, cits, comparison_evidence_score, [str(v1.version_num), str(v2.version_num)]

        return None

    def answer(self, query: str, user=None, session_id: str = None) -> QueryResult:
        t_start = time.time()
        
        # 1. Normalize Query & Fast Authorization Scope
        t_ns0 = time.perf_counter()
        normalized_query = self.router.normalize(query)
        allowed_pids = self.evidence_filter.get_allowed_policy_ids(user)

        # Fast temporal cues check
        is_diff = _is_valid_diff_query(normalized_query)
        has_temporal_cue = is_diff or bool(_HAS_TEMPORAL_CUE_RE.search(normalized_query))

        temporal_context = self.version_resolver.resolve_temporal_context(normalized_query, user) if has_temporal_cue else None
        scope = QueryScope.from_user(user, temporal_context, allowed_policy_ids=allowed_pids)
        t_ns_ms = (time.perf_counter() - t_ns0) * 1000

        # 1.5 Scoped L1 Exact Match Cache Lookup (Sub-millisecond, zero embedding needed)
        t_c0 = time.perf_counter()
        cached = None
        if self.config.use_cache:
            cached = self.cache.get(query=normalized_query, scope=scope, is_diff_query=is_diff)
        t_c_ms = (time.perf_counter() - t_c0) * 1000

        if cached:
            metrics.CACHE_HITS.inc()
            cits = cached.get("citations", [])
            cache_usage = {
                "timing_ms": {
                    "normalize_scope_ms": round(t_ns_ms, 2),
                    "cache_lookup_ms": round(t_c_ms, 2),
                    "fact_lookup_ms": 0.0,
                    "embed_query_ms": 0.0,
                    "hybrid_retrieve_ms": 0.0,
                    "rerank_ms": 0.0,
                    "confidence_score_ms": 0.0,
                    "llm_generate_ms": 0.0
                }
            }
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
                abstained=False,
                model=cached.get("model", "semantic-cache"),
                usage=cache_usage
            )

        # 1.6 Classify Route BEFORE embedding (F1)
        intent, complexity, route_name, meta = self.router.route(normalized_query, pre_normalized=True)
        if temporal_context is None and (route_name in ("TEMPORAL_COMPARISON", "TEMPORAL") or intent in (Intent.TEMPORAL, Intent.COMPARISON)):
            temporal_context = self.version_resolver.resolve_temporal_context(normalized_query, user)
            scope = QueryScope.from_user(user, temporal_context, allowed_policy_ids=allowed_pids)
            is_diff = (route_name == "TEMPORAL_COMPARISON")

        t_fact_ms = 0.0
        # 2. Level 0: Fast Structured Fact Path (Zero embedding needed!)
        if self.config.use_fact:
            t_f0 = time.perf_counter()
            fact_res = self.fact_resolver.try_resolve(normalized_query, scope=scope, temporal=temporal_context, user=user)
            t_fact_ms = (time.perf_counter() - t_f0) * 1000
            if fact_res.found and fact_res.answer:
                cits = self.citation_validator.enrich_only(fact_res.citations)
                if self.config.use_cache:
                    self.cache.put(None, fact_res.answer, cits, 1, scope=scope, confidence=fact_res.confidence, is_diff_query=is_diff, query=normalized_query)
                fact_usage = {
                    "timing_ms": {
                        "normalize_scope_ms": round(t_ns_ms, 2),
                        "cache_lookup_ms": round(t_c_ms, 2),
                        "fact_lookup_ms": round(t_fact_ms, 2),
                        "embed_query_ms": 0.0,
                        "hybrid_retrieve_ms": 0.0,
                        "rerank_ms": 0.0,
                        "confidence_score_ms": 0.0,
                        "llm_generate_ms": 0.0
                    }
                }
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
                    abstained=False,
                    model="fact-engine",
                    usage=fact_usage
                )

        # Fact path missed. NOW embed query for L2 vector cache, QA ANN search, and Hybrid retrieval (F1)
        t_e0 = time.perf_counter()
        q_emb = self.embedder.embed_query(normalized_query)
        t_emb_ms = (time.perf_counter() - t_e0) * 1000
        if self.config.use_cache:
            cached = self.cache.get(query_embedding=q_emb, scope=scope, is_diff_query=is_diff)
            if cached:
                metrics.CACHE_HITS.inc()
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
                    abstained=False,
                    model=cached.get("model", "semantic-cache")
                )
            metrics.CACHE_MISSES.labels(reason="miss").inc()

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
                            abstained=False,
                            model="precompiled-qa"
                        )

        # 4. Level 3: Version Comparison Path (F3 shared helper)
        comp_res = self._run_version_comparison(normalized_query, meta, temporal_context, scope, q_emb=q_emb)
        if comp_res:
            diff_summary, cits, comp_conf, p_versions = comp_res
            return QueryResult(
                answer=diff_summary,
                route="TEMPORAL_COMPARISON",
                confidence=comp_conf,
                citations=cits,
                policy_versions=p_versions,
                latency_ms=(time.time() - t_start) * 1000,
                llm_used=False,
                retrieval_count=2,
                reranker_used=False,
                abstained=False,
                model="diff-engine"
            )

        # 5. Hybrid Retrieval (Dense + Sparse BM25) with Pre-filtering (F3 shared helper)
        retrieval_query = self.router.expand_acronyms(normalized_query)
        filters = self._build_retrieval_filters(scope, temporal_context, has_temporal_cue, is_diff, normalized_query=normalized_query, q_emb=q_emb)
        if filters is None:
            return QueryResult.abstained(DEFAULT_REFUSAL_MESSAGE, (time.time() - t_start) * 1000, abstain_reason="unauthorized")

        retrieval_pack = self._retrieve_and_rank(retrieval_query, q_emb, scope, filters, is_fallthrough=True)
        if not retrieval_pack:
            return QueryResult.abstained(DEFAULT_REFUSAL_MESSAGE, (time.time() - t_start) * 1000, abstain_reason="low_retrieval")

        ranked, score_type, conf, citations = retrieval_pack

        is_synthesis_query = getattr(self.config, "use_llm", True) and (
            "summary" in normalized_query.lower() or "explain" in normalized_query.lower() or "compare" in normalized_query.lower()
        )
        if self.config.use_confidence_gate and conf.abstain and not is_synthesis_query:
            return QueryResult.abstained(DEFAULT_REFUSAL_MESSAGE, (time.time() - t_start) * 1000, abstain_reason=conf.abstain_reason)

        # 9. Answer Generation: Grounded Evidence Extraction vs Local LLM
        ctx_nums = extract_grounding_numbers(ranked[:5])
        llm_used = False
        final_answer = None
        nli_verdict = "none"
        nli_entail_score = 0.0
        nli_contra_score = 0.0
        llm_time_ms = 0.0
        llm_token_count = 0

        if getattr(self.config, "use_llm", True) and (complexity >= ComplexityLevel.LEVEL_2_RETRIEVAL or is_synthesis_query) and self.llm.health_check():
            max_tokens = 200
            t_llm = time.time()
            try:
                llm_output = self.llm.generate_grounded_answer(normalized_query, ranked[:5], max_tokens=max_tokens)
                llm_time_ms = (time.time() - t_llm) * 1000
                ans_text = llm_output.get("answer", "").strip() if llm_output else ""
                if llm_output and ans_text and ans_text != "INSUFFICIENT_EVIDENCE" and not ans_text.startswith("INSUFFICIENT_EVIDENCE"):
                    ans_candidate = ans_text
                    if verify_numeric_grounding(ans_candidate, ctx_nums):
                        if self.config.use_nli:
                            entail_res = self.entailment_verifier.verify(ans_candidate, ranked[:5])
                            # Strict grounding: only accept positive entailment; reject contradictions and ungrounded neutral/unknown claims
                            is_grounded = bool(getattr(entail_res, "is_entailed", False)) and (getattr(entail_res, "verdict", "UNKNOWN") == "ENTAILMENT")
                            nli_verdict = getattr(entail_res, "verdict", "UNKNOWN")
                            nli_entail_score = getattr(entail_res, "score", 0.0)
                            nli_contra_score = getattr(entail_res, "contra_score", 0.0)
                        else:
                            is_grounded = True
                            nli_verdict = "NLI_DISABLED"
                            nli_entail_score = 1.0
                            nli_contra_score = 0.0

                        if is_grounded:
                            final_answer = ans_candidate
                            llm_used = True
                    else:
                        metrics.GROUNDING_REJECTIONS.inc()
            except TimeoutError as te:
                logger.warning(f"Local LLM inference timeout: {te}. Falling back to deterministic grounded extraction.")
            except Exception as e:
                logger.warning(f"Local LLM inference encountered error: {e}. Falling back to deterministic grounded extraction.")

        if not final_answer:
            final_answer = _extract_best_evidence_context(normalized_query, ranked, citations)
            if not final_answer:
                return QueryResult.abstained(DEFAULT_REFUSAL_MESSAGE, (time.time() - t_start) * 1000, abstain_reason="insufficient_evidence")

        if llm_used and final_answer:
            llm_token_count = len(re.findall(r"\w+", final_answer))

        # Cache successful verified answer (F8: both query string and embedding always passed)
        if self.config.use_cache:
            self.cache.put(q_emb, final_answer, citations, len(ranked), scope=scope, model="qwen3" if llm_used else "deterministic-rag", confidence=conf.value, is_diff_query=is_diff, query=normalized_query)

        retrieval_stats = getattr(self, "_last_retrieval_stats", {})
        usage_data = dict(retrieval_stats)
        usage_data["timing_ms"] = {
            "normalize_scope_ms": round(t_ns_ms, 2),
            "cache_lookup_ms": round(t_c_ms, 2),
            "fact_lookup_ms": round(t_fact_ms, 2),
            "embed_query_ms": round(t_emb_ms, 2),
            "hybrid_retrieve_ms": round(retrieval_stats.get("timing_hybrid_retrieve_ms", 0.0), 2),
            "rerank_ms": round(retrieval_stats.get("timing_rerank_ms", 0.0), 2),
            "confidence_score_ms": round(retrieval_stats.get("timing_confidence_score_ms", 0.0), 2),
            "llm_generate_ms": round(llm_time_ms, 2)
        }

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
            abstained=False,
            model="qwen3" if llm_used else "deterministic-rag",
            usage=usage_data,
            abstain_reason=conf.abstain_reason,
            nli_verdict=nli_verdict,
            nli_entailment_score=nli_entail_score,
            nli_contradiction_score=nli_contra_score,
            llm_token_count=llm_token_count,
            llm_time_ms=llm_time_ms
        )

    def stream_answer(self, query: str, user=None, session_id: str = None):
        """
        Token-by-token streaming response generator for low-latency interactive UI chat.
        Implements identical multi-tier routing, security, and verified fallback.
        """
        t_start = time.time()

        # 1. Normalize Query & Fast Authorization Scope
        normalized_query = self.router.normalize(query)
        allowed_pids = self.evidence_filter.get_allowed_policy_ids(user)

        # Fast temporal cues check
        is_diff = _is_valid_diff_query(normalized_query)
        has_temporal_cue = is_diff or bool(_HAS_TEMPORAL_CUE_RE.search(normalized_query))

        temporal_context = self.version_resolver.resolve_temporal_context(normalized_query, user) if has_temporal_cue else None
        scope = QueryScope.from_user(user, temporal_context, allowed_policy_ids=allowed_pids)

        # 1.5 Scoped L1 Exact Match Cache Lookup (Sub-millisecond, zero embedding needed)
        cached = None
        if self.config.use_cache:
            cached = self.cache.get(query=normalized_query, scope=scope, is_diff_query=is_diff)

        if cached:
            metrics.CACHE_HITS.inc()
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
                    "confidence": conf_val,
                    "route": "CACHE_HIT",
                    "llm_used": False,
                    "latency_ms": (time.time() - t_start) * 1000,
                    "fallback": False,
                    "model": cached.get("model", "semantic-cache")
                }
            }
            return

        # 1.6 Classify Route BEFORE embedding (F1)
        intent, complexity, route_name, meta = self.router.route(normalized_query, pre_normalized=True)
        if temporal_context is None and (route_name in ("TEMPORAL_COMPARISON", "TEMPORAL") or intent in (Intent.TEMPORAL, Intent.COMPARISON)):
            temporal_context = self.version_resolver.resolve_temporal_context(normalized_query, user)
            scope = QueryScope.from_user(user, temporal_context, allowed_policy_ids=allowed_pids)
            is_diff = (route_name == "TEMPORAL_COMPARISON")

        # 2. Level 0: Fast Structured Fact Path (Zero embedding needed!)
        if self.config.use_fact:
            fact_res = self.fact_resolver.try_resolve(normalized_query, scope=scope, temporal=temporal_context, user=user)
            if fact_res.found and fact_res.answer:
                cits = self.citation_validator.enrich_only(fact_res.citations)
                if self.config.use_cache:
                    self.cache.put(None, fact_res.answer, cits, 1, scope=scope, confidence=fact_res.confidence, is_diff_query=is_diff, query=normalized_query)
                words = fact_res.answer.split(" ")
                for i, word in enumerate(words):
                    chunk = word if i == len(words) - 1 else word + " "
                    yield {"type": "token", "token": chunk}
                yield {
                    "type": "done",
                    "result": {
                        "answer": fact_res.answer,
                        "citations": cits,
                        "confidence": fact_res.confidence,
                        "route": "FAST_PATH_FACT",
                        "llm_used": False,
                        "latency_ms": (time.time() - t_start) * 1000,
                        "fallback": False,
                        "model": "fact-engine"
                    }
                }
                return

        # Fact path missed. NOW embed query for L2 vector cache, QA ANN search, and Hybrid retrieval (F1)
        q_emb = self.embedder.embed_query(normalized_query)
        if self.config.use_cache:
            cached = self.cache.get(query_embedding=q_emb, scope=scope, is_diff_query=is_diff)
            if cached:
                metrics.CACHE_HITS.inc()
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
                        "confidence": conf_val,
                        "route": "CACHE_HIT",
                        "llm_used": False,
                        "latency_ms": (time.time() - t_start) * 1000,
                        "fallback": False,
                        "model": cached.get("model", "semantic-cache")
                    }
                }
                return
            metrics.CACHE_MISSES.labels(reason="miss").inc()

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
                                "confidence": qa_match["confidence"],
                                "route": "FAST_PATH_COMPILED_QA",
                                "llm_used": False,
                                "latency_ms": (time.time() - t_start) * 1000,
                                "fallback": False,
                                "model": "precompiled-qa"
                            }
                        }
                        return

        # 4. Level 3: Version Comparison Path (F3 shared helper)
        comp_res = self._run_version_comparison(normalized_query, meta, temporal_context, scope, q_emb=q_emb)
        if comp_res:
            diff_summary, cits, comp_conf, p_versions = comp_res
            words = diff_summary.split(" ")
            for i, word in enumerate(words):
                chunk = word if i == len(words) - 1 else word + " "
                yield {"type": "token", "token": chunk}
            yield {
                "type": "done",
                "result": {
                    "answer": diff_summary,
                    "citations": cits,
                    "confidence": comp_conf,
                    "route": "TEMPORAL_COMPARISON",
                    "llm_used": False,
                    "latency_ms": (time.time() - t_start) * 1000,
                    "fallback": False,
                    "model": "diff-engine"
                }
            }
            return

        # 5. Hybrid Retrieval (Dense + Sparse BM25) with Pre-filtering (F3 shared helper)
        filters = self._build_retrieval_filters(scope, temporal_context, has_temporal_cue, is_diff, normalized_query=normalized_query, q_emb=q_emb)
        if filters is None:
            yield {"type": "token", "token": DEFAULT_REFUSAL_MESSAGE}
            yield {
                "type": "done",
                "result": {
                    "answer": DEFAULT_REFUSAL_MESSAGE,
                    "citations": [],
                    "confidence": 0.0,
                    "route": "REFUSAL",
                    "llm_used": False,
                    "latency_ms": (time.time() - t_start) * 1000,
                    "fallback": True,
                    "model": "retrieval-filter"
                }
            }
            return

        retrieval_pack = self._retrieve_and_rank(normalized_query, q_emb, scope, filters, is_fallthrough=True)
        if not retrieval_pack:
            yield {"type": "token", "token": DEFAULT_REFUSAL_MESSAGE}
            yield {
                "type": "done",
                "result": {
                    "answer": DEFAULT_REFUSAL_MESSAGE,
                    "citations": [],
                    "confidence": 0.0,
                    "route": "REFUSAL",
                    "llm_used": False,
                    "latency_ms": (time.time() - t_start) * 1000,
                    "fallback": True,
                    "model": "retrieval-filter"
                }
            }
            return

        ranked, score_type, conf, citations = retrieval_pack

        if self.config.use_confidence_gate and conf.abstain:
            yield {"type": "token", "token": DEFAULT_REFUSAL_MESSAGE}
            yield {
                "type": "done",
                "result": {
                    "answer": DEFAULT_REFUSAL_MESSAGE,
                    "citations": [],
                    "confidence": conf.value,
                    "route": "ABSTAIN",
                    "llm_used": False,
                    "latency_ms": (time.time() - t_start) * 1000,
                    "fallback": True,
                    "model": "confidence-gate"
                }
            }
            return

        # 9. Real-time Streaming Generation (F2: buffer tokens until verified)
        ctx_nums = extract_grounding_numbers(ranked[:5])
        llm_used = False
        full_answer = ""
        # F5: health_check called once in stream_answer
        llm_available = self.llm.health_check()
        
        if complexity >= ComplexityLevel.LEVEL_2_RETRIEVAL and llm_available:
            try:
                prompt = build_streaming_qa_prompt(normalized_query, ranked[:5])
                token_buffer = []
                for token in self.llm.stream(prompt, system_prompt=STREAMING_POLICY_GROUNDING_PROMPT):
                    if token:
                        token_buffer.append(token)
                candidate_text = "".join(token_buffer).strip()
                if (
                    candidate_text
                    and candidate_text != "INSUFFICIENT_EVIDENCE"
                    and not candidate_text.startswith("INSUFFICIENT_EVIDENCE")
                    and verify_numeric_grounding(candidate_text, ctx_nums)
                ):
                    for token in token_buffer:
                        yield {"type": "token", "token": token}
                    full_answer = candidate_text
                    llm_used = True
                else:
                    if candidate_text:
                        metrics.GROUNDING_REJECTIONS.inc()
                    full_answer = ""
            except Exception as e:
                logger.warning(f"Streaming LLM failure: {e}. Falling back to deterministic context.")
                full_answer = ""

        # Deterministic Grounded Fallback if LLM rejected or unavailable
        if not full_answer.strip():
            full_answer = _extract_best_evidence_context(normalized_query, ranked, citations)
            if full_answer:
                words = full_answer.split(" ")
                for i, word in enumerate(words):
                    chunk = word if i == len(words) - 1 else word + " "
                    yield {"type": "token", "token": chunk}
            else:
                yield {"type": "token", "token": DEFAULT_REFUSAL_MESSAGE}
                yield {
                    "type": "done",
                    "result": {
                        "answer": DEFAULT_REFUSAL_MESSAGE,
                        "citations": [],
                        "confidence": conf.value,
                        "route": "ABSTAIN",
                        "llm_used": False,
                        "latency_ms": (time.time() - t_start) * 1000,
                        "fallback": True,
                        "model": "no-evidence"
                    }
                }
                return

        # Cache successful verified answer (F8: always pass both query string and embedding)
        if self.config.use_cache:
            self.cache.put(q_emb, full_answer, citations, len(ranked), scope=scope, model="qwen3" if llm_used else "deterministic-rag", confidence=conf.value, is_diff_query=is_diff, query=normalized_query)

        # F9: done event carries model field
        yield {
            "type": "done",
            "result": {
                "answer": full_answer,
                "citations": citations,
                "confidence": conf.value,
                "route": "HYBRID_RAG",
                "llm_used": llm_used,
                "latency_ms": (time.time() - t_start) * 1000,
                "fallback": not llm_used,
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
