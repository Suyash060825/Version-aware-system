import hashlib
from typing import List
from rag.compiler.document_ir import DocumentIR, ChunkIR

class StructureExtractor:
    def extract(self, document_ir: DocumentIR) -> List[ChunkIR]:
        chunks = []
        
        for section in document_ir.sections:
            # Paragraph splitting on double newlines
            raw_paragraphs = [p.strip() for p in section.content.split('\n\n') if p.strip()]
            
            # Normalize and sub-split oversized paragraphs (>1200 chars)
            final_paragraphs = []
            for raw_p in raw_paragraphs:
                if len(raw_p) <= 1200:
                    final_paragraphs.append(raw_p)
                else:
                    # Sub-split by sentences
                    sentences = [s.strip() for s in raw_p.replace('.\n', '. ').split('. ') if s.strip()]
                    cur_chunk = []
                    cur_len = 0
                    for s in sentences:
                        s_text = s if s.endswith('.') else s + '.'
                        if cur_len + len(s_text) > 1000 and cur_chunk:
                            final_paragraphs.append(" ".join(cur_chunk))
                            cur_chunk = [s_text]
                            cur_len = len(s_text)
                        else:
                            cur_chunk.append(s_text)
                            cur_len += len(s_text) + 1
                    if cur_chunk:
                        final_paragraphs.append(" ".join(cur_chunk))

            for i, para in enumerate(final_paragraphs):
                para = para.strip()
                if not para or len(para) < 15: # skip negligible chunks (<15 chars)
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
