import os
import sys
import pytest

if __name__ == "__main__":
    sys.exit(pytest.main(["-q", "tests/integration/test_query_engine.py"]))
