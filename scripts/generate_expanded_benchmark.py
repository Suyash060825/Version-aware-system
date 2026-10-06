"""
scripts/generate_expanded_benchmark.py
Main generator script for the Veritas Expanded Characterization Benchmark.
Produces all corpus artifacts, benchmark queries, manifests, and integrity reports.
"""
import os
import sys
import json
from datetime import datetime

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tests.expanded_characterization.domains import ENTERPRISE_DOMAINS
from tests.expanded_characterization.user_archetypes import build_enterprise_user_pool
from tests.expanded_characterization.policy_synthesizer import PolicySynthesizer
from tests.expanded_characterization.query_synthesizer import QuerySynthesizer
from tests.expanded_characterization.ledger import ExpandedGroundTruthLedger
from tests.expanded_characterization.integrity_checker import BenchmarkIntegrityChecker

OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "expanded_characterization"))

def run_generation(seed: int = 42):
    print("=" * 80)
    print("VERITAS EXPANDED CHARACTERIZATION BENCHMARK GENERATION")
    print(f"Random Seed: {seed}")
    print(f"Target Directory: {OUTPUT_DIR}")
    print("=" * 80)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 1. Synthesize Policies, Versions, Chunks, Facts, QAs
    print("\n[Step 1/5] Synthesizing enterprise policies and chunk structures...")
    poly_syn = PolicySynthesizer(seed=seed)
    policies, versions, chunks, facts, canonical_qas = poly_syn.synthesize_all()
    print(f"  -> Generated {len(policies)} policies across 24 enterprise domains")
    print(f"  -> Generated {len(versions)} policy versions")
    print(f"  -> Generated {len(chunks)} text chunks with SHA-256 digests")
    print(f"  -> Extracted {len(facts)} structured facts")
    print(f"  -> Created {len(canonical_qas)} canonical QA pairs")

    # 2. Build User Archetypes
    print("\n[Step 2/5] Constructing simulated enterprise user archetypes...")
    users = build_enterprise_user_pool()
    print(f"  -> Generated {len(users)} user archetypes across 25 departmental classifications")

    # 3. Synthesize Benchmark Queries
    print("\n[Step 3/5] Synthesizing benchmark queries across Categories A through P...")
    query_syn = QuerySynthesizer(policies, versions, chunks, facts, users, seed=seed)
    queries = query_syn.synthesize_queries()
    print(f"  -> Generated {len(queries)} unique benchmark query cases")

    # 4. Assemble Ledger
    print("\n[Step 4/5] Assembling ground truth ledger...")
    metadata = {
        "benchmark_name": "Veritas Expanded System Characterization Benchmark",
        "version": "2.0.0",
        "creation_timestamp": datetime.now().isoformat(),
        "seed": seed,
        "author": "Veritas Research & Evaluation Expansion Suite",
        "description": "Synthetic multi-domain enterprise policy benchmark for longitudinal retrieval, version routing, and composite authorization evaluation."
    }
    ledger = ExpandedGroundTruthLedger(
        metadata=metadata,
        policies=policies,
        versions=versions,
        chunks=chunks,
        facts=facts,
        canonical_qas=canonical_qas,
        queries=queries
    )

    # 5. Run Integrity Checks
    print("\n[Step 5/5] Running automated dataset-quality & integrity verification...")
    checker = BenchmarkIntegrityChecker(ledger, users)
    integrity_results = checker.verify_all()
    print(f"  -> Integrity Status: {integrity_results['status']}")
    for check_name, res in integrity_results["checks"].items():
        print(f"     * {check_name}: {'PASSED' if res['passed'] else 'FAILED'}")

    # Serialize Artifacts
    print("\nSerializing artifacts to data/expanded_characterization/...")
    ledger_path = os.path.join(OUTPUT_DIR, "expanded_ground_truth_ledger.json")
    ledger.save_json(ledger_path)
    print(f"  -> Saved full ledger ({os.path.getsize(ledger_path):,} bytes)")

    # Save individual split/component files for downstream evaluation scripts
    def save_json(fname, data):
        p = os.path.join(OUTPUT_DIR, fname)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"  -> Saved {fname}")

    save_json("expanded_policies.json", [p.to_dict() for p in policies])
    save_json("expanded_versions.json", [v.to_dict() for v in versions])
    save_json("expanded_chunks.json", [c.to_dict() for c in chunks])
    save_json("expanded_facts.json", [f.to_dict() for f in facts])
    save_json("expanded_canonical_qas.json", [qa.to_dict() for qa in canonical_qas])
    save_json("expanded_user_archetypes.json", [u.to_dict() for u in users])
    save_json("expanded_benchmark_queries.json", [q.to_dict() for q in queries])
    save_json("expanded_integrity_report.json", integrity_results)
    save_json("expanded_summary_statistics.json", integrity_results["metrics"])

    # Evaluation configuration file
    eval_config = {
        "benchmark_version": "2.0.0",
        "evaluation_regime": "EXPANDED_CHARACTERIZATION",
        "dataset_paths": {
            "ledger": "data/expanded_characterization/expanded_ground_truth_ledger.json",
            "policies": "data/expanded_characterization/expanded_policies.json",
            "versions": "data/expanded_characterization/expanded_versions.json",
            "chunks": "data/expanded_characterization/expanded_chunks.json",
            "facts": "data/expanded_characterization/expanded_facts.json",
            "canonical_qas": "data/expanded_characterization/expanded_canonical_qas.json",
            "users": "data/expanded_characterization/expanded_user_archetypes.json",
            "queries": "data/expanded_characterization/expanded_benchmark_queries.json"
        },
        "evaluation_parameters": {
            "random_seed": seed,
            "metrics": ["precision@1", "recall@1", "recall@5", "recall@10", "mrr", "map", "authorization_accuracy", "temporal_accuracy", "routing_accuracy", "abstention_accuracy", "latency_p50", "latency_p95", "latency_p99"],
            "retrieval_tiers": ["TIER_0_FACT", "TIER_1_SEMANTIC", "TIER_2_HYBRID", "REFUSAL"]
        }
    }
    save_json("eval_config.json", eval_config)

    # Manifest file
    manifest = {
        "manifest_version": "2.0.0",
        "generated_at": datetime.now().isoformat(),
        "integrity_status": integrity_results["status"],
        "corpus_summary": integrity_results["metrics"],
        "files": [
            "expanded_ground_truth_ledger.json",
            "expanded_policies.json",
            "expanded_versions.json",
            "expanded_chunks.json",
            "expanded_facts.json",
            "expanded_canonical_qas.json",
            "expanded_user_archetypes.json",
            "expanded_benchmark_queries.json",
            "expanded_integrity_report.json",
            "expanded_summary_statistics.json",
            "eval_config.json"
        ]
    }
    save_json("expanded_benchmark_manifest.json", manifest)

    print("\n" + "=" * 80)
    print("BENCHMARK EXPANSION COMPLETED SUCCESSFULLY")
    print("=" * 80)
    m = integrity_results["metrics"]
    print(f"1.  Total Enterprise Domains:          {m['total_domains']}")
    print(f"2.  Total Policies:                    {m['total_policies']}")
    print(f"3.  Total Policy Versions:             {m['total_versions']}")
    print(f"4.  Total Chunks (SHA-256 indexed):    {m['total_chunks']}")
    print(f"5.  Total Structured Facts:            {m['total_facts']}")
    print(f"6.  Total Canonical QA Pairs:          {m['total_canonical_qas']}")
    print(f"7.  Total User Archetypes:             {m['total_user_archetypes']}")
    print(f"8.  Total Unique Query Cases:          {m['total_queries']}")
    print(f"9.  Average Versions / Policy:         {m['average_versions_per_policy']}")
    print(f"10. Average Chunks / Version:          {m['average_chunks_per_version']}")
    print(f"11. Train Split Queries:               {m['splits'].get('train', 0)}")
    print(f"12. Dev Split Queries:                 {m['splits'].get('dev', 0)}")
    print(f"13. Test Split Queries:                {m['splits'].get('test', 0)}")
    print(f"14. Expected Routing Distribution:     {m['expected_routes']}")
    print(f"15. Authorization (Allow/Deny):        {m['authorization_distribution']}")
    print(f"16. Expected Abstention / Refusal:     {m['abstention_distribution']}")
    print(f"17. Policy Confidentiality Tiers:      {m['policy_confidentiality_distribution']}")
    print("=" * 80)

if __name__ == "__main__":
    run_generation(seed=42)
