# Security and QA Fixes Log

| Issue | Severity | Root Cause | Fix Applied | Test Added |
|-------|----------|------------|-------------|------------|
| Hardcoded default admin credential | Critical | `DEFAULT_ADMIN_PASSWORD` in `config.py` was loaded with a default fallback, allowing default logins if the environment variable wasn't explicitly changed. | Added a fast-fail check in `app.py` (`validate_production_env`) that raises an error on startup if `FLASK_ENV=production` and the password matches the default. | `test_production_default_password_fails()` |
| Hardcoded debug mode | High | `app.run(debug=True, port=5000)` was hardcoded in `app.py`'s main block. | Modified to `app.run(debug=app.config.get("DEBUG", False), port=5000)` ensuring production config disables Flask debugger. | `test_debug_mode_disabled_in_prod()` |
| Race condition in Active Policy Version | High | Only convention prevented multiple versions from being active simultaneously. | Added partial unique index to PostgreSQL schema using `__table_args__` on `PolicyVersion`. | `test_concurrent_policy_activation()` |
| Unpinned dependency versions | Medium | `requirements.txt` lacked version pinning. | Ran `pip-compile` to generate a strict `requirements.lock.txt`. | N/A |
| Vulnerable ChromaDB version | Medium | `pip-audit` detected CVE-2026-45829 in ChromaDB 1.5.9. | Documented as Accepted Risk because 1.5.9 is the highest available version for this package version range in this environment. RAG API internally shielded. | N/A |
