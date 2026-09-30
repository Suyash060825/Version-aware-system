import sys
import traceback
import rag.compiler.pipeline

old_compile = rag.compiler.pipeline.auto_compile_policy_version

def new_compile(policy_id, version_id):
    try:
        return old_compile(policy_id, version_id)
    except Exception as e:
        print("\n\n[DIAGNOSTIC] EXCEPTION IN AUTO_COMPILE:", str(e))
        traceback.print_exc(file=sys.stdout)
        raise e

rag.compiler.pipeline.auto_compile_policy_version = new_compile

old_advance = rag.compiler.pipeline.KnowledgeCompilerPipeline._advance_stage
def new_advance(self, job, target_stage, execute_fn):
    print(f"\n[DIAGNOSTIC] Advancing job {job.id} to {target_stage}. Previous stage: {job.stage}")
    try:
        execute_fn(job)
        from models import db
        db.session.commit()
    except Exception as execute_err:
        print(f"\n[DIAGNOSTIC] EXCEPTION IN EXECUTE_FN ({target_stage}):", str(execute_err))
        traceback.print_exc(file=sys.stdout)
        raise execute_err
    return job

rag.compiler.pipeline.KnowledgeCompilerPipeline._advance_stage = new_advance
