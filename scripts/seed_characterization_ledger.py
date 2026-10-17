"""
scripts/seed_characterization_ledger.py
Ingests the complete 120-policy, 422-version, 2,110-chunk, 422-fact, 422-QA
Ground Truth Ledger into the SQLite database, Chroma Vector Store, Persistent BM25 Index,
and Canonical QA FAISS Index.
"""
import os
import sys
import json
import hashlib
import logging
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from models import (
    db, User, UserRole, Department, PolicyCategory,
    Policy, PolicyVersion, PolicyStatus, PolicyChunkV2,
    PolicyFact, CanonicalQuestion, CompiledAnswer
)
from tests.system_characterization.corpus.ground_truth_ledger import GroundTruthLedger
from tests.system_characterization.corpus.user_matrix import DEPARTMENTS_CONFIG
from rag.retrieval.sparse import PersistentBM25Index
from rag.vectordb.chroma import get_store
from rag.qa.qa_index import CanonicalQAIndex
from rag.embeddings.embedder import get_embedder

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("seed_characterization")

LEDGER_PATH = "tests/system_characterization/corpus/ground_truth_ledger.json"

def seed_characterization_corpus(ledger_path: str = LEDGER_PATH):
    if not os.path.exists(ledger_path):
        raise FileNotFoundError(f"Ground truth ledger not found at {ledger_path}")

    logger.info(f"Loading Ground Truth Ledger from {ledger_path}...")
    ledger = GroundTruthLedger.load(ledger_path)
    logger.info(f"Loaded: {len(ledger.policies)} policies, {len(ledger.versions)} versions, "
                f"{len(ledger.chunks)} chunks, {len(ledger.facts)} facts, {len(ledger.canonical_qas)} QAs.")

    app = create_app("development")
    with app.app_context():
        # 1. Seed / Ensure Departments
        logger.info("Ensuring 12 enterprise departments exist...")
        dept_map = {}
        for d in DEPARTMENTS_CONFIG:
            dept = db.session.get(Department, d["id"])
            if not dept:
                dept = Department.query.filter_by(name=d["name"]).first()
            if not dept:
                # Ensure unique code
                code = d["code"]
                if Department.query.filter_by(code=code).first():
                    code = f"{d['code']}_{d['id']}"
                dept = Department(id=d["id"], name=d["name"], code=code)
                db.session.add(dept)
                db.session.flush()
            dept_map[d["id"]] = dept
        db.session.commit()

        # 2. Ensure Author User
        admin_user = User.query.filter_by(role=UserRole.ADMIN).first()
        if not admin_user:
            admin_user = User(
                name="System Administrator",
                email="admin@veritas.local",
                role=UserRole.ADMIN,
                department_id=1
            )
            admin_user.set_password("AdminPass123!")
            db.session.add(admin_user)
            db.session.commit()
        author_id = admin_user.id

        # 3. Ensure Policy Categories
        default_cat = PolicyCategory.query.first()
        if not default_cat:
            default_cat = PolicyCategory(name="General", description="General Policies")
            db.session.add(default_cat)
            db.session.commit()

        categories_by_name = {c.name.lower(): c for c in PolicyCategory.query.all()}

        # 3.5 Clear existing policy tables for clean alignment with characterization ledger
        logger.info("Clearing previous policy tables for clean characterization ledger alignment...")
        from models import policy_tags, saved_policies, ApprovalWorkflow, PolicyAcknowledgement, ContradictionFlag
        db.session.execute(policy_tags.delete())
        db.session.execute(saved_policies.delete())
        ApprovalWorkflow.query.delete()
        PolicyAcknowledgement.query.delete()
        ContradictionFlag.query.delete()
        CompiledAnswer.query.delete()
        CanonicalQuestion.query.delete()
        PolicyFact.query.delete()
        PolicyChunkV2.query.delete()
        PolicyVersion.query.delete()
        Policy.query.delete()
        db.session.commit()

        # 4. Ingest Policies
        logger.info("Ingesting 120 policies into SQLite...")
        for p_id, p_entry in ledger.policies.items():
            cat = categories_by_name.get(p_entry.category.lower(), default_cat)
            if not cat and p_entry.category:
                cat = PolicyCategory(name=p_entry.category, description=f"{p_entry.category} policies")
                db.session.add(cat)
                db.session.flush()
                categories_by_name[p_entry.category.lower()] = cat

            active_ver = next((v for v in p_entry.versions if v.is_active), None)
            eff_d = None
            if active_ver and active_ver.effective_start:
                try:
                    eff_d = datetime.strptime(active_ver.effective_start, "%Y-%m-%d").date()
                except ValueError:
                    pass

            pol = Policy(
                id=p_id,
                policy_id=p_entry.policy_code,
                title=p_entry.title,
                description=f"{p_entry.title} - {p_entry.category}",
                category_id=cat.id if cat else default_cat.id,
                department_id=p_entry.department_id,
                author_id=author_id,
                status=PolicyStatus.ACTIVE,
                priority=p_entry.priority,
                is_mandatory=p_entry.is_mandatory,
                confidentiality=p_entry.confidentiality,
                current_version=active_ver.version_label if active_ver else "v1.0",
                effective_date=eff_d
            )
            db.session.add(pol)

        db.session.commit()
        logger.info(f"Policies synchronized: {Policy.query.count()} total in DB.")

        # 5. Ingest Versions
        logger.info("Ingesting 422 policy versions into SQLite...")
        chunks_by_version = {}
        for c in ledger.chunks.values():
            chunks_by_version.setdefault(c.version_id, []).append(c)

        for v_id, v_entry in ledger.versions.items():
            eff_d = None
            if v_entry.effective_start:
                try:
                    eff_d = datetime.strptime(v_entry.effective_start, "%Y-%m-%d").date()
                except ValueError:
                    pass

            ver_chunks = chunks_by_version.get(v_id, [])
            ver_content = "\n\n".join(c.text for c in sorted(ver_chunks, key=lambda x: (x.page, x.paragraph_num)))
            if not ver_content:
                ver_content = f"{v_entry.policy_code} version {v_entry.version_label}"

            pv = PolicyVersion(
                id=v_id,
                policy_id=v_entry.policy_id,
                version_num=v_entry.version_num,
                version_label=v_entry.version_label,
                content=ver_content,
                summary=v_entry.change_summary,
                change_reason=v_entry.mutation_type,
                created_by_id=author_id,
                approved_by_id=author_id,
                is_active=v_entry.is_active,
                status="approved" if v_entry.is_active else "superseded",
                effective_date=eff_d
            )
            db.session.add(pv)

        db.session.commit()
        logger.info(f"PolicyVersions synchronized: {PolicyVersion.query.count()} total in DB.")
        # 6. Ingest Chunks
        logger.info("Ingesting 2,110 policy chunks into SQLite...")
        existing_chunk_ids = {c.chunk_id for c in PolicyChunkV2.query.with_entities(PolicyChunkV2.chunk_id).all()}
        new_chunks = []
        for c_id, c_entry in ledger.chunks.items():
            if c_id not in existing_chunk_ids:
                new_chunks.append(PolicyChunkV2(
                    chunk_id=c_entry.chunk_id,
                    policy_id=c_entry.policy_id,
                    version_id=c_entry.version_id,
                    section_path=c_entry.section_path,
                    page=c_entry.page,
                    paragraph_num=c_entry.paragraph_num,
                    text=c_entry.text,
                    text_hash=c_entry.text_hash,
                    embedding_hash=c_entry.embedding_hash,
                    char_count=c_entry.char_count
                ))
        if new_chunks:
            db.session.bulk_save_objects(new_chunks)
            db.session.commit()
        logger.info(f"PolicyChunkV2 synchronized: {PolicyChunkV2.query.count()} total in DB.")

        # 7. Ingest Facts
        logger.info("Ingesting 422 facts into SQLite...")
        existing_fact_keys = {(f.policy_id, f.version_id, f.predicate) for f in PolicyFact.query.all()}
        new_facts = []
        for f_entry in ledger.facts.values():
            key = (f_entry.policy_id, f_entry.version_id, f_entry.predicate)
            if key not in existing_fact_keys:
                new_facts.append(PolicyFact(
                    policy_id=f_entry.policy_id,
                    version_id=f_entry.version_id,
                    subject=f_entry.subject,
                    predicate=f_entry.predicate,
                    value=f_entry.value,
                    unit=f_entry.unit,
                    scope=f_entry.scope,
                    source_chunk_id=f_entry.source_chunk_id,
                    confidence=f_entry.confidence
                ))
                existing_fact_keys.add(key)
        if new_facts:
            db.session.bulk_save_objects(new_facts)
            db.session.commit()
        logger.info(f"PolicyFact synchronized: {PolicyFact.query.count()} total in DB.")

        # 8. Ingest Canonical Questions and Answers
        logger.info("Ingesting 422 Canonical Questions and Answers into SQLite...")
        for q_entry in ledger.canonical_qas.values():
            composite_hash = hashlib.sha256(
                f"{q_entry.policy_id}:{q_entry.version_id}:{q_entry.question.strip().lower()}".encode()
            ).hexdigest()
            q_obj = CanonicalQuestion.query.filter_by(
                question_hash=composite_hash
            ).first()
            if not q_obj:
                q_obj = CanonicalQuestion(
                    policy_id=q_entry.policy_id,
                    version_id=q_entry.version_id,
                    source_chunk_id=q_entry.source_chunk_ids[0] if q_entry.source_chunk_ids else None,
                    question=q_entry.question,
                    question_hash=composite_hash,
                    quality_score=q_entry.quality_score
                )
                db.session.add(q_obj)
                db.session.flush()

            ans_obj = CompiledAnswer.query.filter_by(question_id=q_obj.id).first()
            if not ans_obj:
                ans_obj = CompiledAnswer(
                    question_id=q_obj.id,
                    answer=q_entry.target_answer,
                    source_chunk_ids=json.dumps(q_entry.source_chunk_ids),
                    confidence=1.0,
                    status="validated"
                )
                db.session.add(ans_obj)

        db.session.commit()
        logger.info(f"Canonical QA synchronized: {CanonicalQuestion.query.count()} questions, "
                    f"{CompiledAnswer.query.count()} compiled answers.")

        # 9. Rebuild BM25 Index
        logger.info("Rebuilding Persistent BM25 index from database...")
        bm25_index = PersistentBM25Index()
        bm25_index.rebuild_from_db()
        logger.info(f"BM25 index rebuilt with {len(bm25_index._corpus)} chunks.")

        # 10. Rebuild FAISS Canonical QA Index
        logger.info("Rebuilding Canonical QA FAISS index from database...")
        qa_index = CanonicalQAIndex()
        qa_index.rebuild_from_db()
        logger.info(f"FAISS QA index rebuilt with {len(qa_index._metadata)} questions.")

        # 11. Ingest Chunks into Chroma Vector Store
        logger.info("Ingesting chunks into Chroma Vector Store...")
        store = get_store()
        embedder = get_embedder()

        # Batch embed and upsert
        all_db_chunks = PolicyChunkV2.query.all()
        versions_map = {v.id: v for v in PolicyVersion.query.all()}
        policies_map = {p.id: p for p in Policy.query.all()}

        batch_size = 128
        for i in range(0, len(all_db_chunks), batch_size):
            chunk_batch = all_db_chunks[i:i + batch_size]
            texts = [c.text for c in chunk_batch]
            embeddings = embedder.embed(texts)

            dicts = []
            for c in chunk_batch:
                pv = versions_map.get(c.version_id)
                pol = policies_map.get(c.policy_id)
                v_ledger = ledger.versions.get(c.version_id)

                p_name = pol.title if pol else "Policy"
                v_lbl = pv.version_label if pv else "v1.0"
                v_num = float(pv.version_num) if pv and pv.version_num is not None else 1.0
                is_act = bool(pv.is_active) if pv else True

                valid_from_ts = 0
                valid_to_ts = 32472144000
                if v_ledger and v_ledger.effective_start:
                    try:
                        valid_from_ts = int(datetime.strptime(v_ledger.effective_start, "%Y-%m-%d").timestamp())
                    except Exception:
                        pass
                if v_ledger and v_ledger.effective_end:
                    try:
                        valid_to_ts = int(datetime.strptime(v_ledger.effective_end, "%Y-%m-%d").timestamp())
                    except Exception:
                        pass
                elif pv and pv.effective_date:
                    try:
                        valid_from_ts = int(datetime.combine(pv.effective_date, datetime.min.time()).timestamp())
                    except Exception:
                        pass

                dicts.append({
                    "chunk_id": c.chunk_id,
                    "policy_id": int(c.policy_id),
                    "policy_name": p_name,
                    "version_id": int(c.version_id),
                    "version": v_lbl,
                    "version_num": v_num,
                    "is_active": is_act,
                    "is_current": is_act,
                    "valid_from_ts": valid_from_ts,
                    "valid_to_ts": valid_to_ts,
                    "section": c.section_path or "General",
                    "section_path": c.section_path or "General",
                    "page": c.page or 1,
                    "text": c.text
                })

            store.upsert_chunks(dicts, embeddings)
            logger.info(f"Upserted Chroma batch {min(i + batch_size, len(all_db_chunks))}/{len(all_db_chunks)}")

        logger.info(f"Chroma Vector Store ingestion complete: {store.count()} total chunks in collection.")
        logger.info("=== CHARACTERIZATION CORPUS INGESTION COMPLETE ===")

if __name__ == "__main__":
    seed_characterization_corpus()
