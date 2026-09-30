import sys
import traceback
from rag.compiler.pipeline import KnowledgeCompilerPipeline

original_advance = KnowledgeCompilerPipeline._advance_stage

def diagnostic_advance(self, job, target_stage, execute_fn):
    print(f"\n[DIAGNOSTIC] Advancing job {job.id} to {target_stage}")
    try:
        return original_advance(self, job, target_stage, execute_fn)
    except Exception as e:
        print(f"\n[DIAGNOSTIC EXCEPTION] in _advance_stage for {target_stage}:")
        traceback.print_exc(file=sys.stdout)
        raise

KnowledgeCompilerPipeline._advance_stage = diagnostic_advance
