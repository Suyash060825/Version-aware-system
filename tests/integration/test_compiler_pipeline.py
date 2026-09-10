import pytest
from app import create_app
from models import db, Policy, PolicyVersion, CompilationJob, CompilationStage, PolicyFact, PolicyChunkV2, User, Department

@pytest.fixture
def app():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

def test_compiler_pipeline(app):
    from rag.compiler.pipeline import KnowledgeCompilerPipeline
    
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
        content="Employees are entitled to 30 days of annual leave.\n\nThe notice period is 2 months.",
        created_by_id=u.id
    )
    db.session.add(v)
    db.session.commit()
    
    pipeline = KnowledgeCompilerPipeline()
    job = pipeline.compile(p.id, v.id)
    
    assert job.stage == CompilationStage.READY
    assert job.chunk_count > 0
    assert job.fact_count == 2
    
    facts = PolicyFact.query.all()
    assert len(facts) == 2
    
    chunks = PolicyChunkV2.query.all()
    assert len(chunks) > 0
    
    from models import CanonicalQuestion, CompiledAnswer
    qs = CanonicalQuestion.query.all()
    assert len(qs) > 0
    ans = CompiledAnswer.query.all()
    assert len(ans) > 0
