### 3. Metric Tables
#### A. Version Selection
- Overall Benchmark Metric: 96/301 = 31.89%
- Numeric-Version-Only Metric: 96/288 = 33.33%
#### B. Answer Quality
- Strict Exact Match: 0
- Token F1 Avg: 0.2119
- Correct Abstentions: 1
- Incorrect Answers: 94
- Incorrect Refusals: 191
#### C. Retrieval
*(Not fully implemented in evaluator, assumed 0 for now pending retrieval IDs)*
#### D. Citation Quality
*(Pending strict citation extraction)*
#### E. Latency Distribution
- P50 Latency: 0.1778s
- P95 Latency: 0.2397s
- HYBRID_RAG Route Avg Latency: 0.2893s
- ABSTAINED Route Avg Latency: 0.1687s
- FAST_PATH_FACT Route Avg Latency: 0.0803s
- TEMPORAL_COMPARISON Route Avg Latency: 0.0884s
#### F. Runtime Behavior
- Ollama Timeouts: 301
- Other Errors: 0
### 7. Category Breakdown
**compiled_qa**
- Total: 225
- Correct Version: 85
- Correct Answer: 15
- Abstained: 132
**fact**
- Total: 44
- Correct Version: 9
- Correct Answer: 0
- Abstained: 32
**semantic_retrieval**
- Total: 8
- Correct Version: 0
- Correct Answer: 0
- Abstained: 8
**adversarial**
- Total: 5
- Correct Version: 0
- Correct Answer: 0
- Abstained: 5
**unanswerable**
- Total: 8
- Correct Version: 0
- Correct Answer: 0
- Abstained: 8
**temporal_historical**
- Total: 4
- Correct Version: 1
- Correct Answer: 0
- Abstained: 3
**version_comparison**
- Total: 2
- Correct Version: 0
- Correct Answer: 0
- Abstained: 0
**department_auth**
- Total: 3
- Correct Version: 1
- Correct Answer: 0
- Abstained: 2
**confidentiality**
- Total: 2
- Correct Version: 0
- Correct Answer: 0
- Abstained: 2