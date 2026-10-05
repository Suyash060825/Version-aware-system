"""
rag/engine/query_scope.py
Structured immutable QueryScope object propagating authorization, tenant, department, and temporal version constraints across all RAG pipeline stages.
"""
from dataclasses import dataclass, field
from datetime import date
from typing import Optional, Tuple, List, Any

@dataclass(frozen=True)
class QueryScope:
    user_id: Optional[int] = None
    tenant_id: Optional[str] = None
    role: str = "employee"
    department_ids: Tuple[int, ...] = ()
    departments: Tuple[str, ...] = ()
    allowed_policy_ids: Optional[Tuple[int, ...]] = None
    allowed_version_ids: Optional[Tuple[int, ...]] = None
    target_date: Optional[date] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    historical: bool = False
    current_only: bool = True
    allowed_confidentiality: Tuple[str, ...] = ("public", "internal")
    is_admin: bool = False
    requested_version: Optional[str] = None

    @classmethod
    def from_user(cls, user: Any = None, temporal_ctx: Any = None, allowed_policy_ids: Optional[List[int]] = None) -> "QueryScope":
        tq = getattr(temporal_ctx, "temporal_query", None) if temporal_ctx else None
        target_d = getattr(temporal_ctx, "target_date", None) if temporal_ctx else None
        start_d = getattr(tq, "start_date", None) if tq else None
        end_d = getattr(tq, "end_date", None) if tq else None
        is_hist = getattr(temporal_ctx, "is_historic", False) if temporal_ctx else False
        req_ver = getattr(temporal_ctx, "requested_version", None) if temporal_ctx else None

        allowed_p_tuple = tuple(allowed_policy_ids) if allowed_policy_ids is not None else None

        if user is None:
            return cls(
                user_id=None,
                tenant_id=None,
                role="employee",
                department_ids=(),
                departments=(),
                allowed_policy_ids=allowed_p_tuple,
                allowed_version_ids=None,
                target_date=target_d,
                start_date=start_d,
                end_date=end_d,
                historical=is_hist,
                current_only=not is_hist,
                allowed_confidentiality=("public", "internal"),
                is_admin=False,
                requested_version=req_ver
            )

        is_adm = False
        if hasattr(user, "is_admin"):
            is_adm = user.is_admin() if callable(user.is_admin) else bool(user.is_admin)
        elif getattr(user, "role", "") in ("admin", "hr"):
            is_adm = True

        role = getattr(user, "role", "employee")
        if hasattr(role, "value"):
            role = role.value
        role = str(role).lower()

        user_id = getattr(user, "id", None)
        tenant_id = getattr(user, "tenant_id", None)

        depts = []
        dept_ids = []
        if getattr(user, "department", None):
            dept_name = getattr(user.department, "name", str(user.department))
            if dept_name:
                depts.append(dept_name)
        if getattr(user, "department_id", None) is not None:
            dept_ids.append(int(user.department_id))
            if not depts:
                depts.append(str(user.department_id))

        if hasattr(user, "allowed_confidentiality"):
            confidentiality = list(user.allowed_confidentiality)
        else:
            confidentiality = ["public", "internal"]
            if is_adm or role in ("admin", "executive", "legal"):
                confidentiality.extend(["confidential", "restricted"])
            elif role in ("hr", "manager"):
                confidentiality.append("confidential")

        return cls(
            user_id=user_id,
            tenant_id=tenant_id,
            role=role,
            department_ids=tuple(dept_ids),
            departments=tuple(depts),
            allowed_policy_ids=allowed_p_tuple,
            allowed_version_ids=None,
            target_date=target_d,
            start_date=start_d,
            end_date=end_d,
            historical=is_hist,
            current_only=not is_hist,
            allowed_confidentiality=tuple(confidentiality),
            is_admin=is_adm,
            requested_version=req_ver
        )
