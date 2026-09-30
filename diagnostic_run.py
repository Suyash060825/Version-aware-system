import json
import time
from app import create_app
from models import User
from rag.engine.query_engine import get_query_engine
from rag.engine.query_scope import QueryScope
from rag.embeddings.embedder import get_embedder

app = create_app("production")

BENCHMARK_FILE = "data/benchmarks/benchmark_test.json"
OUTPUT_FILE = "results/diagnostic_raw.json"

with open(BENCHMARK_FILE) as f:
    queries = json.load(f)

print(f"Loaded {len(queries)} queries.")

results = []
with app.app_context():
    u = User.query.filter_by(email="admin@company.com").first()
    engine = get_query_engine()
    embedder = get_embedder()
    
    for i, item in enumerate(queries):
        query = item["query"]
        
        normalized_query = engine.router.normalize(query)
        intent, complexity, route_name, meta = engine.router.route(normalized_query)
        temporal_context = engine.version_resolver.resolve_temporal_context(normalized_query, u)
        allowed_pids = engine.evidence_filter.get_allowed_policy_ids(u)
        scope = QueryScope.from_user(u, temporal_context, allowed_policy_ids=allowed_pids)
        
        q_emb = embedder.embed_query(normalized_query)
        
        predicted_version = None
        retrieved_policy = None
        confidence = 0
        abstain_reason = None
        llm_required = False
        final_route = "HYBRID_RAG"
        
        # 2. Fast Path Fact
        fact_res = engine.fact_resolver.try_resolve(normalized_query, scope=scope, temporal=temporal_context, user=u)
        if fact_res.found and fact_res.answer:
            cits = engine.citation_validator.validate_and_enrich(fact_res.citations, scope=scope)
            if cits:
                predicted_version = cits[0].get("version")
                retrieved_policy = cits[0].get("policy_name")
            final_route = "FAST_PATH_FACT"
            llm_required = False
        else:
            # 3. Canonical QA
            qa_match = engine.qa_matcher.match(normalized_query, q_emb, scope=scope, threshold=0.80)
            if qa_match:
                predicted_version = qa_match.get("version")
                retrieved_policy = qa_match.get("policy")
                final_route = "CANONICAL_QA"
                llm_required = False
            else:
                # 4. Temporal Comparison
                if intent == "version_compare":
                    final_route = "TEMPORAL_COMPARISON"
                    llm_required = False
                else:
                    # 5. Hybrid Retrieval
                    filters = {}
                    if temporal_context.policy_id:
                        filters["policy_id"] = str(temporal_context.policy_id)
                    raw_candidates = engine.hybrid_retriever.search(normalized_query, filters=filters, top_k=50)
                    
                    # 6. Authorization Filtering
                    authorized_candidates = engine.evidence_filter.filter_chunks(raw_candidates, scope)
                    
                    if not authorized_candidates:
                        abstain_reason = "No authoritative evidence"
                        final_route = "ABSTAINED"
                        llm_required = False
                    else:
                        # 7. Reranking
                        ranked = engine.reranker.rank(normalized_query, authorized_candidates, top_k=8)
                        if not ranked:
                            ranked = authorized_candidates[:8]
                            
                        top_chunk = ranked[0] if ranked else {}
                        predicted_version = top_chunk.get("version", "1.0")
                        retrieved_policy = top_chunk.get("policy_name")
                        
                        # 8. Confidence Gate
                        from rag.engine.query_engine import EvidencePack
                        evidence = EvidencePack(
                            query=normalized_query,
                            route="HYBRID_RAG",
                            chunks=ranked,
                            scores=[c.get("rerank_score", c.get("hybrid_score", 0.5)) for c in ranked]
                        )
                        conf = engine.confidence_engine.score(normalized_query, evidence)
                        confidence = conf.value * 100
                        
                        if conf.abstain:
                            abstain_reason = "Confidence gate rejected"
                            final_route = "ABSTAINED"
                            llm_required = False
                        else:
                            llm_required = True

        results.append({
            "query_id": item["id"],
            "query_category": item["category"],
            "gold_version": item.get("expected_version"),
            "predicted_version": str(predicted_version) if predicted_version else None,
            "route": final_route,
            "llm_required": llm_required,
            "retrieved_policy": retrieved_policy,
            "confidence": confidence,
            "abstain_reason": abstain_reason
        })
        
        if (i + 1) % 50 == 0:
            print(f"Diagnostic {i + 1}/{len(queries)}")

with open(OUTPUT_FILE, "w") as f:
    json.dump(results, f, indent=2)
print(f"Diagnostic results saved to {OUTPUT_FILE}")
