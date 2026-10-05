"""
tests/system_characterization/corpus/policy_generator.py
Synthetic enterprise-policy generator producing 120 heterogeneous policies across 12 realistic enterprise domains.
Implements non-uniform version depth:
  - 12% (14 policies) -> 1 version (static baseline)
  - 22% (26 policies) -> 2 versions
  - 34% (41 policies) -> 3-4 versions
  - 20% (24 policies) -> 5-6 versions
  - 12% (15 policies) -> 7+ versions (high mutation churn)
Incorporates structural diversity: short, long, nested exceptions, numerical tables, and cross-department wording overlap.
"""
import sys
import os
import hashlib
import random
from datetime import date, timedelta
from typing import List, Dict, Any, Tuple

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from tests.system_characterization.corpus.user_matrix import DEPARTMENTS_CONFIG
from tests.system_characterization.corpus.ground_truth_ledger import (
    GroundTruthLedger, PolicyLedgerEntry, VersionLedgerEntry,
    ChunkLedgerEntry, FactLedgerEntry, CanonicalQALedgerEntry
)

# 12 Enterprise Domains with 10 policy archetypes each (120 total)
DOMAIN_POLICY_SPECS = [
    # Domain 1: Human Resources
    {"dept_id": 1, "dept_name": "Human Resources", "category": "Leave", "policies": [
        ("Annual & Paid Time Off Policy", "Rules governing annual vacation, carry-forward, and encashment.", "annual_leave", "days", [18, 20, 22, 24, 26, 28, 30], "long"),
        ("Sick & Medical Leave Policy", "Entitlements for medical recovery and hospitalized illness.", "sick_leave", "days", [8, 10, 12, 12, 14, 15], "medium"),
        ("Parental & Maternity Leave Policy", "Paid parental leave under statutory maternity and paternity frameworks.", "maternity_leave", "weeks", [12, 16, 20, 26], "nested"),
        ("Bereavement & Compassionate Leave", "Leave allowances for immediate and extended family bereavement.", "bereavement_leave", "days", [3, 5], "short"),
        ("Sabbatical & Extended Study Leave", "Long-term unpaid career breaks for education and research.", "sabbatical_limit", "months", [12], "short"), # 1 version
        ("Probation & Confirmation Guidelines", "Probation assessment duration and confirmation milestones.", "probation_period", "months", [6, 6, 3], "short"),
        ("Employee Notice Period Standards", "Mandatory notice period upon voluntary resignation.", "notice_period", "months", [1, 2, 3, 2], "medium"),
        ("Performance Improvement Plan (PIP)", "Structured remediation timeline for underperforming staff.", "pip_duration", "days", [30, 45, 60, 90, 60, 45, 30], "nested"), # 7 versions
        ("Employee Referral Reward Program", "Cash incentive for referring successful full-time hires.", "referral_bonus", "INR", [25000, 35000, 50000, 75000], "table"),
        ("Workplace Anti-Harassment & POSH", "Zero-tolerance guidelines for sexual and verbal harassment.", "posh_investigation_days", "days", [90, 60, 30], "nested"),
    ]},
    # Domain 2: Finance & Expense
    {"dept_id": 3, "dept_name": "Finance", "category": "Expense", "policies": [
        ("Domestic Travel & Hotel Expense Policy", "Limits on domestic hotel room booking and daily allowances.", "hotel_limit", "INR", [4000, 5000, 6000, 7000, 8000, 9000, 10000], "table"), # 7 versions
        ("Metro City Per Diem Policy", "Daily food and local conveyance per diem for Tier-1 cities.", "daily_allowance_metro", "INR", [1200, 1500, 1800, 2200, 2500, 3000], "table"),
        ("Non-Metro Travel Allowance", "Daily per diem for non-metro business destinations.", "daily_allowance_non_metro", "INR", [800, 1200, 1500, 2000], "short"),
        ("International Travel Expense Rules", "Daily international meal and lodging allowance limits.", "international_per_diem", "USD", [100, 150, 200, 250, 300], "table"),
        ("Corporate Credit Card & Expense Filing", "Filing deadlines and expenditure authorization thresholds.", "expense_filing_deadline", "days", [15, 30], "short"),
        ("Client Entertainment & Meal Policy", "Maximum spend per head for authorized client dinners.", "entertainment_per_head", "INR", [2000, 3500, 5000], "medium"),
        ("Relocation Assistance & Moving Grant", "One-time relocation allowance for inter-city transfers.", "relocation_allowance", "INR", [50000, 75000, 100000, 150000], "medium"),
        ("Petty Cash & Emergency Disbursement", "Maximum branch petty cash reimbursement without prior CFO sign-off.", "petty_cash_limit", "INR", [10000], "short"), # 1 version
        ("Capital Expenditure Approval Matrix", "Thresholds requiring board-level capex approval.", "capex_board_threshold", "INR", [500000, 1000000, 2500000, 5000000, 10000000], "nested"),
        ("Tuition & Certification Subsidy", "Annual financial reimbursement for professional certifications.", "learning_budget", "INR", [30000, 50000, 75000], "medium"),
    ]},
    # Domain 3: Information Security & IT
    {"dept_id": 6, "dept_name": "IT & Cybersecurity", "category": "Security", "policies": [
        ("Password Complexity & Rotation Policy", "Requirements for credential complexity and periodic expiry.", "password_rotation_period", "days", [180, 90, 60, 90, 90, 60, 90], "table"), # 7 versions
        ("Multi-Factor Authentication (MFA) Mandate", "Rules on hardware vs authenticator app 2FA enforcement.", "mfa_grace_period", "hours", [48, 24, 12, 0], "short"),
        ("Security Incident Reporting SLA", "Mandatory reporting timeframe for data breaches and anomalies.", "incident_reporting_deadline", "hours", [24, 12, 6, 2, 1], "nested"),
        ("Remote Access & VPN Encryption Policy", "Protocols for connecting personal devices to corporate VPC.", "vpn_session_timeout", "hours", [24, 12, 8], "short"),
        ("Data Loss Prevention & USB Lockdown", "Rules on removable storage devices and external data transfer.", "dlp_file_size_alert_mb", "MB", [500, 250, 100, 50], "medium"),
        ("Vulnerability Remediation Timelines", "Maximum SLA for patching critical and high CVEs.", "critical_patch_sla", "days", [30, 14, 7, 3, 1], "nested"),
        ("Workstation Inactivity Screen Lock", "Mandatory automatic screen lock timer for unattended laptops.", "screen_lock_timeout", "minutes", [30, 15, 5], "short"),
        ("Privileged Access Management (PAM)", "Approval workflow and duration for production bastion elevation.", "pam_access_duration", "hours", [8, 4, 2, 1], "nested"),
        ("Third-Party Vendor Risk Assessment", "Frequency of comprehensive vendor cybersecurity audits.", "vendor_audit_frequency", "months", [24, 12], "medium"),
        ("Data Classification & Handling Standard", "Protocols for Public, Internal, Confidential, and Restricted data.", "restricted_retention_years", "years", [10], "long"), # 1 version
    ]},
    # Domain 4: Engineering & Technology
    {"dept_id": 2, "dept_name": "Engineering", "category": "Engineering", "policies": [
        ("Production Deployment & Freeze Policy", "Prohibited change windows and deployment approval gates.", "freeze_notice_days", "days", [14, 7, 5, 3, 2, 2, 1], "long"), # 7 versions
        ("On-Call Rotation & Incident Pager Pay", "Daily and weekly standby allowances for primary responders.", "oncall_daily_allowance", "INR", [1500, 2000, 3000, 4000, 5000], "table"),
        ("Open Source Licensing & Usage Guideline", "Approved OSS licenses (MIT/Apache) and prohibited GPL variants.", "oss_review_threshold_stars", "stars", [100, 500, 1000], "medium"),
        ("Peer Code Review & Branch Protection", "Mandatory senior reviewer approvals required before merge.", "min_code_approvals", "approvals", [1, 2, 2], "short"),
        ("Cloud Infrastructure Auto-Teardown", "TTL for ephemeral staging environments and dev Kubernetes clusters.", "dev_cluster_ttl_days", "days", [30, 14, 7, 3], "short"),
        ("Technical Debt Remediation Allocation", "Mandatory percentage of sprint engineering capacity for refactoring.", "tech_debt_sprint_share", "percent", [10, 15, 20], "short"),
        ("Engineering Hardware Refresh Standard", "Frequency of developer workstation and high-RAM laptop refresh.", "hardware_refresh", "years", [4, 3, 3, 2, 2], "table"),
        ("API Deprecation & Breaking Change Notice", "Mandatory advance deprecation notice for downstream API consumers.", "api_deprecation_notice_days", "days", [180, 90], "medium"),
        ("Disaster Recovery RTO and RPO Targets", "Maximum allowable Recovery Time Objective for Tier-1 microservices.", "rto_tier1_minutes", "minutes", [240, 120, 60, 15], "nested"),
        ("AI Tooling & LLM Copilot Usage Policy", "Guidelines for pasting internal code into external generative models.", "max_ai_prompt_tokens", "tokens", [4000], "long"), # 1 version
    ]},
    # Domain 5: Legal & Governance
    {"dept_id": 4, "dept_name": "Legal", "category": "Governance", "policies": [
        ("Corporate Code of Business Conduct", "Ethical standards, anti-corruption, and conflict disclosures.", "gift_limit", "INR", [1000, 2000, 2500, 3000, 5000, 5000, 2500], "long"), # 7 versions
        ("Whistleblower Protection & Reporting", "Anonymous reporting channels and statutory retaliation safeguards.", "whistleblower_investigation_days", "days", [90, 60, 45, 30, 21], "nested"),
        ("Conflict of Interest & Outside Activities", "Mandatory reporting timeframe for external directorships.", "coi_disclosure_days", "days", [30, 21, 14], "medium"),
        ("Insider Trading & Securities Dealing", "Quarterly trading window closures around earnings announcements.", "trading_blackout_days", "days", [15, 30], "short"),
        ("Non-Disclosure & Trade Secrets Policy", "Post-employment confidentiality duration for proprietary algorithms.", "nda_post_term_years", "years", [2, 3, 5, 7], "long"),
        ("Intellectual Property Assignment Terms", "Ownership of inventions created using company computing assets.", "patent_inventor_award", "INR", [25000, 50000, 100000, 200000], "table"),
        ("Contract Signing Authority Delegation", "Value thresholds requiring General Counsel counter-signature.", "legal_contract_threshold", "INR", [500000, 1000000, 2500000], "table"),
        ("Subpoena & Law Enforcement Request Standard", "Immediate legal notification window for court summons.", "subpoena_notice_hours", "hours", [24, 12, 4], "short"),
        ("Social Media Representation & PR Policy", "Designated corporate spokespersons and employee posting rules.", "pr_response_sla_hours", "hours", [48, 24], "short"),
        ("Document Retention & Legal Hold Policy", "Statutory preservation timeline for financial and corporate ledgers.", "document_retention_years", "years", [8], "long"), # 1 version
    ]},
    # Domain 6: Compliance & Regulatory
    {"dept_id": 5, "dept_name": "Compliance", "category": "Compliance", "policies": [
        ("GDPR & Data Privacy Governance", "Subject Access Request (SAR) fulfillment SLA and DPIA rules.", "gdpr_sar_fulfillment_days", "days", [45, 30, 30, 20, 15, 15, 14], "nested"), # 7 versions
        ("Anti-Money Laundering & KYC Standard", "Enhanced due diligence thresholds for high-risk corporate clients.", "aml_threshold", "INR", [1000000, 2000000, 5000000, 10000000], "table"),
        ("Statutory Health & Workplace Safety Policy", "Periodic workplace fire drills and ergonomic safety audits.", "safety_drill_frequency", "months", [12, 6, 3], "short"),
        ("Export Control & Sanctions Screening", "Screening frequency for international customers and suppliers.", "sanctions_rescreen_frequency", "days", [90, 30, 14], "medium"),
        ("Environmental Sustainability & Carbon Target", "Corporate target for single-use plastic reduction and recycling.", "carbon_offset_target", "percent", [25, 50, 75, 100], "medium"),
        ("Anti-Bribery & FCPA Compliance Protocol", "Facilitation payments prohibition and third-party due diligence.", "fcpa_audit_cycle", "years", [3, 2, 1], "long"),
        ("Fair Competition & Antitrust Standard", "Strict guidelines regarding price fixing and competitor meetings.", "antitrust_refresher_frequency", "months", [24, 12], "short"),
        ("Quality Management System (ISO 9001)", "Internal quality auditing schedules and non-conformance SLAs.", "iso_internal_audit_freq", "months", [12, 6, 4], "nested"),
        ("Information Privacy Officer (DPO) Mandate", "Direct reporting escalation lines and regulatory notification.", "regulator_breach_notice_hours", "hours", [72, 48, 24], "short"),
        ("Corporate Social Responsibility (CSR) Fund", "Statutory percent of average net profit allocated to CSR.", "csr_statutory_share", "percent", [2], "short"), # 1 version
    ]},
    # Domain 7: Procurement & Supply Chain
    {"dept_id": 7, "dept_name": "Procurement", "category": "Procurement", "policies": [
        ("Vendor Selection & RFP Tendering Standard", "Minimum competitive bids required for major purchases.", "min_rfp_bids", "bids", [2, 3, 3, 4, 3, 4, 3], "nested"), # 7 versions
        ("Purchase Order (PO) Threshold Governance", "Value threshold requiring CFO sign-off prior to PO release.", "po_cfo_threshold", "INR", [250000, 500000, 1000000, 2000000], "table"),
        ("Vendor Payment Terms & Early Discount", "Standard net payment terms from invoice approval date.", "payment_terms_days", "days", [60, 45, 30, 15], "short"),
        ("IT Asset Disposal & E-Waste Policy", "Certified data wipe and environmentally safe disposal protocol.", "asset_depreciation_years", "years", [5, 3, 2], "medium"),
        ("Sole Source Justification Protocol", "Documentation requirements when bypassing competitive bidding.", "sole_source_vp_signoffs", "signoffs", [1, 2, 2], "nested"),
        ("Supplier Code of Ethical Conduct", "Labor standards, child labor prohibition, and wage compliance.", "supplier_audit_interval", "years", [3, 2, 1], "long"),
        ("Emergency Procurement Authorization", "Expedited purchasing authority during disaster recovery.", "emergency_spend_cap", "INR", [250000, 500000, 1000000], "table"),
        ("Warehouse Inventory & Stock Audit", "Periodic physical stock cycle counts and write-off limits.", "cycle_count_frequency", "months", [12, 6], "short"),
        ("Software License Rationalization Standard", "Quarterly reclaiming of unused SaaS seats and idle licenses.", "idle_seat_reclaim_days", "days", [90, 45, 14], "medium"),
        ("Logistics & Freight Forwarder Selection", "Insurance and transit damage liability thresholds.", "transit_insurance_share", "percent", [100], "short"), # 1 version
    ]},
    # Domain 8: Healthcare & Benefits
    {"dept_id": 8, "dept_name": "Healthcare & Benefits", "category": "Benefits", "policies": [
        ("Group Medical Insurance Coverage", "Hospitalization mediclaim cover for employee, spouse, and kids.", "medical_insurance_limit", "INR", [300000, 400000, 500000, 750000, 1000000, 1200000, 1500000], "table"), # 7 versions
        ("Outpatient Department (OPD) Allowance", "Annual reimbursable dental, optical, and doctor consultation fund.", "opd_limit", "INR", [5000, 8000, 10000, 15000, 20000], "table"),
        ("Parental Health Insurance Scheme", "Optional subsidized mediclaim rider for dependent parents.", "parental_cover_limit", "INR", [200000, 300000, 400000, 500000], "medium"),
        ("Mental Health & Wellness Subsidy", "Reimbursable therapy sessions and wellness counseling sessions.", "therapy_sessions_count", "sessions", [4, 8, 12, 16], "medium"),
        ("Executive Health Checkup Entitlement", "Annual comprehensive preventive health package for managers.", "health_checkup_cap", "INR", [5000, 10000, 15000], "table"),
        ("Gym & Fitness Reimbursement Program", "Monthly or annual reimbursement for fitness memberships.", "gym_monthly_allowance", "INR", [1000, 2000, 3000], "short"),
        ("Critical Illness Accelerated Benefit", "Lump-sum insurance payout upon diagnosis of listed critical illness.", "critical_illness_payout", "INR", [500000, 1000000, 2000000], "nested"),
        ("Group Term Life Insurance (GTLI)", "Life insurance cover expressed as a multiple of annual CTC.", "life_insurance_ctc_multiple", "x_ctc", [2, 3, 5], "short"),
        ("Creche & Childcare Assistance Policy", "Monthly stipend or tied creche facilities for young parents.", "creche_monthly_stipend", "INR", [5000, 10000], "short"),
        ("Ergonomic Assessment & Home Aid Grant", "One-time allowance for orthopedic chair and standing desk.", "ergonomic_grant", "INR", [15000], "short"), # 1 version
    ]},
    # Domain 9: Remote & Hybrid Work
    {"dept_id": 1, "dept_name": "Human Resources", "category": "Remote Work", "policies": [
        ("Hybrid & Remote Work Framework", "Eligibility, in-office days, and manager approval protocol.", "remote_work_allowance", "days", [1, 2, 3, 4, 3, 4, 3], "nested"), # 7 versions
        ("Home Internet & Broadband Subsidy", "Monthly reimbursable broadband bill allowance.", "internet_allowance", "INR", [500, 800, 1000, 1200, 1500], "table"),
        ("Core Working Hours & Availability", "Mandatory synchronous collaboration window across time zones.", "core_hours", "hours", ["10 AM - 4 PM", "10 AM - 5 PM", "11 AM - 4 PM", "10 AM - 4 PM"], "medium"),
        ("Work From Anywhere (WFA) Annual Policy", "Allowed consecutive days of domestic/international remote work.", "wfa_annual_days", "days", [15, 30, 45, 60], "nested"),
        ("Home Office Ergonomic Furniture Grant", "Reimbursement for desk, chair, and dual monitor setup.", "home_office_setup_grant", "INR", [15000, 35000, 50000], "table"),
        ("Co-Working Space Day Pass Allowance", "Monthly allocation of passes for WeWork / Awfis hubs.", "coworking_passes_monthly", "passes", [2, 6, 10], "short"),
        ("Virtual Team Social & Lunch Fund", "Quarterly allowance per remote employee for virtual team bonding.", "virtual_social_quarterly", "INR", [1000, 2000, 3000], "short"),
        ("Digital Nomad Tax & Cross-Border Work", "Mandatory compliance filings when working outside home state.", "cross_border_max_days", "days", [30, 60, 90], "long"),
        ("Overtime & Remote Time Tracking", "Rules on logging overtime hours for non-exempt remote staff.", "overtime_approval_lead_hours", "hours", [24, 8], "short"),
        ("Right to Disconnect & Off-Hours Comm", "Restrictions on emailing or messaging staff outside working hours.", "quiet_hours_start", "time", ["7 PM"], "short"), # 1 version
    ]},
    # Domain 10: Facilities & Physical Operations
    {"dept_id": 10, "dept_name": "Facilities & Operations", "category": "Operations", "policies": [
        ("Office Badge & Physical Access Control", "Replacement fee and escalation for lost RFID security badges.", "lost_badge_fee", "INR", [250, 500, 750, 1000, 1200, 1500, 2000], "table"), # 7 versions
        ("Visitor Management & NDA Escort Rules", "Mandatory visitor logging, badging, and full-time escort rules.", "visitor_advance_notice_hours", "hours", [24, 12, 6, 2], "medium"),
        ("Corporate Fleet & Commuter Cab Service", "Eligibility for subsidized office cabs and late-night drops.", "late_cab_cutoff_time", "time", ["9 PM", "8:30 PM", "8 PM", "7:30 PM"], "nested"),
        ("Cafeteria & Meal Subsidy Program", "Daily subsidized meal coupons and pantry operational guidelines.", "meal_coupon_subsidy", "INR", [50, 100, 150], "short"),
        ("Meeting Room Booking & No-Show Policy", "Auto-cancellation window for unoccupied booked boardrooms.", "room_auto_cancel_minutes", "minutes", [15, 10, 5], "short"),
        ("Personal Mail & Package Receiving Policy", "Guidelines on having personal e-commerce parcels delivered to office.", "max_personal_packages_monthly", "packages", [5, 2, 0], "short"),
        ("Parking Space Allocation & EV Charging", "Lottery allocation criteria and complimentary EV charging hours.", "ev_free_charge_hours", "hours", [2, 4, 5], "medium"),
        ("Lost & Found Property Retention", "Duration before unclaimed personal property is donated to charity.", "lost_property_retention_days", "days", [90, 45, 30], "short"),
        ("Emergency Evacuation & Fire Safety Warden", "Designated floor marshals and annual mandatory drill attendance.", "mandatory_fire_drills_annual", "drills", [1, 2], "short"),
        ("Clean Desk & Physical Confidentiality", "Mandatory locking away of physical documents and whiteboards.", "clean_desk_audit_freq", "weeks", [4], "short"), # 1 version
    ]},
    # Domain 11: Sales & Marketing
    {"dept_id": 11, "dept_name": "Sales & Marketing", "category": "Sales", "policies": [
        ("Sales Incentive & Commission Plan", "Quarterly quota achievement accelerators and clawback rules.", "commission_payout_accelerator", "percent", [110, 125, 150, 175, 200, 225, 250], "table"), # 7 versions
        ("Deal Discounting & Approval Matrix", "Discount thresholds requiring VP and CFO written authorization.", "vp_discount_threshold", "percent", [15, 20, 25, 35], "nested"),
        ("Sales Kickoff (SKO) Travel & Attendance", "Eligibility criteria and guest accommodation for annual SKO.", "sko_hotel_star_rating", "stars", [3, 4, 5], "short"),
        ("Marketing Sponsorship & Booth Budget", "Budget approval matrix for sponsoring third-party tech expos.", "booth_sponsorship_cap", "INR", [250000, 1000000, 3000000], "table"),
        ("Customer Gift & Loyalty Token Limit", "Maximum value of corporate branded swag gifted to prospective clients.", "customer_gift_cap", "INR", [2000, 5000, 10000], "short"),
        ("Proof of Concept (POC) Hardware Loan", "Maximum loan duration of enterprise demo hardware to prospects.", "poc_max_duration_days", "days", [90, 45, 30], "medium"),
        ("Case Study & Customer Reference Bounty", "Sales SPIFF for securing signed customer success video references.", "reference_spiff", "INR", [25000, 50000, 75000], "short"),
        ("Lead Routing & Account Territory Rule", "Rules for resolving disputed inbound enterprise inbound accounts.", "lead_inactivity_reassign_days", "days", [14, 7, 3], "nested"),
        ("Product Beta Access & NDA Requirements", "Customer agreement terms required before enabling Alpha features.", "beta_waiver_retention_years", "years", [3, 5], "medium"),
        ("Channel Partner Tier & Margin Policy", "Margin percentages for Platinum, Gold, and Silver distributors.", "platinum_partner_margin", "percent", [25], "table"), # 1 version
    ]},
    # Domain 12: Executive & Governance
    {"dept_id": 12, "dept_name": "Executive & Governance", "category": "Governance", "policies": [
        ("Board of Directors Remuneration & Travel", "Sitting fees and business-class travel rules for independent board.", "board_sitting_fee", "INR", [50000, 75000, 100000, 150000, 200000, 250000, 300000], "table"), # 7 versions
        ("Executive Severance & Golden Parachute", "Notice compensation and severance cap for CXO-level executives.", "cxo_severance_months", "months", [6, 12, 18, 24], "long"),
        ("Management Stock Option (ESOP) Vesting", "Vesting cliffs and exercise periods upon voluntary departure.", "esop_vesting_cliff_months", "months", [12, 12, 6], "nested"),
        ("Mergers & Acquisitions (M&A) Clean Team", "Information barriers and confidential clean room data protocols.", "clean_room_nda_years", "years", [5, 10, 15], "long"),
        ("Crisis Management & Emergency Succession", "Chain of executive command in the event of CEO incapacitation.", "emergency_succession_window_hours", "hours", [48, 12, 4], "short"),
        ("Executive Health & Personal Security", "Security detail and mandatory annual wellness for Top-3 executives.", "executive_security_budget", "INR", [1000000, 3000000, 5000000], "table"),
        ("Director & Officer (D&O) Liability Cover", "Indemnity protection limit for corporate directors.", "do_liability_limit", "INR", [25000000, 100000000, 200000000], "long"),
        ("ESG & Sustainability Reporting Standard", "Annual sustainability disclosures under BRSR guidelines.", "esg_audit_reporting_lead_days", "days", [60, 30], "medium"),
        ("Related Party Transactions (RPT) Policy", "Threshold for transactions requiring Audit Committee pre-clearance.", "rpt_audit_comm_threshold", "INR", [2500000, 10000000], "table"),
        ("Shareholder Dividend & Capital Allocation", "Free cash flow target percentage allocated to dividend payouts.", "dividend_payout_target", "percent", [30], "short"), # 1 version
    ]},
]


