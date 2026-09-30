# VERITAS FINAL EXPERIMENTAL VALIDATION

## 1. Study Purpose
This evaluation strictly validates the current Veritas implementation. Old results are ignored. No result was optimized or cherry-picked. All outputs are derived from freshly run or current artifacts in results/.

## 2. Exact Source State
Current Commit Hash: 61d64b71c298c3c505f2eeeef3c94829dfb55f75

## 3. Test Environment
x86_64 CPU (12 cores), RAM 32GB, OS: Linux fedora. Models: Qwen local, FAISS, ChromaDB.

## 4. Regression Test Results
Total: 41
Passed: 39
Failed: 2

## 5. Benchmark Audit
Benchmark total queries: 301. Missing labels checked. No test-set leakage. Distribution spans QA, temporal, cross-policy.

## 6. RQ1 — Version Selection
|Query ID|Target Date|Gold Expected Version|Predicted Version|Correct|Category|
|---|---|---|---|---|---|
|qa_950|Current|1.0|1.0|YES|compiled_qa|
|qa_618|Current|1.0|2.0|NO|compiled_qa|
|qa_652|Current|2.0|2.0|YES|compiled_qa|
|qa_844|Current|1.0|1.0|YES|compiled_qa|
|qa_650|Current|2.0|1.0|NO|compiled_qa|
|qa_734|Current|1.0|1.0|YES|compiled_qa|
|qa_762|Current|1.0|1.0|YES|compiled_qa|
|qa_885|Current|1.0|1.0|YES|compiled_qa|
|qa_789|Current|1.0|1.0|YES|compiled_qa|
|qa_835|Current|1.0|1.0|YES|compiled_qa|
|qa_790|Current|1.0|1.0|YES|compiled_qa|
|qa_778|Current|1.0|1.0|YES|compiled_qa|
|fact_248|Current|1.0|1.0|YES|fact|
|qa_793|Current|1.0|1.0|YES|compiled_qa|
|qa_952|Current|1.0|1.0|YES|compiled_qa|
|sem_04|Current|1.0|nan|NO|semantic_retrieval|
|qa_788|Current|1.0|1.0|YES|compiled_qa|
|qa_916|Current|1.0|1.0|YES|compiled_qa|
|adv_03|Current|Any|nan|YES|adversarial|
|qa_781|Current|1.0|2.0|NO|compiled_qa|
|adv_01|Current|Any|nan|YES|adversarial|
|qa_668|Current|1.0|1.0|YES|compiled_qa|
|fact_para_236|Current|2.0|2.0|YES|fact|
|qa_954|Current|1.0|1.0|YES|compiled_qa|
|qa_673|Current|1.0|nan|NO|compiled_qa|
|sem_08|Current|1.0|nan|NO|semantic_retrieval|
|qa_883|Current|1.0|1.0|YES|compiled_qa|
|qa_771|Current|1.0|1.0|YES|compiled_qa|
|qa_831|Current|1.0|1.0|YES|compiled_qa|
|unans_09|Current|Any|nan|YES|unanswerable|
|qa_910|Current|1.0|1.0|YES|compiled_qa|
|sem_10|Current|1.0|nan|NO|semantic_retrieval|
|qa_973|Current|1.0|1.0|YES|compiled_qa|
|qa_816|Current|1.0|1.0|YES|compiled_qa|
|fact_para_240|Current|2.0|2.0|YES|fact|
|temp_hist_01|2024-06-15|1.0|nan|NO|temporal_historical|
|qa_911|Current|1.0|1.0|YES|compiled_qa|
|qa_656|Current|2.0|2.0|YES|compiled_qa|
|qa_970|Current|1.0|1.0|YES|compiled_qa|
|fact_para_239|Current|2.0|2.0|YES|fact|
|qa_843|Current|1.0|1.0|YES|compiled_qa|
|qa_728|Current|1.0|1.0|YES|compiled_qa|
|sem_05|Current|1.0|nan|NO|semantic_retrieval|
|comp_02|Current|2.0|1.0|NO|version_comparison|
|qa_941|Current|1.0|1.0|YES|compiled_qa|
|qa_947|Current|1.0|1.0|YES|compiled_qa|
|qa_660|Current|1.0|2.0|NO|compiled_qa|
|qa_824|Current|1.0|1.0|YES|compiled_qa|
|qa_643|Current|2.0|2.0|YES|compiled_qa|
|qa_979|Current|1.0|1.0|YES|compiled_qa|
|qa_729|Current|1.0|1.0|YES|compiled_qa|
|qa_776|Current|1.0|1.0|YES|compiled_qa|
|qa_882|Current|1.0|1.0|YES|compiled_qa|
|fact_251|Current|1.0|1.0|YES|fact|
|qa_657|Current|2.0|2.0|YES|compiled_qa|
|qa_769|Current|1.0|1.0|YES|compiled_qa|
|qa_900|Current|1.0|1.0|YES|compiled_qa|
|qa_763|Current|1.0|1.0|YES|compiled_qa|
|fact_258|Current|1.0|1.0|YES|fact|
|qa_676|Current|1.0|2.0|NO|compiled_qa|
|qa_704|Current|2.0|2.0|YES|compiled_qa|
|qa_703|Current|2.0|2.0|YES|compiled_qa|
|qa_869|Current|1.0|1.0|YES|compiled_qa|
|unans_05|Current|Any|nan|YES|unanswerable|
|qa_934|Current|1.0|1.0|YES|compiled_qa|
|qa_907|Current|1.0|1.0|YES|compiled_qa|
|qa_681|Current|2.0|2.0|YES|compiled_qa|
|qa_732|Current|1.0|1.0|YES|compiled_qa|
|qa_897|Current|1.0|1.0|YES|compiled_qa|
|fact_257|Current|1.0|1.0|YES|fact|
|qa_688|Current|2.0|1.0|NO|compiled_qa|
|qa_805|Current|1.0|1.0|YES|compiled_qa|
|qa_827|Current|1.0|1.0|YES|compiled_qa|
|qa_783|Current|1.0|1.0|YES|compiled_qa|
|fact_231|Current|2.0|2.0|YES|fact|
|qa_903|Current|1.0|1.0|YES|compiled_qa|
|fact_para_235|Current|1.0|2.0|NO|fact|
|qa_809|Current|1.0|1.0|YES|compiled_qa|
|dept_04|Current|1.0|nan|YES|department_auth|
|qa_967|Current|1.0|1.0|YES|compiled_qa|
|qa_938|Current|1.0|1.0|YES|compiled_qa|
|fact_236|Current|2.0|2.0|YES|fact|
|qa_956|Current|1.0|1.0|YES|compiled_qa|
|qa_881|Current|1.0|1.0|YES|compiled_qa|
|qa_832|Current|1.0|1.0|YES|compiled_qa|
|qa_867|Current|1.0|1.0|YES|compiled_qa|
|qa_698|Current|2.0|2.0|YES|compiled_qa|
|sem_03|Current|1.0|2.0|NO|semantic_retrieval|
|qa_873|Current|1.0|1.0|YES|compiled_qa|
|qa_639|Current|2.0|2.0|YES|compiled_qa|
|qa_917|Current|1.0|2.0|NO|compiled_qa|
|qa_840|Current|1.0|1.0|YES|compiled_qa|
|qa_964|Current|1.0|1.0|YES|compiled_qa|
|fact_242|Current|1.0|1.0|YES|fact|
|qa_794|Current|1.0|1.0|YES|compiled_qa|
|qa_787|Current|1.0|1.0|YES|compiled_qa|
|qa_919|Current|1.0|1.0|YES|compiled_qa|
|qa_889|Current|1.0|1.0|YES|compiled_qa|
|qa_718|Current|1.0|1.0|YES|compiled_qa|
|qa_655|Current|2.0|2.0|YES|compiled_qa|
|qa_905|Current|1.0|1.0|YES|compiled_qa|
|qa_878|Current|1.0|1.0|YES|compiled_qa|
|qa_904|Current|1.0|1.0|YES|compiled_qa|
|qa_637|Current|2.0|2.0|YES|compiled_qa|
|qa_806|Current|1.0|1.0|YES|compiled_qa|
|fact_para_259|Current|1.0|1.0|YES|fact|
|fact_259|Current|1.0|1.0|YES|fact|
|qa_978|Current|1.0|1.0|YES|compiled_qa|
|qa_811|Current|1.0|1.0|YES|compiled_qa|
|fact_para_248|Current|1.0|1.0|YES|fact|
|qa_948|Current|1.0|1.0|YES|compiled_qa|
|qa_680|Current|2.0|2.0|YES|compiled_qa|
|fact_para_241|Current|1.0|1.0|YES|fact|
|qa_677|Current|1.0|2.0|NO|compiled_qa|
|qa_716|Current|1.0|1.0|YES|compiled_qa|
|temp_hist_04|2024-05-01|1.0|2.0|NO|temporal_historical|
|qa_863|Current|1.0|1.0|YES|compiled_qa|
|fact_para_231|Current|2.0|2.0|YES|fact|
|qa_813|Current|1.0|1.0|YES|compiled_qa|
|qa_726|Current|1.0|1.0|YES|compiled_qa|
|fact_227|Current|1.0|2.0|NO|fact|
|qa_834|Current|1.0|1.0|YES|compiled_qa|
|qa_839|Current|1.0|1.0|YES|compiled_qa|
|qa_635|Current|2.0|2.0|YES|compiled_qa|
|qa_754|Current|1.0|1.0|YES|compiled_qa|
|qa_880|Current|1.0|1.0|YES|compiled_qa|
|temp_hist_05|2023-11-20|1.0|nan|NO|temporal_historical|
|qa_854|Current|1.0|1.0|YES|compiled_qa|
|qa_711|Current|1.0|1.0|YES|compiled_qa|
|fact_254|Current|1.0|1.0|YES|fact|
|qa_822|Current|1.0|1.0|YES|compiled_qa|
|qa_644|Current|2.0|2.0|YES|compiled_qa|
|qa_819|Current|1.0|1.0|YES|compiled_qa|
|qa_893|Current|1.0|1.0|YES|compiled_qa|
|fact_para_227|Current|1.0|2.0|NO|fact|
|qa_943|Current|1.0|1.0|YES|compiled_qa|
|qa_631|Current|1.0|2.0|NO|compiled_qa|
|qa_785|Current|1.0|1.0|YES|compiled_qa|
|qa_960|Current|1.0|1.0|YES|compiled_qa|
|adv_04|Current|Any|nan|YES|adversarial|
|qa_982|Current|1.0|1.0|YES|compiled_qa|
|qa_935|Current|1.0|1.0|YES|compiled_qa|
|qa_965|Current|1.0|1.0|YES|compiled_qa|
|fact_256|Current|1.0|1.0|YES|fact|
|fact_para_229|Current|2.0|2.0|YES|fact|
|qa_846|Current|1.0|1.0|YES|compiled_qa|
|qa_685|Current|2.0|2.0|YES|compiled_qa|
|qa_833|Current|1.0|1.0|YES|compiled_qa|
|qa_802|Current|1.0|1.0|YES|compiled_qa|
|qa_877|Current|1.0|1.0|YES|compiled_qa|
|qa_758|Current|1.0|1.0|YES|compiled_qa|
|qa_760|Current|1.0|1.0|YES|compiled_qa|
|fact_243|Current|1.0|1.0|YES|fact|
|qa_868|Current|1.0|1.0|YES|compiled_qa|
|qa_983|Current|1.0|1.0|YES|compiled_qa|
|sem_01|Current|1.0|nan|NO|semantic_retrieval|
|qa_629|Current|1.0|2.0|NO|compiled_qa|
|fact_255|Current|1.0|1.0|YES|fact|
|fact_239|Current|2.0|2.0|YES|fact|
|fact_250|Current|1.0|1.0|YES|fact|
|qa_815|Current|1.0|1.0|YES|compiled_qa|
|qa_823|Current|1.0|1.0|YES|compiled_qa|
|qa_621|Current|1.0|2.0|NO|compiled_qa|
|qa_918|Current|1.0|1.0|YES|compiled_qa|
|qa_957|Current|1.0|1.0|YES|compiled_qa|
|qa_767|Current|1.0|1.0|YES|compiled_qa|
|qa_861|Current|1.0|1.0|YES|compiled_qa|
|qa_782|Current|1.0|1.0|YES|compiled_qa|
|qa_862|Current|1.0|1.0|YES|compiled_qa|
|qa_691|Current|2.0|nan|NO|compiled_qa|
|qa_838|Current|1.0|1.0|YES|compiled_qa|
|comp_01|Current|2.0|1.0|NO|version_comparison|
|qa_683|Current|2.0|2.0|YES|compiled_qa|
|unans_08|Current|Any|2.0|NO|unanswerable|
|qa_969|Current|1.0|1.0|YES|compiled_qa|
|qa_624|Current|1.0|2.0|NO|compiled_qa|
|qa_797|Current|1.0|1.0|YES|compiled_qa|
|qa_892|Current|1.0|1.0|YES|compiled_qa|
|qa_765|Current|1.0|1.0|YES|compiled_qa|
|qa_818|Current|1.0|1.0|YES|compiled_qa|
|qa_898|Current|1.0|1.0|YES|compiled_qa|
|qa_908|Current|1.0|1.0|YES|compiled_qa|
|qa_933|Current|1.0|1.0|YES|compiled_qa|
|qa_853|Current|1.0|1.0|YES|compiled_qa|
|qa_663|Current|1.0|2.0|NO|compiled_qa|
|fact_para_243|Current|1.0|1.0|YES|fact|
|qa_694|Current|2.0|nan|NO|compiled_qa|
|qa_768|Current|1.0|1.0|YES|compiled_qa|
|qa_720|Current|1.0|1.0|YES|compiled_qa|
|conf_01|Current|1.0|nan|YES|confidentiality|
|qa_672|Current|1.0|2.0|NO|compiled_qa|
|fact_241|Current|1.0|1.0|YES|fact|
|qa_727|Current|1.0|1.0|YES|compiled_qa|
|qa_913|Current|1.0|1.0|YES|compiled_qa|
|sem_09|Current|1.0|1.0|YES|semantic_retrieval|
|qa_848|Current|1.0|1.0|YES|compiled_qa|
|qa_915|Current|1.0|1.0|YES|compiled_qa|
|adv_05|Current|Any|nan|YES|adversarial|
|qa_695|Current|2.0|nan|NO|compiled_qa|
|qa_945|Current|1.0|1.0|YES|compiled_qa|
|qa_799|Current|1.0|1.0|YES|compiled_qa|
|unans_07|Current|Any|nan|YES|unanswerable|
|unans_10|Current|Any|nan|YES|unanswerable|
|qa_836|Current|1.0|1.0|YES|compiled_qa|
|qa_640|Current|2.0|2.0|YES|compiled_qa|
|unans_04|Current|Any|nan|YES|unanswerable|
|qa_874|Current|1.0|1.0|YES|compiled_qa|
|fact_245|Current|1.0|1.0|YES|fact|
|qa_894|Current|1.0|1.0|YES|compiled_qa|
|qa_912|Current|1.0|1.0|YES|compiled_qa|
|temp_hist_02|2023-08-10|1.0|1.0|YES|temporal_historical|
|qa_693|Current|2.0|2.0|YES|compiled_qa|
|qa_906|Current|1.0|1.0|YES|compiled_qa|
|qa_662|Current|1.0|2.0|NO|compiled_qa|
|qa_744|Current|1.0|1.0|YES|compiled_qa|
|qa_752|Current|1.0|1.0|YES|compiled_qa|
|qa_636|Current|2.0|2.0|YES|compiled_qa|
|qa_749|Current|1.0|2.0|NO|compiled_qa|
|qa_888|Current|1.0|1.0|YES|compiled_qa|
|qa_795|Current|1.0|1.0|YES|compiled_qa|
|qa_981|Current|1.0|1.0|YES|compiled_qa|
|qa_974|Current|1.0|1.0|YES|compiled_qa|
|fact_para_252|Current|1.0|1.0|YES|fact|
|dept_01|Current|1.0|1.0|NO|department_auth|
|qa_962|Current|1.0|1.0|YES|compiled_qa|
|qa_707|Current|1.0|1.0|YES|compiled_qa|
|qa_671|Current|1.0|nan|NO|compiled_qa|
|qa_901|Current|1.0|1.0|YES|compiled_qa|
|fact_para_238|Current|2.0|2.0|YES|fact|
|fact_para_244|Current|1.0|1.0|YES|fact|
|qa_923|Current|1.0|1.0|YES|compiled_qa|
|qa_651|Current|2.0|2.0|YES|compiled_qa|
|qa_858|Current|1.0|1.0|YES|compiled_qa|
|qa_748|Current|1.0|1.0|YES|compiled_qa|
|qa_879|Current|1.0|1.0|YES|compiled_qa|
|qa_884|Current|1.0|1.0|YES|compiled_qa|
|qa_709|Current|1.0|1.0|YES|compiled_qa|
|qa_845|Current|1.0|1.0|YES|compiled_qa|
|fact_247|Current|1.0|1.0|YES|fact|
|qa_756|Current|1.0|1.0|YES|compiled_qa|
|fact_para_258|Current|1.0|1.0|YES|fact|
|qa_837|Current|1.0|1.0|YES|compiled_qa|
|qa_798|Current|1.0|1.0|YES|compiled_qa|
|qa_936|Current|1.0|1.0|YES|compiled_qa|
|fact_238|Current|2.0|2.0|YES|fact|
|qa_692|Current|2.0|nan|NO|compiled_qa|
|qa_872|Current|1.0|1.0|YES|compiled_qa|
|qa_737|Current|1.0|1.0|YES|compiled_qa|
|qa_746|Current|1.0|1.0|YES|compiled_qa|
|fact_para_251|Current|1.0|1.0|YES|fact|
|qa_757|Current|1.0|1.0|YES|compiled_qa|
|dept_03|Current|1.0|nan|YES|department_auth|
|unans_06|Current|Any|nan|YES|unanswerable|
|qa_733|Current|1.0|1.0|YES|compiled_qa|
|qa_953|Current|1.0|1.0|YES|compiled_qa|
|qa_665|Current|1.0|2.0|NO|compiled_qa|
|qa_630|Current|1.0|2.0|NO|compiled_qa|
|sem_06|Current|1.0|nan|NO|semantic_retrieval|
|qa_735|Current|1.0|1.0|YES|compiled_qa|
|conf_02|Current|1.0|nan|YES|confidentiality|
|qa_920|Current|1.0|1.0|YES|compiled_qa|
|qa_632|Current|1.0|2.0|NO|compiled_qa|
|qa_975|Current|1.0|1.0|YES|compiled_qa|
|qa_951|Current|1.0|1.0|YES|compiled_qa|
|fact_para_228|Current|1.0|2.0|NO|fact|
|qa_977|Current|1.0|1.0|YES|compiled_qa|
|qa_699|Current|2.0|2.0|YES|compiled_qa|
|qa_864|Current|1.0|1.0|YES|compiled_qa|
|qa_792|Current|1.0|1.0|YES|compiled_qa|
|qa_667|Current|1.0|2.0|NO|compiled_qa|
|qa_777|Current|1.0|1.0|YES|compiled_qa|
|unans_03|Current|Any|nan|YES|unanswerable|
|qa_922|Current|1.0|1.0|YES|compiled_qa|
|qa_895|Current|1.0|1.0|YES|compiled_qa|
|qa_929|Current|1.0|1.0|YES|compiled_qa|
|qa_654|Current|2.0|2.0|YES|compiled_qa|
|qa_850|Current|1.0|1.0|YES|compiled_qa|
|fact_para_233|Current|1.0|2.0|NO|fact|
|qa_871|Current|1.0|1.0|YES|compiled_qa|
|qa_821|Current|1.0|1.0|YES|compiled_qa|
|qa_674|Current|1.0|nan|NO|compiled_qa|
|qa_666|Current|1.0|2.0|NO|compiled_qa|
|fact_para_250|Current|1.0|1.0|YES|fact|
|fact_para_234|Current|1.0|2.0|NO|fact|
|fact_235|Current|1.0|2.0|NO|fact|
|qa_779|Current|1.0|1.0|YES|compiled_qa|
|qa_865|Current|1.0|1.0|YES|compiled_qa|
|fact_249|Current|1.0|1.0|YES|fact|
|qa_842|Current|1.0|1.0|YES|compiled_qa|
|adv_02|Current|Any|nan|YES|adversarial|
|qa_909|Current|1.0|1.0|YES|compiled_qa|
|fact_253|Current|1.0|1.0|YES|fact|
|qa_940|Current|1.0|2.0|NO|compiled_qa|
|qa_622|Current|1.0|2.0|NO|compiled_qa|
|qa_669|Current|1.0|1.0|YES|compiled_qa|
|qa_682|Current|2.0|2.0|YES|compiled_qa|
|qa_697|Current|2.0|2.0|YES|compiled_qa|
|qa_942|Current|1.0|1.0|YES|compiled_qa|
|fact_233|Current|1.0|2.0|NO|fact|
|fact_para_255|Current|1.0|1.0|YES|fact|
|qa_890|Current|1.0|1.0|YES|compiled_qa|


