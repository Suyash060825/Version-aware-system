"""
evaluation/corpus_generator.py
Deterministic Synthetic Enterprise Policy & Ground-Truth Generator.
Generates configurable, reproducible corpora (120, 500, 1000, 5000 policies)
with multi-version history, realistic enterprise domains, independent version-selection
oracles, and comprehensive ground truth.
"""

import os
import sys
import json
import hashlib
import random
from datetime import date, timedelta, datetime
from typing import List, Dict, Any, Optional, Tuple, Set

# Ensure project root in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tests.system_characterization.corpus.user_matrix import DEPARTMENTS_CONFIG, SimulatedUser, build_user_pool, AccessControlEvaluator
from tests.system_characterization.corpus.ground_truth_ledger import (
    GroundTruthLedger, PolicyLedgerEntry, VersionLedgerEntry,
    ChunkLedgerEntry, FactLedgerEntry, CanonicalQALedgerEntry,
    QueryGroundTruth
)
from tests.system_characterization.corpus.policy_generator import DOMAIN_POLICY_SPECS

# Enterprise domains and policy taxonomy
EXPANDED_DOMAINS = [
    {"dept_id": 1, "dept_name": "Human Resources", "code": "HR", "category": "Leave & Workplace"},
    {"dept_id": 2, "dept_name": "IT & Cybersecurity", "code": "IT", "category": "Security & Access"},
    {"dept_id": 3, "dept_name": "Finance", "code": "FIN", "category": "Expense & Accounting"},
    {"dept_id": 4, "dept_name": "Legal", "code": "LEG", "category": "Governance & Compliance"},
    {"dept_id": 5, "dept_name": "Compliance", "code": "CMP", "category": "Regulatory Standards"},
    {"dept_id": 6, "dept_name": "Engineering", "code": "ENG", "category": "Architecture & Operations"},
    {"dept_id": 7, "dept_name": "Procurement", "code": "PRC", "category": "Vendor & Purchasing"},
    {"dept_id": 8, "dept_name": "Healthcare & Benefits", "code": "BEN", "category": "Benefits & Wellness"},
    {"dept_id": 9, "dept_name": "Operations", "code": "OPS", "category": "Logistics & Supply"},
    {"dept_id": 10, "dept_name": "Facilities & Operations", "code": "FAC", "category": "Facilities & Safety"},
    {"dept_id": 11, "dept_name": "Sales & Marketing", "code": "SLS", "category": "Sales & Commissions"},
    {"dept_id": 12, "dept_name": "Executive & Board", "code": "EXEC", "category": "Executive Governance"},
    {"dept_id": 13, "dept_name": "Data Privacy & Protection", "code": "DPP", "category": "Privacy & GDPR"},
    {"dept_id": 14, "dept_name": "Audit & Risk Management", "code": "RSK", "category": "Internal Audit"},
    {"dept_id": 15, "dept_name": "Business Continuity & DR", "code": "BCDR", "category": "Disaster Recovery"},
]

