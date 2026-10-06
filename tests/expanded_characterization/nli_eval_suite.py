"""
tests/expanded_characterization/nli_eval_suite.py
Constructs a comprehensive 1,000-instance labeled enterprise NLI evaluation dataset
with independent Train (40%), Calibration (20%), and Held-out Test (40%) splits.
Covers 16 core enterprise reasoning phenomena.
"""
import random
import json
import hashlib
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass, asdict

from tests.expanded_characterization.domains import DOMAIN_POLICY_TEMPLATES, ENTERPRISE_DOMAINS

@dataclass
class NLIInstance:
    instance_id: str
    phenomenon: str  # One of 16 phenomena
    slice_category: str  # "semantic", "temporal", "authorization", "adversarial", "multi_clause"
    premise: str
    hypothesis: str
    gold_label: str  # "entailment", "contradiction", "neutral" (unknown)
    binary_grounded: bool  # True if premise strictly entails hypothesis
    split: str  # "train", "calibration", "test"
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class NLIDatasetSynthesizer:
    def __init__(self, seed: int = 42):
        self.seed = seed
        self.rng = random.Random(seed)

    def synthesize_dataset(self, total_instances: int = 1000) -> List[NLIInstance]:
        instances: List[NLIInstance] = []
        counter = 1

        # We will generate balanced instances across 16 phenomena:
        # Target ~62-63 instances per phenomenon to reach exactly 1,000
        phenomena_list = [
            # Entailment phenomena (5)
            ("1_direct_entailment", "semantic", "entailment"),
            ("2_paraphrase_variation", "semantic", "entailment"),
            ("3_multi_clause_entailment", "multi_clause", "entailment"),
            ("4_temporal_interval_entailment", "temporal", "entailment"),
            ("5_hierarchical_clearance_entailment", "authorization", "entailment"),
            
            # Contradiction phenomena (6)
            ("6_direct_contradiction", "semantic", "contradiction"),
            ("7_temporal_contradiction", "temporal", "contradiction"),
            ("8_authorization_contradiction", "authorization", "contradiction"),
            ("9_negation_inversion", "semantic", "contradiction"),
            ("10_numeric_mismatch", "semantic", "contradiction"),
            ("11_version_mismatch", "temporal", "contradiction"),
            
            # Neutral / Unknown / Insufficient Evidence phenomena (5)
            ("12_unknown_insufficient_evidence", "semantic", "neutral"),
            ("13_partial_entailment", "semantic", "neutral"),
            ("14_semantic_distractor", "adversarial", "neutral"),
            ("15_unsupported_exception", "multi_clause", "neutral"),
            ("16_out_of_domain_predicate", "adversarial", "neutral")
        ]

        # Cycle through domains and templates to generate rich, structurally diverse premises and hypotheses
        all_templates = []
        for code, tmpls in DOMAIN_POLICY_TEMPLATES.items():
            for t in tmpls:
                all_templates.append((code, t))

        self.rng.shuffle(all_templates)

        target_per_phenom = total_instances // len(phenomena_list)

        for p_idx, (phenom_name, slice_cat, gold_lbl) in enumerate(phenomena_list):
            count_for_this = target_per_phenom + (1 if p_idx < (total_instances % len(phenomena_list)) else 0)

            for _ in range(count_for_this):
                tmpl_data = self.rng.choice(all_templates)
                dept_code, (title, summary, pred, unit, val_prog, stype, conf) = tmpl_data
                val1 = val_prog[0]
                val2 = val_prog[-1]

                premise = ""
                hypothesis = ""

                if phenom_name == "1_direct_entailment":
                    premise = f"Under {title} (Version 4.0), the standard {pred} is strictly mandated at {val2} {unit} across all departments."
                    hypothesis = f"{title} establishes a mandatory {pred} of {val2} {unit}."
                elif phenom_name == "2_paraphrase_variation":
                    premise = f"According to corporate governance guidelines in {title}, the operating limit for {pred} is {val2} {unit}."
                    hypothesis = f"The standard corporate specification for {pred} within {title} is fixed at {val2} {unit}."
                elif phenom_name == "3_multi_clause_entailment":
                    premise = f"Under {title}, the baseline {pred} is {val2} {unit}; during emergencies, Director approval allows a 30-day grace period, provided audit logs are submitted within 48 hours."
                    hypothesis = f"Emergency dispensations under {title} require Director authorization and subsequent audit reporting within 48 hours."
                elif phenom_name == "4_temporal_interval_entailment":
                    premise = f"{title} is legally enforceable starting from 2025-07-01 with a standard {pred} of {val2} {unit}."
                    hypothesis = f"In October 2025, the enforceable requirement under {title} was {val2} {unit}."
                elif phenom_name == "5_hierarchical_clearance_entailment":
                    premise = f"Access to execute {title} requires {conf.upper()} clearance within Department {dept_code}."
                    hypothesis = f"Personnel with valid {conf.upper()} clearance in Department {dept_code} possess the authorization level required for {title}."
                elif phenom_name == "6_direct_contradiction":
                    premise = f"Under {title} (Version 4.0), the standard {pred} is strictly mandated at {val2} {unit} across all departments."
                    alt_val = val1 if val1 != val2 else f"{val2}_modified"
                    hypothesis = f"Under {title} Version 4.0, the standard {pred} is set at {alt_val} {unit}."
                elif phenom_name == "7_temporal_contradiction":
                    premise = f"Effective from 2025-07-01 to present, {title} (v4.0) enforces {pred} at {val2} {unit}."
                    hypothesis = f"In August 2025, the enforceable requirement under {title} was {val1} {unit}."
                elif phenom_name == "8_authorization_contradiction":
                    premise = f"Access to {title} is strictly restricted to personnel in Department {dept_code} holding Restricted clearance."
                    hypothesis = f"A contractor with Public clearance in an outside department is permitted to execute operations under {title}."
                elif phenom_name == "9_negation_inversion":
                    premise = f"Personnel are strictly prohibited from exceeding the established {pred} of {val2} {unit} without written authorization."
                    hypothesis = f"Personnel may freely exceed the {pred} limit of {val2} {unit} at any time without written authorization."
                elif phenom_name == "10_numeric_mismatch":
                    premise = f"The maximum permissible threshold for {pred} under {title} is {val2} {unit}."
                    mismatch_val = (val2 * 2) if isinstance(val2, (int, float)) else f"{val2}_invalid"
                    hypothesis = f"The maximum permissible threshold for {pred} under {title} is {mismatch_val} {unit}."
                elif phenom_name == "11_version_mismatch":
                    premise = f"Version 1.0 enforced {val1} {unit}, whereas Version 4.0 replaced it with {val2} {unit}."
                    hypothesis = f"Version 1.0 establishes {val2} {unit}."
                elif phenom_name == "12_unknown_insufficient_evidence":
                    premise = f"Under {title}, the standard {pred} is established at {val2} {unit}."
                    hypothesis = f"Employees who violate the {pred} limit in {title} must pay a fine of 50,000 INR."
                elif phenom_name == "13_partial_entailment":
                    premise = f"{title} sets the core {pred} at {val2} {unit} and requires Director approval for exceptions."
                    hypothesis = f"{title} sets the core {pred} at {val2} {unit}, and exceptions are granted automatically by automated scripts without human approval."
                elif phenom_name == "14_semantic_distractor":
                    premise = f"{title} specifies {pred} as {val2} {unit}. The related facility safety guidelines cover emergency building evacuations."
                    hypothesis = f"Facility safety guidelines specify that emergency building evacuations require {val2} {unit}."
                elif phenom_name == "15_unsupported_exception":
                    premise = f"{title} establishes {pred} at {val2} {unit} for domestic corporate operations."
                    hypothesis = f"International subsidiaries are granted a permanent 100% tax exemption under {title}."
                elif phenom_name == "16_out_of_domain_predicate":
                    premise = f"{title} establishes {pred} at {val2} {unit}."
                    hypothesis = f"Deep ocean diving vessels operated by the company must maintain a hull thickness of {val2} {unit}."
                else:
                    premise = f"{title} establishes {pred} at {val2} {unit}."
                    hypothesis = f"{title} establishes {pred} at {val2} {unit}."


                inst = NLIInstance(
                    instance_id=f"NLI-{counter:05d}",
                    phenomenon=phenom_name,
                    slice_category=slice_cat,
                    premise=premise,
                    hypothesis=hypothesis,
                    gold_label=gold_lbl,
                    binary_grounded=(gold_lbl == "entailment"),
                    split="train",  # assigned below
                    metadata={
                        "department": dept_code,
                        "policy_title": title,
                        "predicate": pred,
                        "unit": unit
                    }
                )
                instances.append(inst)
                counter += 1

        # Partition deterministically into 40% Train, 20% Calibration, 40% Held-Out Test
        self.rng.shuffle(instances)
        n_total = len(instances)
        n_train = int(n_total * 0.40)
        n_cal = int(n_total * 0.20)

        for idx, inst in enumerate(instances):
            if idx < n_train:
                inst.split = "train"
            elif idx < n_train + n_cal:
                inst.split = "calibration"
            else:
                inst.split = "test"

        return instances
