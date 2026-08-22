import hashlib
from typing import List
from rag.compiler.document_ir import DocumentIR, ChunkIR

class StructureExtractor:
    def extract(self, document_ir: DocumentIR) -> List[ChunkIR]:
        chunks = []
        
        for section in document_ir.sections:
            # Simple paragraph splitting
            paragraphs = section.content.split('\n\n')
            
            for i, para in enumerate(paragraphs):
                para = para.strip()
                if not para or len(para) < 20: # skip very short chunks
                    continue
                    
                text_hash = hashlib.sha256(para.encode()).hexdigest()
                chunk_id = f"p{document_ir.policy_id}-v{document_ir.version_id}-s{section.section_id}-c{i}"
                
                chunks.append(
                    ChunkIR(
                        chunk_id=chunk_id,
                        policy_id=document_ir.policy_id,
                        version_id=document_ir.version_id,
                        section_path=section.title,
                        text=para,
                        page=section.page_start,
                        paragraph_num=i,
                        text_hash=text_hash,
                        char_count=len(para)
                    )
                )
        return chunks
