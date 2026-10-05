"""
tests/system_characterization/corpus/user_matrix.py
Comprehensive simulated user definitions and formal RBAC / clearance access control matrix.
Defines 32 distinct user profiles across 12 departments, 4 clearance levels, and 6 role archetypes.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

@dataclass(frozen=True)
class SimulatedUser:
    user_id: str
    name: str
    email: str
    department_id: int
    department_name: str
    role: str  # "admin", "executive", "legal", "hr", "manager", "employee", "contractor"
    clearance: str  # "public_only", "internal", "confidential", "restricted"
    grade_level: int  # 1 (Junior) to 5 (Executive)
    is_active: bool = True

    @property
    def allowed_confidentiality(self) -> List[str]:
        if self.clearance == "restricted":
            return ["public", "internal", "confidential", "restricted"]
        elif self.clearance == "confidential":
            return ["public", "internal", "confidential"]
        elif self.clearance == "internal":
            return ["public", "internal"]
        return ["public"]

    def is_admin(self) -> bool:
        return self.role == "admin"

    def can_manage_policies(self) -> bool:
        return self.role in ("admin", "hr", "manager")

    def can_view_confidential(self, policy_dept_id: Optional[int] = None) -> bool:
        if self.role in ("admin", "executive", "legal", "hr"):
            return True
        if self.clearance in ("confidential", "restricted"):
            if policy_dept_id is None:
                return True
            return self.department_id == policy_dept_id
        return False

    def can_view_restricted(self) -> bool:
        return self.role in ("admin", "executive", "legal") or self.clearance == "restricted"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "name": self.name,
            "email": self.email,
            "department_id": self.department_id,
            "department_name": self.department_name,
            "role": self.role,
            "clearance": self.clearance,
            "grade_level": self.grade_level,
            "is_active": self.is_active,
            "allowed_confidentiality": self.allowed_confidentiality
        }


# 12 Corporate Departments
DEPARTMENTS_CONFIG = [
    {"id": 1, "name": "Human Resources", "code": "HR"},
    {"id": 2, "name": "Engineering", "code": "ENG"},
    {"id": 3, "name": "Finance", "code": "FIN"},
    {"id": 4, "name": "Legal", "code": "LEG"},
    {"id": 5, "name": "Compliance", "code": "CMP"},
    {"id": 6, "name": "IT & Cybersecurity", "code": "IT"},
    {"id": 7, "name": "Procurement", "code": "PRC"},
    {"id": 8, "name": "Healthcare & Benefits", "code": "HCB"},
    {"id": 9, "name": "Travel & Expense", "code": "TRE"},
    {"id": 10, "name": "Facilities & Operations", "code": "OPS"},
    {"id": 11, "name": "Sales & Marketing", "code": "MKT"},
    {"id": 12, "name": "Executive & Governance", "code": "EXE"},
]


def build_user_pool() -> List[SimulatedUser]:
    users = [
        # Executive & Admin
        SimulatedUser("U-ADM-01", "Alex Administrator", "admin@veritas.internal", 6, "IT & Cybersecurity", "admin", "restricted", 5),
        SimulatedUser("U-EXE-01", "Eleanor Vance (CEO)", "ceo@veritas.internal", 12, "Executive & Governance", "executive", "restricted", 5),
        SimulatedUser("U-EXE-02", "Charles Montgomery (CFO)", "cfo@veritas.internal", 12, "Executive & Governance", "executive", "restricted", 5),
        
        # Legal & Compliance
        SimulatedUser("U-LEG-01", "Laura Croft (General Counsel)", "legal.lead@veritas.internal", 4, "Legal", "legal", "restricted", 4),
        SimulatedUser("U-LEG-02", "Liam Vance (Compliance Officer)", "compliance.officer@veritas.internal", 5, "Compliance", "legal", "restricted", 3),
        SimulatedUser("U-LEG-03", "Lucas Grey (Legal Associate)", "legal.assoc@veritas.internal", 4, "Legal", "employee", "confidential", 2),

        # Human Resources
        SimulatedUser("U-HR-01", "Hannah Rogers (HR Director)", "hr.dir@veritas.internal", 1, "Human Resources", "hr", "confidential", 4),
        SimulatedUser("U-HR-02", "Harry Potter (HR Generalist)", "hr.gen@veritas.internal", 1, "Human Resources", "hr", "internal", 2),
        SimulatedUser("U-HR-03", "Helen Keller (HR Specialist)", "hr.spec@veritas.internal", 1, "Human Resources", "employee", "internal", 2),

        # Finance
        SimulatedUser("U-FIN-01", "Fiona Gallagher (Finance VP)", "fin.vp@veritas.internal", 3, "Finance", "manager", "confidential", 4),
        SimulatedUser("U-FIN-02", "Frank Castle (Senior Accountant)", "fin.acc@veritas.internal", 3, "Finance", "employee", "confidential", 3),
        SimulatedUser("U-FIN-03", "Felix White (Payroll Analyst)", "payroll@veritas.internal", 3, "Finance", "employee", "internal", 2),

        # Engineering
        SimulatedUser("U-ENG-01", "Evan Wright (VP Engineering)", "eng.vp@veritas.internal", 2, "Engineering", "manager", "confidential", 4),
        SimulatedUser("U-ENG-02", "Emma Watson (Staff Software Engineer)", "eng.staff@veritas.internal", 2, "Engineering", "employee", "confidential", 3),
        SimulatedUser("U-ENG-03", "Ethan Hunt (Software Engineer II)", "eng.sde2@veritas.internal", 2, "Engineering", "employee", "internal", 2),
        SimulatedUser("U-ENG-04", "Ella Fitzgerald (Junior Dev)", "eng.junior@veritas.internal", 2, "Engineering", "employee", "internal", 1),

        # IT & Cybersecurity
        SimulatedUser("U-SEC-01", "Ian Malcolm (CISO)", "ciso@veritas.internal", 6, "IT & Cybersecurity", "manager", "restricted", 4),
        SimulatedUser("U-IT-01", "Isaac Clarke (IT Support Lead)", "it.lead@veritas.internal", 6, "IT & Cybersecurity", "manager", "confidential", 3),
        SimulatedUser("U-IT-02", "Ivy Pepper (Network Admin)", "it.net@veritas.internal", 6, "IT & Cybersecurity", "employee", "internal", 2),

        # Procurement
        SimulatedUser("U-PRC-01", "Peter Parker (Procurement Lead)", "procurement.lead@veritas.internal", 7, "Procurement", "manager", "confidential", 3),
        SimulatedUser("U-PRC-02", "Peggy Carter (Vendor Specialist)", "procurement.spec@veritas.internal", 7, "Procurement", "employee", "internal", 2),

        # Healthcare & Benefits
        SimulatedUser("U-HCB-01", "Harvey Dent (Benefits Manager)", "benefits.mgr@veritas.internal", 8, "Healthcare & Benefits", "manager", "confidential", 3),
        SimulatedUser("U-HCB-02", "Hannah Abbott (Wellness Coordinator)", "wellness@veritas.internal", 8, "Healthcare & Benefits", "employee", "internal", 2),

        # Travel & Expense
        SimulatedUser("U-TRE-01", "Tom Riddle (Travel Desk Manager)", "travel.mgr@veritas.internal", 9, "Travel & Expense", "manager", "confidential", 3),
        SimulatedUser("U-TRE-02", "Tara Maclay (Expense Auditor)", "expense.audit@veritas.internal", 9, "Travel & Expense", "employee", "internal", 2),

        # Facilities & Operations
        SimulatedUser("U-OPS-01", "Oliver Queen (Operations Lead)", "ops.lead@veritas.internal", 10, "Facilities & Operations", "manager", "confidential", 3),
        SimulatedUser("U-OPS-02", "Ophelia Price (Facilities Coordinator)", "facilities@veritas.internal", 10, "Facilities & Operations", "employee", "internal", 2),

        # Sales & Marketing
        SimulatedUser("U-MKT-01", "Samantha Jones (CMO)", "cmo@veritas.internal", 11, "Sales & Marketing", "manager", "confidential", 4),
        SimulatedUser("U-MKT-02", "Steve Rogers (Sales Director)", "sales.dir@veritas.internal", 11, "Sales & Marketing", "manager", "confidential", 3),
        SimulatedUser("U-MKT-03", "Sarah Connor (Marketing Specialist)", "mkt.spec@veritas.internal", 11, "Sales & Marketing", "employee", "internal", 2),

        # External Contractor & Low Clearance
        SimulatedUser("U-EXT-01", "Clark Kent (Contract Journalist/Vendor)", "vendor.ext@contractor.internal", 7, "Procurement", "contractor", "public_only", 1),
        SimulatedUser("U-EXT-02", "Bruce Wayne (Third-Party Security Auditor)", "auditor.ext@external.internal", 6, "IT & Cybersecurity", "contractor", "public_only", 1),
    ]
    return users


class AccessControlEvaluator:
    """
    Independent ground-truth evaluator for enterprise authorization decisions.
    Strictly verifies whether a given SimulatedUser is permitted to access a given policy chunk or version.
    """
    @staticmethod
    def is_authorized(user: SimulatedUser, policy_dept_id: Optional[int], policy_confidentiality: str, policy_status: str = "active") -> bool:
        if not user.is_active:
            return False

        conf = str(policy_confidentiality).lower()
        status = str(policy_status).lower()

        # Admin & Executive always authorized across all active policies
        if user.role in ("admin", "executive", "legal"):
            return True

        if status not in ("active", "published"):
            return False

        # Restricted confidentiality requires restricted clearance or admin/executive/legal
        if conf == "restricted":
            return user.clearance == "restricted" or user.role in ("admin", "executive", "legal")

        # Confidential policies: allowed if user has confidential/restricted clearance AND matching department (or HR)
        if conf == "confidential":
            if user.clearance not in ("confidential", "restricted"):
                return False
            if user.role == "hr":
                return True
            if policy_dept_id is None:
                return True
            return user.department_id == policy_dept_id

        # Internal policies: allowed for all active employees with internal+ clearance
        if conf == "internal":
            if user.clearance == "public_only":
                return False
            # Universal policies (dept_id is None) are open to all internal employees
            if policy_dept_id is None or user.role in ("hr", "legal", "admin", "executive"):
                return True
            # Department specific policies restricted to department unless universal
            return user.department_id == policy_dept_id

        # Public policies: open to all active users
        if conf == "public":
            return True

        return False
