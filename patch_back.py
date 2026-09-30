import re
with open("scripts/test_policy_creation_lifecycle.py", "r") as f:
    content = f.read()
content = content.replace('from app import create_app\nfrom models import', 'os.environ["DATABASE_URL"] = "sqlite:///data/ledger.db"\nfrom app import create_app\nfrom models import')
with open("scripts/test_policy_creation_lifecycle.py", "w") as f:
    f.write(content)
