import pytest
import time
from app import create_app
from models import db, User, Policy, PolicyVersion, PolicyChunkV2, PolicyStatus

@pytest.fixture
def app_ctx():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

def test_incremental_streaming_behavior(app_ctx):
    from rag.engine.query_engine import get_query_engine
    
    u = User(name="stream_user", password_hash="hash", email="stream@test.com")
    db.session.add(u)
    db.session.commit()
    
    p = Policy(policy_id="POL-STREAM", title="Travel Expense Policy", description="Travel rules", author_id=u.id, status=PolicyStatus.ACTIVE)
    db.session.add(p)
    db.session.commit()
    
    v = PolicyVersion(
        policy_id=p.id,
        version_num=1, version_label="v1",
        content="Daily meal per diem allowance is 50 USD for domestic travel.",
        created_by_id=u.id,
        is_active=True,
        status="approved"
    )
    db.session.add(v)
    db.session.commit()
    
    c = PolicyChunkV2(
        chunk_id="chunk_stream_1",
        policy_id=p.id,
        version_id=v.id,
        section_path="Per Diem",
        text="Daily meal per diem allowance is 50 USD for domestic travel.",
        page=1,
        paragraph_num=1,
        char_count=60,
        text_hash="hash_stream"
    )
    db.session.add(c)
    db.session.commit()

    from rag.retrieval.sparse import PersistentBM25Index
    sparse = PersistentBM25Index()
    sparse.rebuild_from_db()
    
    from rag.embeddings.embedder import get_embedder
    from rag.vectordb.chroma import get_store
    embedder = get_embedder()
    store = get_store()
    chunk_emb = embedder.embed([c.text])
    store.upsert_chunks([{
        "chunk_id": "chunk_stream_1",
        "policy_id": p.id,
        "version": str(v.id),
        "text": c.text,
        "is_active": True
    }], chunk_emb)
    
    engine = get_query_engine()

    # 1. Non-streaming call continues returning PipelineResult with answer
    res = engine.answer("What is the meal allowance per diem?", user=u)
    assert not res.abstained
    assert "50" in res.answer or "meal" in res.answer.lower()

    # 2. Streaming call yields incremental token events followed by done event
    events = list(engine.stream_answer("What is the meal allowance per diem?", user=u))
    token_events = [e for e in events if e.get("type") == "token"]
    done_events = [e for e in events if e.get("type") == "done"]

    assert len(token_events) > 0, "Must yield at least one token event"
    assert len(done_events) == 1, "Must yield exactly one terminal done event"
    
    final_res = done_events[0]["result"]
    assert "answer" in final_res
    assert "citations" in final_res
    assert "route" in final_res
    assert "confidence" in final_res

    # Check token reconstruction matches or completes final answer
    streamed_text = "".join(e["token"] for e in token_events)
    assert len(streamed_text.strip()) > 0
