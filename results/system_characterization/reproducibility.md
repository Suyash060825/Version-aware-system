# Reproducibility & Benchmark Execution Guide

### 1. Environment & Dependencies
* Python 3.14 / 3.11+
* SQLite 3, FAISS-CPU, ChromaDB, FlashRank, NumPy, SciPy, Matplotlib, Scikit-Learn.
* Fixed Random Seed: `42`

### 2. Execution Commands
```bash
# 1. Generate Expanded Corpus and Ground-Truth Ledger (120 policies, 600 versions, 3000 chunks)
python3 tests/system_characterization/corpus/policy_generator.py

# 2. Generate Benchmark Queries across Categories A through T (922 queries)
python3 tests/system_characterization/corpus/query_generator.py

# 3. Execute Master Test Runner
python3 tests/system_characterization/runner.py

# 4. Render All 24 Publication Figures
python3 tests/system_characterization/analysis/plot_generator.py

# 5. Compile Formal Markdown Tables and Reports
python3 tests/system_characterization/analysis/report_generator.py
```

### 3. Verification of Zero Modification Rule
* All production application code in `rag/`, `app.py`, `models.py`, `seed.py`, and `config.py` remained 100% unaltered.
* All testing artifacts and generated datasets are strictly contained within `tests/system_characterization/` and `results/system_characterization/`.
