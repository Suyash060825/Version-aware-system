"""
rag/authorization/evidence_filter.py
Enforces strict policy and chunk authorization before context construction.
"""
from typing import List, Dict, Any, Optional
from models import db, Policy, PolicyVersion, User, UserRole, PolicyStatus, ConfidentialityLevel

class EvidenceFilter:
    def __init__(self):
        pass

    def is_authorized_for_policy(self, user_or_scope: Optional[Any], policy: Policy, version: Optional[PolicyVersion] = None) -> bool:
        if not policy:
            return False

        conf = getattr(policy, "confidentiality", ConfidentialityLevel.INTERNAL)
        if hasattr(conf, "value"):
            conf = conf.value
        conf_str = str(conf).lower()

        status_val = policy.status.value if hasattr(policy.status, "value") else str(policy.status)
        status_str = str(status_val).lower()

        if user_or_scope is None:
            # Unauthenticated / default requests can only access active non-restricted, non-confidential policies
            return status_str in ("active", "published") and conf_str in ("public", "internal")

        # Case A: QueryScope object passed
        if type(user_or_scope).__name__ == "QueryScope" or hasattr(user_or_scope, "allowed_confidentiality"):
            scope = user_or_scope
            if scope.is_admin:
                return True

            if status_str not in ("active", "published"):
                if getattr(scope, "user_id", None) and policy.author_id == scope.user_id:
                    return True
                return False

            if scope.allowed_policy_ids is not None and policy.id not in scope.allowed_policy_ids:
                return False

            if conf_str not in scope.allowed_confidentiality:
                return False

            if policy.department_id is not None and scope.role not in ("admin", "executive", "legal", "hr"):
                if scope.department_ids and policy.department_id not in scope.department_ids:
                    return False

            return True

        # Case B: User model / proxy passed
        user = user_or_scope
        if user.is_admin() or user.can_manage_policies():
            return True

        if status_str not in ("active", "published"):
            if policy.author_id == getattr(user, "id", None):
                return True
            return False

        user_role = user.role.value if hasattr(user.role, "value") else str(user.role)
        user_role = user_role.lower()

        if conf_str == "restricted":
            if user_role not in ("admin", "executive", "legal"):
                return False
        elif conf_str == "confidential":
            if user_role not in ("admin", "executive", "legal", "hr"):
                user_dept = getattr(user, "department_id", None)
                if user_dept is not None and policy.department_id is not None and user_dept != policy.department_id:
                    return False

        # General Department restriction for standard employees
        if policy.department_id is not None and user_role not in ("admin", "executive", "legal", "hr"):
            user_dept = getattr(user, "department_id", None)
            if user_dept is not None and user_dept != policy.department_id:
                return False

        return True

    def filter_chunks(self, chunks: List[Dict[str, Any]], user_or_scope: Optional[Any]) -> List[Dict[str, Any]]:
        """Filter out any retrieved chunks the user/scope is not authorized to see."""
        if not chunks:
            return []
            
        if user_or_scope and getattr(user_or_scope, "is_admin", False):
            if callable(user_or_scope.is_admin):
                if user_or_scope.is_admin():
                    return chunks
            elif user_or_scope.is_admin:
                return chunks

        authorized = []
        policy_cache = {}

        for chunk in chunks:
            policy_id = chunk.get("policy_id")
            if not policy_id:
                continue

            try:
                p_id = int(policy_id)
            except (ValueError, TypeError):
                continue

            if p_id not in policy_cache:
                try:
                    from flask import has_app_context
                    if not has_app_context():
                        policy = None
                    else:
                        policy = db.session.get(Policy, p_id)
                except Exception:
                    policy = None
                policy_cache[p_id] = policy
            else:
                policy = policy_cache[p_id]

            if not policy:
                from flask import has_app_context
                if not has_app_context():
                    authorized.append(chunk)
                continue

            if self.is_authorized_for_policy(user_or_scope, policy):
                # Enrich chunk with authoritative policy title if missing
                if "policy_name" not in chunk or chunk["policy_name"] in ("Policy", None):
                    chunk["policy_name"] = policy.title
                authorized.append(chunk)

        return authorized

    def get_allowed_policy_ids(self, user_or_scope: Optional[Any]) -> Optional[List[int]]:
        """Return list of allowed policy IDs for retrieval pre-filtering, or None if no restriction."""
        if user_or_scope and getattr(user_or_scope, "is_admin", False):
            if callable(user_or_scope.is_admin) and user_or_scope.is_admin():
                return None
            elif not callable(user_or_scope.is_admin) and user_or_scope.is_admin:
                return None

        query = Policy.query.filter(Policy.status == PolicyStatus.ACTIVE)
        policies = query.all()
        return [p.id for p in policies if self.is_authorized_for_policy(user_or_scope, p)]
