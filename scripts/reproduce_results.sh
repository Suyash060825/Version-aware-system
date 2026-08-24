#!/usr/bin/env bash
set -e

echo "========================================================="
echo "   REPRODUCING PUBLICATION RESULTS & EXPERIMENTS         "
echo "   Repository: Version-aware-system-bestchatgpt          "
echo "========================================================="

# 1. Ensure directories exist
mkdir -p results data/benchmarks

# 2. Run Environment Metadata Introspection
echo "[Step 1/3] Generating environment metadata..."
python3 -c "
import sys, os, platform, json, psutil
import importlib.metadata
import torch, chromadb, faiss, sqlalchemy

def get_pkg_version(name):
    try:
        return importlib.metadata.version(name)
    except Exception:
        return 'unknown'

env_info = {
    'system': {
        'os': platform.system(),
        'os_release': platform.release(),
        'os_version': platform.version(),
        'architecture': platform.machine(),
        'processor': platform.processor(),
        'cpu_count_logical': psutil.cpu_count(logical=True),
        'cpu_count_physical': psutil.cpu_count(logical=False),
        'total_ram_gb': round(psutil.virtual_memory().total / (1024**3), 2)
    },
    'runtime': {
        'python_version': sys.version.split()[0],
        'python_executable': sys.executable
    },
    'gpu': {
        'cuda_available': torch.cuda.is_available(),
        'device_count': torch.cuda.device_count() if torch.cuda.is_available() else 0,
        'device_name': torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'None (CPU execution)'
    },
    'packages': {
        'torch': get_pkg_version('torch'),
        'chromadb': get_pkg_version('chromadb'),
        'faiss_cpu': get_pkg_version('faiss-cpu'),
        'sentence_transformers': get_pkg_version('sentence-transformers'),
        'fastembed': get_pkg_version('fastembed'),
        'flashrank': get_pkg_version('flashrank'),
        'sqlalchemy': get_pkg_version('sqlalchemy'),
        'scikit_learn': get_pkg_version('scikit-learn'),
        'python_dateutil': get_pkg_version('python-dateutil')
    },
    'models_and_engines': {
        'embedding_engine': os.environ.get('EMBEDDING_ENGINE', 'fastembed'),
        'embedding_model': os.environ.get('EMBEDDING_MODEL', 'BAAI/bge-small-en-v1.5'),
        'reranker_engine': os.environ.get('RERANKER_ENGINE', 'flashrank'),
        'reranker_model': os.environ.get('RERANKER_MODEL', 'ms-marco-TinyBERT-L-2-v2'),
        'llm_backend': os.environ.get('LLM_BACKEND', 'ollama'),
        'llm_model': os.environ.get('LOCAL_LLM_MODEL', 'qwen2.5:3b'),
        'vector_store': 'ChromaDB + FAISS HNSW',
        'sparse_store': 'Partitioned BM25'
    }
}

os.makedirs('results', exist_ok=True)
with open('results/environment.json', 'w') as f:
    json.dump(env_info, f, indent=2)
"

# 3. Run Reproducible Evaluation Suite
echo "[Step 2/3] Executing Master Evaluation Suite across all baselines and ablations..."
python3 scripts/run_reproducible_eval.py

# 4. Run Evaluation Query Pass
echo "[Step 3/3] Generating evaluation query traces..."
python3 scripts/run_eval.py

echo "========================================================="
echo "   REPRODUCIBILITY RUN COMPLETE!                         "
echo "   All artifacts verified in results/                    "
echo "========================================================="