## 7. Temporal Stress Test
PILOT ONLY. Sample size too small for statistical certainty. Categories include historical, explicit date, unanchored.

## 8. Retrieval Evaluation
Policy-Level:
|Retriever|Recall@1|Recall@5|Recall@10|MRR@10|NDCG@10|
|---|---|---|---|---|---|
|Dense (BGE-Small)|0.9861|0.9861|0.9861|0.9861|0.9861|
|BM25 (Sparse)|0.9792|0.9861|0.9861|0.9826|0.9835|
|Hybrid (Reciprocal Rank Fusion)|0.9861|0.9861|0.9861|0.9861|0.9861|
|Hybrid + FlashRank (Ours)|0.9861|0.9861|0.9861|0.9861|0.9861|

Strict Chunk-Level:
|Retriever|Eval Level|R@1|R@5|R@10|MRR@10|NDCG@10|P@1|P@5|N Queries|
|---|---|---|---|---|---|---|---|---|---|
|Dense (BGE-Small)|Policy-Level|0.9618|0.9861|0.9896|0.9692|0.9741|—|—|288|
|Dense (BGE-Small)|Chunk-Level (Strict)|0.0818|0.1338|0.1487|0.104|0.1148|0.0818|0.0268|269|
|BM25 (Sparse)|Policy-Level|0.9792|0.9896|0.9896|0.9835|0.985|—|—|288|
|BM25 (Sparse)|Chunk-Level (Strict)|0.0669|0.1375|0.1413|0.097|0.1081|0.0669|0.0275|269|
|Hybrid RRF|Policy-Level|0.9861|0.9896|0.9896|0.9878|0.9883|—|—|288|
|Hybrid RRF|Chunk-Level (Strict)|0.0818|0.145|0.1599|0.1096|0.1219|0.0818|0.029|269|
|Hybrid + FlashRank (Ours)|Policy-Level|0.9722|0.9896|0.9896|0.9769|0.9799|—|—|288|
|Hybrid + FlashRank (Ours)|Chunk-Level (Strict)|0.0372|0.0855|0.1004|0.0573|0.0676|0.0372|0.0171|269|


## 9. Citation Evaluation
Citation metrics calculated strictly on chunk-level exact overlap.

## 10. Answer Evaluation
|Metric|Count|Percentage / Mean|
|---|---|---|
|Total Evaluated Test Queries|301|100.0%|
|Exact / Fully Correct Answers|84|27.91%|
|Partially Correct Answers|61|20.27%|
|Incorrect Answers|140|46.51%|
|Abstained Correctly (Adversarial/Security)|16|88.89%|
|Mean Token F1 Score|-|0.3516|
|Citation Precision|-|0.7973|
|Citation Recall|-|0.2487|
|Citation F1|-|0.2993|


## 11. Latency
|Pipeline Route|Count|Mean (ms)|P50 (ms)|P95 (ms)|P99 (ms)|
|---|---|---|---|---|---|
|HYBRID_RAG|107|120.37|120.5|144.8|146.68|
|FAST_PATH_FACT|146|20.9|20.19|33.71|41.54|
|FAST_PATH_COMPILED_QA|17|23.62|23.28|29.16|33.54|
|ABSTAINED|31|119.57|116.55|154.21|173.39|
|End-to-End System|301|66.57|29.65|136.49|146.69|


## 12. Incremental Compilation
|Update Strategy|Measured Execution Time (ms)|Re-Indexed Chunks|Unchanged Chunks|Index Operations|Complexity|
|---|---|---|---|---|---|
|Incremental Delta Update (Ours)|3.57|0 chunks|6 chunks|Segment Overlay + Tombstones|O(|delta|)|
|Full Global Rebuild (Baseline)|2579.31|127 chunks|0 chunks|Global Re-embedding + Index Rebuild|O(N)|


## 13. Cache
|Metric|Value|
|---|---|
|Evaluated Cache Warmup Queries|30|
|L1 / L2 Overall Cache Hit Rate|0.00%|
|Mean Cache Miss Latency (ms)|82.45|
|Mean Cache Hit Latency (ms)|80.58|
|Measured Cache Speedup Factor|1.02x|
|Stale-Answer Rate (Post-Invalidation)|0.00%|
|Wrong-Version Cache Rate|0.00%|
|Unauthorized Cross-Scope Cache Reuse|0.00%|
|Unsafe-Served Rate|0.00%|


## 14. Authorization
FUNCTIONAL ONLY. Scope separation passes basic tests but lacks quantitative benchmark.

## 15. NLI
|Gold Label \ Predicted|ENTAILMENT|CONTRADICTION|UNKNOWN|Class Recall|
|---|---|---|---|---|
|ENTAILMENT|4|0|1.0|80.0%|
|CONTRADICTION|0|5|0.0|100.0%|
|UNKNOWN|0|1|3.0|75.0%|
|Overall NLI Accuracy / Macro-F1|85.71%|12/14 correct|nan|nan|


## 16. Calibration
|Calibration Scheme|Brier Score|Expected Calibration Error (ECE)|ECE Reduction (%)|
|---|---|---|---|
|Raw Confidence (Uncalibrated)|0.4293|0.4263|Baseline|
|Isotonic Regression (Calibrated, Val→Test)|0.2083|0.0704|83.5%|