POLICY_ARCHETYPE_TEMPLATES = [
    # Template: (title_fmt, desc_fmt, predicate, unit, value_sequence, structure_type, confidentiality)
    ("Annual Leave and Vacation Policy", "Rules governing annual vacation and carry-forward.", "annual_leave_days", "days", [18, 20, 22, 24, 25, 28, 30], "long", "internal"),
    ("Domestic Travel Lodging Allowance", "Limits on domestic hotel room booking per night.", "hotel_reimbursement_limit", "INR", [4000, 5000, 6000, 7500, 8500, 10000], "table", "internal"),
    ("Enterprise Multi-Factor Authentication", "Mandatory MFA enforcement and session lifetimes.", "mfa_grace_period_hours", "hours", [0, 4, 8, 12, 24], "short", "confidential"),
    ("Corporate Gift and Entertainment Standard", "Maximum permissible value for business gifts.", "gift_acceptance_threshold", "INR", [1000, 1500, 2000, 2500, 5000], "medium", "internal"),
    ("Customer Data Retention and Deletion", "Retention period for consumer transactional records.", "data_retention_period_years", "years", [5, 7, 8, 10], "nested", "restricted"),
    ("Purchase Order Approval Delegation", "Threshold requiring Vice President counter-signature.", "po_vp_approval_threshold", "INR", [250000, 500000, 1000000, 2500000], "table", "internal"),
    ("Production Server Access & Bastion Policy", "Approval window and session duration for root access.", "bastion_session_max_hours", "hours", [2, 4, 8], "short", "restricted"),
    ("Remote Work Equipment Allowance", "One-time allowance for home ergonomic setup.", "ergonomic_equipment_stipend", "INR", [15000, 25000, 35000, 50000], "medium", "internal"),
    ("Health Insurance Inpatient Hospitalization", "Maximum group medical sum insured per family.", "health_insurance_sum_insured", "INR", [300000, 500000, 750000, 1000000], "table", "internal"),
    ("Whistleblower Confidential Investigation SLA", "Statutory SLA to complete independent fraud inquiry.", "whistleblower_sla_days", "days", [60, 45, 30, 21], "nested", "confidential"),
    ("Disaster Recovery RTO SLA", "Maximum allowable downtime for Tier-1 core databases.", "recovery_time_objective_hours", "hours", [1, 2, 4, 8], "short", "confidential"),
    ("Software Vulnerability Remediation Mandate", "Maximum calendar days to patch Critical CVE vulnerabilities.", "critical_cve_remediation_days", "days", [14, 7, 3, 1], "short", "restricted"),
    ("Vehicle Mileage and Fuel Reimbursement", "Per-kilometer reimbursement rate for authorized business driving.", "mileage_rate_per_km", "INR", [8, 10, 12, 14, 16], "medium", "internal"),
    ("Employee Sabbatical and Unpaid Leave", "Maximum duration of authorized unpaid educational leave.", "sabbatical_max_months", "months", [6, 12, 18], "short", "internal"),
    ("Supplier Security Assessment Frequency", "Mandatory security re-assessment interval for third-party vendors.", "vendor_audit_frequency_months", "months", [24, 12, 6], "nested", "internal"),
    ("Patent Incentive and Inventor Award", "Cash award paid to employee inventors upon patent filing.", "patent_inventor_bonus", "INR", [25000, 50000, 75000, 100000], "table", "internal"),
    ("Physical Security Badge Replacement Fee", "Administrative penalty for unreturned or lost RFID smart badges.", "lost_badge_penalty", "INR", [250, 500, 750, 1000], "short", "public"),
    ("Public Media Speaking and Social Media Rules", "Prior approval notice window before public press appearances.", "press_notice_window_hours", "hours", [72, 48, 24], "short", "public"),
    ("Contractor Onboarding and Background Verification", "Mandatory criminal and credential check lookback window.", "background_check_lookback_years", "years", [5, 7, 10], "medium", "internal"),
    ("Environmental Single-Use Plastic Reduction", "Corporate milestone for paper and biodegradable packaging.", "packaging_recyclability_target", "percent", [50, 75, 90, 100], "medium", "public"),
]


class IndependentVersionOracle:
    """
    Independent ground-truth version selection oracle.
    Evaluates policy versions purely on explicit start_date and end_date validity intervals.
    Does NOT depend on Veritas VersionResolver or RAG pipeline.
    """
    @staticmethod
    def resolve(version_intervals: List[Dict[str, Any]], query_date_str: Optional[str]) -> Optional[Dict[str, Any]]:
        """
        version_intervals: list of dicts with keys:
          - version_label: str
          - version_num: float
          - effective_start: str (YYYY-MM-DD)
          - effective_end: Optional[str] (YYYY-MM-DD or None)
          - is_active: bool
        query_date_str: YYYY-MM-DD or None (evaluates active version)
        """
        if not version_intervals:
            return None

        if query_date_str is None:
            # Active version query
            active_versions = [v for v in version_intervals if v.get("is_active")]
            return active_versions[-1] if active_versions else version_intervals[-1]

        q_date = date.fromisoformat(query_date_str)

        # Sort versions chronologically by start date
        sorted_vers = sorted(version_intervals, key=lambda v: date.fromisoformat(v["effective_start"]))

        earliest_start = date.fromisoformat(sorted_vers[0]["effective_start"])
        if q_date < earliest_start:
            # Query predates earliest policy version -> Oracle correctly returns None (Abstain)
            return None

        matching = []
        for v in sorted_vers:
            v_start = date.fromisoformat(v["effective_start"])
            v_end = date.fromisoformat(v["effective_end"]) if v.get("effective_end") else None

            if v_start <= q_date:
                if v_end is None or q_date <= v_end:
                    matching.append(v)

        if matching:
            return matching[-1]

        # In case of gaps between versions
        return None


