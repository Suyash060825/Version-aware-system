import os
import pytest

os.environ["EMBEDDING_DEVICE"] = "cpu"
os.environ["RERANKER_DEVICE"] = "cpu"
os.environ["ENTAILMENT_ENABLED"] = "true"
