# Veritas Research Paper: Figures & Tables Selection Checklist

This checklist defines the 10 recommended publication figures and 5 empirical tables for the manuscript, mapping each item directly to its high-resolution PNG image, CSV source file, and raw evidence rows.

---

## 📊 Recommended Publication Figures (10 Figures)

| Item | Figure Title / Caption | Source Image File Path | Raw Evidence Source File & Rows to Cite | Key Plotted Metric |
| :--- | :--- | :--- | :--- | :--- |
| **Fig. 1** | **Component Coverage & Matrix** | `results/system_characterization/paper_figures/fig01_coverage_matrix.png` | `results/system_characterization/results_master.csv` (all 922 rows across 12 domains) | Full matrix test coverage across all 12 corporate policy domains |
| **Fig. 2** | **Multi-Tier Router Traffic Share** | `results/system_characterization/paper_figures/fig04_router_traffic.png` | `results/system_characterization/routing_results.csv` (summary counts) | 63.4% fast-path offload (Tier 0 Fact, Tier 1 Canonical QA, Tier 3 Diff) vs 36.6% Hybrid RAG |
| **Fig. 3** | **Retrieval Recall@K & Pipeline Progression** | `results/system_characterization/paper_figures/fig06_retrieval_recall.png` | `results/system_characterization/retrieval_results.csv` (BM25, Dense, RRF, CrossEncoder rows) | Recall@1: BM25 (72.4%), Dense (78.6%), RRF (88.2%), CrossEncoder (94.5%) |
| **Fig. 4** | **Latency Distribution Profiles (P50/P90/P95/P99)** | `results/system_characterization/paper_figures/fig08_latency_distributions.png` | `results/system_characterization/metrics_verified.csv` (rows 3:8) | Tier 0 ($0.95\text{ms}$), Tier 1 ($1.85\text{ms}$), Tier 3 ($2.10\text{ms}$), Tier 2 ($22.4\text{ms}$) |
| **Fig. 5** | **Incremental Compiler vs. Mutation Rate** | `results/system_characterization/paper_figures/fig11_mutation_vs_compile_time.png` | `results/system_characterization/compiler_results.csv` (corpus_size=3000 rows, 1% to 100% deltas) | $24.95\times$ speedup at 5% mutation ($2.10\text{s}$ vs $52.4\text{s}$ cold rebuild) |
| **Fig. 6** | **Pre-Retrieval Authorization Confusion Matrix** | `results/system_characterization/paper_figures/fig14_auth_confusion_matrix.png` | `results/system_characterization/security_results.csv` (all 3,840 records) | 1,840 True Positives, 2,000 True Negatives, 0 False Positives, 0 Leaks |
| **Fig. 7** | **Confidence Calibration Reliability Diagram** | `results/system_characterization/paper_figures/fig16_calibration_reliability.png` | `results/system_characterization/calibration_results.csv` (10 reliability bins) | Isotonic regression ECE reduction from 0.148 to 0.041 (validation) vs 0.295 (runtime) |
| **Fig. 8** | **Fixed-Evidence Generation Fidelity vs End-to-End** | `results/system_characterization/paper_figures/fig17_local_vs_cloud.png` | `results/system_characterization/fixed_evidence_llm_comparison.csv` (rows 2:101) | Decoupled generation (0.962 Token F1, 100% concept match) vs End-to-End RAG (0.352 Token F1) |
| **Fig. 9** | **Standardized Failure Distribution & Heatmap** | `results/system_characterization/paper_figures/fig18_failure_distribution.png` | `results/system_characterization/failures_verified.jsonl` (74 verified failure traces) | Frequency of F1–F10 edge cases (compound multi-clause queries, temporal ambiguity) |
| **Fig. 10** | **Temporal Version Resolution Across Dates** | `results/system_characterization/paper_figures/fig21_temporal_accuracy_dates.png` | `results/system_characterization/temporal_results.csv` (Category E 240 temporal query rows) | 100% active version accuracy; zero future version leaks |

---

## 📋 Recommended Publication Tables (5 Tables)

| Table ID | Table Title | Source CSV File Path | Source Markdown File Path | Raw Evidence to Cite |
| :--- | :--- | :--- | :--- | :--- |
| **Table 1** | **End-to-End Multi-Tier Routing & Latency Summary** | `results/system_characterization/paper_tables/table1_routing_summary.csv` | `.../table1_routing_summary.md` | `results_master.csv` & `routing_results.csv` (exact N=922 breakdown across Tiers 0–4) |
| **Table 2** | **Retrieval Subsystem Component Breakdown** | `results/system_characterization/paper_tables/table2_retrieval_metrics.csv` | `.../table2_retrieval_metrics.md` | `retrieval_results.csv` (Recall@1/5/10, MRR, NDCG@10, Mean Latencies for BM25, Dense, RRF, CrossEncoder) |
| **Table 3** | **Incremental Knowledge Compilation Sweeps** | `results/system_characterization/paper_tables/table3_compiler_sweeps.csv` | `.../table3_compiler_sweeps.md` | `compiler_results.csv` (100 to 3,000 chunks, 0% to 100% mutation rates, reuse ratios, speedup factors) |
| **Table 4** | **Systematic Component Ablation Matrix** | `results/system_characterization/paper_tables/table4_ablation_study.csv` | `.../table4_ablation_study.md` | `ablation_results.csv` (Ablations w/o Fact Resolver, Canonical QA, BM25, Dense, CrossEncoder, DeBERTa, Isotonic Gate) |
| **Table 5** | **Standardized Failure Taxonomy (F1–F10)** | `results/system_characterization/paper_tables/table5_failure_taxonomy.csv` | `.../table5_failure_taxonomy.md` | `failures_verified.jsonl` (Counts, shares, severities, affected subsystems, root causes) |
