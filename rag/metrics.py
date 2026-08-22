from prometheus_client import Counter, Histogram
import os
import contextlib
import logging

logger = logging.getLogger("rag.telemetry")

CACHE_HITS = Counter("rag_cache_hits_total", "Total semantic cache hits")
CACHE_MISSES = Counter("rag_cache_misses_total", "Total semantic cache misses", ["reason"])
CACHE_INVALIDATIONS = Counter("rag_cache_invalidations_total", "Cache invalidation events", ["reason"])

LLM_REQUESTS = Counter("rag_llm_requests_total", "LLM generation requests", ["backend"])
LLM_LATENCY = Histogram("rag_llm_latency_seconds", "LLM generation latency", ["backend"])

RETRIEVAL_LATENCY = Histogram("rag_retrieval_latency_seconds", "Retrieval stage latency")
RERANK_LATENCY = Histogram("rag_rerank_latency_seconds", "Rerank stage latency")
CACHE_LATENCY = Histogram("rag_cache_lookup_latency_seconds", "Cache lookup latency")
GUARDRAIL_LATENCY = Histogram("rag_guardrail_latency_seconds", "Guardrail execution latency")
GENERATION_LATENCY = Histogram("rag_generation_latency_seconds", "End-to-end generation stage latency")

GROUNDING_REJECTIONS = Counter("rag_grounding_rejections_total", "Number of answers rejected due to zero citations")

@contextlib.contextmanager
def trace_span(name: str, attributes: dict = None):
    """
    OpenTelemetry distributed trace span context manager.
    Safely no-ops if OpenTelemetry is not configured.
    """
    otel_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    if otel_endpoint:
        try:
            from opentelemetry import trace
            tracer = trace.get_tracer("policy_ledger_rag")
            with tracer.start_as_current_span(name) as span:
                if attributes:
                    for k, v in attributes.items():
                        span.set_attribute(k, str(v))
                yield span
                return
        except Exception:
            pass
    yield None
