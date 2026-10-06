"""
tests/expanded_characterization/policy_synthesizer.py
Generates the comprehensive synthetic enterprise policy corpus:
- 600 distinct policies across 24 domains
- 2,700+ policy versions with temporal lifecycle (enactment, amendment, revision, revocation, future)
- 13,000+ chunks with SHA-256 digests
- Structured facts and canonical Q&A pairs
Deterministic generation with SEED=42.
"""
import hashlib
import random
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime

from tests.expanded_characterization.domains import (
    ENTERPRISE_DOMAINS,
    DOMAIN_POLICY_TEMPLATES,
    DEPT_CODE_TO_ID,
    DEPT_ID_TO_META
)
from tests.expanded_characterization.ledger import (
    PolicyMetadata,
    PolicyVersion,
    PolicyChunk,
    PolicyFact,
    CanonicalQAPair
)

# Standard lifecycle intervals for 4-5 version progressions
LIFECYCLE_INTERVALS = [
    ("v1.0", "2021-01-01T00:00:00", "2022-06-30T23:59:59", "initial", "Initial policy enactment and baseline threshold governance."),
    ("v2.0", "2022-07-01T00:00:00", "2023-12-31T23:59:59", "minor_amendment", "Updated thresholds following annual compliance review and operational adjustments."),
    ("v3.0", "2024-01-01T00:00:00", "2025-06-30T23:59:59", "major_revision", "Comprehensive enterprise restructuring and tightened governance standards."),
    ("v4.0", "2025-07-01T00:00:00", None, "active_standard", "Current enterprise operating standard under enhanced digital oversight."),
]

FUTURE_INTERVAL = ("v5.0_scheduled", "2027-01-01T00:00:00", None, "future_scheduled", "Approved forward-looking standard scheduled for future fiscal year enactment.")
REVOCATION_INTERVAL = ("v4.0_revoked", "2025-07-01T00:00:00", "2026-03-31T23:59:59", "revocation", "Policy officially revoked and retired due to consolidation of enterprise workflows.")

def compute_chunk_hash(chunk_text: str) -> str:
    return hashlib.sha256(chunk_text.strip().encode("utf-8")).hexdigest()

