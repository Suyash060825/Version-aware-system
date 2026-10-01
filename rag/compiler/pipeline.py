"""
rag/compiler/pipeline.py
Master Knowledge Compiler Pipeline orchestrating end-to-end offline policy compilation.
"""
import json
import logging
from typing import Callable, Any, List
from datetime import datetime
from models import db, CompilationJob, CompilationStage, Policy, PolicyVersion, PolicyChunkV2, PolicyFact, CanonicalQuestion, CompiledAnswer, now_utc
from rag.compiler.document_ir import DocumentIR, ChunkIR
from rag.compiler.document_normalizer import DocumentNormalizer
from rag.compiler.structure_extractor import StructureExtractor
from rag.compiler.fact_extractor import FactExtractor
from rag.compiler.question_generator import QuestionGenerator
from rag.compiler.answer_generator import AnswerGenerator
from rag.compiler.answer_validator import AnswerValidator
from rag.compiler.metadata_extractor import MetadataExtractor
from rag.compiler.entity_extractor import EntityExtractor
from rag.compiler.temporal_extractor import TemporalExtractor
from rag.compiler.compilation_manifest import CompilationManifest

logger = logging.getLogger("rag.compiler.pipeline")

class KnowledgeCompilerPipeline:
    COMPILER_VERSION = "2.0.0"
    PARSER_VERSION = "1.0.0"

    def __init__(self):
        self.normalizer = DocumentNormalizer()
        self.structure_extractor = StructureExtractor()
        self.fact_extractor = FactExtractor()
        self.question_generator = QuestionGenerator()
        self.answer_generator = AnswerGenerator()
        self.answer_validator = AnswerValidator()
        self.metadata_extractor = MetadataExtractor()
        self.entity_extractor = EntityExtractor()
        self.temporal_extractor = TemporalExtractor()

    def _get_or_create_job(self, policy_id: int, version_id: int) -> CompilationJob:
        job = CompilationJob.query.filter_by(version_id=version_id).first()
        if not job:
            job = CompilationJob(policy_id=policy_id, version_id=version_id)
            db.session.add(job)
            try:
                db.session.commit()
            except Exception:
                db.session.rollback()
                job = CompilationJob.query.filter_by(version_id=version_id).first()
        elif job.policy_id != policy_id:
            job.policy_id = policy_id
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
            logger.error(f"Stage {target_stage} failed for policy {job.policy_id} v{job.version_id}: {e}")
            db.session.rollback()
            job.stage = CompilationStage.FAILED
            job.error = str(e)
            db.session.commit()
            
        return job

    def compile(self, policy_id: int, version_id: int) -> CompilationJob:
        job = self._get_or_create_job(policy_id, version_id)
        if job.stage == CompilationStage.FAILED:
            job.stage = None
            job.error = None
            db.session.commit()
        
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
        version = db.session.get(PolicyVersion, job.version_id)
        if not version or not version.content or len(version.content.strip()) == 0:
            raise ValueError(f"Policy version {job.version_id} has no readable content to compile.")

    def _stage_normalize(self, job: CompilationJob):
        policy = db.session.get(Policy, job.policy_id)
        version = db.session.get(PolicyVersion, job.version_id)
        raw_text = version.content or ""
        self._document_ir = self.normalizer.normalize(raw_text, policy, version)
        job.document_hash = self._document_ir.source_hash

    def _stage_chunk(self, job: CompilationJob):
        self._chunks = self.structure_extractor.extract(self._document_ir)
        job.chunk_count = len(self._chunks)
        
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
        PolicyFact.query.filter_by(policy_id=job.policy_id, version_id=job.version_id).delete()
        for f in facts:
            db.session.add(f)

    def _stage_qa(self, job: CompilationJob):
        self._questions = self.question_generator.generate(self._chunks)
        job.qa_count = len(self._questions)
        
        # Clean up existing questions for this version
        old_q_ids = [q.id for q in CanonicalQuestion.query.filter_by(policy_id=job.policy_id, version_id=job.version_id).all()]
        if old_q_ids:
            CompiledAnswer.query.filter(CompiledAnswer.question_id.in_(old_q_ids)).delete(synchronize_session=False)
            CanonicalQuestion.query.filter_by(policy_id=job.policy_id, version_id=job.version_id).delete()
            db.session.commit()

        # Add questions and flush to get primary keys
        for q in self._questions:
            db.session.add(q)
        db.session.flush()

        new_q_ids = [q.id for q in self._questions if q.id]
        if new_q_ids:
            CompiledAnswer.query.filter(CompiledAnswer.question_id.in_(new_q_ids)).delete(synchronize_session=False)
        
        raw_answers = self.answer_generator.generate(self._questions, self._chunks)
        chunk_map = {c.chunk_id: [{"text": c.text}] for c in self._chunks}
        
        for ans in raw_answers:
            cids = []
            try:
                cids = json.loads(ans.source_chunk_ids)
            except Exception:
                cids = [ans.source_chunk_ids]

            source_c_list = []
            for cid in cids:
                if cid in chunk_map:
                    source_c_list.extend(chunk_map[cid])
            if not source_c_list:
                source_c_list = [{"text": ans.answer}]

            is_valid, entail_score = self.answer_validator.validate(ans.answer, source_c_list)
            ans.entailment_score = entail_score
            ans.confidence = float(entail_score)
            ans.status = "validated" if is_valid else "rejected"
            db.session.add(ans)
                
        db.session.commit()

    def _stage_embed(self, job: CompilationJob):
        from rag.embeddings.embedder import get_embedder
        embedder = get_embedder()
        policy_title = getattr(self._document_ir, "title", "Policy")
        version_label = getattr(self._document_ir, "version_label", "1.0")
        dept_name = getattr(self._document_ir, "department", "Universal")
        
        # Contextual Retrieval (Late Chunking metadata prepending)
        texts = [
            f"[Policy: {policy_title} (v{version_label}) | Department: {dept_name} | Section: {c.section_path or 'General'}]\n{c.text}"
            for c in self._chunks
        ]
        self._embeddings = embedder.embed(texts)
        job.embedding_model = getattr(embedder, "model_name", "unknown")

    def _stage_index(self, job: CompilationJob):
        from rag.vectordb.chroma import get_store
        store = get_store()
        chunk_dicts = []
        for c in self._chunks:
            chunk_dicts.append({
                "chunk_id": c.chunk_id,
                "text": c.text,
                "policy_id": c.policy_id,
                "version": str(c.version_id),
                "version_id": c.version_id,
                "department": self._document_ir.department or "Company",
                "section": c.section_path or "General",
                "section_path": c.section_path or "General",
                "page": c.page or 1,
                "chunk_index": c.paragraph_num or 0,
                "is_active": True
            })
        store.delete_policy_version(job.policy_id, str(job.version_id))
        store.upsert_chunks(chunk_dicts, self._embeddings)
        
        # Incremental Delta Updates for BM25 and Canonical QA indexes
        from rag.retrieval.sparse import PersistentBM25Index
        PersistentBM25Index().update_policy_version(job.policy_id, job.version_id, chunk_dicts)

        from rag.qa.qa_index import CanonicalQAIndex
        qa_index = CanonicalQAIndex()
        # Find newly created valid QA pairs for this version
        valid_qs = CanonicalQuestion.query.filter_by(policy_id=job.policy_id, version_id=job.version_id).all()
        valid_ans = [CompiledAnswer.query.filter_by(question_id=q.id, status="validated").first() for q in valid_qs]
        valid_pairs = [(q, a) for q, a in zip(valid_qs, valid_ans) if a is not None]
        
        if valid_pairs:
            from rag.embeddings.embedder import get_embedder
            embedder = get_embedder()
            q_texts = [p[0].question for p in valid_pairs]
            q_embs = embedder.embed(q_texts)
            qa_index.update_policy_version_qa(
                job.policy_id, job.version_id,
                [p[0] for p in valid_pairs],
                [p[1] for p in valid_pairs],
                q_embs
            )
        else:
            qa_index.delete_policy_version(job.policy_id, job.version_id)

        # Invalidate affected cache entries
        from rag.cache.semantic_cache import get_cache
        get_cache().invalidate_version(job.policy_id, job.version_id)


def auto_compile_policy_version(policy_id: int, version_id: int):
    """
    Compile and index a policy version immediately upon creation or update.
    Executes KnowledgeCompilerPipeline synchronously so that all indexes
    (ChromaDB, BM25, FAISS QA index), chunks, facts, and QAs are instantly
    ready and reflected on all dashboards.
    """
    import logging
    _log = logging.getLogger("rag.compiler.auto")
    try:
        compiler = KnowledgeCompilerPipeline()
        job = compiler.compile(policy_id, version_id)
        _log.info(
            f"Auto-compiled policy {policy_id} v{version_id}: {job.stage} "
            f"({job.chunk_count} chunks, {job.fact_count} facts, {job.qa_count} QAs)"
        )
        return job
    except Exception as e:
        _log.exception(f"Auto-compilation failed for policy {policy_id} v{version_id}: {e}")
        return None

