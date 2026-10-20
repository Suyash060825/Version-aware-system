"""
rag/router/temporal_router.py
Routes temporal and version comparison queries by identifying target dates and version numbers.
"""
import re
from typing import Dict, Any

class TemporalRouter:
    VERSION_DIFF_PATTERN = re.compile(
        r"\b(?:between|compare\s+)?(?:version\s+|v)?(\d+(?:\.\d+)?)\s*(?:and|vs|versus|to|\-)\s*(?:version\s+|v)?(\d+(?:\.\d+)?)\b",
        re.I
    )
    SINGLE_VERSION_PATTERN = re.compile(r"\b(?:version\s+|v)(\d+(?:\.\d+)?)\b", re.I)
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

        # Check for version diff (e.g. "v1 vs v2", "version 1.0 vs version 2.0", "between v3 and v4")
        diff_match = self.VERSION_DIFF_PATTERN.search(query)
        if diff_match:
            g1, g2 = diff_match.group(1), diff_match.group(2)
            # Ensure not 4-digit years (e.g. between 2022 and 2023)
            if not (len(g1) == 4 and g1.startswith(("19", "20"))) and not (len(g2) == 4 and g2.startswith(("19", "20"))):
                result["is_comparison"] = True
                result["version_v1"] = float(g1) if "." in g1 else int(g1)
                result["version_v2"] = float(g2) if "." in g2 else int(g2)
                return result

        # Check for single version reference (e.g. "in v2", "version 1.0")
        v_match = self.SINGLE_VERSION_PATTERN.search(query)
        if v_match:
            vg = v_match.group(1)
            result["target_version"] = float(vg) if "." in vg else int(vg)
            result["is_historic"] = True

        # Check for year
        y_match = self.YEAR_PATTERN.search(query)
        if y_match:
            result["target_year"] = int(y_match.group(0))
            result["is_historic"] = True

        return result
