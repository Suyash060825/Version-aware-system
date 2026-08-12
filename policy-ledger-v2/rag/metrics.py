from prometheus_client import Counter, Histogram

CACHE_HITS = Counter("rag_cache_hits_total", "Total semantic cache hits")
CACHE_MISSES = Counter("rag_cache_misses_total", "Total semantic cache misses", ["reason"])
CACHE_INVALIDATIONS = Counter("rag_cache_invalidations_total", "Cache invalidation events", ["reason"])

LLM_REQUESTS = Counter("rag_llm_requests_total", "LLM generation requests", ["backend"])
LLM_LATENCY = Histogram("rag_llm_latency_seconds", "LLM generation latency", ["backend"])

GROUNDING_REJECTIONS = Counter("rag_grounding_rejections_total", "Number of answers rejected due to zero citations")
