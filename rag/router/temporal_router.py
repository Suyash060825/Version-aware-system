"""
rag/router/temporal_router.py
Routes temporal and version comparison queries by identifying target dates and version numbers.
"""
import re
from datetime import datetime, date
from typing import Optional, Tuple, List, Dict, Any
from models import Policy, PolicyVersion

class TemporalRouter:
    VERSION_DIFF_PATTERN = re.compile(r"\bv(\d+)\s*(?:and|vs|versus|to|\-)\s*v(\d+)\b", re.I)
    SINGLE_VERSION_PATTERN = re.compile(r"\bv(\d+)\b", re.I)
    YEAR_PATTERN = re.compile(r"\b(19|20)\d{2}\b")

    def route_temporal_query(self, query: str) -> Dict[str, Any]:
        result = {
            "is_comparison": False,
            "version_v1": None,
            "version_v2": None,
            "target_version": None,
            "target_year": None,
            "is_historic": False
        }

        # Check for version diff (e.g. "v1 vs v2", "between v3 and v4")
        diff_match = self.VERSION_DIFF_PATTERN.search(query)
        if diff_match:
            result["is_comparison"] = True
            result["version_v1"] = int(diff_match.group(1))
            result["version_v2"] = int(diff_match.group(2))
            return result

        # Check for single version reference (e.g. "in v2")
        v_match = self.SINGLE_VERSION_PATTERN.search(query)
        if v_match:
            result["target_version"] = int(v_match.group(1))
            result["is_historic"] = True

        # Check for year
        y_match = self.YEAR_PATTERN.search(query)
        if y_match:
            result["target_year"] = int(y_match.group(0))
            result["is_historic"] = True

        return result
