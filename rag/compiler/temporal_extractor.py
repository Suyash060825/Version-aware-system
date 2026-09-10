"""
rag/compiler/temporal_extractor.py
Extracts temporal validity boundaries, dates, and version references from policy chunks.
"""
import re
from datetime import datetime, date
from typing import List, Dict, Any, Optional
from rag.compiler.document_ir import ChunkIR

class TemporalExtractor:
    VERSION_REF_PATTERNS = [
        r"\b(?:supersedes|replaces|updates)\s+(?:version|v\.?)\s*([0-9\.]+)\b",
        r"\b(?:previous\s+version|prior\s+policy)\s*[:\-]?\s*(?:v\.?)?([0-9\.]+)\b",
    ]

    DATE_PATTERNS = [
        r"\b(?:effective\s+(?:from|date)|as\s+of|commencing\s+on)\s*[:\-]?\s*([0-9]{1,2}[/-][0-9]{1,2}[/-][0-9]{2,4}|[A-Za-z]+\s+[0-9]{1,2},?\s+[0-9]{4}|[0-9]{4}-[0-9]{2}-[0-9]{2})\b",
        r"\b(?:valid\s+until|expires\s+on|effective\s+to)\s*[:\-]?\s*([0-9]{1,2}[/-][0-9]{1,2}[/-][0-9]{2,4}|[A-Za-z]+\s+[0-9]{1,2},?\s+[0-9]{4}|[0-9]{4}-[0-9]{2}-[0-9]{2})\b",
    ]

    def extract(self, chunks: List[ChunkIR]) -> Dict[str, Any]:
        results = {
            "supersedes_version": None,
            "effective_from": None,
            "effective_to": None,
            "temporal_clauses": []
        }

        for chunk in chunks:
            text = chunk.text

            # Check supersedes
            for pattern in self.VERSION_REF_PATTERNS:
                match = re.search(pattern, text, re.I)
                if match:
                    results["supersedes_version"] = match.group(1)
                    break

            # Check dates
            for pattern in self.DATE_PATTERNS:
                match = re.search(pattern, text, re.I)
                if match:
                    results["temporal_clauses"].append({
                        "chunk_id": chunk.chunk_id,
                        "date_str": match.group(1),
                        "clause": text[:200]
                    })

        return results