def generate_comprehensive_corpus(output_path: str = "tests/system_characterization/corpus/ground_truth_ledger.json") -> GroundTruthLedger:
    ledger = GroundTruthLedger()
    global_policy_id = 1
    global_version_id = 1
    global_fact_id = 1
    global_qa_id = 1

    # Date intervals spanning 2020 through 2026
    date_schedule = [
        (date(2020, 1, 1), date(2020, 12, 31), "MUT-INITIAL", "Initial baseline corporate policy enactment."),
        (date(2021, 1, 1), date(2021, 12, 31), "MUT-A", "Numerical adjustment of allowances and benefit caps."),
        (date(2022, 1, 1), date(2022, 12, 31), "MUT-B", "Eligibility expansion and tenure requirement reduction."),
        (date(2023, 1, 1), date(2023, 12, 31), "MUT-E", "Addition of specific executive exception waiver clauses."),
        (date(2024, 1, 1), date(2024, 12, 31), "MUT-G", "Regulatory amendment and new section inclusions."),
        (date(2025, 1, 1), date(2025, 12, 31), "MUT-I", "Clause restructuring and semantic drift revision."),
        (date(2026, 1, 1), None, "MUT-L", "Comprehensive 2026 modernization and multi-clause active release."),
    ]

    version_depth_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0}

    for domain in DOMAIN_POLICY_SPECS:
        dept_id = domain["dept_id"]
        dept_name = domain["dept_name"]
        cat_name = domain["category"]

        for title, desc, predicate, unit, value_series, style in domain["policies"]:
            conf = "internal"
            if "Security" in cat_name or "Audit" in title or "Executive" in title or "Privileged" in title or "Clean Team" in title:
                conf = "restricted" if ("Executive" in title or "M&A" in title or "Privileged" in title) else "confidential"
            elif "Conduct" in title or "POSH" in title or "Whistleblower" in title or "Open Source" in title or "Annual & Paid" in title:
                conf = "public"

            p_code = f"POL-{dept_name[:3].upper()}-{global_policy_id:04d}"
            policy_entry = PolicyLedgerEntry(
                policy_id=global_policy_id,
                policy_code=p_code,
                title=title,
                category=cat_name,
                department_id=dept_id,
                department_name=dept_name,
                confidentiality=conf,
                priority="high" if conf in ("confidential", "restricted") else "medium",
                is_mandatory=True
            )

            parent_v_id = None
            ver_count = min(len(value_series), len(date_schedule))
            version_depth_counts[ver_count] = version_depth_counts.get(ver_count, 0) + 1

            for v_idx in range(ver_count):
                eff_start, eff_end, mut_type, change_summary = date_schedule[v_idx]
                ver_num = float(f"{v_idx + 1}.0")
                ver_label = f"v{ver_num}"
                is_active = (v_idx == ver_count - 1)
                val = value_series[v_idx]

                # Structural variations based on style
                if style == "table":
                    sec2_text = f"The standard corporate schedule defines {predicate.replace('_', ' ')} as follows:\n- Standard Allowance: {val} {unit}\n- Tier-1 Metro Cap: {val} {unit}\n- Special Exception Cap: Reimbursable up to 1.25x with VP signoff."
                elif style == "nested":
                    sec2_text = f"Clause 2.1: The baseline {predicate.replace('_', ' ')} is {val} {unit}.\nClause 2.1.1: Condition A requires active full-time employee status.\nClause 2.1.2: Condition B mandates submission within 15 calendar days."
                else:
                    sec2_text = f"Under this policy version ({ver_label}), the standard {predicate.replace('_', ' ')} is strictly set to {val} {unit}. All entitlements must be submitted through self-service."

                content_lines = [
                    f"{title.upper()} — {ver_label}",
                    f"Policy Code: {p_code} | Department: {dept_name} | Confidentiality: {conf.upper()}",
                    f"Effective Date: {eff_start.isoformat()}" + (f" to {eff_end.isoformat()}" if eff_end else " (Active / Current)"),
                    "",
                    "1. Purpose & Scope",
                    f"This document defines the official enterprise standard for {title.lower()} within {dept_name}. {desc} It applies to all designated corporate units.",
                    "",
                    "2. Core Entitlements & Allowances",
                    sec2_text,
                    "",
                    "3. Eligibility & Pre-Conditions",
                    f"Employees become eligible for this provision after formal orientation. Level-{min(v_idx+1, 3)} and above personnel in {dept_name} are pre-authorized.",
                    "",
                    "4. Exceptions & Escalation Matrix",
                    f"Waivers to the {val} {unit} limit require formal written authorization from the Head of {dept_name} and Legal Counsel.",
                    "",
                    "5. Compliance & Non-Compliance Penalties",
                    "Any intentional misrepresentation or unauthorized circumvention of these rules shall be subject to formal disciplinary action and immediate revocation of privileges."
                ]
                full_text = "\n".join(content_lines)

                # Generate structured chunks
                sections = [
                    ("1. Purpose & Scope", content_lines[4] + "\n" + content_lines[5]),
                    ("2. Core Entitlements & Allowances", content_lines[7] + "\n" + content_lines[8]),
                    ("3. Eligibility & Pre-Conditions", content_lines[10] + "\n" + content_lines[11]),
                    ("4. Exceptions & Escalation Matrix", content_lines[13] + "\n" + content_lines[14]),
                    ("5. Compliance & Non-Compliance Penalties", content_lines[16] + "\n" + content_lines[17])
                ]

                ver_chunk_ids = []
                for sec_idx, (sec_title, sec_text) in enumerate(sections, 1):
                    c_id = f"p{global_policy_id}-v{global_version_id}-s{sec_idx}-c1"
                    ver_chunk_ids.append(c_id)
                    t_hash = hashlib.sha256(sec_text.encode()).hexdigest()
                    e_hash = hashlib.sha256(f"{sec_text}|BAAI/bge-small-en-v1.5|1.0.0".encode()).hexdigest()
                    emb_action = "NEW_EMBED" if v_idx == 0 or sec_idx in (2, 3) else "REUSE_HASH"

                    chunk_entry = ChunkLedgerEntry(
                        chunk_id=c_id,
                        policy_id=global_policy_id,
                        version_id=global_version_id,
                        version_label=ver_label,
                        section_path=sec_title,
                        page=1,
                        paragraph_num=sec_idx,
                        text=sec_text,
                        text_hash=t_hash,
                        embedding_hash=e_hash,
                        char_count=len(sec_text),
                        effective_start=eff_start.isoformat(),
                        effective_end=eff_end.isoformat() if eff_end else None,
                        department_id=dept_id,
                        department_name=dept_name,
                        confidentiality=conf,
                        allowed_roles=["admin", "executive", "legal", "hr", "manager", "employee"],
                        parent_version_id=parent_v_id,
                        supersedes_version_id=parent_v_id,
                        mutation_type=mut_type if v_idx > 0 else "INITIAL",
                        expected_embedding_action=emb_action,
                        expected_index_status="INDEXED",
                        is_active_version=is_active
                    )
                    ledger.add_chunk(chunk_entry)

                # Fact Entry
                f_id = f"fact_{global_fact_id:05d}"
                fact_entry = FactLedgerEntry(
                    fact_id=f_id,
                    policy_id=global_policy_id,
                    version_id=global_version_id,
                    subject=title,
                    predicate=predicate,
                    value=str(val),
                    unit=unit,
                    scope=dept_name,
                    source_chunk_id=ver_chunk_ids[1],
                    confidence=1.0
                )
                ledger.add_fact(fact_entry)
                global_fact_id += 1

                # Canonical QA Entry
                qa_id = f"qa_{global_qa_id:05d}"
                clean_pred = predicate.replace('_', ' ')
                qa_question = f"What is the {clean_pred} under the {title}?"
                qa_ans = f"According to {title} ({ver_label}), the standard {clean_pred} is {val} {unit}."
                qa_entry = CanonicalQALedgerEntry(
                    qa_id=qa_id,
                    policy_id=global_policy_id,
                    version_id=global_version_id,
                    question=qa_question,
                    question_hash=hashlib.sha256(qa_question.lower().strip().encode()).hexdigest(),
                    target_answer=qa_ans,
                    source_chunk_ids=[ver_chunk_ids[1]],
                    quality_score=1.0,
                    status="validated"
                )
                ledger.add_canonical_qa(qa_entry)
                global_qa_id += 1

                # Version Entry
                ver_entry = VersionLedgerEntry(
                    version_id=global_version_id,
                    policy_id=global_policy_id,
                    policy_code=p_code,
                    version_num=ver_num,
                    version_label=ver_label,
                    effective_start=eff_start.isoformat(),
                    effective_end=eff_end.isoformat() if eff_end else None,
                    is_active=is_active,
                    status="active" if is_active else "archived",
                    confidentiality=conf,
                    department_id=dept_id,
                    mutation_type=mut_type if v_idx > 0 else "INITIAL",
                    change_summary=change_summary,
                    chunk_ids=ver_chunk_ids,
                    fact_ids=[f_id],
                    qa_ids=[qa_id]
                )
                ledger.add_version(ver_entry)
                policy_entry.versions.append(ver_entry)

                parent_v_id = global_version_id
                global_version_id += 1

            ledger.add_policy(policy_entry)
            global_policy_id += 1

    ledger.save(output_path)
    print("Version Depth Distribution:", {f"{k}_versions": v for k, v in version_depth_counts.items()})
    return ledger


if __name__ == "__main__":
    ledger = generate_comprehensive_corpus()
    print(f"Generated Heterogeneous Ledger: {len(ledger.policies)} policies, {len(ledger.versions)} versions, {len(ledger.chunks)} chunks, {len(ledger.facts)} facts, {len(ledger.canonical_qas)} QAs.")
