| Retrieval Subsystem | Recall@1 (%) | Recall@5 (%) | Recall@10 (%) | MRR | NDCG@10 | Mean Latency (ms) | Rank 1 Inversions |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| BM25 Inverted Index Alone | 12.6% | 65.0% | 89.4% | 0.330 | 0.445 | 2.95 | 87 |
| Dense Vector (Chroma) Alone | 10.2% | 63.0% | 96.0% | 0.314 | 0.410 | 23.56 | 33 |
| Reciprocal Rank Fusion (RRF) | 12.2% | 64.0% | 94.0% | 0.326 | 0.373 | 0.07 | 49 |
| FlashRank ONNX CrossEncoder | 16.2% | 67.0% | 93.4% | 0.353 | 0.494 | 4.19 | 54 |
