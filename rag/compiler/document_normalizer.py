import hashlib
from rag.compiler.document_ir import DocumentIR, SectionNode
from models import Policy, PolicyVersion

class DocumentNormalizer:
    def normalize(self, raw_text: str, policy: Policy, version: PolicyVersion) -> DocumentIR:
        # 1. Clean text (remove extra spaces, standardize newlines)
        cleaned = "\n".join([line.strip() for line in raw_text.split('\n') if line.strip()])
        
        # 2. Compute source hash
        source_hash = hashlib.sha256(cleaned.encode()).hexdigest()
        
        # 3. Very naive section parsing (for demo purposes)
        # We just create one root section
        root_section = SectionNode(
            section_id="root",
            title=policy.title,
            level=1,
            content=cleaned,
            page_start=1,
            page_end=1,
            children=[]
        )
        
        return DocumentIR(
            document_id=f"doc-{policy.id}-{version.id}",
            policy_id=policy.id,
            version_id=version.id,
            title=policy.title,
            department=policy.department.name if policy.department else "",
            effective_from=version.effective_date.isoformat() if hasattr(version, 'effective_date') and version.effective_date else None,
            effective_to=None,
            sections=[root_section],
            source_hash=source_hash
        )
