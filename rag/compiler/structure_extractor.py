import re
import hashlib
from typing import List
from rag.compiler.document_ir import DocumentIR, ChunkIR

class StructureExtractor:
    MAX_CHUNK_CHARS = 1000
    MIN_CHUNK_CHARS = 30

    def extract(self, document_ir: DocumentIR) -> List[ChunkIR]:
        chunks = []

        for section in document_ir.sections:
            paragraphs = section.content.split('\n\n')
            
            blocks = []
            pending_prefix = ""
            for p in paragraphs:
                p = p.strip()
                if not p:
                    continue
                # Merge very short standalone titles/fragments (< 40 chars) with following text
                if len(p) < 40 and not pending_prefix:
                    pending_prefix = p + "\n"
                    continue
                if pending_prefix:
                    p = pending_prefix + p
                    pending_prefix = ""

                if len(p) <= self.MAX_CHUNK_CHARS:
                    blocks.append(p)
                else:
                    # Sub-split long blocks on sentence boundaries to preserve embedding capacity
                    sentences = re.split(r'(?<=[.!?])\s+', p)
                    cur_block = ""
                    for s in sentences:
                        if cur_block and len(cur_block) + len(s) + 1 > (self.MAX_CHUNK_CHARS - 100):
                            blocks.append(cur_block.strip())
                            cur_block = s
                        else:
                            cur_block = (cur_block + " " + s).strip() if cur_block else s
                    if cur_block:
                        blocks.append(cur_block.strip())

            if pending_prefix:
                if blocks:
                    blocks[-1] = blocks[-1] + "\n" + pending_prefix.strip()
                else:
                    blocks.append(pending_prefix.strip())

            for i, block in enumerate(blocks):
                block = block.strip()
                if not block or len(block) < self.MIN_CHUNK_CHARS:
                    continue

                text_hash = hashlib.sha256(block.encode()).hexdigest()
                chunk_id = f"p{document_ir.policy_id}-v{document_ir.version_id}-s{section.section_id}-c{i}"

                chunks.append(
                    ChunkIR(
                        chunk_id=chunk_id,
                        policy_id=document_ir.policy_id,
                        version_id=document_ir.version_id,
                        section_path=section.title,
                        text=block,
                        page=section.page_start,
                        paragraph_num=i,
                        text_hash=text_hash,
                        char_count=len(block)
                    )
                )

        return chunks