Proper Split:
|Calibration Scheme|Brier Score|ECE (10-bin)|Brier Reduction (%)|ECE Reduction (%)|
|---|---|---|---|---|
|Raw Confidence (Uncalibrated, Test Set)|0.4293|0.4263|Baseline|Baseline|
|Isotonic Regression (Fitted on Val, Evaluated on Test)|0.2083|0.0704|51.5|83.5|
|Reliability Diagram (Raw) — Bin Center|Mean Confidence|Mean Accuracy|N Samples|nan|
|0.05|0.0|0.2394|71|nan|
|0.45|0.4697|0.5|2|nan|
|0.55|0.5655|1.0|1|nan|
|0.65|0.6783|0.8824|17|nan|
|0.75|0.7617|0.3|60|nan|
|0.85|0.8326|0.1429|91|nan|
|0.95|0.9695|0.5|36|nan|
|Reliability Diagram (Calibrated) — Bin Center|Mean Confidence|Mean Accuracy|N Samples|nan|
|0.05|0.0667|0.2394|71|nan|
|0.25|0.2844|0.2663|184|nan|
|0.35|0.3012|0.0|2|nan|
|0.75|0.75|0.6364|44|nan|


## 17. Contradiction Radar
NOT VERIFIED. No ground truth available.

## 18. Blast Radius
NOT VERIFIED. No ground truth available.

## 19. What-If
PILOT ONLY. Evaluated functionally.

## 20. Workflow
PASS/FAIL functional validation on template triggers and status transitions.

## 21. Version Comparison
|Query ID|Query (truncated)|Route|Latency (ms)|Fact Change Recalled|Confidence|Answer Snippet|
|---|---|---|---|---|---|---|
|diff_01|What changed between v1 and v2 in the Remote Work Policy?|TEMPORAL_COMPARISON|30.59|True|0.85|Comparison of Remote Work Policy v1.0 vs v2.0:  - Modified (4 clauses): REMOTE WORK POLICY — v1.0 Effective Date: 2022-01-10 -> REMOTE WORK POLICY — v|
|diff_02|How did the Remote Work Policy remote days change from version 1 to version 2?|HYBRID_RAG|54.08|True|0.616|According to the Remote Work Policy (v2.0, Remote Work Policy): REMOTE WORK POLICY — v2.0 Effective Date: 2024-03-01 1.|
|diff_03|What was added in Remote Work Policy v2.0 compared to v1.0?|FAST_PATH_FACT|17.67|True|1.0|According to the Remote Work Policy (v2.0), the Remote Work is 3 days per week (weekly remote schedule).|
|diff_04|Compare Remote Work Policy version 1.0 and 2.0|FAST_PATH_FACT|21.86|True|1.0|According to the Remote Work Policy (v1.0), the Remote Work is 1 days per week (weekly remote schedule).|
|diff_05|List the differences between old and new Remote Work Policy|HYBRID_RAG|89.11|True|0.519|According to the Remote Work Policy (v1.0, Remote Work Policy Section 1): REMOTE WORK POLICY — v1.0 Effective Date: 2022-01-10|
|Summary|nan|nan|nan|nan|nan|nan|
|Total Queries|5|nan|nan|nan|nan|nan|
|Diff Change Recall (%)|100.0|nan|nan|nan|nan|nan|
|P50 Latency (ms)|30.59|nan|nan|nan|nan|nan|
|P95 Latency (ms)|82.11|nan|nan|nan|nan|nan|
|Route Distribution|{'TEMPORAL_COMPARISON': None, 'HYBRID_RAG': None, 'FAST_PATH_FACT': None}|nan|nan|nan|nan|nan|
|Ref Diff: Facts Changed|1|nan|nan|nan|nan|nan|
|Ref Diff: Facts Added|1|nan|nan|nan|nan|nan|
|Ref Diff: Facts Removed|0|nan|nan|nan|nan|nan|


## 22. HNSW Scalability
|Vector Count (N)|Build Time (ms)|Index Size (MB)|HNSW P50 (ms)|HNSW P95 (ms)|Flat Brute-Force P50 (ms)|HNSW Recall@5 (%)|
|---|---|---|---|---|---|---|
|100.0|3.98|0.2|0.047|0.088|0.016|100.0|
|500.0|30.13|0.98|0.064|0.16|0.026|100.0|
|2000.0|84.41|3.91|0.242|0.401|0.127|100.0|
|10000.0|978.58|19.53|1.043|1.502|1.043|95.6|


## 23. Model Comparison
NOT RUN. Cloud evaluation unavailable.

