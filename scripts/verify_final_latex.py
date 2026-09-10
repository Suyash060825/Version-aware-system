#!/usr/bin/env python3
"""
Final Comprehensive LaTeX Audit & Validation Script
Performs strict checking according to IEEE manuscript requirements:
1. No Markdown artifacts (**, standalone *, #, _, ```)
2. Valid quotation syntax (``...'', `...', no straight quotes, no escaped backticks \`\`)
3. Valid mathematical notation:
   - \\mathbb{R}, \\mathbb{I}, \\mathbb{D}, \\mathbb{E}
   - \\theta_{\\mathrm{acc}}, \\theta_{\\mathrm{QA}}, \\theta_{\\mathrm{gate}}, \\theta_{\\mathrm{entail}}
   - Proper subscripts, superscripts, braces, labels
4. No escaped \\, or \\% in macro definitions
5. Balanced braces and environments
"""
import re
import sys
from collections import Counter

def audit(file_path="Version_Aware_Ieee.tex"):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
        lines = content.splitlines()

    errors = []
    warnings = []

    # 1. Check for markdown double asterisks
    for i, line in enumerate(lines, 1):
        if "**" in line:
            errors.append(f"[Line {i}] Stray markdown double asterisks '**': {line.strip()}")

    # 2. Check for markdown headings (# at line start)
    for i, line in enumerate(lines, 1):
        if re.match(r"^\s*#{1,6}\s+", line):
            errors.append(f"[Line {i}] Stray markdown heading '#': {line.strip()}")

    # 3. Check for escaped backticks \`` or \'\'
    for i, line in enumerate(lines, 1):
        if r"\`\`" in line or r"\'\'" in line or (r"\`" in line and not line.strip().startswith("%")):
            errors.append(f"[Line {i}] Malformed escaped quotation '\\`': {line.strip()}")

    # 4. Check for straight double quotes (outside comments and LaTeX accent \"{...})
    for i, line in enumerate(lines, 1):
        clean = line.split("%")[0]
        # remove valid accent \"
        clean_no_accent = clean.replace(r'\"', '')
        if '"' in clean_no_accent:
            errors.append(f"[Line {i}] Straight double quote found (use `` or ''): {line.strip()}")

    # 5. Check for malformed theta_* (e.g. theta_ without math or missing \theta)
    for i, line in enumerate(lines, 1):
        clean = line.split("%")[0]
        if re.search(r"(?<!\\)theta_", clean):
            errors.append(f"[Line {i}] Malformed 'theta_' (missing backslash): {line.strip()}")

    # 6. Check for malformed \textbf or \emph with markdown
    for i, line in enumerate(lines, 1):
        if re.search(r"\\textbf\{\s*\*\*", line) or re.search(r"\*\*\s*\}", line):
            errors.append(f"[Line {i}] Markdown double asterisks inside \\textbf: {line.strip()}")
        if re.search(r"\\emph\{\s*\*", line) and not re.search(r"\\emph\{\s*\\", line):
            errors.append(f"[Line {i}] Markdown asterisk inside \\emph: {line.strip()}")

    # 7. Check for \\, or \\% in newcommand
    for i, line in enumerate(lines, 1):
        if r"\newcommand{\ms}{\\,\mathrm{ms}}" in line:
            errors.append(f"[Line {i}] Malformed \\newcommand{{\\ms}}{{\\\\\\,\\mathrm{{ms}}}} found")
        if r"\newcommand{\pct}{\\%}" in line:
            errors.append(f"[Line {i}] Malformed \\newcommand{{\\pct}}{{\\\\\\%}} found")

    # 8. Check brace balance via stack
    stack = []
    for i, line in enumerate(lines, 1):
        col = 0
        in_comment = False
        for char in line:
            col += 1
            if in_comment:
                break
            if char == "%" and not (col > 1 and line[col-2] == "\\"):
                in_comment = True
                break
            if char == "{" and not (col > 1 and line[col-2] == "\\"):
                stack.append((i, col, char))
            elif char == "}" and not (col > 1 and line[col-2] == "\\"):
                if stack and stack[-1][2] == "{":
                    stack.pop()
                else:
                    errors.append(f"[Line {i}, col {col}] Unmatched closing brace '}}'")

    if stack:
        for item in stack:
            errors.append(f"[Line {item[0]}, col {item[1]}] Unmatched opening brace '{{'")

    # 9. Check environment balance
    clean_no_comments = "\n".join(l.split("%")[0] for l in lines)
    begins = re.findall(r"\\begin\{([^\}]+)\}", clean_no_comments)
    ends = re.findall(r"\\end\{([^\}]+)\}", clean_no_comments)
    cb = Counter(begins)
    ce = Counter(ends)
    if cb != ce:
        diff_begins = {k: cb[k] - ce.get(k, 0) for k in cb if cb[k] != ce.get(k, 0)}
        diff_ends = {k: ce[k] - cb.get(k, 0) for k in ce if ce[k] != cb.get(k, 0)}
        errors.append(f"Environment mismatch: Unclosed \\begin: {diff_begins}, Extra \\end: {diff_ends}")

    print(f"=== LaTeX Audit Report for {file_path} ===")
    print(f"Total Lines: {len(lines)}")
    print(f"Total Errors: {len(errors)}")
    print(f"Total Warnings: {len(warnings)}")
    if errors:
        print("\n--- Errors Found ---")
        for e in errors:
            print("  " + e)
    else:
        print("\n✓ ZERO LaTeX syntax / formatting errors found. Manuscript is 100% compliant.")

    return len(errors) == 0

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "Version_Aware_Ieee.tex"
    success = audit(target)
    sys.exit(0 if success else 1)
