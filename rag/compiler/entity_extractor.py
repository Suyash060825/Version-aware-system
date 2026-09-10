"""
rag/compiler/entity_extractor.py
Extracts named entities and relationships from policy chunks for graph and structured queries.
"""
import re
from typing import List, Tuple
from models import PolicyEntity, PolicyRelationship, now_utc
from rag.compiler.document_ir import ChunkIR

class EntityExtractor:
    ENTITY_PATTERNS = [
        ("ROLE", r"\b(?:employee|manager|director|supervisor|hr manager|approver|author|auditor|contractor)\b"),
        ("DEPARTMENT", r"\b(?:human resources|information technology|finance|legal|engineering|marketing|sales|operations)\b"),
        ("BENEFIT", r"\b(?:annual leave|sick leave|maternity leave|paternity leave|health insurance|travel allowance|wfh allowance)\b"),
        ("FORM", r"\b(?:form [a-z0-9-]+|annexure [a-z0-9-]+|reimbursement claim|leave request|nda)\b"),
        ("AUTHORITY", r"\b(?:ceo|cto|cfo|head of hr|board of directors|vp of engineering)\b"),
    ]

    def extract(self, chunks: List[ChunkIR]) -> Tuple[List[PolicyEntity], List[PolicyRelationship]]:
        entities = []
        relationships = []
        seen_entities = set()

        for chunk in chunks:
            text = chunk.text.lower()

            chunk_entities = []
            for ent_type, pattern in self.ENTITY_PATTERNS:
                matches = re.finditer(pattern, text, re.I)
                for m in matches:
                    name = m.group(0).title()
                    norm_name = name.lower()
                    key = (chunk.policy_id, chunk.version_id, ent_type, norm_name)
                    
                    if key in seen_entities:
                        continue
                    seen_entities.add(key)

                    ent = PolicyEntity(
                        policy_id=chunk.policy_id,
                        version_id=chunk.version_id,
                        entity_type=ent_type,
                        entity_name=name,
                        normalized_name=norm_name,
                        source_chunk_id=chunk.chunk_id,
                        created_at=now_utc()
                    )
                    entities.append(ent)
                    chunk_entities.append(ent)

            # Extract basic relationships within same chunk
            for i in range(len(chunk_entities)):
                for j in range(i + 1, len(chunk_entities)):
                    e1, e2 = chunk_entities[i], chunk_entities[j]
                    if e1.entity_type == "ROLE" and e2.entity_type == "BENEFIT":
                        rel = PolicyRelationship(
                            policy_id=chunk.policy_id,
                            version_id=chunk.version_id,
                            source_entity_id=e1.id or 1,
                            relation="eligible_for",
                            target_entity_id=e2.id or 1
                        )
                        relationships.append(rel)

        return entities, relationships
