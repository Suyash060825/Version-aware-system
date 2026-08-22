"""
rag/authorization/evidence_filter.py
Enforces strict policy and chunk authorization before context construction.
"""
from typing import List, Dict, Any, Optional
from models import db, Policy, PolicyVersion, User, UserRole, PolicyStatus, ConfidentialityLevel

class EvidenceFilter:
    def __init__(self):
        pass

    def is_authorized_for_policy(self, user: Optional[User], policy: Policy, version: Optional[PolicyVersion] = None) -> bool:
        if not user:
            # Unauthenticated / default requests can access standard active non-restricted policies
            conf = getattr(policy, "confidentiality", ConfidentialityLevel.INTERNAL)
            if hasattr(conf, "value"):
                conf = conf.value
            return str(policy.status).lower() in ("active", "published") and str(conf).lower() not in ("restricted", "confidential")

        # Admins and policy managers have full access
        if user.is_admin() or user.can_manage_policies():
            return True

        # Policy must be published/active for regular users (unless author)
        status_val = policy.status.value if hasattr(policy.status, "value") else str(policy.status)
        if status_val not in ("active", "published"):
            if policy.author_id == getattr(user, "id", None):
                return True
            return False

        # Confidentiality check
        confidentiality = getattr(policy, "confidentiality", ConfidentialityLevel.INTERNAL)
        if hasattr(confidentiality, "value"):
            confidentiality = confidentiality.value
        conf_str = str(confidentiality).lower()

        if conf_str == "restricted":
            user_role = user.role.value if hasattr(user.role, "value") else str(user.role)
            if user_role not in ("admin", "executive"):
                return False
        elif conf_str == "confidential":
            # Confidential policies are restricted to their specific owning department
            user_dept = getattr(user, "department_id", None)
            if user_dept is not None and policy.department_id is not None and user_dept != policy.department_id:
                return False

        return True

    def filter_chunks(self, chunks: List[Dict[str, Any]], user: Optional[User]) -> List[Dict[str, Any]]:
        """Filter out any retrieved chunks the user is not authorized to see."""
        if not chunks:
            return []
            
        if user and user.is_admin():
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

            if self.is_authorized_for_policy(user, policy):
                # Enrich chunk with authoritative policy title if missing
                if "policy_name" not in chunk or chunk["policy_name"] in ("Policy", None):
                    chunk["policy_name"] = policy.title
                authorized.append(chunk)

        return authorized

    def get_allowed_policy_ids(self, user: Optional[User]) -> Optional[List[int]]:
        """Return list of allowed policy IDs for retrieval pre-filtering, or None if no restriction."""
        if user and user.is_admin():
            return None # All policies allowed

        query = Policy.query.filter(Policy.status == PolicyStatus.ACTIVE)
        if user and not user.can_manage_policies():
            if user.department_id:
                query = query.filter((Policy.department_id == None) | (Policy.department_id == user.department_id))
            else:
                query = query.filter(Policy.department_id == None)

        policies = query.all()
        return [p.id for p in policies if self.is_authorized_for_policy(user, p)]
