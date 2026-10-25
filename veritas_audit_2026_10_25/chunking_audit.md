# Veritas Chunking Audit

**Audit Date:** 2026-10-25 | **Branch:** `improv` / `0ebae05`

---

## 1. Document Parsing & Structure Extraction

### 1.1 Parsing Implementation
**File:** [`rag/chunking/chunker.py`](file:///home/suyashpradhan/Desktop/Version%20aware%20_%20Vision-chatgpt/rag/chunking/chunker.py) and [`rag/compiler/structure_extractor.py`](file:///home/suyashpradhan/Desktop/Version%20aware%20_%20Vision-chatgpt/rag/compiler/structure_extractor.py)

- **Input Formats:** Text strings extracted from `PolicyVersion.content` or PDFs via `pdf_parser.py`.
- **Heading Detection Patterns:**
  1. Markdown-style `#`, `##`, `###`
  2. Numbered sections (`1. Title`, `Section 2: ...`)
  3. Decimal sub-clauses (`1.1 Title`, `4.2.1 ...`)
  4. ALL CAPS short headers (≤60 chars)
  5. Explicit `[Page N]` page boundary markers

### 1.2 Parsing Vulnerabilities & Structural Loss
- **No Table-Structure Extraction:** Tables formatted as ASCII or tab-separated text are processed as continuous unstructured character streams. Rows and columns get severed during window splitting.
- **Aggressive Header Deduplication (L152):** Headings starting within 10 characters of each other are deduplicated. In dense policy tables of contents or definitions sections, valid consecutive headings are dropped.
- **Section-Isolated Page Tracking (L70–73):** Page number is tracked based on `[Page N]` markers occurring inside the currently active section. If a section spans pages 3 through 6 without repeating the marker in every sub-chunk, subsequent chunks inherit page 6 or retain stale numbers.

---

## 2. Chunk Boundaries & Sizing

### 2.1 Boundary Rules
- **Units:** Character count (`len(text)`), **not tokens**.
  - `MAX_CHUNK_SIZE = 1200` chars (~250–350 tokens)
  - `MIN_CHUNK_SIZE = 15` chars
  - `OVERLAP = 150` chars
- **Snapping Logic (L189–192):**
  - Tries `rfind(".")` and `rfind("\n")` within the overlap margin.
  - Snaps to periods regardless of context, severing decimal numbers (e.g., `4.2%` split across chunks), version strings (`v1.0`), and abbreviations (`e.g.`, `i.e.`).
- **Separation of Conditions and Exceptions:**
  - In `CAT_11_EXCEPTIONS` (where accuracy is 0.0%), policy rules state general provisions in the opening sentence and list critical disqualifiers/exceptions 1,000+ characters down or in subordinate bullet blocks. The fixed 1,200 character window separates the rule condition from its exception clause.

---

## 3. Chunk Metadata & Provenance

Each chunk persists the following fields:
```python
{
  "chunk_id": "CHK-{policy_id}-V{version_id}-{index}",
  "policy_id": int,
  "policy_name": str,
  "version_id": int,
  "version": str,
  "section": str,
  "section_path": str,
  "page": int,
  "valid_from_ts": int,
  "valid_to_ts": int,
  "is_current": bool
}
```

### 3.1 Metadata Failures & Vulnerabilities
1. **Timestamp Sentinels:** Undated policies receive `valid_from_ts = 0` (1970) and `valid_to_ts = 32472144000` (year 3000). Any temporal query checking `$lte target_ts` will automatically match undated policies as valid for historical dates.
2. **Missing Hierarchical Lineage:** Chunks lack breadcrumb paths (e.g., `Article IV > Section 2 > Subsection B`). Sub-clauses only store their immediate header or fall back to `"General"`.
3. **No Cross-Reference Anchoring:** References such as "Subject to the provisions in Section 8.1" do not resolve or link the target chunk ID.

---

## 4. Controlled Chunking Strategy Comparison (Ablation Design)

| Strategy | Mechanism | Expected Benefit | Risk / Tradeoff |
|---|---|---|---|
| **A. Baseline (Current)** | Regex headers + 1200-char sliding window | Fast, low index footprint | Splits exceptions and tables; 0% CAT_11 |
| **B. Clause-Aware Boundary Snapping** | Token-based (300 tokens); protected regex for decimals, dates, and bullet lists | Eliminates broken numbers and abbreviations | Slightly variable chunk sizes |
| **C. Hierarchical Parent Context Injection** | Small clause chunks (150 tokens) with parent section header + preamble prepended | Preserves exception-condition relationships | 20–30% increase in indexed token volume |
| **D. Table & List Structure Preservation** | Markdown table and list block detection prior to text chunking | Recovers table cell integrity | Requires structured document pre-parser |
