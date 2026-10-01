import re
import hashlib
from rag.compiler.document_ir import DocumentIR, SectionNode
from models import Policy, PolicyVersion

class DocumentNormalizer:
    def normalize(self, raw_text: str, policy: Policy, version: PolicyVersion) -> DocumentIR:
        # 1. Normalize line endings and whitespace, preserving paragraph breaks (\n\n)
        raw_lines = [line.strip() for line in raw_text.replace('\r\n', '\n').replace('\r', '\n').split('\n')]
        cleaned = re.sub(r'\n{3,}', '\n\n', '\n'.join(raw_lines)).strip()
        
        # 2. Compute source hash
        source_hash = hashlib.sha256(cleaned.encode()).hexdigest()
        
        # 3. Section parsing: split on standard corporate heading styles
        # Supports: "Section 1: ...", "Article 2 - ...", "1. Eligibility", "1.1 Scope", "## Heading", "HEADING:"
        heading_pattern = (
            r'\n(?=(?:'
            r'(?:Section|Article|Part|Clause)\s+\w+[\.\:\-\s]'
            r'|\d+\.(?:\d+\.?)*\s+[A-Z]'
            r'|#{1,4}\s+[A-Za-z0-9]'
            r'|[A-Z][A-Za-z0-9\s]{3,40}:(?:\s*\n|\s+[A-Z])'
            r'))'
        )
        sections = []
        raw_sections = [s.strip() for s in re.split(heading_pattern, cleaned) if s.strip()]
        
        if len(raw_sections) > 1:
            for s_idx, sec_text in enumerate(raw_sections):
                sec_lines = sec_text.strip().split('\n')
                first_line = sec_lines[0].strip()
                title_match = re.match(
                    r'^(?:[0-9]+(?:\.[0-9]+)*|\b(?:Section|Article|Part|Clause)\s+\w+[\.\:\-]?|#{1,4})\s*(.*)$',
                    first_line, re.IGNORECASE
                )
                if title_match and title_match.group(1):
                    sec_title = f"{policy.title} - {first_line.lstrip('#').strip()}"
                elif s_idx == 0:
                    sec_title = f"{policy.title} - Overview"
                else:
                    sec_title = f"{policy.title} Section {s_idx+1}"
                
                sections.append(
                    SectionNode(
                        section_id=f"s{s_idx+1}",
                        title=sec_title,
                        level=2 if s_idx > 0 else 1,
                        content=sec_text.strip(),
                        page_start=1 + (s_idx // 3),
                        page_end=1 + (s_idx // 3),
                        children=[]
                    )
                )
        else:
            sections.append(
                SectionNode(
                    section_id="root",
                    title=policy.title,
                    level=1,
                    content=cleaned,
                    page_start=1,
                    page_end=1,
                    children=[]
                )
            )
        
        eff_from = version.effective_date.isoformat() if hasattr(version, 'effective_date') and version.effective_date else None
        eff_to = version.effective_to.isoformat() if hasattr(version, 'effective_to') and version.effective_to else None
        
        return DocumentIR(
            document_id=f"doc-{policy.id}-{version.id}",
            policy_id=policy.id,
            version_id=version.id,
            title=policy.title,
            department=policy.department.name if policy.department else "",
            effective_from=eff_from,
            effective_to=eff_to,
            sections=sections,
            source_hash=source_hash
        )
