import pytest
from app import create_app
from models import db, Policy, PolicyVersion, PolicyChunkV2, User, PolicyStatus

@pytest.fixture
def app():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

def test_query_engine(app):
    from rag.engine.query_engine import get_query_engine
    
    # Create test data
    u = User(name="test", password_hash="hash", email="test@test.com")
    db.session.add(u)
    db.session.commit()
    
    p = Policy(policy_id="POL-001", title="Test Leave Policy", description="test", author_id=u.id, status=PolicyStatus.ACTIVE)
    db.session.add(p)
    db.session.commit()
    
    v = PolicyVersion(
        policy_id=p.id,
        version_num=1, version_label="v1",
        content="Employees are entitled to 30 days of annual leave.",
        created_by_id=u.id
    )
    db.session.add(v)
    db.session.commit()
    
    c = PolicyChunkV2(
        chunk_id="chunk1",
        policy_id=p.id,
        version_id=v.id,
        section_path="General",
        text="Employees are entitled to 30 days of annual leave.",
        page=1,
        paragraph_num=1,
        char_count=50,
        text_hash="hash"
    )
    db.session.add(c)
    db.session.commit()

    # Rebuild bm25 explicitly for testing
    from rag.retrieval.sparse import PersistentBM25Index
    sparse = PersistentBM25Index()
    sparse.rebuild_from_db()
    
    # Push to chroma
    from rag.embeddings.embedder import get_embedder
    from rag.vectordb.chroma import get_store
    embedder = get_embedder()
    store = get_store()
    chunk_emb = embedder.embed([c.text])
    store.upsert_chunks([{
        "chunk_id": "chunk1",
        "policy_id": p.id,
        "version": str(v.id),
        "text": c.text,
        "is_active": True
    }], chunk_emb)
    
    engine = get_query_engine()
    res = engine.answer("How many days of annual leave?")
    
    assert res.abstained is False
    assert "30 days" in res.answer or "30" in res.answer

    # Test stream_answer generator
    events = list(engine.stream_answer("How many days of annual leave?"))
    assert len(events) > 0
    token_events = [e for e in events if e["type"] == "token"]
    done_events = [e for e in events if e["type"] == "done"]
    assert len(token_events) > 0
    assert len(done_events) == 1
    assert done_events[0]["result"]["fallback"] is False
    assert "30" in done_events[0]["result"]["answer"]

    # Test MultiLevelCache
    from rag.cache.semantic_cache import get_cache
    cache = get_cache()
    q_vec = embedder.embed_query("How many days of annual leave?")
    cache.put(q_vec, "Test cached 30 days leave", [{"policy_id": p.id, "version": "1.0"}], 1)
    cached_hit = cache.get(q_vec)
    assert cached_hit is not None
    assert "30 days" in cached_hit["answer"]
