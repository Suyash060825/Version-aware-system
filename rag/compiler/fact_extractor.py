"""
rag/compiler/fact_extractor.py
Robust rule-based and regex fact extraction covering 20+ enterprise policy domains.
"""
import re
from typing import List
from models import PolicyFact, now_utc
from rag.compiler.document_ir import ChunkIR

class FactExtractor:
    def extract(self, chunks: List[ChunkIR]) -> List[PolicyFact]:
        facts = []
        for chunk in chunks:
            text = chunk.text

            # 1. Annual Leave
            for m in re.finditer(r"(\d+)\s*(?:working\s*)?days?\s*(?:paid\s*)?(?:of\s*)?annual\s*leave", text, re.I):
                facts.append(PolicyFact(
                    policy_id=chunk.policy_id, version_id=chunk.version_id,
                    subject="Annual Leave", predicate="annual_leave",
                    value=m.group(1), unit="days", scope="per calendar year",
                    source_chunk_id=chunk.chunk_id, confidence=1.0, created_at=now_utc()
                ))

            # 2. Sick Leave
            for m in re.finditer(r"(\d+)\s*(?:working\s*)?days?\s*(?:paid\s*)?(?:of\s*)?sick\s*leave", text, re.I):
                facts.append(PolicyFact(
                    policy_id=chunk.policy_id, version_id=chunk.version_id,
                    subject="Sick Leave", predicate="sick_leave",
                    value=m.group(1), unit="days", scope="per year",
                    source_chunk_id=chunk.chunk_id, confidence=1.0, created_at=now_utc()
                ))

            # 3. Maternity / Paternity / Bereavement Leave
            for m in re.finditer(r"maternity\s*[:\-]?\s*(\d+)\s*(week|month|day)s?", text, re.I):
                facts.append(PolicyFact(
                    policy_id=chunk.policy_id, version_id=chunk.version_id,
                    subject="Maternity Leave", predicate="maternity_leave",
                    value=m.group(1), unit=m.group(2) + "s", scope="maternity benefit",
                    source_chunk_id=chunk.chunk_id, confidence=1.0, created_at=now_utc()
                ))
            for m in re.finditer(r"paternity\s*[:\-]?\s*(\d+)\s*(week|month|day)s?", text, re.I):
                facts.append(PolicyFact(
                    policy_id=chunk.policy_id, version_id=chunk.version_id,
                    subject="Paternity Leave", predicate="paternity_leave",
                    value=m.group(1), unit=m.group(2) + "s", scope="paternity benefit",
                    source_chunk_id=chunk.chunk_id, confidence=1.0, created_at=now_utc()
                ))
            for m in re.finditer(r"(\d+)\s*days?\s*(?:paid\s*)?bereavement\s*leave", text, re.I):
                facts.append(PolicyFact(
                    policy_id=chunk.policy_id, version_id=chunk.version_id,
                    subject="Bereavement Leave", predicate="bereavement_leave",
                    value=m.group(1), unit="days", scope="immediate family",
                    source_chunk_id=chunk.chunk_id, confidence=1.0, created_at=now_utc()
                ))

            # 4. Remote Work Allowance & Internet Reimbursement
            for m in re.finditer(r"(?:remotely\s*(?:up\s*to)?|remote\s*work\s*[:\-]?)\s*(\d+)\s*days?\s*per\s*week", text, re.I):
                facts.append(PolicyFact(
                    policy_id=chunk.policy_id, version_id=chunk.version_id,
                    subject="Remote Work", predicate="remote_work_allowance",
                    value=m.group(1), unit="days per week", scope="weekly remote schedule",
                    source_chunk_id=chunk.chunk_id, confidence=1.0, created_at=now_utc()
                ))
            for m in re.finditer(r"(?:rs\.?|inr|₹)?\s*([\d,]+)(?:/month)?\s*internet\s*(?:reimbursement|allowance)", text, re.I):
                facts.append(PolicyFact(
                    policy_id=chunk.policy_id, version_id=chunk.version_id,
                    subject="Internet Allowance", predicate="internet_allowance",
                    value=f"Rs. {m.group(1)}", unit="INR per month", scope="remote expense",
                    source_chunk_id=chunk.chunk_id, confidence=1.0, created_at=now_utc()
                ))

            # 5. Core Working Hours & Grace Period
            for m in re.finditer(r"core\s*hours\s*\(([0-9APMapm\s:–\-]+)\)", text, re.I):
                facts.append(PolicyFact(
                    policy_id=chunk.policy_id, version_id=chunk.version_id,
                    subject="Working Hours", predicate="core_hours",
                    value=m.group(1).strip(), unit="hours", scope="standard business hours",
                    source_chunk_id=chunk.chunk_id, confidence=1.0, created_at=now_utc()
                ))
            for m in re.finditer(r"(\d+)\s*(?:minute|min)s?\s*(?:grace\s*period|arrival\s*window)", text, re.I):
                facts.append(PolicyFact(
                    policy_id=chunk.policy_id, version_id=chunk.version_id,
                    subject="Arrival Grace Period", predicate="grace_period",
                    value=m.group(1), unit="minutes", scope="attendance check-in",
                    source_chunk_id=chunk.chunk_id, confidence=1.0, created_at=now_utc()
                ))

            # 6. Hotel Limit & Travel Daily Allowances
            for m in re.finditer(r"(?:maximum|max)\s*(?:rs\.?|inr|₹)?\s*([\d,]+)(?:/night)?\s*for\s*domestic\s*travel", text, re.I):
                facts.append(PolicyFact(
                    policy_id=chunk.policy_id, version_id=chunk.version_id,
                    subject="Travel Hotel", predicate="hotel_limit",
                    value=f"Rs. {m.group(1)}", unit="INR per night", scope="domestic travel",
                    source_chunk_id=chunk.chunk_id, confidence=1.0, created_at=now_utc()
                ))
            for m in re.finditer(r"(?:rs\.?|inr|₹)?\s*([\d,]+)(?:/day)?\s*for\s*metro\s*cities", text, re.I):
                facts.append(PolicyFact(
                    policy_id=chunk.policy_id, version_id=chunk.version_id,
                    subject="Daily Allowance (Metro)", predicate="daily_allowance_metro",
                    value=f"Rs. {m.group(1)}", unit="INR per day", scope="metro cities",
                    source_chunk_id=chunk.chunk_id, confidence=1.0, created_at=now_utc()
                ))
            for m in re.finditer(r"(?:rs\.?|inr|₹)?\s*([\d,]+)(?:/day)?\s*for\s*non-metro\s*cities", text, re.I):
                facts.append(PolicyFact(
                    policy_id=chunk.policy_id, version_id=chunk.version_id,
                    subject="Daily Allowance (Non-Metro)", predicate="daily_allowance_non_metro",
                    value=f"Rs. {m.group(1)}", unit="INR per day", scope="non-metro cities",
                    source_chunk_id=chunk.chunk_id, confidence=1.0, created_at=now_utc()
                ))

            # 7. Medical & OPD Insurance
            for m in re.finditer(r"(?:rs\.?|inr|₹)?\s*([\d,]+)\s*(?:base\s*)?(?:medical|health|hospitalization)\s*cover", text, re.I):
                facts.append(PolicyFact(
                    policy_id=chunk.policy_id, version_id=chunk.version_id,
                    subject="Medical Insurance Cover", predicate="medical_insurance_limit",
                    value=f"Rs. {m.group(1)}", unit="INR", scope="family floater coverage",
                    source_chunk_id=chunk.chunk_id, confidence=1.0, created_at=now_utc()
                ))
            for m in re.finditer(r"opd\s*(?:limit|allowance|benefit)?\s*(?:of|is)?\s*(?:rs\.?|inr|₹)?\s*([\d,]+)", text, re.I):
                facts.append(PolicyFact(
                    policy_id=chunk.policy_id, version_id=chunk.version_id,
                    subject="OPD Insurance Limit", predicate="opd_limit",
                    value=f"Rs. {m.group(1)}", unit="INR per year", scope="outpatient medical expenses",
                    source_chunk_id=chunk.chunk_id, confidence=1.0, created_at=now_utc()
                ))

            # 8. Notice Period & PIP Duration
            for m in re.finditer(r"notice\s+period\s+(?:of\s+|is\s+)?(\d+)\s*(day|week|month)s?", text, re.I):
                facts.append(PolicyFact(
                    policy_id=chunk.policy_id, version_id=chunk.version_id,
                    subject="Notice Period", predicate="notice_period",
                    value=m.group(1), unit=m.group(2) + "s", scope="resignation & termination",
                    source_chunk_id=chunk.chunk_id, confidence=1.0, created_at=now_utc()
                ))
            for m in re.finditer(r"(\d+)\s*(?:day|week|month)s?\s*(?:performance\s*improvement\s*plan|pip)", text, re.I):
                facts.append(PolicyFact(
                    policy_id=chunk.policy_id, version_id=chunk.version_id,
                    subject="PIP Timeline", predicate="pip_duration",
                    value=m.group(1), unit="days", scope="performance improvement plan",
                    source_chunk_id=chunk.chunk_id, confidence=1.0, created_at=now_utc()
                ))

            # 9. Learning Budget & Hardware Refresh
            for m in re.finditer(r"(?:learning|training|education)\s*(?:budget|allowance)?\s*(?:of|is)?\s*(?:rs\.?|inr|₹)?\s*([\d,]+)", text, re.I):
                facts.append(PolicyFact(
                    policy_id=chunk.policy_id, version_id=chunk.version_id,
                    subject="Annual Learning Budget", predicate="learning_budget",
                    value=f"Rs. {m.group(1)}", unit="INR per year", scope="professional development",
                    source_chunk_id=chunk.chunk_id, confidence=1.0, created_at=now_utc()
                ))
            for m in re.finditer(r"laptop\s*refresh\s*(?:cycle\s*)?(?:every|after)?\s*(\d+)\s*(year|month)s?", text, re.I):
                facts.append(PolicyFact(
                    policy_id=chunk.policy_id, version_id=chunk.version_id,
                    subject="Hardware Refresh Cycle", predicate="hardware_refresh",
                    value=m.group(1), unit=m.group(2) + "s", scope="company laptop replacement",
                    source_chunk_id=chunk.chunk_id, confidence=1.0, created_at=now_utc()
                ))

            # 10. Referral Bonus & Relocation Package
            for m in re.finditer(r"(?:rs\.?|inr|₹)?\s*([\d,]+)\s*for\s*(?:senior|lead)\s*roles?", text, re.I):
                facts.append(PolicyFact(
                    policy_id=chunk.policy_id, version_id=chunk.version_id,
                    subject="Senior Referral Bonus", predicate="referral_bonus_senior",
                    value=f"Rs. {m.group(1)}", unit="INR", scope="talent acquisition referral",
                    source_chunk_id=chunk.chunk_id, confidence=1.0, created_at=now_utc()
                ))
            for m in re.finditer(r"(?:rs\.?|inr|₹)?\s*([\d,]+)\s*for\s*(?:junior|standard)\s*roles?", text, re.I):
                facts.append(PolicyFact(
                    policy_id=chunk.policy_id, version_id=chunk.version_id,
                    subject="Junior Referral Bonus", predicate="referral_bonus_junior",
                    value=f"Rs. {m.group(1)}", unit="INR", scope="talent acquisition referral",
                    source_chunk_id=chunk.chunk_id, confidence=1.0, created_at=now_utc()
                ))
            for m in re.finditer(r"relocation\s*(?:package|allowance)?\s*(?:up\s*to|of)?\s*(?:rs\.?|inr|₹)?\s*([\d,]+)", text, re.I):
                facts.append(PolicyFact(
                    policy_id=chunk.policy_id, version_id=chunk.version_id,
                    subject="Relocation Package", predicate="relocation_allowance",
                    value=f"Rs. {m.group(1)}", unit="INR", scope="domestic relocation assistance",
                    source_chunk_id=chunk.chunk_id, confidence=1.0, created_at=now_utc()
                ))

            # 11. Gift Limit & Incident Reporting
            for m in re.finditer(r"(?:gift|hospitality)\s*(?:value|worth|limit)?\s*(?:of|is)?\s*(?:rs\.?|inr|₹)?\s*([\d,]+)", text, re.I):
                facts.append(PolicyFact(
                    policy_id=chunk.policy_id, version_id=chunk.version_id,
                    subject="Gift Limit", predicate="gift_limit",
                    value=f"Rs. {m.group(1)}", unit="INR", scope="anti-bribery and compliance",
                    source_chunk_id=chunk.chunk_id, confidence=1.0, created_at=now_utc()
                ))
            for m in re.finditer(r"within\s*(\d+)\s*(hour|minute|day)s?\s*of\s*discovery", text, re.I):
                facts.append(PolicyFact(
                    policy_id=chunk.policy_id, version_id=chunk.version_id,
                    subject="Security Incident Reporting", predicate="incident_reporting_deadline",
                    value=m.group(1), unit=m.group(2) + "s", scope="incident discovery",
                    source_chunk_id=chunk.chunk_id, confidence=1.0, created_at=now_utc()
                ))
            for m in re.finditer(r"change\s*every\s*(\d+)\s*days", text, re.I):
                facts.append(PolicyFact(
                    policy_id=chunk.policy_id, version_id=chunk.version_id,
                    subject="Password Expiration", predicate="password_rotation_period",
                    value=m.group(1), unit="days", scope="password security policy",
                    source_chunk_id=chunk.chunk_id, confidence=1.0, created_at=now_utc()
                ))

        return facts