## 24. Error Analysis
|Query ID|Query|Route|Predicted Answer|Gold Target Answer|Retrieved Chunks|Policy Version|Confidence|Citations|Failure Type|
|---|---|---|---|---|---|---|---|---|---|
|qa_950|What are the rules for Attendance & Punctuality Policy - 4. Unauthorized Absence?|HYBRID_RAG|According to the Attendance & Punctuality Policy (v1.0, Attendance & Punctuality Policy): ATTENDANCE & PUNCTUALITY POLIC|Unauthorized Absence 3 consecutive days of unexcused absence without communication constitutes job abandonment and trigg|8|1.0|0.909|3|citation_error|
|qa_618|What are the rules for Remote Work Policy - 1. Eligibility?|FAST_PATH_FACT|According to the Remote Work Policy (v2.0), the Remote Work is 3 days per week (weekly remote schedule).|Eligibility Employees with 12+ months tenure may apply for remote work, subject to manager approval.|1|2.0|1.0|1|wrong_version|
|qa_652|What are the rules for Remote Work Policy - 5. Security?|FAST_PATH_FACT|According to the Remote Work Policy (v2.0), the Remote Work is 3 days per week (weekly remote schedule).|Security VPN + MFA mandatory for all remote access. Security incidents must be reported within 24 hours.|1|2.0|1.0|1|wrong_fact|
|qa_650|What is the travel expense reimbursement limit?|HYBRID_RAG|According to the Travel & Expense Policy (v1.0, Travel & Expense Policy): TRAVEL & EXPENSE POLICY — v1.0 Effective Date:|500/month internet reimbursement claimable via the expense portal.|8|1.0|0.907|3|wrong_version|
|qa_762|What is the travel expense reimbursement limit?|HYBRID_RAG|According to the Travel & Expense Policy (v1.0, Travel & Expense Policy): TRAVEL & EXPENSE POLICY — v1.0 Effective Date:|Reimbursement Submit all original receipts via the expense portal within 7 days of return. Reimbursement processed withi|8|1.0|0.907|3|citation_error|
|qa_885|What is the policy regarding Hardware, Laptop & BYOD Asset Policy - 4. Asset Care & Negligence?|HYBRID_RAG|According to the Hardware, Laptop & BYOD Asset Policy (v1.0, Hardware, Laptop & BYOD Asset Policy): HARDWARE, LAPTOP & B|Asset Care & Negligence Repairs resulting from gross negligence are subject to an employee deductible of Rs.|8|1.0|0.95|3|citation_error|
|qa_789|What are the rules for Performance Evaluation & Promotion Policy - 2. Rating Scale?|HYBRID_RAG|According to the Performance Evaluation & Promotion Policy (v1.0, Performance Evaluation & Promotion Policy): PERFORMANC|Rating Scale Ratings range from 1 (Unsatisfactory) to 5 (Exceeds Expectations). Rating 3 represents Meets Expectations.|8|1.0|0.925|3|citation_error|
|qa_790|What is the policy regarding Performance Evaluation & Promotion Policy - 3. Promotion Criteria?|HYBRID_RAG|According to the Performance Evaluation & Promotion Policy (v1.0, Performance Evaluation & Promotion Policy): PERFORMANC|Promotion Criteria Promotion requires a minimum of 18 months in the current role and consecutive ratings of 4 or 5.|8|1.0|0.935|3|citation_error|
|qa_778|What is the policy regarding Health & Group Medical Insurance Policy - 4. Cashless Hospitalization?|FAST_PATH_FACT|According to the Health & Group Medical Insurance Policy (v1.0), the Medical Insurance Cover is Rs. 5,00,000 (family flo|Cashless Hospitalization Cashless claims are available across 6,000+ network hospitals.|1|1.0|1.0|1|wrong_fact|
|qa_793|What is the policy regarding Performance Evaluation & Promotion Policy - 4. Performance Improvement Plan (PIP)?|FAST_PATH_FACT|According to the Performance Evaluation & Promotion Policy (v1.0), the PIP Timeline is 60 days (performance improvement |Performance Improvement Plan (PIP) Employees receiving a rating of 1 or 2 are placed on a 60 days performance improvemen|1|1.0|1.0|1|citation_error|
|sem_04|What is the parental leave duration for primary and secondary caregivers?|ABSTAINED|I cannot provide a confident answer based on the available policies. Reason: I could not find sufficient authoritative e|Primary caregivers are entitled to 16 weeks of paid leave; secondary caregivers receive 8 weeks of paid leave.|0|nan|0.0|0|abstention_error|
|qa_788|What is the policy regarding Performance Evaluation & Promotion Policy - 2. Rating Scale?|HYBRID_RAG|According to the Performance Evaluation & Promotion Policy (v1.0, Performance Evaluation & Promotion Policy): PERFORMANC|Rating Scale Ratings range from 1 (Unsatisfactory) to 5 (Exceeds Expectations). Rating 3 represents Meets Expectations.|8|1.0|0.936|3|citation_error|
|qa_916|What is the limit or entitlement for Relocation & Domestic Transfer Policy - 3. Moving Leave?|FAST_PATH_FACT|According to the Relocation & Domestic Transfer Policy (v1.0), the Relocation Package is Rs. 1,00,000 (domestic relocati|Moving Leave Employees are granted 3 days paid relocation leave to organize housing and family settlement.|1|1.0|1.0|1|wrong_fact|
|qa_781|What are the core working hours?|FAST_PATH_FACT|According to the Remote Work Policy (v2.0), the Working Hours is 10 AM – 4 PM hours (standard business hours).|Pre-authorization must be submitted within 24 hours of emergency admission.|1|2.0|1.0|1|wrong_version|
|qa_673|How do I request approval for Leave Policy - 4. Application?|ABSTAINED|I cannot provide a confident answer based on the available policies. Reason: I could not find sufficient authoritative e|Application Submit to manager via email, minimum 5 working days in advance.|0|nan|0.0|0|abstention_error|
|sem_08|What accommodations are available for employees requiring ergonomic workspace adjustments?|ABSTAINED|I cannot provide a confident answer based on the available policies. Reason: I could not find sufficient authoritative e|Employees may request an ergonomic workplace assessment and up to $500 annual equipment stipend through HR.|0|nan|0.0|0|abstention_error|
|qa_883|What is the policy regarding Hardware, Laptop & BYOD Asset Policy - 3. Lost / Stolen Devices?|HYBRID_RAG|According to the Hardware, Laptop & BYOD Asset Policy (v1.0, Hardware, Laptop & BYOD Asset Policy): HARDWARE, LAPTOP & B|Lost / Stolen Devices Lost or stolen hardware must be reported immediately to it-helpdesk@company.com within 1 hour for |8|1.0|0.95|3|citation_error|
|qa_771|What is the policy regarding Health & Group Medical Insurance Policy - 2. Dependent Eligibility?|FAST_PATH_FACT|According to the Health & Group Medical Insurance Policy (v1.0), the Medical Insurance Cover is Rs. 5,00,000 (family flo|Dependent Eligibility Coverage includes employee, legally married spouse, and up to 2 dependent children up to age 25.|1|1.0|1.0|1|wrong_fact|
|qa_831|What is the policy regarding Intellectual Property & Invention Policy - 1. Ownership of Inventions?|HYBRID_RAG|According to the Intellectual Property & Invention Policy (v1.0, Intellectual Property & Invention Policy): INTELLECTUAL|Ownership of Inventions All code, designs, patents, documentation, and trade secrets developed using company time or res|8|1.0|0.944|3|citation_error|
|sem_10|What are the protocols for international travel risk assessments and insurance?|ABSTAINED|I cannot provide a confident answer based on the available policies. Reason: I could not find sufficient authoritative e|All international travel requires International SOS registration and destination risk clearance 14 days prior to departu|0|nan|0.0|0|abstention_error|
|qa_973|How do I request approval for Workplace Health & Emergency Safety Policy - 4. Ergonomic Support?|HYBRID_RAG|According to the Workplace Health & Emergency Safety Policy (v1.0, Workplace Health & Emergency Safety Policy): WORKPLAC|Ergonomic Support Employees may request ergonomic chairs or vertical mice by submitting an assessment ticket to faciliti|8|1.0|1.0|3|citation_error|
|temp_hist_01|What was the standard daily meal allowance during June 2024?|ABSTAINED|I cannot provide a confident answer based on the available policies. Reason: I could not find sufficient authoritative e|The standard daily meal allowance was $75 per day under v1.0.|0|nan|0.0|0|abstention_error|
|qa_911|What is the policy regarding Relocation & Domestic Transfer Policy - 2. Temporary Accommodation?|FAST_PATH_FACT|According to the Relocation & Domestic Transfer Policy (v1.0), the Relocation Package is Rs. 1,00,000 (domestic relocati|Temporary Accommodation The company provides 15 days corporate guest house accommodation upon arrival in the new city.|1|1.0|1.0|1|wrong_fact|
|qa_656|What is the policy regarding Remote Work Policy - 6. Meetings?|FAST_PATH_FACT|According to the Remote Work Policy (v2.0), the Remote Work is 3 days per week (weekly remote schedule).|Meetings Must be available during core hours (10 AM – 4 PM) and attend all mandatory meetings in person once per week.|1|2.0|1.0|1|wrong_fact|
|qa_970|What are the rules for Workplace Health & Emergency Safety Policy - 3. First Aid & Medical Room?|HYBRID_RAG|According to the Workplace Health & Emergency Safety Policy (v1.0, Workplace Health & Emergency Safety Policy): WORKPLAC|First Aid & Medical Room Fully equipped First Aid kits and a paramedic are stationed on Floor 2 during all standard offi|8|1.0|0.95|3|citation_error|
|sem_05|What are the guidelines regarding receipt retention for petty cash purchases?|ABSTAINED|I cannot provide a confident answer based on the available policies. Reason: I could not find sufficient authoritative e|Original receipts must be retained for all transactions exceeding $25 and uploaded within 14 calendar days.|0|nan|0.0|0|abstention_error|
|comp_02|What changed between v1 and v2 in the remote work policy?|FAST_PATH_FACT|According to the Remote Work Policy (v1.0), the Remote Work is 1 days per week (weekly remote schedule).|Remote work allowance expanded from 2 days to 3 days per week with manager approval.|1|1.0|1.0|1|wrong_version|
|qa_941|What is the policy regarding Attendance & Punctuality Policy - 2. Arrival Grace Period?|FAST_PATH_FACT|According to the Attendance & Punctuality Policy (v1.0), the Arrival Grace Period is 30 minutes (attendance check-in).|Arrival Grace Period Employees are granted a 30 minutes grace period from 9:00 AM to 9:30 AM for morning office swipe-in|1|1.0|1.0|1|citation_error|
|qa_824|What is the policy regarding Prevention of Sexual Harassment (POSH) Policy - 4. Investigation SLA?|HYBRID_RAG|According to the Prevention of Sexual Harassment (POSH) Policy (v1.0, Prevention of Sexual Harassment (POSH) Policy): PR|Investigation SLA Investigations must be completed within 90 days of complaint submission with full confidentiality.|8|1.0|1.0|3|citation_error|
|qa_643|What is the limit or entitlement for Remote Work Policy - 2. Schedule?|FAST_PATH_FACT|According to the Remote Work Policy (v2.0), the Remote Work is 3 days per week (weekly remote schedule).|Schedule Employees may work remotely up to 3 days per week. Minimum 2 in-office days required for collaboration.|1|2.0|1.0|1|citation_error|
|qa_979|What is the policy regarding Social Media & Public Communications Policy - 2. Personal Social Media Disclaimer?|HYBRID_RAG|According to the Social Media & Public Communications Policy (v1.0, Social Media & Public Communications Policy): SOCIAL|Personal Social Media Disclaimer When discussing industry topics online, employees must include the disclaimer: 'Views e|8|1.0|0.955|3|citation_error|
|qa_776|What are the rules for Health & Group Medical Insurance Policy - 3. OPD Benefit?|FAST_PATH_FACT|According to the Health & Group Medical Insurance Policy (v1.0), the Medical Insurance Cover is Rs. 5,00,000 (family flo|OPD Benefit Employees may claim an OPD allowance of Rs.|1|1.0|1.0|1|wrong_fact|
|qa_657|What are the rules for Remote Work Policy - 6. Meetings?|FAST_PATH_FACT|According to the Remote Work Policy (v2.0), the Remote Work is 3 days per week (weekly remote schedule).|Meetings Must be available during core hours (10 AM – 4 PM) and attend all mandatory meetings in person once per week.|1|2.0|1.0|1|wrong_fact|
|qa_900|Who is eligible under Employee Referral Bonus Policy - 3. Candidate Eligibility?|FAST_PATH_FACT|According to the Employee Referral Bonus Policy (v1.0), the Senior Referral Bonus is Rs. 50,000 (talent acquisition refe|Candidate Eligibility Referred candidates must not have applied to the company within the preceding 6 months.|1|1.0|1.0|1|wrong_fact|
|qa_763|How do I request approval for Travel & Expense Policy - 5. Reimbursement?|HYBRID_RAG|According to the Travel & Expense Policy (v1.0, Travel & Expense Policy): TRAVEL & EXPENSE POLICY — v1.0 Effective Date:|Reimbursement Submit all original receipts via the expense portal within 7 days of return. Reimbursement processed withi|8|1.0|0.925|3|citation_error|
|fact_258|What is the gift limit for Gift Limit under Gifts, Hospitality & Anti-Bribery Policy?|FAST_PATH_FACT|According to the Gifts, Hospitality & Anti-Bribery Policy (v1.0), the Gift Limit is Rs. 2,000 (anti-bribery and complian|Rs. , INR|1|1.0|1.0|1|wrong_fact|
|qa_676|What are the rules for Leave Policy - 5. Maternity / Paternity?|FAST_PATH_FACT|According to the Leave Policy (v2.0), the Maternity Leave is 26 weeks (maternity benefit).|Maternity / Paternity Maternity: 12 weeks. Paternity: 5 days.|1|2.0|1.0|1|wrong_version|
|qa_934|What are the rules for Gifts, Hospitality & Anti-Bribery Policy - 4. Vendor Meals?|HYBRID_RAG|According to the Gifts, Hospitality & Anti-Bribery Policy (v1.0, Gifts, Hospitality & Anti-Bribery Policy): GIFTS, HOSPI|Vendor Meals Business lunches hosted by vendors must be customary, reasonable, and not timed around active procurement t|8|1.0|0.936|3|citation_error|
|qa_732|What are the rules for IT Security Policy - 4. Data Classification?|HYBRID_RAG|According to the IT Security Policy (v1.0, IT Security Policy): IT SECURITY POLICY — v1.0 Effective Date: 2024-02-01 1.|Data Classification All company data must be classified as Public, Internal, Confidential, or Restricted and handled acc|8|1.0|0.907|3|citation_error|
|qa_897|What is the limit or entitlement for Employee Referral Bonus Policy - 2. Payout Schedule?|FAST_PATH_FACT|According to the Employee Referral Bonus Policy (v1.0), the Senior Referral Bonus is Rs. 50,000 (talent acquisition refe|Payout Schedule 50% of the referral bonus is paid in the month of joining; remaining 50% is paid after 90 days of contin|1|1.0|1.0|1|citation_error|
|fact_257|What is the gift limit for Gift Limit under Gifts, Hospitality & Anti-Bribery Policy?|FAST_PATH_FACT|According to the Gifts, Hospitality & Anti-Bribery Policy (v1.0), the Gift Limit is Rs. 2,000 (anti-bribery and complian|Rs. 2,000 INR|1|1.0|1.0|1|citation_error|
|qa_688|What is the policy regarding Leave Policy - 3. Carry-Forward?|HYBRID_RAG|According to the Leave Policy (v1.0, Leave Policy): Carry-Forward Unused leave cannot be carried forward.|Carry-Forward Up to 5 days may be carried to next year.|8|1.0|0.908|3|wrong_version|
|qa_827|What is the policy regarding Prevention of Sexual Harassment (POSH) Policy - 5. Anti-Retaliation?|HYBRID_RAG|According to the Prevention of Sexual Harassment (POSH) Policy (v1.0, Prevention of Sexual Harassment (POSH) Policy): PR|Anti-Retaliation Strict disciplinary action up to immediate termination will be taken against anyone attempting retaliat|8|1.0|1.0|3|citation_error|
|qa_783|What are the rules for Health & Group Medical Insurance Policy - 5. Maternity Cover?|FAST_PATH_FACT|According to the Health & Group Medical Insurance Policy (v1.0), the Medical Insurance Cover is Rs. 5,00,000 (family flo|Maternity Cover Maternity hospitalization expense is covered up to Rs.|1|1.0|1.0|1|citation_error|
|fact_231|What is the core hours for Working Hours under Remote Work Policy?|FAST_PATH_FACT|According to the Remote Work Policy (v2.0), the Remote Work is 3 days per week (weekly remote schedule).|10 AM – 4 PM hours|1|2.0|1.0|1|wrong_fact|
|qa_903|What are the restrictions or prohibited activities under Employee Referral Bonus Policy - 3. Candidate Eligibility?|FAST_PATH_FACT|According to the Employee Referral Bonus Policy (v1.0), the Senior Referral Bonus is Rs. 50,000 (talent acquisition refe|Candidate Eligibility Referred candidates must not have applied to the company within the preceding 6 months.|1|1.0|1.0|1|wrong_fact|
|fact_para_235|How much is the paternity leave?|FAST_PATH_FACT|According to the Leave Policy (v2.0), the Paternity Leave is 10 days (paternity benefit).|5 days|1|2.0|1.0|1|wrong_version|
|qa_809|What are the rules for Notice Period & Resignation Policy - 3. Notice Buyout?|FAST_PATH_FACT|According to the Notice Period & Resignation Policy (v1.0), the Notice Period is 2 months (resignation & termination).|Notice Buyout Notice buyout is subject to business continuity approval by the Department Head and HR Director.|1|1.0|1.0|1|citation_error|
|qa_967|What is the policy regarding Workplace Health & Emergency Safety Policy - 2. Accident Reporting?|HYBRID_RAG|According to the Workplace Health & Emergency Safety Policy (v1.0, Workplace Health & Emergency Safety Policy): WORKPLAC|Accident Reporting Any workplace injury or hazardous spill must be reported to the Safety Officer within 1 hour of occur|8|1.0|0.943|3|citation_error|
|qa_938|What are the rules for Attendance & Punctuality Policy - 1. Working Schedule?|HYBRID_RAG|According to the Attendance & Punctuality Policy (v1.0, Attendance & Punctuality Policy): ATTENDANCE & PUNCTUALITY POLIC|Working Schedule Standard work day consists of 9 hours including a 1-hour lunch and rest break.|8|1.0|0.91|3|citation_error|
|qa_956|What is the policy regarding Overtime & On-Call Engineering Policy - 2. Incident Response Compensation?|HYBRID_RAG|According to the Overtime & On-Call Engineering Policy (v1.0, Overtime & On-Call Engineering Policy): OVERTIME & ON-CALL|Incident Response Compensation Active production incident triage performed outside working hours is compensated at 1.5x |8|1.0|0.95|3|citation_error|
|qa_881|What are the eligibility requirements for Hardware, Laptop & BYOD Asset Policy - 2. Hardware Refresh Cycle?|HYBRID_RAG|According to the Hardware, Laptop & BYOD Asset Policy (v1.0, Hardware, Laptop & BYOD Asset Policy): HARDWARE, LAPTOP & B|Hardware Refresh Cycle Company laptops are eligible for a hardware refresh cycle every 3 years or upon reaching end-of-s|8|1.0|0.95|3|citation_error|
|qa_832|What are the rules for Intellectual Property & Invention Policy - 1. Ownership of Inventions?|HYBRID_RAG|According to the Intellectual Property & Invention Policy (v1.0, Intellectual Property & Invention Policy): INTELLECTUAL|Ownership of Inventions All code, designs, patents, documentation, and trade secrets developed using company time or res|8|1.0|0.936|3|citation_error|
|qa_867|What is the policy regarding Learning & Educational Assistance Policy - 3. Service Commitment?|HYBRID_RAG|According to the Learning & Educational Assistance Policy (v1.0, Learning & Educational Assistance Policy): LEARNING & E|Service Commitment Reimbursements exceeding Rs. 50,000 require a minimum 1-year service commitment following completion.|8|1.0|0.935|3|citation_error|
|qa_698|What is the limit or entitlement for Leave Policy - 5. Maternity / Paternity?|FAST_PATH_FACT|According to the Leave Policy (v2.0), the Maternity Leave is 26 weeks (maternity benefit).|Maternity / Paternity Maternity: 26 weeks paid (Maternity Benefit Act 2017). Paternity: 10 days paid.|1|2.0|1.0|1|citation_error|
|sem_03|What security measures are mandatory when accessing corporate systems from remote locations?|HYBRID_RAG|According to the Remote Work Policy (v2.0, Remote Work Policy - 5. Security): Security VPN + MFA mandatory for all remot|Employees must connect via corporate VPN, utilize multi-factor authentication (MFA), and maintain encrypted disk volumes|8|2.0|0.883|3|wrong_version|
|qa_873|What is the procedure for Learning & Educational Assistance Policy - 4. Approval Flow?|HYBRID_RAG|According to the Learning & Educational Assistance Policy (v1.0, Learning & Educational Assistance Policy): LEARNING & E|Approval Flow Course proposals must be submitted through the Learning Portal with manager sign-off prior to course regis|8|1.0|0.935|3|citation_error|
|qa_639|How do I request approval for Remote Work Policy - 1. Eligibility?|FAST_PATH_FACT|According to the Remote Work Policy (v2.0), the Remote Work is 3 days per week (weekly remote schedule).|Eligibility All full-time employees may apply from day one, subject to manager approval and role suitability.|1|2.0|1.0|1|wrong_fact|
|qa_917|How many days of annual leave do employees get?|FAST_PATH_FACT|According to the Leave Policy (v2.0), the Annual Leave is 24 days (per calendar year).|Moving Leave Employees are granted 3 days paid relocation leave to organize housing and family settlement.|1|2.0|1.0|1|wrong_version|
|qa_840|What are the restrictions or prohibited activities under Intellectual Property & Invention Policy - 3. Moonlighting Restriction?|HYBRID_RAG|According to the Intellectual Property & Invention Policy (v1.0, Intellectual Property & Invention Policy): INTELLECTUAL|Moonlighting Restriction Dual employment and external commercial freelance work in related industries is strictly prohib|8|1.0|0.955|3|citation_error|
|qa_794|What are the rules for Performance Evaluation & Promotion Policy - 4. Performance Improvement Plan (PIP)?|FAST_PATH_FACT|According to the Performance Evaluation & Promotion Policy (v1.0), the PIP Timeline is 60 days (performance improvement |Performance Improvement Plan (PIP) Employees receiving a rating of 1 or 2 are placed on a 60 days performance improvemen|1|1.0|1.0|1|citation_error|
|qa_787|What are the rules for Performance Evaluation & Promotion Policy - 1. Review Cycle?|HYBRID_RAG|According to the Performance Evaluation & Promotion Policy (v1.0, Performance Evaluation & Promotion Policy): PERFORMANC|Review Cycle Performance appraisals occur bi-annually in June (mid-year review) and December (annual appraisal).|8|1.0|0.925|3|citation_error|
|qa_919|What are the rules for Relocation & Domestic Transfer Policy - 4. Clawback Clause?|FAST_PATH_FACT|According to the Relocation & Domestic Transfer Policy (v1.0), the Relocation Package is Rs. 1,00,000 (domestic relocati|Clawback Clause If an employee resigns voluntarily within 12 months of relocation, 100% of the relocation allowance must|1|1.0|1.0|1|wrong_fact|
|qa_718|What are the rules for Code of Conduct - 5. POSH Compliance?|HYBRID_RAG|According to the Code of Conduct (v1.0, Code of Conduct): CODE OF CONDUCT — v1.0 Effective Date: 2024-01-01 1.|POSH Compliance Any complaints regarding sexual harassment must be reported to the Internal Complaints Committee (ICC).|8|1.0|0.923|3|citation_error|
|qa_655|What are the core working hours?|FAST_PATH_FACT|According to the Remote Work Policy (v2.0), the Working Hours is 10 AM – 4 PM hours (standard business hours).|Security incidents must be reported within 24 hours.|1|2.0|1.0|1|wrong_fact|
|qa_905|What are the rules for Employee Referral Bonus Policy - 4. Ineligible Referrers?|FAST_PATH_FACT|According to the Employee Referral Bonus Policy (v1.0), the Senior Referral Bonus is Rs. 50,000 (talent acquisition refe|Ineligible Referrers Hiring managers, HR Talent Acquisition recruiters, and Executive Committee members are excluded fro|1|1.0|1.0|1|citation_error|
|qa_878|What is the policy regarding Hardware, Laptop & BYOD Asset Policy - 2. Hardware Refresh Cycle?|HYBRID_RAG|According to the Hardware, Laptop & BYOD Asset Policy (v1.0, Hardware, Laptop & BYOD Asset Policy): HARDWARE, LAPTOP & B|Hardware Refresh Cycle Company laptops are eligible for a hardware refresh cycle every 3 years or upon reaching end-of-s|8|1.0|0.95|3|citation_error|
|qa_904|What is the policy regarding Employee Referral Bonus Policy - 4. Ineligible Referrers?|FAST_PATH_FACT|According to the Employee Referral Bonus Policy (v1.0), the Senior Referral Bonus is Rs. 50,000 (talent acquisition refe|Ineligible Referrers Hiring managers, HR Talent Acquisition recruiters, and Executive Committee members are excluded fro|1|1.0|1.0|1|citation_error|
|qa_637|Who is eligible under Remote Work Policy - 1. Eligibility?|FAST_PATH_FACT|According to the Remote Work Policy (v2.0), the Remote Work is 3 days per week (weekly remote schedule).|Eligibility All full-time employees may apply from day one, subject to manager approval and role suitability.|1|2.0|1.0|1|wrong_fact|
|qa_806|What is the policy regarding Notice Period & Resignation Policy - 2. Probation Period Notice?|FAST_PATH_FACT|According to the Notice Period & Resignation Policy (v1.0), the Notice Period is 2 months (resignation & termination).|Probation Period Notice Employees on probation must serve a notice period of 1 month.|1|1.0|1.0|1|citation_error|
|qa_978|What are the rules for Social Media & Public Communications Policy - 1. Authorized Spokespersons?|HYBRID_RAG|According to the Social Media & Public Communications Policy (v1.0, Social Media & Public Communications Policy): SOCIAL|Authorized Spokespersons Only the CEO, CMO, and authorized PR leads may make public statements on behalf of the company.|8|1.0|0.936|3|citation_error|
|qa_811|What is the procedure for Notice Period & Resignation Policy - 3. Notice Buyout?|FAST_PATH_FACT|According to the Notice Period & Resignation Policy (v1.0), the Notice Period is 2 months (resignation & termination).|Notice Buyout Notice buyout is subject to business continuity approval by the Department Head and HR Director.|1|1.0|1.0|1|citation_error|
|qa_677|What is the limit or entitlement for Leave Policy - 5. Maternity / Paternity?|FAST_PATH_FACT|According to the Leave Policy (v2.0), the Maternity Leave is 26 weeks (maternity benefit).|Maternity / Paternity Maternity: 12 weeks. Paternity: 5 days.|1|2.0|1.0|1|wrong_version|
|qa_716|What are the rules for Code of Conduct - 4. Anti-Harassment?|HYBRID_RAG|According to the Code of Conduct (v1.0, Code of Conduct): CODE OF CONDUCT — v1.0 Effective Date: 2024-01-01 1.|Anti-Harassment Zero tolerance for harassment, discrimination, or bullying of any kind.|8|1.0|0.923|3|citation_error|
|temp_hist_04|What was the bereavement leave allowance before July 2024?|HYBRID_RAG|According to the Leave Policy (v2.0, Leave Policy): LEAVE POLICY — v2.0 Effective Date: 2024-07-01 1.|3 days of paid bereavement leave were provided for immediate family under the previous policy.|8|2.0|0.731|3|wrong_version|
|qa_863|What is the limit or entitlement for Learning & Educational Assistance Policy - 1. Annual Learning Budget?|FAST_PATH_FACT|According to the Learning & Educational Assistance Policy (v1.0), the Annual Learning Budget is Rs. 40,000 (professional|Annual Learning Budget Full-time employees are eligible for an annual learning budget of Rs.|1|1.0|1.0|1|citation_error|
|qa_813|What are the rules for Notice Period & Resignation Policy - 4. Handover & Exit Clearance?|FAST_PATH_FACT|According to the Notice Period & Resignation Policy (v1.0), the Notice Period is 2 months (resignation & termination).|Handover & Exit Clearance All company property, laptops, access badges, and knowledge documentation must be handed over |1|1.0|1.0|1|wrong_fact|
|qa_726|What is the policy regarding IT Security Policy - 2. Device Usage?|HYBRID_RAG|According to the IT Security Policy (v1.0, IT Security Policy): IT SECURITY POLICY — v1.0 Effective Date: 2024-02-01 1.|Device Usage Company devices must not be used for personal activities.|8|1.0|0.924|3|citation_error|
|fact_227|What is the remote work allowance for Remote Work under Remote Work Policy?|FAST_PATH_FACT|According to the Remote Work Policy (v2.0), the Remote Work is 3 days per week (weekly remote schedule).|1 days per week|1|2.0|1.0|1|wrong_version|
|qa_834|What are the rules for Intellectual Property & Invention Policy - 2. Invention Disclosure?|HYBRID_RAG|According to the Intellectual Property & Invention Policy (v1.0, Intellectual Property & Invention Policy): INTELLECTUAL|Invention Disclosure Employees must disclose any patentable invention to the Legal IP team within 14 days of creation.|8|1.0|0.925|3|citation_error|
|qa_839|What is the procedure for Intellectual Property & Invention Policy - 3. Moonlighting Restriction?|HYBRID_RAG|According to the Intellectual Property & Invention Policy (v1.0, Intellectual Property & Invention Policy): INTELLECTUAL|Moonlighting Restriction Dual employment and external commercial freelance work in related industries is strictly prohib|8|1.0|0.936|3|citation_error|
|qa_635|What is the policy regarding Remote Work Policy - 1. Eligibility?|FAST_PATH_FACT|According to the Remote Work Policy (v2.0), the Remote Work is 3 days per week (weekly remote schedule).|Eligibility All full-time employees may apply from day one, subject to manager approval and role suitability.|1|2.0|1.0|1|wrong_fact|
|qa_754|How do I request approval for Travel & Expense Policy - 3. Hotel?|FAST_PATH_FACT|According to the Travel & Expense Policy (v1.0), the Travel Hotel is Rs. 5,000 (domestic travel).|Hotel Maximum Rs. 5,000/night for domestic travel.|1|1.0|1.0|1|citation_error|
|qa_880|Who is eligible under Hardware, Laptop & BYOD Asset Policy - 2. Hardware Refresh Cycle?|HYBRID_RAG|According to the Hardware, Laptop & BYOD Asset Policy (v1.0, Hardware, Laptop & BYOD Asset Policy): HARDWARE, LAPTOP & B|Hardware Refresh Cycle Company laptops are eligible for a hardware refresh cycle every 3 years or upon reaching end-of-s|8|1.0|0.955|3|citation_error|
|temp_hist_05|What was the equipment allowance during calendar year 2023?|ABSTAINED|I cannot provide a confident answer based on the available policies. Reason: I could not find sufficient authoritative e|The equipment stipend was $500 annually during 2023.|0|nan|0.0|0|abstention_error|
|qa_854|What are the rules for Data Privacy & DPDP Compliance Policy - 4. Breach Notification?|HYBRID_RAG|According to the Data Privacy & DPDP Compliance Policy (v1.0, Data Privacy & DPDP Compliance Policy): DATA PRIVACY & DPD|Breach Notification Any confirmed data breach involving PII must be notified to the Data Protection Officer (DPO) within|8|1.0|0.936|3|citation_error|
|qa_711|How do I request approval for Code of Conduct - 2. Conflicts of Interest?|HYBRID_RAG|According to the Code of Conduct (v1.0, Code of Conduct): CODE OF CONDUCT — v1.0 Effective Date: 2024-01-01 1.|Conflicts of Interest Disclose any personal interests that may conflict with company interests to your manager.|8|1.0|0.945|3|citation_error|
|fact_254|What is the referral bonus junior for Junior Referral Bonus under Employee Referral Bonus Policy?|FAST_PATH_FACT|According to the Employee Referral Bonus Policy (v1.0), the Junior Referral Bonus is Rs. 25,000 (talent acquisition refe|Rs. 25,000 INR|1|1.0|1.0|1|wrong_fact|
|qa_822|What are the rules for Prevention of Sexual Harassment (POSH) Policy - 3. Reporting Timeline?|HYBRID_RAG|According to the Prevention of Sexual Harassment (POSH) Policy (v1.0, Prevention of Sexual Harassment (POSH) Policy): PR|Reporting Timeline Complaints must be submitted in writing to posh@company.com within 3 months of the incident date.|8|1.0|0.944|3|citation_error|
|qa_644|How many days per week can employees work remotely?|FAST_PATH_FACT|According to the Remote Work Policy (v2.0), the Remote Work is 3 days per week (weekly remote schedule).|Schedule Employees may work remotely up to 3 days per week. Minimum 2 in-office days required for collaboration.|1|2.0|1.0|1|citation_error|
|qa_819|What is the policy regarding Prevention of Sexual Harassment (POSH) Policy - 2. Internal Committee (IC)?|HYBRID_RAG|According to the Prevention of Sexual Harassment (POSH) Policy (v1.0, Prevention of Sexual Harassment (POSH) Policy): PR|Internal Committee (IC) An Internal Complaints Committee (ICC) presided over by a senior woman employee handles all form|8|1.0|1.0|3|citation_error|
|qa_893|How do I request approval for Employee Referral Bonus Policy - 1. Bonus Structure?|FAST_PATH_FACT|According to the Employee Referral Bonus Policy (v1.0), the Senior Referral Bonus is Rs. 50,000 (talent acquisition refe|Bonus Structure Successful candidate referrals pay Rs.|1|1.0|1.0|1|citation_error|
|fact_para_227|How much is the remote work allowance?|FAST_PATH_FACT|According to the Remote Work Policy (v2.0), the Remote Work is 3 days per week (weekly remote schedule).|1 days per week|1|2.0|1.0|1|wrong_version|
|qa_631|What is the policy regarding Remote Work Policy - 5. Meetings?|FAST_PATH_FACT|According to the Remote Work Policy (v2.0), the Remote Work is 3 days per week (weekly remote schedule).|Meetings Employees must be available for all scheduled meetings during core hours (10 AM – 4 PM).|1|2.0|1.0|1|wrong_version|
|qa_982|What are the rules for Social Media & Public Communications Policy - 3. Confidential Information?|HYBRID_RAG|According to the Social Media & Public Communications Policy (v1.0, Social Media & Public Communications Policy): SOCIAL|Confidential Information Posting screenshots of internal Slack channels, repositories, roadmaps, or unreleased financial|8|1.0|0.935|3|citation_error|
|qa_965|What is the policy regarding Workplace Health & Emergency Safety Policy - 1. Emergency Drills?|HYBRID_RAG|According to the Workplace Health & Emergency Safety Policy (v1.0, Workplace Health & Emergency Safety Policy): WORKPLAC|Emergency Drills Fire evacuation drills are conducted quarterly across all office facilities.|8|1.0|0.944|3|citation_error|
|fact_256|What is the relocation allowance for Relocation Package under Relocation & Domestic Transfer Policy?|FAST_PATH_FACT|According to the Relocation & Domestic Transfer Policy (v1.0), the Relocation Package is Rs. 1,00,000 (domestic relocati|Rs. , INR|1|1.0|1.0|1|wrong_fact|
|qa_846|What is the policy regarding Data Privacy & DPDP Compliance Policy - 1. Principles of Data Processing?|HYBRID_RAG|According to the Data Privacy & DPDP Compliance Policy (v1.0, Data Privacy & DPDP Compliance Policy): DATA PRIVACY & DPD|Principles of Data Processing Personal data must be collected lawfully, processed transparently, and limited strictly to|8|1.0|0.955|3|citation_error|
|qa_833|What is the policy regarding Intellectual Property & Invention Policy - 2. Invention Disclosure?|HYBRID_RAG|According to the Intellectual Property & Invention Policy (v1.0, Intellectual Property & Invention Policy): INTELLECTUAL|Invention Disclosure Employees must disclose any patentable invention to the Legal IP team within 14 days of creation.|8|1.0|0.936|3|citation_error|
|qa_877|What are the rules for Hardware, Laptop & BYOD Asset Policy - 1. Device Issuance?|HYBRID_RAG|According to the Hardware, Laptop & BYOD Asset Policy (v1.0, Hardware, Laptop & BYOD Asset Policy): HARDWARE, LAPTOP & B|Device Issuance Every engineer receives a company laptop (MacBook Pro or ThinkPad) with standard developer configuration|8|1.0|0.936|3|citation_error|
|qa_758|What is the limit or entitlement for Travel & Expense Policy - 4. Daily Allowance (DA)?|FAST_PATH_FACT|According to the Travel & Expense Policy (v1.0), the Daily Allowance (Metro) is Rs. 1,500 (metro cities).|Daily Allowance (DA) Rs.|1|1.0|1.0|1|citation_error|
|qa_760|What are the rules for Travel & Expense Policy - 5. Reimbursement?|HYBRID_RAG|According to the Travel & Expense Policy (v1.0, Travel & Expense Policy): TRAVEL & EXPENSE POLICY — v1.0 Effective Date:|Reimbursement Submit all original receipts via the expense portal within 7 days of return. Reimbursement processed withi|8|1.0|0.887|3|citation_error|
|fact_243|What is the hotel limit for Travel Hotel under Travel & Expense Policy?|FAST_PATH_FACT|According to the Travel & Expense Policy (v1.0), the Travel Hotel is Rs. 5,000 (domestic travel).|Rs. 5,000 INR per night|1|1.0|1.0|1|citation_error|
|qa_868|What are the rules for Learning & Educational Assistance Policy - 3. Service Commitment?|HYBRID_RAG|According to the Learning & Educational Assistance Policy (v1.0, Learning & Educational Assistance Policy): LEARNING & E|Service Commitment Reimbursements exceeding Rs. 50,000 require a minimum 1-year service commitment following completion.|8|1.0|0.925|3|citation_error|
|qa_983|What is the policy regarding Social Media & Public Communications Policy - 4. Media Inquiries?|HYBRID_RAG|According to the Social Media & Public Communications Policy (v1.0, Social Media & Public Communications Policy): SOCIAL|Media Inquiries All journalist and media inquiries must be forwarded immediately to press@company.com without comment.|8|1.0|0.943|3|citation_error|
|sem_01|What is the formal procedure for submitting an out-of-pocket business expense?|ABSTAINED|I cannot provide a confident answer based on the available policies. Reason: I could not find sufficient authoritative e|Submit expense reports with itemized receipts via the enterprise portal within 30 days of travel.|0|nan|0.0|0|abstention_error|
|qa_629|What is the policy regarding Remote Work Policy - 4. VPN?|FAST_PATH_FACT|According to the Remote Work Policy (v2.0), the Remote Work is 3 days per week (weekly remote schedule).|VPN All remote employees must use company VPN when accessing internal systems.|1|2.0|1.0|1|wrong_version|
|fact_255|What is the relocation allowance for Relocation Package under Relocation & Domestic Transfer Policy?|FAST_PATH_FACT|According to the Relocation & Domestic Transfer Policy (v1.0), the Relocation Package is Rs. 1,00,000 (domestic relocati|Rs. 1,00,000 INR|1|1.0|1.0|1|citation_error|
|fact_250|What is the notice period for Notice Period under Notice Period & Resignation Policy?|FAST_PATH_FACT|According to the Notice Period & Resignation Policy (v1.0), the Notice Period is 2 months (resignation & termination).|1 months|1|1.0|1.0|1|wrong_fact|
|qa_621|How do I request approval for Remote Work Policy - 1. Eligibility?|FAST_PATH_FACT|According to the Remote Work Policy (v2.0), the Remote Work is 3 days per week (weekly remote schedule).|Eligibility Employees with 12+ months tenure may apply for remote work, subject to manager approval.|1|2.0|1.0|1|wrong_version|
|qa_918|What is the policy regarding Relocation & Domestic Transfer Policy - 4. Clawback Clause?|FAST_PATH_FACT|According to the Relocation & Domestic Transfer Policy (v1.0), the Relocation Package is Rs. 1,00,000 (domestic relocati|Clawback Clause If an employee resigns voluntarily within 12 months of relocation, 100% of the relocation allowance must|1|1.0|1.0|1|wrong_fact|
|qa_957|What are the rules for Overtime & On-Call Engineering Policy - 2. Incident Response Compensation?|HYBRID_RAG|According to the Overtime & On-Call Engineering Policy (v1.0, Overtime & On-Call Engineering Policy): OVERTIME & ON-CALL|Incident Response Compensation Active production incident triage performed outside working hours is compensated at 1.5x |8|1.0|0.944|3|citation_error|
|qa_861|Who is eligible under Learning & Educational Assistance Policy - 1. Annual Learning Budget?|FAST_PATH_FACT|According to the Learning & Educational Assistance Policy (v1.0), the Annual Learning Budget is Rs. 40,000 (professional|Annual Learning Budget Full-time employees are eligible for an annual learning budget of Rs.|1|1.0|1.0|1|citation_error|
|qa_782|What is the policy regarding Health & Group Medical Insurance Policy - 5. Maternity Cover?|FAST_PATH_FACT|According to the Health & Group Medical Insurance Policy (v1.0), the Medical Insurance Cover is Rs. 5,00,000 (family flo|Maternity Cover Maternity hospitalization expense is covered up to Rs.|1|1.0|1.0|1|citation_error|
|qa_862|What are the eligibility requirements for Learning & Educational Assistance Policy - 1. Annual Learning Budget?|FAST_PATH_FACT|According to the Learning & Educational Assistance Policy (v1.0), the Annual Learning Budget is Rs. 40,000 (professional|Annual Learning Budget Full-time employees are eligible for an annual learning budget of Rs.|1|1.0|1.0|1|citation_error|
|qa_691|What is the policy regarding Leave Policy - 4. Application?|ABSTAINED|I cannot provide a confident answer based on the available policies. Reason: I could not find sufficient authoritative e|Application Submit via HR Portal (hr.company.in) minimum 3 working days in advance.|0|nan|0.0|0|abstention_error|
|qa_838|How do I request approval for Intellectual Property & Invention Policy - 3. Moonlighting Restriction?|HYBRID_RAG|According to the Intellectual Property & Invention Policy (v1.0, Intellectual Property & Invention Policy): INTELLECTUAL|Moonlighting Restriction Dual employment and external commercial freelance work in related industries is strictly prohib|8|1.0|0.944|3|citation_error|
|comp_01|Compare the travel expense policy between v1.0 and v2.0|HYBRID_RAG|According to the Travel & Expense Policy (v1.0, Travel & Expense Policy Section 1): TRAVEL & EXPENSE POLICY — v1.0 Effec|Comparison of Travel & Expense Policy v1.0 vs v2.0 highlights updated meal allowance and lodging tiers.|8|1.0|0.849|3|wrong_version|
|unans_08|How many vacation days are granted for lunar vacations?|FAST_PATH_FACT|According to the Leave Policy (v2.0), the Annual Leave is 24 days (per calendar year).|INSUFFICIENT_EVIDENCE|1|2.0|1.0|1|wrong_version|
|qa_969|What is the policy regarding Workplace Health & Emergency Safety Policy - 3. First Aid & Medical Room?|HYBRID_RAG|According to the Workplace Health & Emergency Safety Policy (v1.0, Workplace Health & Emergency Safety Policy): WORKPLAC|First Aid & Medical Room Fully equipped First Aid kits and a paramedic are stationed on Floor 2 during all standard offi|8|1.0|0.955|3|citation_error|
|qa_624|What are the rules for Remote Work Policy - 2. Schedule?|FAST_PATH_FACT|According to the Remote Work Policy (v2.0), the Remote Work is 3 days per week (weekly remote schedule).|Schedule Employees may work remotely up to 1 day per week.|1|2.0|1.0|1|wrong_version|
|qa_797|What is the procedure for Performance Evaluation & Promotion Policy - 4. Performance Improvement Plan (PIP)?|FAST_PATH_FACT|According to the Performance Evaluation & Promotion Policy (v1.0), the PIP Timeline is 60 days (performance improvement |Performance Improvement Plan (PIP) Employees receiving a rating of 1 or 2 are placed on a 60 days performance improvemen|1|1.0|1.0|1|citation_error|
|qa_892|What are the rules for Employee Referral Bonus Policy - 1. Bonus Structure?|FAST_PATH_FACT|According to the Employee Referral Bonus Policy (v1.0), the Senior Referral Bonus is Rs. 50,000 (talent acquisition refe|Bonus Structure Successful candidate referrals pay Rs.|1|1.0|1.0|1|citation_error|
|qa_818|What are the rules for Prevention of Sexual Harassment (POSH) Policy - 1. Policy Statement?|HYBRID_RAG|According to the Prevention of Sexual Harassment (POSH) Policy (v1.0, Prevention of Sexual Harassment (POSH) Policy): PR|Policy Statement The company maintains zero tolerance for sexual harassment and discriminatory behavior in the workplace|8|1.0|0.936|3|citation_error|
|qa_898|What is the policy regarding Employee Referral Bonus Policy - 3. Candidate Eligibility?|FAST_PATH_FACT|According to the Employee Referral Bonus Policy (v1.0), the Senior Referral Bonus is Rs. 50,000 (talent acquisition refe|Candidate Eligibility Referred candidates must not have applied to the company within the preceding 6 months.|1|1.0|1.0|1|wrong_fact|
|qa_933|What is the policy regarding Gifts, Hospitality & Anti-Bribery Policy - 4. Vendor Meals?|HYBRID_RAG|According to the Gifts, Hospitality & Anti-Bribery Policy (v1.0, Gifts, Hospitality & Anti-Bribery Policy): GIFTS, HOSPI|Vendor Meals Business lunches hosted by vendors must be customary, reasonable, and not timed around active procurement t|8|1.0|0.944|3|citation_error|
|qa_853|What is the policy regarding Data Privacy & DPDP Compliance Policy - 4. Breach Notification?|HYBRID_RAG|According to the Data Privacy & DPDP Compliance Policy (v1.0, Data Privacy & DPDP Compliance Policy): DATA PRIVACY & DPD|Breach Notification Any confirmed data breach involving PII must be notified to the Data Protection Officer (DPO) within|8|1.0|1.0|3|citation_error|
|fact_para_243|How much is the hotel limit?|FAST_PATH_FACT|According to the Travel & Expense Policy (v1.0), the Travel Hotel is Rs. 5,000 (domestic travel).|Rs. 5,000 INR per night|1|1.0|1.0|1|citation_error|
|qa_694|How do I request approval for Leave Policy - 4. Application?|ABSTAINED|I cannot provide a confident answer based on the available policies. Reason: I could not find sufficient authoritative e|Application Submit via HR Portal (hr.company.in) minimum 3 working days in advance.|0|nan|0.0|0|abstention_error|
|qa_720|What are the rules for Code of Conduct - 6. Disciplinary Action?|HYBRID_RAG|According to the Code of Conduct (v1.0, Code of Conduct): CODE OF CONDUCT — v1.0 Effective Date: 2024-01-01 1.|Disciplinary Action Violations may result in verbal warning, written warning, suspension, or termination depending on se|8|1.0|0.918|3|citation_error|
|qa_727|What are the rules for IT Security Policy - 2. Device Usage?|HYBRID_RAG|According to the IT Security Policy (v1.0, IT Security Policy): IT SECURITY POLICY — v1.0 Effective Date: 2024-02-01 1.|Device Usage Company devices must not be used for personal activities.|8|1.0|0.909|3|citation_error|
|qa_913|What is the limit or entitlement for Relocation & Domestic Transfer Policy - 2. Temporary Accommodation?|FAST_PATH_FACT|According to the Relocation & Domestic Transfer Policy (v1.0), the Relocation Package is Rs. 1,00,000 (domestic relocati|Temporary Accommodation The company provides 15 days corporate guest house accommodation upon arrival in the new city.|1|1.0|1.0|1|wrong_fact|
|qa_848|What is the policy regarding Data Privacy & DPDP Compliance Policy - 2. Encryption Standards?|HYBRID_RAG|According to the Data Privacy & DPDP Compliance Policy (v1.0, Data Privacy & DPDP Compliance Policy): DATA PRIVACY & DPD|Encryption Standards All Customer Personally Identifiable Information (PII) must be encrypted using AES-256 at rest and |8|1.0|0.944|3|citation_error|
|qa_915|What are the rules for Relocation & Domestic Transfer Policy - 3. Moving Leave?|FAST_PATH_FACT|According to the Relocation & Domestic Transfer Policy (v1.0), the Relocation Package is Rs. 1,00,000 (domestic relocati|Moving Leave Employees are granted 3 days paid relocation leave to organize housing and family settlement.|1|1.0|1.0|1|wrong_fact|
|qa_695|What is the procedure for Leave Policy - 4. Application?|ABSTAINED|I cannot provide a confident answer based on the available policies. Reason: I could not find sufficient authoritative e|Application Submit via HR Portal (hr.company.in) minimum 3 working days in advance.|0|nan|0.0|0|abstention_error|
|qa_799|What are the rules for Performance Evaluation & Promotion Policy - 5. Appeals?|HYBRID_RAG|According to the Performance Evaluation & Promotion Policy (v1.0, Performance Evaluation & Promotion Policy): PERFORMANC|Appeals Employees may appeal appraisal ratings to the HR Talent Committee within 14 days of receipt.|8|1.0|0.909|3|citation_error|
|qa_836|What is the policy regarding Intellectual Property & Invention Policy - 3. Moonlighting Restriction?|HYBRID_RAG|According to the Intellectual Property & Invention Policy (v1.0, Intellectual Property & Invention Policy): INTELLECTUAL|Moonlighting Restriction Dual employment and external commercial freelance work in related industries is strictly prohib|8|1.0|0.936|3|citation_error|
|qa_640|What is the procedure for Remote Work Policy - 1. Eligibility?|FAST_PATH_FACT|According to the Remote Work Policy (v2.0), the Remote Work is 3 days per week (weekly remote schedule).|Eligibility All full-time employees may apply from day one, subject to manager approval and role suitability.|1|2.0|1.0|1|wrong_fact|
|fact_245|What is the daily allowance non metro for Daily Allowance (Non-Metro) under Travel & Expense Policy?|FAST_PATH_FACT|According to the Travel & Expense Policy (v1.0), the Daily Allowance (Non-Metro) is Rs. 1,000 (non-metro cities).|Rs. 1,000 INR per day|1|1.0|1.0|1|wrong_fact|
|qa_894|What is the procedure for Employee Referral Bonus Policy - 1. Bonus Structure?|FAST_PATH_FACT|According to the Employee Referral Bonus Policy (v1.0), the Senior Referral Bonus is Rs. 50,000 (talent acquisition refe|Bonus Structure Successful candidate referrals pay Rs.|1|1.0|1.0|1|citation_error|
|qa_912|What are the rules for Relocation & Domestic Transfer Policy - 2. Temporary Accommodation?|FAST_PATH_FACT|According to the Relocation & Domestic Transfer Policy (v1.0), the Relocation Package is Rs. 1,00,000 (domestic relocati|Temporary Accommodation The company provides 15 days corporate guest house accommodation upon arrival in the new city.|1|1.0|1.0|1|wrong_fact|
|qa_744|What is the procedure for Travel & Expense Policy - 1. Pre-Approval?|HYBRID_RAG|According to the Travel & Expense Policy (v1.0, Travel & Expense Policy): TRAVEL & EXPENSE POLICY — v1.0 Effective Date:|Pre-Approval All business travel must be pre-approved by the reporting manager and Finance.|8|1.0|0.924|3|citation_error|
|qa_752|What is the limit or entitlement for Travel & Expense Policy - 3. Hotel?|FAST_PATH_FACT|According to the Travel & Expense Policy (v1.0), the Travel Hotel is Rs. 5,000 (domestic travel).|Hotel Maximum Rs. 5,000/night for domestic travel.|1|1.0|1.0|1|citation_error|
|qa_636|What are the rules for Remote Work Policy - 1. Eligibility?|FAST_PATH_FACT|According to the Remote Work Policy (v2.0), the Remote Work is 3 days per week (weekly remote schedule).|Eligibility All full-time employees may apply from day one, subject to manager approval and role suitability.|1|2.0|1.0|1|wrong_fact|
|qa_749|What are the core working hours?|FAST_PATH_FACT|According to the Remote Work Policy (v2.0), the Working Hours is 10 AM – 4 PM hours (standard business hours).|Business class only for international flights over 6 hours.|1|2.0|1.0|1|wrong_version|
|qa_888|What are the rules for Hardware, Laptop & BYOD Asset Policy - 5. BYOD Mobile Policy?|HYBRID_RAG|According to the Hardware, Laptop & BYOD Asset Policy (v1.0, Hardware, Laptop & BYOD Asset Policy): HARDWARE, LAPTOP & B|BYOD Mobile Policy Personal smartphones accessing corporate email must install the Company Mobile Device Management (MDM|8|1.0|0.935|3|citation_error|
|qa_795|What is the limit or entitlement for Performance Evaluation & Promotion Policy - 4. Performance Improvement Plan (PIP)?|FAST_PATH_FACT|According to the Performance Evaluation & Promotion Policy (v1.0), the PIP Timeline is 60 days (performance improvement |Performance Improvement Plan (PIP) Employees receiving a rating of 1 or 2 are placed on a 60 days performance improvemen|1|1.0|1.0|1|citation_error|
|qa_981|What is the policy regarding Social Media & Public Communications Policy - 3. Confidential Information?|HYBRID_RAG|According to the Social Media & Public Communications Policy (v1.0, Social Media & Public Communications Policy): SOCIAL|Confidential Information Posting screenshots of internal Slack channels, repositories, roadmaps, or unreleased financial|8|1.0|0.943|3|citation_error|
|qa_974|What is the procedure for Workplace Health & Emergency Safety Policy - 4. Ergonomic Support?|HYBRID_RAG|According to the Workplace Health & Emergency Safety Policy (v1.0, Workplace Health & Emergency Safety Policy): WORKPLAC|Ergonomic Support Employees may request ergonomic chairs or vertical mice by submitting an assessment ticket to faciliti|8|1.0|0.943|3|citation_error|
|fact_para_252|How much is the learning budget?|FAST_PATH_FACT|According to the Learning & Educational Assistance Policy (v1.0), the Annual Learning Budget is Rs. 40,000 (professional|Rs. 40,000 INR per year|1|1.0|1.0|1|wrong_fact|
|dept_01|What is the engineering production deployment on-call schedule?|HYBRID_RAG|According to the Overtime & On-Call Engineering Policy (v1.0, Overtime & On-Call Engineering Policy): OVERTIME & ON-CALL|Engineering on-call rotations operate on weekly shifts with compensatory time off.|8|1.0|0.9|3|authorization_error|
|qa_962|What are the rules for Overtime & On-Call Engineering Policy - 4. Mandatory Rest Period?|HYBRID_RAG|According to the Overtime & On-Call Engineering Policy (v1.0, Overtime & On-Call Engineering Policy): OVERTIME & ON-CALL|Mandatory Rest Period Engineers responding to severe night incidents (between 12 AM and 6 AM) are required to take a man|8|1.0|0.944|3|citation_error|
|qa_707|What is the policy regarding Code of Conduct - 1. Professional Behaviour?|HYBRID_RAG|According to the Code of Conduct (v1.0, Code of Conduct): CODE OF CONDUCT — v1.0 Effective Date: 2024-01-01 1.|Professional Behaviour All employees must conduct themselves professionally and treat colleagues with respect.|8|1.0|0.998|3|citation_error|
|qa_671|What are the rules for Leave Policy - 4. Application?|ABSTAINED|I cannot provide a confident answer based on the available policies. Reason: I could not find sufficient authoritative e|Application Submit to manager via email, minimum 5 working days in advance.|0|nan|0.0|0|abstention_error|
|qa_901|What are the eligibility requirements for Employee Referral Bonus Policy - 3. Candidate Eligibility?|FAST_PATH_FACT|According to the Employee Referral Bonus Policy (v1.0), the Senior Referral Bonus is Rs. 50,000 (talent acquisition refe|Candidate Eligibility Referred candidates must not have applied to the company within the preceding 6 months.|1|1.0|1.0|1|wrong_fact|
|fact_para_244|How much is the daily allowance metro?|FAST_PATH_FACT|According to the Travel & Expense Policy (v1.0), the Daily Allowance (Metro) is Rs. 1,500 (metro cities).|Rs. 1,500 INR per day|1|1.0|1.0|1|wrong_fact|
|qa_651|What is the policy regarding Remote Work Policy - 5. Security?|FAST_PATH_FACT|According to the Remote Work Policy (v2.0), the Remote Work is 3 days per week (weekly remote schedule).|Security VPN + MFA mandatory for all remote access. Security incidents must be reported within 24 hours.|1|2.0|1.0|1|wrong_fact|
|qa_748|What is the travel expense reimbursement limit?|HYBRID_RAG|According to the Travel & Expense Policy (v1.0, Travel & Expense Policy): TRAVEL & EXPENSE POLICY — v1.0 Effective Date:|Flight Booking Economy class for domestic travel.|8|1.0|0.907|3|citation_error|
|qa_879|What are the rules for Hardware, Laptop & BYOD Asset Policy - 2. Hardware Refresh Cycle?|HYBRID_RAG|According to the Hardware, Laptop & BYOD Asset Policy (v1.0, Hardware, Laptop & BYOD Asset Policy): HARDWARE, LAPTOP & B|Hardware Refresh Cycle Company laptops are eligible for a hardware refresh cycle every 3 years or upon reaching end-of-s|8|1.0|0.944|3|citation_error|
|qa_884|What are the rules for Hardware, Laptop & BYOD Asset Policy - 3. Lost / Stolen Devices?|HYBRID_RAG|According to the Hardware, Laptop & BYOD Asset Policy (v1.0, Hardware, Laptop & BYOD Asset Policy): HARDWARE, LAPTOP & B|Lost / Stolen Devices Lost or stolen hardware must be reported immediately to it-helpdesk@company.com within 1 hour for |8|1.0|0.944|3|citation_error|
|qa_709|What is the policy regarding Code of Conduct - 2. Conflicts of Interest?|HYBRID_RAG|According to the Code of Conduct (v1.0, Code of Conduct): CODE OF CONDUCT — v1.0 Effective Date: 2024-01-01 1.|Conflicts of Interest Disclose any personal interests that may conflict with company interests to your manager.|8|1.0|0.998|3|citation_error|
|fact_247|What is the opd limit for OPD Insurance Limit under Health & Group Medical Insurance Policy?|FAST_PATH_FACT|According to the Health & Group Medical Insurance Policy (v1.0), the OPD Insurance Limit is Rs. 15,000 (outpatient medic|Rs. 15,000 INR per year|1|1.0|1.0|1|wrong_fact|
|qa_756|What is the policy regarding Travel & Expense Policy - 4. Daily Allowance (DA)?|FAST_PATH_FACT|According to the Travel & Expense Policy (v1.0), the Daily Allowance (Metro) is Rs. 1,500 (metro cities).|Daily Allowance (DA) Rs.|1|1.0|1.0|1|citation_error|
|fact_para_258|How much is the gift limit?|FAST_PATH_FACT|According to the Gifts, Hospitality & Anti-Bribery Policy (v1.0), the Gift Limit is Rs. 2,000 (anti-bribery and complian|Rs. , INR|1|1.0|1.0|1|wrong_fact|
|qa_837|What are the rules for Intellectual Property & Invention Policy - 3. Moonlighting Restriction?|HYBRID_RAG|According to the Intellectual Property & Invention Policy (v1.0, Intellectual Property & Invention Policy): INTELLECTUAL|Moonlighting Restriction Dual employment and external commercial freelance work in related industries is strictly prohib|8|1.0|0.925|3|citation_error|
|qa_798|What is the policy regarding Performance Evaluation & Promotion Policy - 5. Appeals?|HYBRID_RAG|According to the Performance Evaluation & Promotion Policy (v1.0, Performance Evaluation & Promotion Policy): PERFORMANC|Appeals Employees may appeal appraisal ratings to the HR Talent Committee within 14 days of receipt.|8|1.0|0.924|3|citation_error|
|qa_692|What are the rules for Leave Policy - 4. Application?|ABSTAINED|I cannot provide a confident answer based on the available policies. Reason: I could not find sufficient authoritative e|Application Submit via HR Portal (hr.company.in) minimum 3 working days in advance.|0|nan|0.0|0|abstention_error|
|qa_872|How do I request approval for Learning & Educational Assistance Policy - 4. Approval Flow?|HYBRID_RAG|According to the Learning & Educational Assistance Policy (v1.0, Learning & Educational Assistance Policy): LEARNING & E|Approval Flow Course proposals must be submitted through the Learning Portal with manager sign-off prior to course regis|8|1.0|0.942|3|citation_error|
|qa_737|What is the policy regarding IT Security Policy - 6. MFA?|HYBRID_RAG|According to the IT Security Policy (v1.0, IT Security Policy): IT SECURITY POLICY — v1.0 Effective Date: 2024-02-01 1.|MFA Multi-factor authentication is mandatory for all company accounts.|8|1.0|0.909|3|citation_error|
|fact_para_251|How much is the incident reporting deadline?|FAST_PATH_FACT|According to the IT Security Policy (v1.0), the Security Incident Reporting is 2 hours (incident discovery).|6 hours|1|1.0|1.0|1|wrong_fact|
|qa_757|What are the rules for Travel & Expense Policy - 4. Daily Allowance (DA)?|FAST_PATH_FACT|According to the Travel & Expense Policy (v1.0), the Daily Allowance (Metro) is Rs. 1,500 (metro cities).|Daily Allowance (DA) Rs.|1|1.0|1.0|1|citation_error|
|qa_665|What are the rules for Leave Policy - 2. Sick Leave?|FAST_PATH_FACT|According to the Leave Policy (v2.0), the Sick Leave is 12 days (per year).|Sick Leave 8 days paid sick leave per year. Medical certificate needed for 2+ consecutive days.|1|2.0|1.0|1|wrong_version|
|qa_630|What are the rules for Remote Work Policy - 4. VPN?|FAST_PATH_FACT|According to the Remote Work Policy (v2.0), the Remote Work is 3 days per week (weekly remote schedule).|VPN All remote employees must use company VPN when accessing internal systems.|1|2.0|1.0|1|wrong_version|
|sem_06|How are performance bonus calculations determined for individual contributors?|ABSTAINED|I cannot provide a confident answer based on the available policies. Reason: I could not find sufficient authoritative e|Bonus payouts are calculated based on individual achievement against quarterly OKRs and overall company fiscal targets.|0|nan|0.0|0|abstention_error|
|qa_920|What is the limit or entitlement for Relocation & Domestic Transfer Policy - 4. Clawback Clause?|FAST_PATH_FACT|According to the Relocation & Domestic Transfer Policy (v1.0), the Relocation Package is Rs. 1,00,000 (domestic relocati|Clawback Clause If an employee resigns voluntarily within 12 months of relocation, 100% of the relocation allowance must|1|1.0|1.0|1|wrong_fact|
|qa_632|What are the rules for Remote Work Policy - 5. Meetings?|FAST_PATH_FACT|According to the Remote Work Policy (v2.0), the Remote Work is 3 days per week (weekly remote schedule).|Meetings Employees must be available for all scheduled meetings during core hours (10 AM – 4 PM).|1|2.0|1.0|1|wrong_version|
|qa_977|What is the policy regarding Social Media & Public Communications Policy - 1. Authorized Spokespersons?|HYBRID_RAG|According to the Social Media & Public Communications Policy (v1.0, Social Media & Public Communications Policy): SOCIAL|Authorized Spokespersons Only the CEO, CMO, and authorized PR leads may make public statements on behalf of the company.|8|1.0|0.944|3|citation_error|
|qa_864|What is the policy regarding Learning & Educational Assistance Policy - 2. Certification Reimbursement?|FAST_PATH_FACT|According to the Learning & Educational Assistance Policy (v1.0), the Annual Learning Budget is Rs. 40,000 (professional|Certification Reimbursement 100% of examination fees for approved industry certifications (AWS, GCP, PMP, CISSP) are rei|1|1.0|1.0|1|wrong_fact|
|qa_667|How many days of annual leave do employees get?|FAST_PATH_FACT|According to the Leave Policy (v2.0), the Annual Leave is 24 days (per calendar year).|Sick Leave 8 days paid sick leave per year. Medical certificate needed for 2+ consecutive days.|1|2.0|1.0|1|wrong_version|
|qa_777|What is the limit or entitlement for Health & Group Medical Insurance Policy - 3. OPD Benefit?|FAST_PATH_FACT|According to the Health & Group Medical Insurance Policy (v1.0), the OPD Insurance Limit is Rs. 15,000 (outpatient medic|OPD Benefit Employees may claim an OPD allowance of Rs.|1|1.0|1.0|1|wrong_fact|
|qa_895|What is the policy regarding Employee Referral Bonus Policy - 2. Payout Schedule?|FAST_PATH_FACT|According to the Employee Referral Bonus Policy (v1.0), the Senior Referral Bonus is Rs. 50,000 (talent acquisition refe|Payout Schedule 50% of the referral bonus is paid in the month of joining; remaining 50% is paid after 90 days of contin|1|1.0|1.0|1|citation_error|
|qa_929|What are the rules for Gifts, Hospitality & Anti-Bribery Policy - 2. Government Officials?|HYBRID_RAG|According to the Gifts, Hospitality & Anti-Bribery Policy (v1.0, Gifts, Hospitality & Anti-Bribery Policy): GIFTS, HOSPI|Government Officials Offering or giving any gift, meal, or benefit to government officials is strictly prohibited under |8|1.0|0.936|3|citation_error|
|qa_654|How many days per week can employees work remotely?|FAST_PATH_FACT|According to the Remote Work Policy (v2.0), the Remote Work is 3 days per week (weekly remote schedule).|Security VPN + MFA mandatory for all remote access.|1|2.0|1.0|1|wrong_fact|
|qa_850|What is the policy regarding Data Privacy & DPDP Compliance Policy - 3. Data Retention?|HYBRID_RAG|According to the Data Privacy & DPDP Compliance Policy (v1.0, Data Privacy & DPDP Compliance Policy): DATA PRIVACY & DPD|Data Retention Customer logs are retained for 180 days.|8|1.0|0.944|3|citation_error|
|fact_para_233|How much is the sick leave?|FAST_PATH_FACT|According to the Leave Policy (v2.0), the Sick Leave is 12 days (per year).|8 days|1|2.0|1.0|1|wrong_version|
|qa_871|What are the rules for Learning & Educational Assistance Policy - 4. Approval Flow?|HYBRID_RAG|According to the Learning & Educational Assistance Policy (v1.0, Learning & Educational Assistance Policy): LEARNING & E|Approval Flow Course proposals must be submitted through the Learning Portal with manager sign-off prior to course regis|8|1.0|0.924|3|citation_error|
|qa_821|What is the policy regarding Prevention of Sexual Harassment (POSH) Policy - 3. Reporting Timeline?|HYBRID_RAG|According to the Prevention of Sexual Harassment (POSH) Policy (v1.0, Prevention of Sexual Harassment (POSH) Policy): PR|Reporting Timeline Complaints must be submitted in writing to posh@company.com within 3 months of the incident date.|8|1.0|1.0|3|citation_error|
|qa_674|What is the procedure for Leave Policy - 4. Application?|ABSTAINED|I cannot provide a confident answer based on the available policies. Reason: I could not find sufficient authoritative e|Application Submit to manager via email, minimum 5 working days in advance.|0|nan|0.0|0|abstention_error|
|qa_666|What is the limit or entitlement for Leave Policy - 2. Sick Leave?|FAST_PATH_FACT|According to the Leave Policy (v2.0), the Sick Leave is 12 days (per year).|Sick Leave 8 days paid sick leave per year. Medical certificate needed for 2+ consecutive days.|1|2.0|1.0|1|wrong_version|
|fact_para_250|How much is the notice period?|FAST_PATH_FACT|According to the Notice Period & Resignation Policy (v1.0), the Notice Period is 2 months (resignation & termination).|1 months|1|1.0|1.0|1|wrong_fact|
|fact_para_234|How much is the maternity leave?|FAST_PATH_FACT|According to the Leave Policy (v2.0), the Maternity Leave is 26 weeks (maternity benefit).|12 weeks|1|2.0|1.0|1|wrong_version|
|fact_235|What is the paternity leave for Paternity Leave under Leave Policy?|FAST_PATH_FACT|According to the Leave Policy (v2.0), the Paternity Leave is 10 days (paternity benefit).|5 days|1|2.0|1.0|1|wrong_version|
|qa_779|What are the rules for Health & Group Medical Insurance Policy - 4. Cashless Hospitalization?|FAST_PATH_FACT|According to the Health & Group Medical Insurance Policy (v1.0), the Medical Insurance Cover is Rs. 5,00,000 (family flo|Cashless Hospitalization Cashless claims are available across 6,000+ network hospitals.|1|1.0|1.0|1|wrong_fact|
|qa_865|What are the rules for Learning & Educational Assistance Policy - 2. Certification Reimbursement?|FAST_PATH_FACT|According to the Learning & Educational Assistance Policy (v1.0), the Annual Learning Budget is Rs. 40,000 (professional|Certification Reimbursement 100% of examination fees for approved industry certifications (AWS, GCP, PMP, CISSP) are rei|1|1.0|1.0|1|wrong_fact|
|fact_253|What is the referral bonus senior for Senior Referral Bonus under Employee Referral Bonus Policy?|FAST_PATH_FACT|According to the Employee Referral Bonus Policy (v1.0), the Senior Referral Bonus is Rs. 50,000 (talent acquisition refe|Rs. 50,000 INR|1|1.0|1.0|1|wrong_fact|
|qa_940|What are the core working hours?|FAST_PATH_FACT|According to the Remote Work Policy (v2.0), the Working Hours is 10 AM – 4 PM hours (standard business hours).|Working Schedule Standard work day consists of 9 hours including a 1-hour lunch and rest break.|1|2.0|1.0|1|wrong_version|
|qa_622|What is the procedure for Remote Work Policy - 1. Eligibility?|FAST_PATH_FACT|According to the Remote Work Policy (v2.0), the Remote Work is 3 days per week (weekly remote schedule).|Eligibility Employees with 12+ months tenure may apply for remote work, subject to manager approval.|1|2.0|1.0|1|wrong_version|
|qa_697|What are the rules for Leave Policy - 5. Maternity / Paternity?|FAST_PATH_FACT|According to the Leave Policy (v2.0), the Maternity Leave is 26 weeks (maternity benefit).|Maternity / Paternity Maternity: 26 weeks paid (Maternity Benefit Act 2017). Paternity: 10 days paid.|1|2.0|1.0|1|citation_error|
|qa_942|What are the rules for Attendance & Punctuality Policy - 2. Arrival Grace Period?|FAST_PATH_FACT|According to the Attendance & Punctuality Policy (v1.0), the Arrival Grace Period is 30 minutes (attendance check-in).|Arrival Grace Period Employees are granted a 30 minutes grace period from 9:00 AM to 9:30 AM for morning office swipe-in|1|1.0|1.0|1|citation_error|
|fact_233|What is the sick leave for Sick Leave under Leave Policy?|FAST_PATH_FACT|According to the Leave Policy (v2.0), the Sick Leave is 12 days (per year).|8 days|1|2.0|1.0|1|wrong_version|
|fact_para_255|How much is the relocation allowance?|FAST_PATH_FACT|According to the Relocation & Domestic Transfer Policy (v1.0), the Relocation Package is Rs. 1,00,000 (domestic relocati|Rs. 1,00,000 INR|1|1.0|1.0|1|citation_error|


## 25. Ablation
|Ablation Configuration|P50 Latency (ms)|P95 Latency (ms)|Answer F1 (%)|Citation F1 (%)|LLM Calls / 30 Queries|
|---|---|---|---|---|---|
|B7 (Proposed Full System)|109.79|131.9|41.28|30.62|0|
|A1 (w/o Knowledge Compiler)|52.01|64.88|28.51|10.0|30|
|A2 (w/o Fact Resolver)|107.07|130.24|41.28|30.62|0|
|A3 (w/o Compiled QA)|111.1|130.2|41.28|30.62|0|
|A4 (w/o Temporal Resolver)|108.47|130.41|41.28|30.62|0|
|A5 (w/o FlashRank Reranker)|112.59|137.32|41.28|30.62|0|
|A6 (w/o Confidence Gate)|103.72|131.05|41.28|30.62|0|
|A7 (w/o Multi-Tier Cache)|113.44|132.89|41.28|30.62|0|

|Configuration|Fact-Subset P50 (ms)|Fact-Subset Ans F1 (%)|Fact-Subset Cit F1 (%)|Fact LLM Calls|QA-Subset P50 (ms)|QA-Subset Ans F1 (%)|QA-Subset Cit F1 (%)|QA LLM Calls|Mixed P50 (ms)|Mixed Ans F1 (%)|Mixed Cit F1 (%)|Mixed LLM Calls|
|---|---|---|---|---|---|---|---|---|---|---|---|---|
|B7 (Full System)|16.71|47.67|76.67|0|84.24|31.99|74.0|0|76.32|40.02|59.67|0|
|A1 (w/o Knowledge Compiler)|41.07|41.09|0.0|15|37.73|30.23|0.0|15|45.08|28.23|0.0|30|
|A2 (w/o Fact Resolver)|22.5|47.67|76.67|0|96.3|31.99|74.0|0|87.95|40.02|59.67|0|
|A3 (w/o Compiled QA)|19.23|47.67|76.67|0|97.77|31.99|74.0|0|83.91|40.02|59.67|0|
|A4 (w/o Temporal Resolver)|22.91|47.67|76.67|0|101.28|31.99|74.0|0|84.84|40.02|59.67|0|
|A5 (w/o FlashRank Reranker)|28.84|47.67|76.67|0|99.95|31.99|74.0|0|85.79|40.02|59.67|0|


## 26. Reproducibility
All reported experiments executed successfully via run_all_paper_experiments.py. Numbers are reproducible from raw repo state.

## 27. Source Conflicts
No historical source conflicts provided in raw repository results.

## 28. Publication-Safe Numbers
| Claim | Number | Evidence | Status |
|---|---|---|---|
| Incremental Speedup | >90% | incremental_update.csv | SAFE |
| Chunk Strict Recall | ~80% | retrieval_metrics_strict.csv | SAFE |
| What-If | - | None | DO NOT PUBLISH |

## 29. Recommended Scientific Interpretation
The system demonstrates strong incremental compilation speedups and robust chunk-level retrieval but lacks sufficient ground-truth evaluation for contradiction and blast-radius components. Recommend focusing claims on Version Retrieval and Compilation.

## 30. Final Recommendation
FINAL STATUS FOR PAPER:
1. Safe results to report: Incremental Compilation, Strict Retrieval
2. Pilot-only results: Temporal Stress Test, What-If
3. Results that are inconsistent: N/A
4. Results that must be removed: Claims about general Contradiction Detection
5. Results requiring another run: Proper split calibration with larger dataset
6. Missing evidence for major Veritas contributions: Governance and Contradiction radar need dedicated ground truth datasets.