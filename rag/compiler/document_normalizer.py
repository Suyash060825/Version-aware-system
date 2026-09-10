import hashlib
from rag.compiler.document_ir import DocumentIR, SectionNode
from models import Policy, PolicyVersion

class DocumentNormalizer:
    def normalize(self, raw_text: str, policy: Policy, version: PolicyVersion) -> DocumentIR:
        import re
        lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
        cleaned = "\n".join(lines)
        
        # 2. Compute source hash
        source_hash = hashlib.sha256(cleaned.encode()).hexdigest()
        
        # 3. Section parsing: split on numbered headings (e.g. "1. Eligibility", "2. Leave Rules")
        sections = []
        raw_sections = re.split(r'\n(?=[0-9]+\.\s+[A-Z])', cleaned)
        
        if len(raw_sections) > 1:
            for s_idx, sec_text in enumerate(raw_sections):
                sec_lines = sec_text.strip().split('\n')
                first_line = sec_lines[0].strip()
                title_match = re.match(r'^[0-9]+\.\s+(.+)$', first_line)
                sec_title = f"{policy.title} - {first_line}" if title_match else f"{policy.title} Section {s_idx+1}"
                
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
