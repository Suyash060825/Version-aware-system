import pytest
class A:
    def __init__(self, path="default"):
        print("A.__init__ path=", path)

@pytest.fixture(autouse=True)
def patch_it(monkeypatch):
    orig = A.__init__
    def new_init(self, path=None):
        print("new_init called with path=", path)
        if path is None:
            path = "patched"
        orig(self, path=path)
    monkeypatch.setattr(A, "__init__", new_init)

def test_a():
    a = A()
