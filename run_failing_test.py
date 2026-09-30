import os
import tempfile
import sys
import pytest

if __name__ == "__main__":
    sys.exit(pytest.main(["-q", "tests/test_hardening_regression.py::test_canonical_qa_matcher_and_rejection_on_deleted_chunk"]))
