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
    BETWEEN_VERSIONS_RE = re.compile(r'\b(?:between|compare)\s+(?:version\s+|v)?(\d+(?:\.\d+)?)\s+(?:and|vs|to)\s+(?:version\s+|v)?(\d+(?:\.\d+)?)\b', re.IGNORECASE)
    BETWEEN_DATES_RE = re.compile(r'\b(?:between|from)\s+(?:(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)\s+)?(\d{4})\s+(?:and|to|until|through)\s+(?:(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)\s+)?(\d{4})\b', re.IGNORECASE)
    UNTIL_DATE_RE = re.compile(r'\b(?:until|up to|through)\s+(?:the\s+)?(?:(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)\s+)?(\d{4})\b', re.IGNORECASE)
    SINCE_DATE_RE = re.compile(r'\b(?:since|starting from)\s+(?:the\s+)?(?:(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)\s+)?(\d{4})\b', re.IGNORECASE)

    def parse_temporal_query(self, query: str) -> TemporalQuery:
        q_lower = query.lower().strip()
        tq = TemporalQuery(raw_expression=query)

        # 1. Date Range ('between 2023 and 2024', 'from June 2023 to July 2024')
        range_match = self.BETWEEN_DATES_RE.search(q_lower)
        if range_match:
            m1_str, y1_str, m2_str, y2_str = range_match.group(1), range_match.group(2), range_match.group(3), range_match.group(4)
            y1, y2 = int(y1_str), int(y2_str)
            m1 = self.MONTH_NAMES.get(m1_str.lower(), 1) if m1_str else 1
            m2 = self.MONTH_NAMES.get(m2_str.lower(), 12) if m2_str else 12
            last_day_m2 = calendar.monthrange(y2, m2)[1]
            tq.start_date = date(y1, m1, 1)
            tq.end_date = date(y2, m2, last_day_m2)
            tq.target_date = tq.end_date
            tq.historical = (tq.end_date < date.today())
            tq.current = not tq.historical
            return tq

        # 2. Version Comparison ('between v1 and v2', 'v1 vs v2')
        cmp_match = self.BETWEEN_VERSIONS_RE.search(q_lower)
        if cmp_match:
            v1, v2 = cmp_match.group(1), cmp_match.group(2)
            # Ensure not 4-digit years
            if len(v1) < 4 and len(v2) < 4:
                tq.comparison_versions = (v1, v2)
                tq.historical = True
                tq.current = False
                return tq

        # 3. Specific requested version ('v1.0', 'version 2')
        ver_match = self.VERSION_NUM_RE.search(q_lower)
        if ver_match and not ("between" in q_lower or "vs" in q_lower):
            tq.requested_version = ver_match.group(1)

        # 4. Before Date / After Date / As Of Date / Until Date / Since Date
        before_match = self.BEFORE_DATE_RE.search(q_lower)
        if before_match:
            month_str, year_str = before_match.group(1), before_match.group(2)
            year = int(year_str)
            if month_str:
                month = self.MONTH_NAMES.get(month_str.lower(), 1)
                # Day before 1st of that month (exclusive end boundary)
                if month == 1:
                    tq.end_date = date(year - 1, 12, 31)
                else:
                    prev_month = month - 1
                    last_day_prev = calendar.monthrange(year, prev_month)[1]
                    tq.end_date = date(year, prev_month, last_day_prev)
            else:
                tq.end_date = date(year - 1, 12, 31)
            tq.target_date = tq.end_date
            tq.historical = True
            tq.current = False
            return tq

        after_match = self.AFTER_DATE_RE.search(q_lower)
        if after_match:
            month_str, year_str = after_match.group(1), after_match.group(2)
            year = int(year_str)
            if month_str:
                month = self.MONTH_NAMES.get(month_str.lower(), 1)
                # Day after last day of that month (exclusive start boundary)
                if month == 12:
                    tq.start_date = date(year + 1, 1, 1)
                else:
                    tq.start_date = date(year, month + 1, 1)
            else:
                tq.start_date = date(year + 1, 1, 1)
            tq.target_date = tq.start_date
            tq.historical = tq.start_date < date.today()
            tq.current = not tq.historical
            return tq

        until_match = self.UNTIL_DATE_RE.search(q_lower)
        if until_match:
            month_str, year_str = until_match.group(1), until_match.group(2)
            year = int(year_str)
            month = self.MONTH_NAMES.get(month_str.lower(), 12) if month_str else 12
            last_day = calendar.monthrange(year, month)[1]
            tq.end_date = date(year, month, last_day)
            tq.target_date = tq.end_date
            tq.historical = (tq.end_date < date.today())
            tq.current = not tq.historical
            return tq

        since_match = self.SINCE_DATE_RE.search(q_lower)
        if since_match:
            month_str, year_str = since_match.group(1), since_match.group(2)
            year = int(year_str)
            month = self.MONTH_NAMES.get(month_str.lower(), 1) if month_str else 1
            tq.start_date = date(year, month, 1)
            tq.target_date = tq.start_date
            tq.historical = (tq.start_date < date.today())
            tq.current = not tq.historical
            return tq

        as_of_match = self.AS_OF_RE.search(q_lower) or self.MONTH_YEAR_RE.search(q_lower)
        if as_of_match:
            month_str, year_str = as_of_match.group(1), as_of_match.group(2)
            year = int(year_str)
            month = self.MONTH_NAMES.get(month_str.lower(), 6) if month_str else 6
            last_day = calendar.monthrange(year, month)[1]
            tq.start_date = date(year, month, 1)
            tq.end_date = date(year, month, last_day)
            tq.target_date = date(year, month, 15)  # Midpoint representing full month
            tq.historical = (tq.end_date < date.today())
            tq.current = not tq.historical
            return tq

        # 5. Bare Year match ('in 2024', '2023 policy')
        year_match = self.YEAR_RE.search(q_lower)
        if year_match:
            year = int(year_match.group(1))
            tq.start_date = date(year, 1, 1)
            tq.end_date = date(year, 12, 31)
            tq.target_date = date(year, 6, 15)
            tq.historical = (year < date.today().year)
            tq.current = not tq.historical
            return tq

        # 6. Keywords for historical vs current
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

    def get_active_version(self, policy_id: int, target_date: Optional[date] = None, requested_version: Optional[str] = None, start_date: Optional[date] = None, end_date: Optional[date] = None) -> Optional[PolicyVersion]:
        """
        Find the active version for a policy on a given date/interval using effective interval enforcement.
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

        versions = PolicyVersion.query.filter_by(policy_id=policy_id).order_by(PolicyVersion.version_num.desc()).all()
        if not versions:
            return None

        if start_date or end_date:
            for v in versions:
                if v.is_valid_for_interval(start_date, end_date):
                    return v

        if target_date:
            for v in versions:
                if v.is_valid_for_date(target_date):
                    return v
            # If target date is before all versions, return the earliest version
            earliest_from = versions[-1].effective_from
            if earliest_from and target_date < earliest_from:
                return versions[-1]
            return versions[0]

        active = PolicyVersion.query.filter_by(policy_id=policy_id, is_active=True).first()
        if not active:
            active = versions[0]
        return active