class PolicySynthesizer:
    def __init__(self, seed: int = 42):
        self.seed = seed
        self.rng = random.Random(seed)

    def synthesize_all(self) -> Tuple[List[PolicyMetadata], List[PolicyVersion], List[PolicyChunk], List[PolicyFact], List[CanonicalQAPair]]:
        policies: List[PolicyMetadata] = []
        versions: List[PolicyVersion] = []
        chunks: List[PolicyChunk] = []
        facts: List[PolicyFact] = []
        canonical_qas: List[CanonicalQAPair] = []

        policy_seq = 1
        chunk_seq = 1
        fact_seq = 1
        qa_seq = 1

        for dept_meta in ENTERPRISE_DOMAINS:
            dept_code = dept_meta["code"]
            dept_id = dept_meta["dept_id"]
            dept_name = dept_meta["name"]
            default_conf = dept_meta["default_confidentiality"]
            templates = DOMAIN_POLICY_TEMPLATES.get(dept_code, [])

            for tmpl_idx, tmpl in enumerate(templates, start=1):
                title, summary, predicate, unit, val_prog, structure_type, conf_override = tmpl
                confidentiality = conf_override or default_conf
                policy_id = f"POL-{dept_code}-{tmpl_idx:03d}"

                # 1. Create Policy Metadata
                policy = PolicyMetadata(
                    policy_id=policy_id,
                    title=title,
                    department_id=dept_id,
                    department_name=dept_name,
                    department_code=dept_code,
                    confidentiality=confidentiality,
                    predicate=predicate,
                    unit=unit,
                    structure_type=structure_type,
                    domain_description=summary,
                    created_at="2021-01-01T00:00:00"
                )
                policies.append(policy)

                # 2. Generate Versions (4-5 versions per policy)
                num_vals = len(val_prog)
                # Standard 4 versions lifecycle
                version_specs = [
                    ("v1.0", "2021-01-01T00:00:00", "2022-06-30T23:59:59", "initial", "Initial policy enactment and baseline threshold governance."),
                    ("v2.0", "2022-07-01T00:00:00", "2023-12-31T23:59:59", "minor_amendment", "Updated thresholds following annual compliance review and operational adjustments."),
                    ("v3.0", "2024-01-01T00:00:00", "2025-06-30T23:59:59", "major_revision", "Comprehensive enterprise restructuring and tightened governance standards."),
                    ("v4.0", "2025-07-01T00:00:00", None, "active_standard", "Current enterprise operating standard under enhanced digital oversight."),
                ]
                
                # Add 5th version for ~20% of policies (future scheduled or revocation)
                if (tmpl_idx % 5 == 0):
                    if tmpl_idx % 10 == 0:
                        # Revoked scenario
                        version_specs[3] = ("v4.0", "2025-07-01T00:00:00", "2026-03-31T23:59:59", "revoked", "Policy revoked and discontinued in 2026.")
                    else:
                        version_specs.append(FUTURE_INTERVAL)

                prev_version_id: Optional[str] = None


                for v_idx, v_spec in enumerate(version_specs):
                    v_tag, eff_from, eff_to, change_type, change_sum = v_spec
                    version_id = f"{policy_id}-V{v_idx+1}"
                    is_active = (eff_to is None)
                    is_revoked = ("revok" in change_type.lower())

                    # Assign predicate value for this version
                    val_index = min(v_idx, len(val_prog) - 1)
                    val = val_prog[val_index]

                    # Generate rich section texts
                    sec1_text = f"POLICY OVERVIEW & ADMINISTRATIVE AUTHORITY:\n{title} (Document ID: {policy_id}, Version: {v_tag}). Governed by the {dept_name} Department. Purpose: {summary} Effective Date: {eff_from}. Status: {'ACTIVE' if is_active else 'SUPERSEDED' if not is_revoked else 'REVOKED'}. Confidentiality Classification: {confidentiality.upper()}."
                    
                    sec2_text = f"CORE OPERATING THRESHOLDS & SPECIFICATION MATRIX:\nUnder {policy_id} ({v_tag}), the primary operating metric '{predicate}' is formally established at {val} {unit}. All organizational units reporting under {dept_name} must adhere strictly to this limit. Historical progression and audit criteria require logging all transactions against the benchmark of {val} {unit}."

                    sec3_text = f"ROLE RESTRICTIONS & CLEARANCE CONTROLS:\nAccess to execute or modify procedures under {policy_id} requires {confidentiality.upper()} clearance within Department {dept_id} ({dept_code}). Authorization follows strict role-based access control (RBAC). Personnel without authorized clearance or grade level are barred from executing overrides."

                    sec4_text = f"EXCEPTIONS, SPECIAL DISPENSATIONS & ESCALATION:\nIn emergency circumstances or formal audit situations, exceptions to the {val} {unit} limit require written sign-off from the Department Director and Corporate Compliance. Unapproved deviations are flagged for immediate administrative review within 48 hours."

                    sec5_text = f"ENFORCEMENT, AUDIT TRAILS & VERSION HISTORY:\nRevision history summary: {change_sum} Previous supersession link: {prev_version_id or 'None (Original Enactment)'}. Compliance records must be preserved for at least 7 years in the corporate digital ledger."

                    full_text = "\n\n".join([sec1_text, sec2_text, sec3_text, sec4_text, sec5_text])

                    p_version = PolicyVersion(
                        version_id=version_id,
                        policy_id=policy_id,
                        version_number=v_idx + 1,
                        version_tag=v_tag,
                        effective_from=eff_from,
                        effective_to=eff_to,
                        is_active=is_active,
                        is_revoked=is_revoked,
                        supersedes_version_id=prev_version_id,
                        change_type=change_type,
                        change_summary=change_sum,
                        predicate_value=val,
                        full_text=full_text
                    )
                    versions.append(p_version)

                    # 3. Create Chunks for this version (5 distinct chunks)
                    sections = [
                        ("Overview & Scope", sec1_text),
                        ("Core Operating Matrix", sec2_text),
                        ("Role & Access Controls", sec3_text),
                        ("Exceptions & Escalation", sec4_text),
                        ("Enforcement & Audit History", sec5_text)
                    ]

                    version_chunk_ids = []
                    for c_idx, (sec_title, sec_content) in enumerate(sections, start=1):
                        chunk_id = f"CHK-{dept_code}-{chunk_seq:06d}"
                        chunk_seq += 1
                        version_chunk_ids.append(chunk_id)

                        chunk_hash = compute_chunk_hash(sec_content)
                        token_est = len(sec_content.split())

                        p_chunk = PolicyChunk(
                            chunk_id=chunk_id,
                            policy_id=policy_id,
                            version_id=version_id,
                            chunk_index=c_idx,
                            section_title=sec_title,
                            text=sec_content,
                            sha256_hash=chunk_hash,
                            token_count_est=token_est,
                            effective_from=eff_from,
                            effective_to=eff_to,
                            department_id=dept_id,
                            confidentiality=confidentiality
                        )
                        chunks.append(p_chunk)

                    # 4. Create Structured Fact for this version (linked to chunk 2)
                    fact_id = f"FCT-{dept_code}-{fact_seq:06d}"
                    fact_seq += 1
                    p_fact = PolicyFact(
                        fact_id=fact_id,
                        policy_id=policy_id,
                        version_id=version_id,
                        chunk_id=version_chunk_ids[1],  # Sec 2 is Core Operating Matrix
                        predicate=predicate,
                        value=val,
                        unit=unit,
                        effective_from=eff_from,
                        effective_to=eff_to,
                        department_id=dept_id,
                        confidentiality=confidentiality
                    )
                    facts.append(p_fact)

                    # 5. Create Canonical QA Pair for this version
                    qa_id = f"QA-{dept_code}-{qa_seq:06d}"
                    qa_seq += 1
                    canonical_qa = CanonicalQAPair(
                        qa_id=qa_id,
                        policy_id=policy_id,
                        version_id=version_id,
                        query_text=f"What is the {predicate} under {title} ({v_tag})?",
                        canonical_answer=f"Under {title} ({v_tag}), the established {predicate} is {val} {unit}.",
                        evidence_chunk_ids=[version_chunk_ids[1]],
                        predicate=predicate,
                        effective_from=eff_from,
                        effective_to=eff_to
                    )
                    canonical_qas.append(canonical_qa)

                    prev_version_id = version_id
                policy_seq += 1

        return policies, versions, chunks, facts, canonical_qas