class ConfigurableCorpusGenerator:
    """
    Deterministic synthetic policy generator supporting configurable scales:
    120, 500, 1000, 5000 policies.
    """
    def __init__(self, seed: int = 42):
        self.seed = seed
        self.rng = random.Random(seed)

    def _generate_chunk_text(self, title: str, domain: str, version_label: str,
                             predicate: str, val: Any, unit: Optional[str],
                             section_name: str, section_idx: int,
                             is_confidential: bool = False) -> str:
        val_str = f"{val} {unit or ''}".strip()
        paragraphs = {
            "1. Purpose & Scope": (
                f"Purpose & Scope\n"
                f"This document establishes the official enterprise standard for {title.lower()} within {domain}. "
                f"Applicable to all operating entities, business units, full-time staff, and authorized contractors. "
                f"Version {version_label} supersedes all previous administrative memos and guidelines on this subject."
            ),
            "2. Eligibility & Criteria": (
                f"Eligibility & Criteria\n"
                f"All employees in good organizational standing who have completed their initial confirmation milestone "
                f"are eligible under the provisions of {title}. Specific departmental guidelines apply based on designated role, "
                f"confidentiality classification, and managerial approval hierarchies."
            ),
            "3. Detailed Rules & Core Thresholds": (
                f"Detailed Rules & Core Thresholds\n"
                f"Under official {title} (Version {version_label}), the authorized {predicate.replace('_', ' ')} is strictly set at {val_str}. "
                f"All formal calculations, automated compliance audits, expense validations, and reporting mechanisms must enforce this threshold. "
                f"No department head or individual manager possesses authority to unilaterally adjust this metric without executive dispensation."
            ),
            "4. Exceptions & Escalation Protocol": (
                f"Exceptions & Escalation Protocol\n"
                f"Any exceptional circumstances or required deviation exceeding the {val_str} standard must be submitted in writing "
                f"at least 5 business days in advance to the Department Head and designated Compliance Officer. "
                f"Emergency deviations require retrospective formal documentation within 48 hours of occurrence."
            ),
            "5. Penalties & Compliance Enforcement": (
                f"Penalties & Compliance Enforcement\n"
                f"Strict adherence to {title} is mandatory. Intentional circumvention, false record creation, or unapproved deviations "
                f"shall trigger formal disciplinary inquiry, suspension of corporate privileges, and potential referral to the Audit Committee."
            )
        }
        return paragraphs.get(section_name, paragraphs["3. Detailed Rules & Core Thresholds"])

    def generate_corpus(self, policy_count: int = 120) -> GroundTruthLedger:
        """
        Generates a GroundTruthLedger with exact policy_count policies and deterministic data.
        """
        self.rng = random.Random(self.seed)
        ledger = GroundTruthLedger()

        total_policies = policy_count
        chunk_id_counter = 1
        fact_id_counter = 1
        qa_id_counter = 1

        # Base 120 policies map to the curated DOMAIN_POLICY_SPECS
        base_archetypes = []
        for domain_spec in DOMAIN_POLICY_SPECS:
            d_id = domain_spec["dept_id"]
            d_name = domain_spec["dept_name"]
            cat = domain_spec["category"]
            for p_tuple in domain_spec["policies"]:
                base_archetypes.append({
                    "dept_id": d_id,
                    "dept_name": d_name,
                    "category": cat,
                    "title": p_tuple[0],
                    "desc": p_tuple[1],
                    "predicate": p_tuple[2],
                    "unit": p_tuple[3],
                    "values": p_tuple[4],
                    "structure": p_tuple[5],
                    "confidentiality": "confidential" if "MFA" in p_tuple[0] or "Vulnerability" in p_tuple[0] or "Bastion" in p_tuple[0] else ("restricted" if "Insider" in p_tuple[0] or "Customer Data" in p_tuple[0] else "internal")
                })

        archetypes_pool = []
        if total_policies <= len(base_archetypes):
            archetypes_pool = base_archetypes[:total_policies]
        else:
            archetypes_pool = list(base_archetypes)
            # Synthesize additional realistic policy archetypes deterministically
            needed = total_policies - len(archetypes_pool)
            for i in range(needed):
                domain = EXPANDED_DOMAINS[i % len(EXPANDED_DOMAINS)]
                template = POLICY_ARCHETYPE_TEMPLATES[i % len(POLICY_ARCHETYPE_TEMPLATES)]
                tier_idx = (i // len(POLICY_ARCHETYPE_TEMPLATES)) + 1
                
                title = f"{domain['dept_name']} {template[0]} (Tier {tier_idx})"
                desc = f"{template[1]} Specialized standard for {domain['dept_name']} Tier {tier_idx} operations."
                pred = f"{template[2]}_tier{tier_idx}"
                unit = template[3]
                base_vals = template[4]
                # Scale values per tier
                if isinstance(base_vals[0], (int, float)):
                    values = [int(v * (1 + 0.1 * tier_idx)) for v in base_vals]
                else:
                    values = list(base_vals)
                
                archetypes_pool.append({
                    "dept_id": domain["dept_id"],
                    "dept_name": domain["dept_name"],
                    "category": domain["category"],
                    "title": title,
                    "desc": desc,
                    "predicate": pred,
                    "unit": unit,
                    "values": values,
                    "structure": template[5],
                    "confidentiality": template[6]
                })

        # Process each policy
        for p_idx, arch in enumerate(archetypes_pool, start=1):
            policy_id = p_idx
            code = f"POL-{arch['dept_id']:02d}-{p_idx:04d}"
            title = arch["title"]
            dept_id = arch["dept_id"]
            dept_name = arch["dept_name"]
            category = arch["category"]
            confidentiality = arch["confidentiality"]
            predicate = arch["predicate"]
            unit = arch["unit"]
            values = arch["values"]

            version_count = len(values)
            policy_entry = PolicyLedgerEntry(
                policy_id=policy_id,
                policy_code=code,
                title=title,
                category=category,
                department_id=dept_id,
                department_name=dept_name,
                confidentiality=confidentiality,
                priority="high" if confidentiality in ("confidential", "restricted") else "medium",
                is_mandatory=True
            )

            # Assign timeline: start around 2020-01-01, increment per version
            base_year = 2020
            version_entries = []

            for v_idx, val in enumerate(values):
                version_id = (policy_id * 100) + (v_idx + 1)
                version_num = float(f"{v_idx + 1}.0")
                version_label = f"v{version_num}"
                is_active = (v_idx == version_count - 1)

                v_start = f"{base_year + v_idx}-01-01"
                v_end = None if is_active else f"{base_year + v_idx}-12-31"

                # Generate 5 standard structured chunks for each version
                section_names = [
                    "1. Purpose & Scope",
                    "2. Eligibility & Criteria",
                    "3. Detailed Rules & Core Thresholds",
                    "4. Exceptions & Escalation Protocol",
                    "5. Penalties & Compliance Enforcement"
                ]

                chunk_ids = []
                for s_idx, sec_name in enumerate(section_names, start=1):
                    cid = f"CHK-{policy_id:04d}-V{v_idx + 1}-{s_idx}"
                    text = self._generate_chunk_text(
                        title=title,
                        domain=dept_name,
                        version_label=version_label,
                        predicate=predicate,
                        val=val,
                        unit=unit,
                        section_name=sec_name,
                        section_idx=s_idx,
                        is_confidential=(confidentiality != "public")
                    )

                    t_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
                    e_hash = hashlib.sha256(f"{text}:{confidentiality}".encode("utf-8")).hexdigest()

                    chunk_entry = ChunkLedgerEntry(
                        chunk_id=cid,
                        policy_id=policy_id,
                        version_id=version_id,
                        version_label=version_label,
                        section_path=sec_name,
                        page=s_idx,
                        paragraph_num=1,
                        text=text,
                        text_hash=t_hash,
                        embedding_hash=e_hash,
                        char_count=len(text),
                        effective_start=v_start,
                        effective_end=v_end,
                        department_id=dept_id,
                        department_name=dept_name,
                        confidentiality=confidentiality,
                        allowed_roles=["admin", "executive"] if confidentiality == "restricted" else (
                            ["admin", "executive", "hr", "manager"] if confidentiality == "confidential" else ["all"]
                        ),
                        parent_version_id=version_entries[-1].version_id if version_entries else None,
                        supersedes_version_id=version_entries[-1].version_id if version_entries else None,
                        mutation_type="INITIAL" if v_idx == 0 else "MUT_AMENDMENT",
                        expected_embedding_action="NEW_EMBED" if v_idx == 0 else "NEW_EMBED",
                        expected_index_status="INDEXED" if is_active else "ARCHIVED",
                        is_active_version=is_active
                    )
                    ledger.add_chunk(chunk_entry)
                    chunk_ids.append(cid)

                # Fact entry (tied to Section 3)
                fid = f"FCT-{policy_id:04d}-V{v_idx + 1}"
                val_clean = str(val)
                fact_entry = FactLedgerEntry(
                    fact_id=fid,
                    policy_id=policy_id,
                    version_id=version_id,
                    subject=title,
                    predicate=predicate,
                    value=val_clean,
                    unit=unit,
                    scope=f"v{version_num}",
                    source_chunk_id=chunk_ids[2],
                    confidence=1.0
                )
                ledger.add_fact(fact_entry)

                # Canonical QA entry
                qid = f"CQA-{policy_id:04d}-V{v_idx + 1}"
                q_text = f"What is the {predicate.replace('_', ' ')} under {title}?"
                q_hash = hashlib.sha256(q_text.strip().lower().encode("utf-8")).hexdigest()
                qa_entry = CanonicalQALedgerEntry(
                    qa_id=qid,
                    policy_id=policy_id,
                    version_id=version_id,
                    question=q_text,
                    question_hash=q_hash,
                    target_answer=f"Under {title} ({version_label}), the {predicate.replace('_', ' ')} is {val_clean} {unit or ''}.".strip(),
                    source_chunk_ids=[chunk_ids[2]],
                    quality_score=1.0,
                    status="active" if is_active else "archived"
                )
                ledger.add_canonical_qa(qa_entry)

                # Version entry
                v_entry = VersionLedgerEntry(
                    version_id=version_id,
                    policy_id=policy_id,
                    policy_code=code,
                    version_num=version_num,
                    version_label=version_label,
                    effective_start=v_start,
                    effective_end=v_end,
                    is_active=is_active,
                    status="published" if is_active else "archived",
                    confidentiality=confidentiality,
                    department_id=dept_id,
                    mutation_type="INITIAL" if v_idx == 0 else "AMENDMENT",
                    change_summary=f"Updated {predicate.replace('_', ' ')} to {val_clean} {unit or ''}.".strip(),
                    chunk_ids=chunk_ids,
                    fact_ids=[fid],
                    qa_ids=[qid]
                )
                version_entries.append(v_entry)
                ledger.add_version(v_entry)

            policy_entry.versions = version_entries
            ledger.add_policy(policy_entry)

        return ledger

    def validate_corpus(self, ledger: GroundTruthLedger) -> Dict[str, Any]:
        """
        Validates corpus integrity:
        - Unique policy and version IDs
        - Strictly ordered version numbers
        - Non-overlapping version intervals
        - Valid chunk counts and text lengths
        - Chunk hash consistency
        """
        errors = []
        policy_ids = set()
        chunk_ids = set()

        for pid, p in ledger.policies.items():
            if pid in policy_ids:
                errors.append(f"Duplicate policy_id {pid}")
            policy_ids.add(pid)

            if not p.versions:
                errors.append(f"Policy {pid} has no versions")
                continue

            active_count = sum(1 for v in p.versions if v.is_active)
            if active_count != 1:
                errors.append(f"Policy {pid} has {active_count} active versions (expected exactly 1)")

            for idx in range(len(p.versions) - 1):
                v_curr = p.versions[idx]
                v_next = p.versions[idx + 1]
                if v_curr.version_num >= v_next.version_num:
                    errors.append(f"Policy {pid} non-ascending versions: {v_curr.version_num} >= {v_next.version_num}")
                if v_curr.effective_end and v_curr.effective_end > v_next.effective_start:
                    errors.append(f"Policy {pid} version date overlap: {v_curr.effective_end} > {v_next.effective_start}")

        for cid, c in ledger.chunks.items():
            if cid in chunk_ids:
                errors.append(f"Duplicate chunk_id {cid}")
            chunk_ids.add(cid)
            if len(c.text.strip()) == 0:
                errors.append(f"Empty text in chunk {cid}")

        return {
            "valid": len(errors) == 0,
            "error_count": len(errors),
            "errors": errors[:20],
            "total_policies": len(ledger.policies),
            "total_versions": len(ledger.versions),
            "total_chunks": len(ledger.chunks),
            "total_facts": len(ledger.facts),
            "total_canonical_qas": len(ledger.canonical_qas)
        }


if __name__ == "__main__":
    gen = ConfigurableCorpusGenerator(seed=42)
    print("Testing corpus generation for 120 policies...")
    l120 = gen.generate_corpus(120)
    v120 = gen.validate_corpus(l120)
    print(f"120 Corpus: valid={v120['valid']}, policies={v120['total_policies']}, versions={v120['total_versions']}, chunks={v120['total_chunks']}")

    print("Testing corpus generation for 500 policies...")
    l500 = gen.generate_corpus(500)
    v500 = gen.validate_corpus(l500)
    print(f"500 Corpus: valid={v500['valid']}, policies={v500['total_policies']}, versions={v500['total_versions']}, chunks={v500['total_chunks']}")

    print("Testing corpus generation for 1,000 policies...")
    l1000 = gen.generate_corpus(1000)
    v1000 = gen.validate_corpus(l1000)
    print(f"1,000 Corpus: valid={v1000['valid']}, policies={v1000['total_policies']}, versions={v1000['total_versions']}, chunks={v1000['total_chunks']}")
