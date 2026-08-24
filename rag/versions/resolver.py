"""
rag/versions/resolver.py
Authoritative temporal query parser and interval validity resolver.
Supports date intervals (e.g., 'during June 2024', 'before July 2025', 'after January 2024',
'as of June 2024', 'previous', 'old', 'latest', 'between v1 and v2').
"""
import re
import calendar
from datetime import datetime, date
from typing import Optional, Tuple, List
from dataclasses import dataclass
from models import PolicyVersion, Policy

@dataclass
class TemporalQuery:
    target_date: Optional[date] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    requested_version: Optional[str] = None
    comparison_versions: Optional[Tuple[str, str]] = None
    historical: bool = False
    current: bool = True
    raw_expression: Optional[str] = None

@dataclass
class TemporalContext:
    target_date: Optional[date]
    version_id: Optional[int]
    policy_id: Optional[int]
    is_historic: bool = False
    requested_version: Optional[str] = None
    temporal_query: Optional[TemporalQuery] = None

class VersionResolver:
    """
    Resolves temporal queries to specific policy versions using authoritative validity intervals.
    """
    MONTH_NAMES = {
        "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3,
        "april": 4, "apr": 4, "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7,
        "august": 8, "aug": 8, "september": 9, "sep": 9, "sept": 9, "october": 10, "oct": 10,
        "november": 11, "nov": 11, "december": 12, "dec": 12
    }

    YEAR_RE = re.compile(r'\b(19\d{2}|20\d{2})\b')
    MONTH_YEAR_RE = re.compile(r'\b(?:in|during|as of|for)?\s*(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)\s+(\d{4})\b', re.IGNORECASE)
    BEFORE_DATE_RE = re.compile(r'\bbefore\s+(?:the\s+)?(?:(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)\s+)?(\d{4})\b', re.IGNORECASE)
    AFTER_DATE_RE = re.compile(r'\bafter\s+(?:the\s+)?(?:(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)\s+)?(\d{4})\b', re.IGNORECASE)
    AS_OF_RE = re.compile(r'\bas of\s+(?:(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)\s+)?(\d{4})\b', re.IGNORECASE)
    VERSION_NUM_RE = re.compile(r'\b(?:version|v)\s*(\d+(?:\.\d+)?)\b', re.IGNORECASE)
    BETWEEN_VERSIONS_RE = re.compile(r'\b(?:between|compare)\s+v?(\d+(?:\.\d+)?)\s+(?:and|vs|to)\s+v?(\d+(?:\.\d+)?)\b', re.IGNORECASE)

    def parse_temporal_query(self, query: str) -> TemporalQuery:
        q_lower = query.lower().strip()
        tq = TemporalQuery(raw_expression=query)

        # 1. Version Comparison ('between v1 and v2', 'v1 vs v2')
        cmp_match = self.BETWEEN_VERSIONS_RE.search(q_lower)
        if cmp_match:
            v1, v2 = cmp_match.group(1), cmp_match.group(2)
            tq.comparison_versions = (v1, v2)
            tq.historical = True
            tq.current = False
            return tq

        # 2. Specific requested version ('v1.0', 'version 2')
        ver_match = self.VERSION_NUM_RE.search(q_lower)
        if ver_match and not ("between" in q_lower or "vs" in q_lower):
            tq.requested_version = ver_match.group(1)

        # 3. Before Date / After Date / As Of Date
        before_match = self.BEFORE_DATE_RE.search(q_lower)
        if before_match:
            month_str, year_str = before_match.group(1), before_match.group(2)
            year = int(year_str)
            month = self.MONTH_NAMES.get(month_str.lower(), 1) if month_str else 1
            tq.target_date = date(year, month, 1)
            tq.end_date = date(year, month, 1)
            tq.historical = True
            tq.current = False
            return tq

        after_match = self.AFTER_DATE_RE.search(q_lower)
        if after_match:
            month_str, year_str = after_match.group(1), after_match.group(2)
            year = int(year_str)
            month = self.MONTH_NAMES.get(month_str.lower(), 12) if month_str else 1
            last_day = calendar.monthrange(year, month)[1]
            tq.target_date = date(year, month, last_day)
            tq.start_date = date(year, month, 1)
            tq.historical = year < date.today().year
            tq.current = not tq.historical
            return tq

        as_of_match = self.AS_OF_RE.search(q_lower) or self.MONTH_YEAR_RE.search(q_lower)
        if as_of_match:
            month_str, year_str = as_of_match.group(1), as_of_match.group(2)
            year = int(year_str)
            month = self.MONTH_NAMES.get(month_str.lower(), 6) if month_str else 6
            last_day = calendar.monthrange(year, month)[1]
            tq.target_date = date(year, month, last_day)
            tq.start_date = date(year, month, 1)
            tq.end_date = date(year, month, last_day)
            tq.historical = (tq.target_date < date.today())
            tq.current = not tq.historical
            return tq

        # 4. Bare Year match ('in 2024', '2023 policy')
        year_match = self.YEAR_RE.search(q_lower)
        if year_match:
            year = int(year_match.group(1))
            tq.target_date = date(year, 12, 31)
            tq.start_date = date(year, 1, 1)
            tq.end_date = date(year, 12, 31)
            tq.historical = (year < date.today().year)
            tq.current = not tq.historical
            return tq

        # 5. Keywords for historical vs current
        if any(w in q_lower for w in ["previous", "old", "used to", "earlier", "prior", "historical", "was", "deprecated"]):
            tq.historical = True
            tq.current = False
        elif any(w in q_lower for w in ["current", "latest", "now", "active", "present", "effective"]):
            tq.historical = False
            tq.current = True

        return tq

    def resolve_temporal_context(self, query: str, user=None) -> TemporalContext:
        tq = self.parse_temporal_query(query)
        is_historic = tq.historical or (tq.target_date is not None and tq.target_date < date.today())

        return TemporalContext(
            target_date=tq.target_date,
            version_id=None,
            policy_id=None,
            is_historic=is_historic,
            requested_version=tq.requested_version,
            temporal_query=tq
        )

    def get_active_version(self, policy_id: int, target_date: Optional[date] = None, requested_version: Optional[str] = None) -> Optional[PolicyVersion]:
        """
        Find the active version for a policy on a given date using effective interval enforcement.
        effective_from <= target_date AND (effective_to IS NULL OR target_date <= effective_to)
        """
        if requested_version:
            # Match explicit requested version
            try:
                v_num = float(requested_version)
                ver = PolicyVersion.query.filter(
                    PolicyVersion.policy_id == policy_id,
                    (PolicyVersion.version_num == v_num) | (PolicyVersion.version_label.ilike(f"%{requested_version}%"))
                ).first()
                if ver:
                    return ver
            except ValueError:
                ver = PolicyVersion.query.filter(
                    PolicyVersion.policy_id == policy_id,
                    PolicyVersion.version_label.ilike(f"%{requested_version}%")
                ).first()
                if ver:
                    return ver

        if target_date:
            versions = PolicyVersion.query.filter_by(policy_id=policy_id).order_by(PolicyVersion.version_num.desc()).all()
            for v in versions:
                if v.is_valid_for_date(target_date):
                    return v
            if versions:
                # If target date is before all versions, return the earliest version
                if target_date < versions[-1].effective_from:
                    return versions[-1]
                # If target date is after all versions, return the latest active version
                return versions[0]
            return None
        else:
            active = PolicyVersion.query.filter_by(policy_id=policy_id, is_active=True).first()
            if not active:
                active = PolicyVersion.query.filter_by(policy_id=policy_id).order_by(PolicyVersion.version_num.desc()).first()
            return active
