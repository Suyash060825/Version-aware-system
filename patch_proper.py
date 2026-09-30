import re
with open("scripts/test_policy_creation_lifecycle.py", "r") as f:
    content = f.read()
# Remove the diagnostic_advance patch from test_policy_creation_lifecycle.py!
content = re.sub(r'        cls.original_advance = rag.compiler.pipeline.KnowledgeCompilerPipeline._advance_stage.*?rag.compiler.pipeline.KnowledgeCompilerPipeline._advance_stage = diagnostic_advance\n', '', content, flags=re.DOTALL)
content = re.sub(r'        rag.compiler.pipeline.KnowledgeCompilerPipeline._advance_stage = cls.original_advance\n', '', content)

with open("scripts/test_policy_creation_lifecycle.py", "w") as f:
    f.write(content)

