from rag.llm_provider import CascadeProvider, LLMResponse, LLMProvider
from rag.cache.semantic_cache import SemanticCache

class DummyProvider(LLMProvider):
    def __init__(self, fail=False, text="dummy"):
        self.fail = fail
        self.text = text
        self.called = False
    
    def generate(self, prompt, **kwargs):
        self.called = True
        if self.fail:
            return LLMResponse(text="", fallback=True, error="failed", model="dummy", usage={})
        return LLMResponse(text=self.text, fallback=False, model="dummy", usage={})
        
    def get_model_name(self): 
        return "dummy"
    
    def health_check(self):
        return True
        
    def embed(self, text):
        return [0.0] * 384

def test_cascade_failover():
    primary = DummyProvider(fail=True)
    secondary = DummyProvider(fail=False, text="secondary success")
    cascade = CascadeProvider(primary, secondary)
    
    resp = cascade.generate("hello")
    assert primary.called
    assert secondary.called
    assert resp.text == "secondary success"
    assert not resp.fallback

def test_cascade_use_secondary():
    primary = DummyProvider(fail=False, text="primary success")
    secondary = DummyProvider(fail=False, text="secondary success")
    cascade = CascadeProvider(primary, secondary)
    
    resp = cascade.generate("hello", use_secondary=True)
    assert not primary.called
    assert secondary.called
    assert resp.text == "secondary success"
    assert not resp.fallback

def test_semantic_cache():
    # Use local cache for test
    cache = SemanticCache()
    cache.use_redis = False
    vec = [0.1] * 384
    
    # put
    cache.put(vec, "test answer", [{"policy_id": "1", "version": "1.0", "section": "test"}], 1, ["Engineering"])
    
    # get match
    hit = cache.get(vec, ["Engineering"])
    assert hit is not None
    assert hit["answer"] == "test answer"
    
    # get miss dept
    miss = cache.get(vec, ["HR"])
    assert miss is None
    
    # get miss diff
    miss_diff = cache.get(vec, ["Engineering"], is_diff_query=True)
    assert miss_diff is None
