import re
from datetime import datetime, date
from typing import Optional
from dataclasses import dataclass
from models import PolicyVersion, Policy

@dataclass
class TemporalContext:
    target_date: Optional[date]
    version_id: Optional[int]
    policy_id: Optional[int]
    is_historic: bool = False

class VersionResolver:
    """
    Resolves temporal queries to specific policy versions.
    "What was the travel limit in June 2024?" -> TemporalContext
    """
    
    # Simple regex for year extraction as a baseline
    YEAR_PATTERN = re.compile(r'\b(19|20)\d{2}\b')
    
    def resolve_temporal_context(self, query: str, user=None) -> TemporalContext:
        target_date = self._extract_date(query)
        if target_date:
            return TemporalContext(target_date=target_date, version_id=None, policy_id=None, is_historic=True)
        return TemporalContext(target_date=None, version_id=None, policy_id=None, is_historic=False)

    def _extract_date(self, query: str) -> Optional[date]:
        # Naive implementation: look for a year
        match = self.YEAR_PATTERN.search(query)
        if match:
            try:
                year = int(match.group())
                # Default to end of year for "in 2024"
                return date(year, 12, 31)
            except ValueError:
                pass
        return None

    def get_active_version(self, policy_id: int, target_date: Optional[date] = None) -> Optional[PolicyVersion]:
        """Find the active version for a policy on a given date, or the currently active one."""
        if target_date:
            # PolicyVersion where effective_date <= target_date, ordered by effective_date DESC
            # Since SQLite/SQLAlchemy might not have effective_date strictly populated in old versions,
            # we fall back to created_at
            versions = PolicyVersion.query.filter_by(policy_id=policy_id).order_by(PolicyVersion.created_at.desc()).all()
            for v in versions:
                # If we had effective_date properly, we'd check it. We use created_at as proxy for now.
                if v.created_at and v.created_at.date() <= target_date:
                    return v
            # Fallback to oldest if target date is before all versions
            if versions:
                return versions[-1]
            return None
        else:
            return PolicyVersion.query.filter_by(policy_id=policy_id, is_active=True).first()
