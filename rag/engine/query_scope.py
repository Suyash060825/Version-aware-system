"""
rag/engine/query_scope.py
Structured QueryScope object propagating authorization, tenant, department, and temporal version constraints across all RAG pipeline stages.
"""
from dataclasses import dataclass, field
from datetime import date
from typing import Optional, List, Any

@dataclass
class QueryScope:
    tenant_id: Optional[str] = None
    user_id: Optional[int] = None
    role: str = "employee"
    departments: List[str] = field(default_factory=list)
    policy_ids: List[int] = field(default_factory=list)
    version_ids: List[int] = field(default_factory=list)
    target_date: Optional[date] = None
    allowed_confidentiality: List[str] = field(default_factory=lambda: ["public", "internal"])
    is_admin: bool = False
    is_historical: bool = False
    requested_version: Optional[str] = None

    @classmethod
    def from_user(cls, user: Any = None, temporal_ctx: Any = None) -> "QueryScope":
        if user is None:
            return cls(
                role="employee",
                departments=[],
                is_admin=False,
                target_date=getattr(temporal_ctx, "target_date", None) if temporal_ctx else None,
                is_historical=getattr(temporal_ctx, "is_historic", False) if temporal_ctx else False,
                version_ids=[temporal_ctx.version_id] if temporal_ctx and getattr(temporal_ctx, "version_id", None) else []
            )

        is_adm = False
        if hasattr(user, "is_admin"):
            is_adm = user.is_admin() if callable(user.is_admin) else bool(user.is_admin)
        elif getattr(user, "role", "") in ("admin", "hr"):
            is_adm = True

        role = getattr(user, "role", "employee")
        user_id = getattr(user, "id", None)

        depts = []
        if getattr(user, "department", None):
            dept_name = getattr(user.department, "name", str(user.department))
            if dept_name:
                depts.append(dept_name)
        elif getattr(user, "department_id", None):
            depts.append(str(user.department_id))

        confidentiality = ["public", "internal"]
        if is_adm or role in ("admin", "hr", "legal"):
            confidentiality.extend(["confidential", "restricted"])

        target_d = getattr(temporal_ctx, "target_date", None) if temporal_ctx else None
        is_hist = getattr(temporal_ctx, "is_historic", False) if temporal_ctx else False
        v_ids = [temporal_ctx.version_id] if temporal_ctx and getattr(temporal_ctx, "version_id", None) else []
        p_ids = [temporal_ctx.policy_id] if temporal_ctx and getattr(temporal_ctx, "policy_id", None) else []

        return cls(
            user_id=user_id,
            role=role,
            departments=depts,
            policy_ids=p_ids,
            version_ids=v_ids,
            target_date=target_d,
            allowed_confidentiality=confidentiality,
            is_admin=is_adm,
            is_historical=is_hist,
            requested_version=getattr(temporal_ctx, "requested_version", None) if temporal_ctx else None
        )
