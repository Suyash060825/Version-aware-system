#!/usr/bin/env python3
"""
LaTeX Manuscript Syntax & Consistency Auditor
Checks for markdown syntax, quotes, math environments, and braces.
"""
import re
import sys

def audit_latex_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        content = "".join(lines)

    issues = []

    # 1. Search for markdown syntax
    if "**" in content:
        for idx, line in enumerate(lines, 1):
            if "**" in line:
                issues.append(f"Line {idx}: Contains markdown '**': {line.strip()}")

    # 2. Search for markdown headings
    for idx, line in enumerate(lines, 1):
        if re.match(r'^\s*#{1,6}\s+', line):
            issues.append(f"Line {idx}: Contains markdown heading: {line.strip()}")

    # 3. Search for malformed quotes
    if r"\`\`" in content or r"\'\'" in content:
        for idx, line in enumerate(lines, 1):
            if r"\`\`" in line or r"\'\'" in line:
                issues.append(f"Line {idx}: Malformed escaped backticks: {line.strip()}")

    # Search for straight double quotes
    for idx, line in enumerate(lines, 1):
        # ignore comments
        clean_line = line.split('%')[0] if '%' in line else line
        if '"' in clean_line:
            issues.append(f"Line {idx}: Straight double quote found: {line.strip()}")

    # 4. Search for un-math theta or subscript
    for idx, line in enumerate(lines, 1):
        clean_line = line.split('%')[0] if '%' in line else line
        # Match theta_ outside $
        if "theta_" in clean_line and "$" not in clean_line and "\\[" not in clean_line:
            issues.append(f"Line {idx}: 'theta_' found outside math: {line.strip()}")

    # 5. Check brace matching
    open_braces = content.count('{') - content.count(r'\{')
    close_braces = content.count('}') - content.count(r'\}')
    if open_braces != close_braces:
        issues.append(f"Brace mismatch: {open_braces} open braces vs {close_braces} close braces")

    # 6. Check for malformed commands
    for idx, line in enumerate(lines, 1):
        if r"\textbf{**" in line or r"**}" in line:
            issues.append(f"Line {idx}: Malformed \\textbf with markdown: {line.strip()}")
        if r"\emph{*" in line or r"*}" in line:
            issues.append(f"Line {idx}: Malformed \\emph with markdown: {line.strip()}")
        if r"\\," in line:
            issues.append(f"Line {idx}: Found '\\\\,' instead of '\\,': {line.strip()}")
        if r"\\%" in line:
            issues.append(f"Line {idx}: Found '\\\\%' instead of '\\%': {line.strip()}")

    print(f"Audit completed for {filepath}: {len(issues)} issues found.")
    for issue in issues:
        print("  - " + issue)
    return len(issues) == 0

if __name__ == "__main__":
    filepath = sys.argv[1] if len(sys.argv) > 1 else "Version_Aware_Ieee.tex"
    audit_latex_file(filepath)
