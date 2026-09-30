from app import create_app
from models import db, CompilationJob, CompilationStage, Policy, User
app = create_app('testing')
with app.app_context():
    db.create_all()
    u = User(email="test@test.com", name="Test"); db.session.add(u); db.session.commit()
    p = Policy(title="Test", author_id=u.id); db.session.add(p); db.session.commit()
    job = CompilationJob(policy_id=p.id, version_id=1)
    db.session.add(job)
    db.session.commit()
    
    job.stage = "embedding"
    db.session.commit()
    
    try:
        raise ModuleNotFoundError("No module named 'torch'")
    except Exception as e:
        db.session.rollback()
        job.stage = "failed"
        job.error = str(e)
        db.session.commit()
        
    job2 = db.session.get(CompilationJob, job.id)
    print("Final stage:", job2.stage)
