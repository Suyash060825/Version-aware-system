"""
rag/compiler/question_generator.py
Generates high-value canonical questions for policy chunks across standard categories.
"""
import os
import re
import hashlib
from typing import List
from models import CanonicalQuestion, now_utc
from rag.compiler.document_ir import ChunkIR

class QuestionGenerator:
    def __init__(self):
        self.enabled = os.environ.get("COMPILER_QA_ENABLED", "true").lower() == "true"
        self.max_questions = int(os.environ.get("COMPILER_MAX_QUESTIONS_PER_CHUNK", "6"))

    def generate(self, chunks: List[ChunkIR]) -> List[CanonicalQuestion]:
        if not self.enabled or not chunks:
            return []

        questions = []
        seen_hashes = set()

        for chunk in chunks:
            text = chunk.text.strip()
            if len(text) < 30:
                continue

            section = chunk.section_path or ""
            section_clean = re.sub(r"^[0-9\.\s>]+", "", section).strip()

            generated_prompts = []

            # 1. Section-based questions
            if section_clean and len(section_clean) > 3:
                generated_prompts.append(f"What is the policy regarding {section_clean}?")
                generated_prompts.append(f"What are the rules for {section_clean}?")

            # 2. Eligibility & Application
            if re.search(r"\b(?:eligible|eligibility|applies to|who can|qualify|entitled)\b", text, re.I):
                generated_prompts.append(f"Who is eligible under {section_clean or 'this policy'}?")
                generated_prompts.append(f"What are the eligibility requirements for {section_clean or 'this policy'}?")

            # 3. Limits, Entitlements & Allowances
            limit_match = re.search(r"(\d+(?:\s*(?:days|hours|months|years|INR|USD|\$|%|per day|per month|annually|per year)))", text, re.I)
            if limit_match or re.search(r"\b(?:limit|maximum|minimum|allowance|entitlement|cap|threshold)\b", text, re.I):
                generated_prompts.append(f"What is the limit or entitlement for {section_clean or 'this section'}?")
                if "leave" in text.lower():
                    generated_prompts.append("How many days of annual leave do employees get?")
                if "travel" in text.lower() or "expense" in text.lower():
                    generated_prompts.append("What is the travel expense reimbursement limit?")
                if "remote" in text.lower() or "work from home" in text.lower() or "wfh" in text.lower():
                    generated_prompts.append("How many days per week can employees work remotely?")
                if "hours" in text.lower():
                    generated_prompts.append("What are the core working hours?")
                if "gift" in text.lower():
                    generated_prompts.append("What is the maximum allowed value for business gifts?")

            # 4. Procedure & Approval
            if re.search(r"\b(?:approval|manager|submit|apply|request|process|procedure|notify)\b", text, re.I):
                generated_prompts.append(f"How do I request approval for {section_clean or 'this policy'}?")
                generated_prompts.append(f"What is the procedure for {section_clean or 'submitting a request'}?")

            # 5. Exceptions & Restrictions
            if re.search(r"\b(?:exception|prohibited|not allowed|must not|restriction|penalty|violation)\b", text, re.I):
                generated_prompts.append(f"What are the restrictions or prohibited activities under {section_clean or 'this policy'}?")

            # Dedup and build objects
            for q_text in generated_prompts[:self.max_questions]:
                q_clean = q_text.strip()
                q_hash = hashlib.sha256(f"{chunk.policy_id}:{chunk.version_id}:{chunk.chunk_id}:{q_clean.lower()}".encode()).hexdigest()
                
                if q_hash in seen_hashes:
                    continue
                seen_hashes.add(q_hash)

                questions.append(
                    CanonicalQuestion(
                        policy_id=chunk.policy_id,
                        version_id=chunk.version_id,
                        source_chunk_id=chunk.chunk_id,
                        question=q_clean,
                        question_hash=q_hash,
                        quality_score=0.95,
                        created_at=now_utc()
                    )
                )

        return questions
