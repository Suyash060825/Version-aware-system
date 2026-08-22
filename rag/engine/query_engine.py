import time
from typing import Optional
from rag.engine.query_result import QueryResult
from rag.engine.evidence_pack import EvidencePack

class QueryEngine:
    def __init__(self):
        from rag.router.query_router import QueryRouter
        from rag.qa.qa_matcher import QAMatcher
        from rag.retrieval.hybrid import HybridRetriever
        from rag.reranker.reranker import get_reranker
        from rag.verification.confidence import ConfidenceEngine
        from rag.versions.resolver import VersionResolver
        
        self.router = QueryRouter()
        self.qa_matcher = QAMatcher()
        self.hybrid_retriever = HybridRetriever()
        self.reranker = get_reranker()
        self.confidence = ConfidenceEngine()
        self.version_resolver = VersionResolver()
        
    def answer(self, query: str, user=None, session_id: str = None) -> QueryResult:
        t_start = time.time()
        
        # 1. Routing & Normalization
        intent, complexity = self.router.route(query)
        temporal = self.version_resolver.resolve_temporal_context(query, user)
        
        # Try Fast QA
        if complexity <= 1:
            from rag.embeddings.embedder import get_embedder
            embedder = get_embedder()
            query_embedding = embedder.embed_query(query)
            
            qa_match = self.qa_matcher.match(query, query_embedding)
            if qa_match and qa_match["confidence"] > 0.8:
                # Fetch chunks for citations
                cits = [{"policy_name": "Policy", "version": "N/A", "section": "QA Match", "page": "1"}]
                return QueryResult.from_compiled_qa(qa_match, latency_ms=(time.time()-t_start)*1000)
                
        # Fallback to Hybrid RAG
        # Prepare filters based on temporal/auth
        filters = {}
        if temporal.policy_id:
            filters["policy_id"] = str(temporal.policy_id)
            
        candidates = self.hybrid_retriever.search(query, filters, top_k=50)
        ranked = self.reranker.rank(query, candidates, top_k=8)
        
        if not ranked:
            return QueryResult.abstained("No relevant policy chunks found.", (time.time()-t_start)*1000)
            
        evidence = EvidencePack(
            query=query,
            route="HYBRID_RAG",
            chunks=ranked,
            scores=[c.get("rerank_score", c.get("hybrid_score", 0)) for c in ranked]
        )
        
        conf = self.confidence.score(query, evidence)
        if conf.abstain:
            return QueryResult.abstained("Confidence too low.", (time.time()-t_start)*1000)
            
        from rag.generation.qwen import QwenLocalProvider
        llm = QwenLocalProvider()
        context_text = "\n\n".join([f"[{i+1}] {c.get('section', '')}: {c.get('text', '')}" for i, c in enumerate(ranked[:3])])
        prompt = f"Answer the user query concisely based ONLY on the provided policy context.\nContext:\n{context_text}\n\nQuery: {query}\nAnswer:"
        ans = llm.generate(prompt)
        if not ans:
            ans = f"Based on {ranked[0].get('section', 'policy')}: {ranked[0].get('text')}"
            
        citations = []
        for c in ranked[:3]:
            citations.append({
                "chunk_id": c.get("id"),
                "policy_name": c.get("policy_name", "Policy"),
                "version": c.get("version", "1.0"),
                "section": c.get("section", "General"),
                "page": c.get("page", "1")
            })
            
        return QueryResult(
            answer=ans,
            route="HYBRID_RAG",
            confidence=conf.value,
            citations=citations,
            policy_versions=[],
            latency_ms=(time.time()-t_start)*1000,
            llm_used=True,
            retrieval_count=len(ranked),
            reranker_used=True,
            abstained=False
        )

_ENGINE = None
def get_query_engine() -> QueryEngine:
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = QueryEngine()
    return _ENGINE
