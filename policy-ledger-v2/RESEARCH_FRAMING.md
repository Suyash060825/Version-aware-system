# Research Framing: Version-Aware RAG in Enterprise Document Corpora

## 1. Core Research Question
**"How can retrieval-augmented generation (RAG) systems remain temporally correct, cost-efficient, and hallucination-free when the underlying document corpus is versioned and continuously updated?"**

## 2. Core Claims
This system demonstrates three key contributions that answer the research question:
1. **Temporal Correctness via Version-Scoped Caching (Module 27)**: Linking cache invalidation directly to document lifecycle events (version drift) guarantees that users never receive stale policy information, preventing a major class of errors in dynamic environments.
2. **Cost-Accuracy Tradeoff via Cascade Routing (Module 28)**: Dynamically escalating to larger, more expensive models only when retrieval confidence drops below a defined threshold (or when complex cross-version reasoning is detected) significantly reduces operating costs while preserving accuracy on difficult queries.
3. **Hallucination Reduction via Hard Grounding Checks (Module 29 / 31)**: Enforcing strict citation linkages and utilizing explicit version-diff contexts in the prompt prevents the model from silently fabricating information or hallucinating changes between versions.

## 3. Gaps in Existing Published RAG Work
1. **The Static-Corpus Assumption**: The majority of RAG evaluations (e.g., standard QA benchmarks) assume a frozen corpus. There is a lack of rigorous methodology for handling document versioning, supersessions, and temporal drift. `[FIND CITATION: static corpus limitations in RAG benchmarks]`
2. **Naïve Cache Invalidation**: Existing semantic caching layers often rely on simple TTLs or global purges. There is little work on fine-grained, dependency-aware cache invalidation tied to document lifecycle events. `[FIND CITATION: semantic caching strategies and limitations in LLMs]`
3. **Unmeasured Cost-Adaptive Routing**: While model cascading is conceptually discussed, empirical evaluations of cost-adaptive routing specifically in the context of enterprise document QA (measuring escalation rate vs. query difficulty) are scarce. `[FIND CITATION: model cascading and routing in production LLM applications]`

## 4. Claims Requiring Empirical Validation
The current `RESULTS.md` contains claims that must be replaced with rigorous, measured numbers before publication (see Part E):
- **UNVERIFIED CLAIM**: *"Achieves up to 80% cost reduction by only using expensive LLM calls when necessary"* (Needs to be verified via the confidence-threshold sweep and cascade evaluation).
- **UNVERIFIED CLAIM**: *"The Cascade Provider proves that cheap/local models can serve the majority of standard retrieval queries"* (Needs exact percentages from the baseline vs. cascade evaluation).
- **UNVERIFIED CLAIM**: *"The system guarantees time-accurate policy responses"* (Needs quantitative backing from the "version-drift correctness" metric in the expanded eval set).
