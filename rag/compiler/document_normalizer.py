import hashlib
import re
from rag.compiler.document_ir import DocumentIR, SectionNode
from models import Policy, PolicyVersion

class DocumentNormalizer:
    def normalize(self, raw_text: str, policy: Policy, version: PolicyVersion) -> DocumentIR:
        # 1. Normalize line breaks while preserving paragraph boundaries
        cleaned = re.sub(r'\r\n', '\n', raw_text)
        cleaned = re.sub(r'[ \t]+', ' ', cleaned)
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned).strip()
        
        # 2. Compute source hash
        source_hash = hashlib.sha256(cleaned.encode()).hexdigest()
        
        # 3. Section parsing: split on numbered, markdown (#), or all-caps headings
        heading_split_pattern = r'\n(?=(?:[0-9]+(?:\.[0-9]+)*\.\s+[A-Z]|#{1,4}\s+[A-Za-z0-9]|[A-Z][A-Z0-9\s]{4,60}\n))'
        raw_sections = re.split(heading_split_pattern, cleaned)
        
        sections = []
        if len(raw_sections) > 1:
            for s_idx, sec_text in enumerate(raw_sections):
                sec_text = sec_text.strip()
                if not sec_text:
                    continue
                sec_lines = sec_text.split('\n')
                first_line = sec_lines[0].strip()
                first_line_clean = re.sub(r"^#{1,4}\s+", "", first_line)
                
                title_match = re.match(r'^[0-9]+(?:\.[0-9]+)*\.\s+(.+)$', first_line_clean)
                if title_match:
                    sec_title = f"{policy.title} - {first_line_clean}"
                elif first_line_clean and len(first_line_clean) < 80 and not first_line_clean.endswith("."):
                    sec_title = f"{policy.title} - {first_line_clean}"
                else:
                    sec_title = f"{policy.title} Section {s_idx+1}"
                
                sections.append(
                    SectionNode(
                        section_id=f"s{s_idx+1}",
                        title=sec_title,
                        level=2 if s_idx > 0 else 1,
                        content=sec_text,
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
