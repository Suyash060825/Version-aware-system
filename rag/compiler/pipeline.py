"""
rag/compiler/pipeline.py
Master Knowledge Compiler Pipeline orchestrating end-to-end offline policy compilation.
"""
import json
import logging
from typing import Callable
from models import db, CompilationJob, CompilationStage, Policy, PolicyVersion, PolicyChunkV2, PolicyFact, CanonicalQuestion, CompiledAnswer, now_utc
from rag.compiler.document_normalizer import DocumentNormalizer
from rag.compiler.structure_extractor import StructureExtractor
from rag.compiler.fact_extractor import FactExtractor
from rag.compiler.question_generator import QuestionGenerator
from rag.compiler.answer_generator import AnswerGenerator
from rag.compiler.answer_validator import AnswerValidator
from rag.compiler.metadata_extractor import MetadataExtractor
from rag.compiler.entity_extractor import EntityExtractor
from rag.compiler.incremental import IncrementalCompiler, IncrementalDiff
from rag.compiler.temporal_extractor import TemporalExtractor

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
        self.incremental_compiler = IncrementalCompiler()

    def _get_or_create_job(self, policy_id: int, version_id: int) -> CompilationJob:
        job = CompilationJob.query.filter_by(policy_id=policy_id, version_id=version_id).with_for_update().first()
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
        
        # Incremental diff tracking if a prior version exists for this policy
        try:
            prev_version = PolicyVersion.query.filter(
                PolicyVersion.policy_id == job.policy_id,
                PolicyVersion.id != job.version_id
            ).order_by(PolicyVersion.version_num.desc()).first()
            if prev_version:
                self._incremental_diff = self.incremental_compiler.diff_versions(self._chunks, prev_version.id)
                self._prev_version_id = prev_version.id
                logger.info(
                    f"Incremental diff for policy {job.policy_id} v{job.version_id} vs v{prev_version.id}: "
                    f"{len(self._incremental_diff.unchanged_chunks)} unchanged, "
                    f"{len(self._incremental_diff.changed_chunks)} changed, "
                    f"{len(self._incremental_diff.added_chunks)} added, "
                    f"{len(self._incremental_diff.deleted_chunk_ids)} deleted"
                )
            else:
                self._incremental_diff = None
        except Exception as e:
            logger.warning(f"Incremental diff calculation encountered error (falling back to full compile): {e}")
            self._incremental_diff = None

        pv = db.session.get(PolicyVersion, job.version_id)
        pol = db.session.get(Policy, job.policy_id)
        v_active = bool(pv.is_active) if pv else True
        v_from_ts = 0
        v_to_ts = 32472144000
        if pv and pv.effective_from:
            from datetime import datetime, time as dt_time
            v_from_ts = int(datetime.combine(pv.effective_from, dt_time.min).timestamp())
        if pv and pv.effective_to:
            from datetime import datetime, time as dt_time
            v_to_ts = int(datetime.combine(pv.effective_to, dt_time.max).timestamp())
        t_id = getattr(pol, "tenant_id", None) if pol else None

        PolicyChunkV2.query.filter_by(policy_id=job.policy_id, version_id=job.version_id).delete()
        pcs = [
            PolicyChunkV2(
                chunk_id=c.chunk_id, policy_id=c.policy_id, version_id=c.version_id,
                section_path=c.section_path, page=c.page, paragraph_num=c.paragraph_num,
                text=c.text, text_hash=c.text_hash, char_count=c.char_count,
                valid_from_ts=v_from_ts, valid_to_ts=v_to_ts, is_active=v_active, tenant_id=t_id
            )
            for c in self._chunks
        ]
        if pcs:
            db.session.add_all(pcs)

    def _stage_facts(self, job: CompilationJob):
        facts = self.fact_extractor.extract(self._chunks)
        job.fact_count = len(facts)
        PolicyFact.query.filter_by(policy_id=job.policy_id, version_id=job.version_id).delete()
        if facts:
            db.session.add_all(facts)
        db.session.flush()

        # FIX 8: Log all unique predicates to data/compiled_predicates.json
        try:
            os.makedirs("data", exist_ok=True)
            db_preds = [p[0] for p in PolicyFact.query.with_entities(PolicyFact.predicate).distinct().all() if p[0]]
            with open(os.path.join("data", "compiled_predicates.json"), "w") as f:
                json.dump(sorted(list(set(db_preds))), f, indent=2)
        except Exception as e:
            logger.warning(f"Failed writing data/compiled_predicates.json: {e}")

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
        if self._questions:
            db.session.add_all(self._questions)
        db.session.flush()
        
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
        
        if raw_answers:
            db.session.add_all(raw_answers)
                
        db.session.commit()

    def _stage_embed(self, job: CompilationJob):
        from rag.embeddings.embedder import get_embedder
        from rag.vectordb.chroma import get_store
        embedder = get_embedder()
        policy_title = getattr(self._document_ir, "title", "Policy")
        version_label = getattr(self._document_ir, "version_label", "1.0")
        dept_name = getattr(self._document_ir, "department", "Universal")
        
        # Contextual Retrieval (Late Chunking metadata prepending)
        texts = [
            f"[Policy: {policy_title} (v{version_label}) | Department: {dept_name} | Section: {c.section_path or 'General'}]\n{c.text}"
            for c in self._chunks
        ]

        cached_embeddings = {}
        old_by_hash = {}
        if getattr(self, "_incremental_diff", None) and getattr(self, "_prev_version_id", None):
            try:
                old_chunks = PolicyChunkV2.query.filter_by(version_id=self._prev_version_id).all()
                old_by_hash = {c.text_hash: c.chunk_id for c in old_chunks}
                unchanged_old_ids = [
                    old_by_hash[c.text_hash] for c in self._incremental_diff.unchanged_chunks
                    if c.text_hash in old_by_hash
                ]
                if unchanged_old_ids:
                    store = get_store()
                    col_res = store._col.get(ids=unchanged_old_ids, include=["embeddings"])
                    if col_res and col_res.get("ids") and col_res.get("embeddings") is not None:
                        for cid, emb in zip(col_res["ids"], col_res["embeddings"]):
                            if emb is not None:
                                cached_embeddings[cid] = emb
            except Exception as e:
                logger.warning(f"Incremental embedding lookup failed (falling back to embedding all chunks): {e}")

        to_embed_indices = []
        to_embed_texts = []
        final_embeddings = [None] * len(self._chunks)

        for idx, (c, t) in enumerate(zip(self._chunks, texts)):
            matched_cid = old_by_hash.get(c.text_hash) if (cached_embeddings and hasattr(c, "text_hash")) else None
            if matched_cid and matched_cid in cached_embeddings:
                final_embeddings[idx] = cached_embeddings[matched_cid]
            else:
                to_embed_indices.append(idx)
                to_embed_texts.append(t)

        if to_embed_texts:
            new_embs = embedder.embed(to_embed_texts)
            for idx, emb in zip(to_embed_indices, new_embs):
                final_embeddings[idx] = emb

        logger.info(
            f"Stage embed: {len(self._chunks) - len(to_embed_texts)} reused from cache, "
            f"{len(to_embed_texts)} newly embedded."
        )
        self._embeddings = final_embeddings
        job.embedding_model = getattr(embedder, "model_name", "unknown")

    def _stage_index(self, job: CompilationJob):
        from rag.vectordb.chroma import get_store
        store = get_store()
        
        pv = db.session.get(PolicyVersion, job.version_id)
        pol = db.session.get(Policy, job.policy_id)
        v_num = float(pv.version_num) if pv and pv.version_num is not None else 1.0
        v_lbl = pv.version_label if pv and pv.version_label else f"v{v_num}"
        is_curr = bool(pv.is_active) if pv else True
        p_name = pol.title if pol else (getattr(self._document_ir, "title", "Policy") or "Policy")

        valid_from_ts = 0
        valid_to_ts = 32472144000
        if pv and pv.effective_from:
            from datetime import datetime, time
            valid_from_ts = int(datetime.combine(pv.effective_from, time.min).timestamp())
        if pv and pv.effective_to:
            from datetime import datetime, time
            valid_to_ts = int(datetime.combine(pv.effective_to, time.max).timestamp())

        chunk_dicts = []
        for c in self._chunks:
            chunk_dicts.append({
                "chunk_id": c.chunk_id,
                "text": c.text,
                "policy_id": int(c.policy_id),
                "policy_name": p_name,
                "version": v_lbl,
                "version_num": v_num,
                "version_id": int(c.version_id),
                "department": self._document_ir.department or "Company",
                "section": c.section_path or "General",
                "section_path": c.section_path or "General",
                "page": c.page or 1,
                "chunk_index": c.paragraph_num or 0,
                "is_active": is_curr,
                "is_current": is_curr,
                "valid_from_ts": valid_from_ts,
                "valid_to_ts": valid_to_ts
            })
        store.delete_policy_version(job.policy_id, str(job.version_id))
        store.upsert_chunks(chunk_dicts, self._embeddings)
        
        # Incremental Delta Updates for BM25 and Canonical QA indexes
        from rag.retrieval.sparse import get_bm25_index
        get_bm25_index().update_policy_version(job.policy_id, job.version_id, chunk_dicts)

        from rag.qa.qa_index import get_qa_index
        qa_index = get_qa_index()
        # Find newly created valid QA pairs for this version
        valid_qs = CanonicalQuestion.query.filter_by(policy_id=job.policy_id, version_id=job.version_id).all()
        if valid_qs:
            q_ids = [q.id for q in valid_qs]
            answers_by_qid = {
                a.question_id: a for a in CompiledAnswer.query.filter(
                    CompiledAnswer.question_id.in_(q_ids),
                    CompiledAnswer.status == "validated"
                ).all()
            }
            valid_pairs = [(q, answers_by_qid[q.id]) for q in valid_qs if q.id in answers_by_qid]
        else:
            valid_pairs = []
        
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

        # Invalidate affected cache entries, fact predicates, diff cache, and evidence filter cache
        from rag.cache.semantic_cache import get_cache
        get_cache().invalidate_version(job.policy_id, job.version_id)
        try:
            from rag.facts.fact_resolver import FactResolver
            FactResolver().invalidate()
        except Exception:
            pass
        try:
            from rag.versions.diff_engine import clear_diff_cache
            clear_diff_cache()
        except Exception:
            pass
        try:
            from rag.authorization.evidence_filter import get_evidence_filter
            get_evidence_filter().clear_cache()
        except Exception:
            pass
        try:
            from rag.engine.policy_title_index import rebuild_title_index
            rebuild_title_index()
        except Exception:
            pass


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
        try:
            from rag.engine.policy_title_index import rebuild_title_index
            rebuild_title_index()
        except Exception:
            pass
        return job
    except Exception as e:
        _log.exception(f"Auto-compilation failed for policy {policy_id} v{version_id}: {e}")
        return None

