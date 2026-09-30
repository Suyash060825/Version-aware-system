#!/bin/bash
set -e

echo "=== Hashing Production Artifacts ==="
find data/ -type f -not -name "ledger.db" -exec md5sum {} \; > before_hashes.txt

echo "=== Running Tests ==="
pytest tests/ -q || echo "tests/ failed"
pytest scripts/test_policy_creation_lifecycle.py -q || echo "scripts/ test failed"

echo "=== Hashing Production Artifacts Again ==="
find data/ -type f -not -name "ledger.db" -exec md5sum {} \; > after_hashes.txt

echo "=== Comparing Hashes ==="
if diff before_hashes.txt after_hashes.txt > diff.txt; then
    echo "SUCCESS: Production indexes remained byte-for-byte unchanged."
else
    echo "ERROR: Production artifacts changed!"
    cat diff.txt
fi
