from dataclasses import dataclass, field
from typing import Optional, List

@dataclass
class SectionNode:
    section_id: str
    title: str
    level: int           # 1=H1, 2=H2, 3=H3
    content: str
    page_start: int
    page_end: int
    children: List["SectionNode"] = field(default_factory=list)

@dataclass
class DocumentIR:
    document_id: str
    policy_id: int
    version_id: int
    title: str
    department: str
    effective_from: Optional[str]
    effective_to: Optional[str]
    sections: List[SectionNode]
    source_hash: str        # SHA256 of raw text
    parser_version: str = "1.0"

@dataclass
class ChunkIR:
    chunk_id: str           # "p42-v8-s4-2-c3" format
    policy_id: int
    version_id: int
    section_path: str       # "4.2 Eligibility"
    text: str
    page: int
    paragraph_num: int
    text_hash: str          # SHA256(normalized_text)
    char_count: int
    is_table: bool = False
    is_list: bool = False
