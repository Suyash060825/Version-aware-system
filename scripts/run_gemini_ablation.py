#!/usr/bin/env python3
"""
scripts/run_gemini_ablation.py
Runs the reproducible evaluation suite using Google Gemini as the LLM backend
to demonstrate the architecture's true accuracy when unconstrained by local hardware.
Outputs are saved to results/gemini/ to avoid overwriting the Qwen baseline.
"""
import os
import sys
import importlib.util

os.environ["LLM_BACKEND"] = "gemini"
if "sqlite" not in os.environ.get("DATABASE_URL", ""):
    # Point to local sqlite ledger if postgres is not available
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    db_path = os.path.join(base_dir, "data", "ledger.db")
    if os.path.exists(db_path):
        os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"

if not os.environ.get("GEMINI_API_KEY"):
    print("WARNING: GEMINI_API_KEY environment variable is not set.")
    print("Please run this script as: GEMINI_API_KEY='your_key' python scripts/run_gemini_ablation.py")
    print("Attempting to run anyway (it may fall back to Extractive if the Gemini client fails)...\n")

original_open = open
def intercepted_open(file, mode='r', buffering=-1, encoding=None, errors=None, newline=None, closefd=True, opener=None):
    if isinstance(file, str) and file.startswith("results/") and not file.startswith("results/gemini"):
        file = file.replace("results/", "results/gemini/")
        os.makedirs(os.path.dirname(file), exist_ok=True)
    return original_open(file, mode, buffering, encoding, errors, newline, closefd, opener)

import builtins
builtins.open = intercepted_open

eval_script_path = os.path.join(os.path.dirname(__file__), "run_reproducible_eval.py")
spec = importlib.util.spec_from_file_location("run_reproducible_eval", eval_script_path)
eval_module = importlib.util.module_from_spec(spec)
sys.modules["run_reproducible_eval"] = eval_module
spec.loader.exec_module(eval_module)

if __name__ == "__main__":
    print("\n--- Starting LLM Ablation Study (Backend: GEMINI) ---")
    os.makedirs("results/gemini", exist_ok=True)
    try:
        eval_module.run_reproducible_evaluation()
    finally:
        builtins.open = original_open
        print("\n--- Ablation Study Complete ---")
        print("Gemini results saved to: results/gemini/")
