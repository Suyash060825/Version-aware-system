import pytest
from app import create_app
from models import db, Policy, PolicyVersion, PolicyChunkV2, User

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
    
    p = Policy(policy_id="POL-001", title="Test Leave Policy", description="test", author_id=u.id)
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
    from rag.vectordb.chroma import get_store
    store = get_store()
    store._col.delete(where={"policy_id": {"$eq": str(p.id)}}); store.upsert_chunks([{
        "chunk_id": "chunk1",
        "policy_id": p.id,
        "version": str(v.id),
        "text": c.text,
        "is_active": True
    }], [[0.1] * 384])
    
    engine = get_query_engine()
    res = engine.answer("How many days of annual leave?")
    
    assert res.abstained is False
    assert res.route == "HYBRID_RAG"
    assert "30 days" in res.answer
