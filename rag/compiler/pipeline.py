import logging
from typing import Callable, Any
from models import db, CompilationJob, CompilationStage, Policy, PolicyVersion, now_utc

logger = logging.getLogger("rag.compiler.pipeline")

class KnowledgeCompilerPipeline:
    COMPILER_VERSION = "1.0.0"

    def __init__(self):
        from rag.compiler.document_normalizer import DocumentNormalizer
        from rag.compiler.structure_extractor import StructureExtractor
        from rag.compiler.fact_extractor import FactExtractor
        from rag.compiler.question_generator import QuestionGenerator
        from rag.compiler.answer_generator import AnswerGenerator
        from rag.compiler.answer_validator import AnswerValidator
        
        self.normalizer = DocumentNormalizer()
        self.structure_extractor = StructureExtractor()
        self.fact_extractor = FactExtractor()
        self.question_generator = QuestionGenerator()
        self.answer_generator = AnswerGenerator()
        self.answer_validator = AnswerValidator()

    def _get_or_create_job(self, policy_id: int, version_id: int) -> CompilationJob:
        job = CompilationJob.query.filter_by(policy_id=policy_id, version_id=version_id).first()
        if not job:
            job = CompilationJob(policy_id=policy_id, version_id=version_id)
            db.session.add(job)
            db.session.commit()
        return job

    def _advance_stage(self, job: CompilationJob, target_stage: str, execute_fn: Callable) -> CompilationJob:
        if job.stage == CompilationStage.FAILED:
            return job
            
        logger.info(f"Advancing job {job.id} to {target_stage}")
        job.stage = target_stage
        db.session.commit()
        
        try:
            execute_fn(job)
            db.session.commit()
        except Exception as e:
            logger.error(f"Stage {target_stage} failed: {e}")
            job.stage = CompilationStage.FAILED
            job.error = str(e)
            db.session.commit()
            
        return job

    def compile(self, policy_id: int, version_id: int) -> CompilationJob:
        job = self._get_or_create_job(policy_id, version_id)
        
        stages = [
            (CompilationStage.PARSING, self._stage_parse),
            (CompilationStage.NORMALIZED, self._stage_normalize),
            (CompilationStage.CHUNKED, self._stage_chunk),
            (CompilationStage.FACT_EXTRACTION, self._stage_facts),
            (CompilationStage.QA_COMPILATION, self._stage_qa),
            (CompilationStage.EMBEDDING, self._stage_embed),
            (CompilationStage.INDEXING, self._stage_index),
        ]
        
        for stage_name, stage_fn in stages:
            job = self._advance_stage(job, stage_name, stage_fn)
            if job.stage == CompilationStage.FAILED:
                return job
                
        job.stage = CompilationStage.READY
        job.completed_at = now_utc()
        db.session.commit()
        
        return job
        
    def _stage_parse(self, job: CompilationJob):
        pass

    def _stage_normalize(self, job: CompilationJob):
        policy = db.session.get(Policy, job.policy_id)
        version = db.session.get(PolicyVersion, job.version_id)
        raw_text = version.content or ""
        self._document_ir = self.normalizer.normalize(raw_text, policy, version)
        job.document_hash = self._document_ir.source_hash

    def _stage_chunk(self, job: CompilationJob):
        self._chunks = self.structure_extractor.extract(self._document_ir)
        job.chunk_count = len(self._chunks)
        from models import PolicyChunkV2
        PolicyChunkV2.query.filter_by(policy_id=job.policy_id, version_id=job.version_id).delete()
        for c in self._chunks:
            pc = PolicyChunkV2(
                chunk_id=c.chunk_id, policy_id=c.policy_id, version_id=c.version_id,
                section_path=c.section_path, page=c.page, paragraph_num=c.paragraph_num,
                text=c.text, text_hash=c.text_hash, char_count=c.char_count
            )
            db.session.add(pc)

    def _stage_facts(self, job: CompilationJob):
        facts = self.fact_extractor.extract(self._chunks)
        job.fact_count = len(facts)
        from models import PolicyFact
        PolicyFact.query.filter_by(policy_id=job.policy_id, version_id=job.version_id).delete()
        for f in facts:
            db.session.add(f)

    def _stage_qa(self, job: CompilationJob):
        questions = self.question_generator.generate(self._chunks)
        
        from models import CanonicalQuestion, CompiledAnswer
        CanonicalQuestion.query.filter_by(policy_id=job.policy_id, version_id=job.version_id).delete()
        # Have to commit so questions get IDs for answers
        for q in questions:
            db.session.add(q)
        db.session.commit()
        
        answers = self.answer_generator.generate(questions, self._chunks)
        for a in answers:
            db.session.add(a)
        
        job.qa_count = len(questions)

    def _stage_embed(self, job: CompilationJob):
        from rag.embeddings.embedder import get_embedder
        embedder = get_embedder()
        texts = [c.text for c in self._chunks]
        self._embeddings = embedder.embed(texts)
        job.embedding_model = getattr(embedder, "model_name", "unknown")

        # Optionally embed the canonical questions here so QA matcher can use them
        if hasattr(self, '_questions') and self._questions:
            q_texts = [q.question for q in self._questions]
            self._q_embeddings = embedder.embed_query(q_texts)

    def _stage_index(self, job: CompilationJob):
        from rag.vectordb.chroma import get_store
        store = get_store()
        chunk_dicts = []
        for c in self._chunks:
            chunk_dicts.append({
                "text": c.text, "policy_id": c.policy_id, "version": str(c.version_id),
                "department": self._document_ir.department, "section": c.section_path,
                "page": c.page, "chunk_index": c.paragraph_num, "is_active": True
            })
        store.delete_policy_version(job.policy_id, str(job.version_id))
        store.upsert_chunks(chunk_dicts, self._embeddings)
        
        # Rebuild BM25 index immediately after indexing
        from rag.retrieval.sparse import PersistentBM25Index
        PersistentBM25Index().rebuild_from_db()
