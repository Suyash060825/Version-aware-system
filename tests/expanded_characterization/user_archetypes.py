"""
tests/expanded_characterization/user_archetypes.py
Defines 64 comprehensive simulated enterprise user archetypes across 24 departments, 8 role tiers, and 4 clearance levels.
Implements the multi-dimensional Access Control Evaluator supporting composite authorization predicates.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Set

@dataclass(frozen=True)
class EnterpriseUser:
    user_id: str
    name: str
    email: str
    department_id: int
    department_name: str
    department_code: str
    role: str  # "admin", "executive", "director", "manager", "senior_staff", "employee", "contractor", "auditor", "intern"
    clearance: str  # "public_only", "internal", "confidential", "restricted"
    grade_level: int  # 1 (Intern) to 6 (Executive / Board)
    special_permissions: List[str] = field(default_factory=list)
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

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "name": self.name,
            "email": self.email,
            "department_id": self.department_id,
            "department_name": self.department_name,
            "department_code": self.department_code,
            "role": self.role,
            "clearance": self.clearance,
            "grade_level": self.grade_level,
            "special_permissions": list(self.special_permissions),
            "is_active": self.is_active,
            "allowed_confidentiality": self.allowed_confidentiality
        }


class AccessControlEvaluator:
    """
    Evaluates role-based, department-based, clearance-based, and multi-restriction authorization.
    Fails closed on ambiguous or conflicting rules.
    """

    @staticmethod
    def is_authorized(
        user: EnterpriseUser,
        policy_department_id: int,
        policy_confidentiality: str,
        required_role: Optional[str] = None,
        required_min_grade: int = 1,
        allowed_roles: Optional[List[str]] = None,
        is_company_wide: bool = False
    ) -> bool:
        if not user.is_active:
            return False

        # 1. Clearance Check (Hierarchy: public < internal < confidential < restricted)
        clearance_hierarchy = {"public": 1, "internal": 2, "confidential": 3, "restricted": 4}
        user_clearance_level = clearance_hierarchy.get(user.clearance, 1)
        if user.clearance == "public_only":
            user_clearance_level = 1

        policy_level = clearance_hierarchy.get(policy_confidentiality.lower(), 2)
        if user_clearance_level < policy_level:
            return False

        # 2. Grade Level Check
        if user.grade_level < required_min_grade:
            return False

        # 3. Role Restriction Check
        if required_role and user.role != required_role:
            if user.role not in ("admin", "executive"):
                return False

        if allowed_roles and len(allowed_roles) > 0:
            if user.role not in allowed_roles and user.role not in ("admin", "executive"):
                return False

        # 4. Department Boundary Check
        # Global bypass roles: admin, executive, corporate auditor
        if user.role in ("admin", "executive", "auditor"):
            return True

        # Public / General company-wide policies are open to all departments
        if is_company_wide or policy_department_id == 0 or policy_confidentiality == "public":
            return True

        # Normal department match
        if user.department_id == policy_department_id:
            return True

        # Special permission cross-department grant
        dept_perm = f"cross_dept_access_{policy_department_id}"
        if dept_perm in user.special_permissions:
            return True

        return False


def build_enterprise_user_pool() -> List[EnterpriseUser]:
    """
    Constructs 64 heterogeneous simulated users across 24 corporate departments.
    """
    users = [
        # Executive & Admin Tier
        EnterpriseUser("U-EXE-001", "Eleanor Vance", "ceo@enterprise.internal", 23, "Executive Governance", "EXE", "executive", "restricted", 6, ["board_signoff", "m_and_a_access"]),
        EnterpriseUser("U-EXE-002", "Charles Montgomery", "cfo@enterprise.internal", 2, "Finance", "FIN", "executive", "restricted", 6, ["treasury_wire_override", "board_signoff"]),
        EnterpriseUser("U-EXE-003", "Dr. Aris Thorne", "cto@enterprise.internal", 11, "Engineering", "ENG", "executive", "restricted", 6, ["prod_infra_override"]),
        EnterpriseUser("U-ADM-001", "Alex Administrator", "sysadmin@enterprise.internal", 5, "IT", "IT", "admin", "restricted", 5, ["global_admin_override"]),
        EnterpriseUser("U-ADM-002", "Samantha Vance", "secadmin@enterprise.internal", 16, "Information Security", "INF", "admin", "restricted", 5, ["soc_master_override"]),

        # Legal & Compliance Officers
        EnterpriseUser("U-LEG-001", "Laura Croft", "general.counsel@enterprise.internal", 6, "Legal", "LEG", "director", "restricted", 5, ["court_subpoena_lead"]),
        EnterpriseUser("U-LEG-002", "Lucas Grey", "litigation.mgr@enterprise.internal", 6, "Legal", "LEG", "manager", "confidential", 4),
        EnterpriseUser("U-LEG-003", "Maya Lin", "contracts.assoc@enterprise.internal", 6, "Legal", "LEG", "senior_staff", "internal", 3),
        EnterpriseUser("U-CMP-001", "Marcus Aurelius", "chief.compliance@enterprise.internal", 7, "Compliance", "CMP", "director", "restricted", 5, ["aml_officer"]),
        EnterpriseUser("U-CMP-002", "Chloe Decker", "compliance.auditor@enterprise.internal", 7, "Compliance", "CMP", "auditor", "confidential", 4, ["cross_dept_audit"]),
        EnterpriseUser("U-CMP-003", "Daniel Faraday", "privacy.officer@enterprise.internal", 7, "Compliance", "CMP", "manager", "confidential", 4, ["gdpr_dpo"]),

        # Human Resources & Benefits
        EnterpriseUser("U-HR-001", "Hannah Rogers", "hr.vp@enterprise.internal", 1, "Human Resources", "HR", "director", "confidential", 5),
        EnterpriseUser("U-HR-002", "Harry Potter", "hr.manager@enterprise.internal", 1, "Human Resources", "HR", "manager", "confidential", 4),
        EnterpriseUser("U-HR-003", "Helen Keller", "hr.specialist@enterprise.internal", 1, "Human Resources", "HR", "employee", "internal", 2),
        EnterpriseUser("U-HR-004", "Hector Salamanca", "recruiter.staff@enterprise.internal", 1, "Human Resources", "HR", "employee", "internal", 2),
        EnterpriseUser("U-HCB-001", "Dr. Beverly Crusher", "benefits.lead@enterprise.internal", 8, "Healthcare & Benefits", "HCB", "manager", "confidential", 4),
        EnterpriseUser("U-HCB-002", "Ben Cartwright", "wellness.coord@enterprise.internal", 8, "Healthcare & Benefits", "HCB", "employee", "internal", 2),

        # Finance & Expense Management
        EnterpriseUser("U-FIN-001", "Fiona Gallagher", "controller@enterprise.internal", 2, "Finance", "FIN", "director", "confidential", 5),
        EnterpriseUser("U-FIN-002", "Frank Castle", "accounting.mgr@enterprise.internal", 2, "Finance", "FIN", "manager", "confidential", 4),
        EnterpriseUser("U-FIN-003", "Felicity Smoak", "tax.specialist@enterprise.internal", 2, "Finance", "FIN", "senior_staff", "confidential", 3),
        EnterpriseUser("U-FIN-004", "Farhan Akhtar", "payroll.lead@enterprise.internal", 2, "Finance", "FIN", "senior_staff", "confidential", 3),
        EnterpriseUser("U-EXP-001", "Edward Nygma", "expense.auditor@enterprise.internal", 19, "Expense Management", "EXP", "manager", "confidential", 4),
        EnterpriseUser("U-EXP-002", "Emma Watson", "expense.analyst@enterprise.internal", 19, "Expense Management", "EXP", "employee", "internal", 2),

        # Procurement & Vendor Management
        EnterpriseUser("U-PRC-001", "Peter Parker", "procurement.head@enterprise.internal", 3, "Procurement", "PRC", "director", "confidential", 5),
        EnterpriseUser("U-PRC-002", "Penny Lane", "sourcing.mgr@enterprise.internal", 3, "Procurement", "PRC", "manager", "internal", 4),
        EnterpriseUser("U-PRC-003", "Pavel Chekov", "buyer.staff@enterprise.internal", 3, "Procurement", "PRC", "employee", "internal", 2),
        EnterpriseUser("U-VND-001", "Victor Stone", "vendor.governance@enterprise.internal", 15, "Vendor Management", "VND", "manager", "confidential", 4),
        EnterpriseUser("U-VND-002", "Vanessa Ives", "vendor.auditor@enterprise.internal", 15, "Vendor Management", "VND", "senior_staff", "confidential", 3),

        # Security & Physical Access
        EnterpriseUser("U-SEC-001", "Steve Rogers", "cso@enterprise.internal", 4, "Security", "SEC", "director", "restricted", 5),
        EnterpriseUser("U-SEC-002", "Sarah Connor", "soc.manager@enterprise.internal", 4, "Security", "SEC", "manager", "restricted", 4),
        EnterpriseUser("U-SEC-003", "Scott Lang", "soc.analyst@enterprise.internal", 4, "Security", "SEC", "senior_staff", "confidential", 3),
        EnterpriseUser("U-PHY-001", "Phil Coulson", "facility.security@enterprise.internal", 17, "Physical Access", "PHY", "manager", "internal", 4),
        EnterpriseUser("U-PHY-002", "Pam Beesly", "badge.office@enterprise.internal", 17, "Physical Access", "PHY", "employee", "internal", 2),

        # IT & Information Security
        EnterpriseUser("U-IT-001", "Isaac Newton", "it.operations.vp@enterprise.internal", 5, "IT", "IT", "director", "confidential", 5),
        EnterpriseUser("U-IT-002", "Ian Malcolm", "helpdesk.manager@enterprise.internal", 5, "IT", "IT", "manager", "internal", 4),
        EnterpriseUser("U-IT-003", "Iris West", "endpoint.admin@enterprise.internal", 5, "IT", "IT", "senior_staff", "internal", 3),
        EnterpriseUser("U-INF-001", "Irene Adler", "ciso@enterprise.internal", 16, "Information Security", "INF", "director", "restricted", 5),
        EnterpriseUser("U-INF-002", "Inigo Montoya", "appsec.lead@enterprise.internal", 16, "Information Security", "INF", "manager", "restricted", 4),
        EnterpriseUser("U-INF-003", "Ivy Valentine", "threat.hunter@enterprise.internal", 16, "Information Security", "INF", "senior_staff", "restricted", 3),

        # Engineering & Technology
        EnterpriseUser("U-ENG-001", "Grace Hopper", "vp.engineering@enterprise.internal", 11, "Engineering", "ENG", "director", "confidential", 5),
        EnterpriseUser("U-ENG-002", "Gordon Freeman", "principal.architect@enterprise.internal", 11, "Engineering", "ENG", "senior_staff", "internal", 4),
        EnterpriseUser("U-ENG-003", "Gillian Anderson", "devops.lead@enterprise.internal", 11, "Engineering", "ENG", "manager", "internal", 4),
        EnterpriseUser("U-ENG-004", "Geordi La Forge", "software.engineer@enterprise.internal", 11, "Engineering", "ENG", "employee", "internal", 2),
        EnterpriseUser("U-ENG-005", "Gwen Stacy", "junior.dev@enterprise.internal", 11, "Engineering", "ENG", "employee", "internal", 1),

        # Sales & Marketing
        EnterpriseUser("U-SLS-001", "Sterling Cooper", "sales.vp@enterprise.internal", 12, "Sales", "SLS", "director", "confidential", 5),
        EnterpriseUser("U-SLS-002", "Saul Goodman", "enterprise.sales.mgr@enterprise.internal", 12, "Sales", "SLS", "manager", "confidential", 4),
        EnterpriseUser("U-SLS-003", "Sam Winchester", "account.exec@enterprise.internal", 12, "Sales", "SLS", "employee", "internal", 2),
        EnterpriseUser("U-MKT-001", "Madeline Albright", "cmo@enterprise.internal", 13, "Marketing", "MKT", "director", "internal", 5),
        EnterpriseUser("U-MKT-002", "Michael Scott", "brand.manager@enterprise.internal", 13, "Marketing", "MKT", "manager", "public", 4),
        EnterpriseUser("U-MKT-003", "Mia Wallace", "content.specialist@enterprise.internal", 13, "Marketing", "MKT", "employee", "public", 2),

        # Data Governance, Operations & Remote Work
        EnterpriseUser("U-DGV-001", "Dana Scully", "chief.data.officer@enterprise.internal", 14, "Data Governance", "DGV", "director", "restricted", 5),
        EnterpriseUser("U-DGV-002", "Dean Winchester", "data.steward@enterprise.internal", 14, "Data Governance", "DGV", "manager", "confidential", 4),
        EnterpriseUser("U-OPS-001", "Oliver Queen", "facilities.director@enterprise.internal", 10, "Operations", "OPS", "director", "internal", 5),
        EnterpriseUser("U-OPS-002", "Oscar Martinez", "real.estate.mgr@enterprise.internal", 10, "Operations", "OPS", "manager", "internal", 4),
        EnterpriseUser("U-RMT-001", "Rachel Green", "workplace.lead@enterprise.internal", 18, "Remote Work", "RMT", "manager", "public", 4),
        EnterpriseUser("U-TRV-001", "Tom Paris", "travel.desk.mgr@enterprise.internal", 9, "Travel", "TRV", "manager", "public", 4),
        EnterpriseUser("U-LVE-001", "Leonard Hofstadter", "attendance.officer@enterprise.internal", 20, "Leave & Attendance", "LVE", "manager", "public", 4),

        # Quality, Support & Research
        EnterpriseUser("U-QAD-001", "Quentin Coldwater", "quality.vp@enterprise.internal", 21, "Quality & Audit", "QAD", "director", "confidential", 5),
        EnterpriseUser("U-QAD-002", "Quinn Fabray", "iso.auditor@enterprise.internal", 21, "Quality & Audit", "QAD", "auditor", "confidential", 3, ["cross_dept_audit"]),
        EnterpriseUser("U-SUP-001", "Spock", "support.director@enterprise.internal", 22, "Customer Support", "SUP", "director", "internal", 5),
        EnterpriseUser("U-SUP-002", "Sulu Hikaru", "tier3.support.lead@enterprise.internal", 22, "Customer Support", "SUP", "senior_staff", "internal", 3),
        EnterpriseUser("U-RND-001", "Dr. Walter Bishop", "head.research@enterprise.internal", 24, "Research & Development", "RND", "director", "restricted", 6, ["patent_fast_track"]),
        EnterpriseUser("U-RND-002", "Dr. Emmett Brown", "senior.scientist@enterprise.internal", 24, "Research & Development", "RND", "senior_staff", "restricted", 4),

        # Contractors & External Third-Parties
        EnterpriseUser("U-CTR-001", "Carl Grimes (Vendor QA)", "contractor.qa@external.partner", 11, "Engineering", "ENG", "contractor", "internal", 2),
        EnterpriseUser("U-CTR-002", "Casey Jones (Field Tech)", "field.tech@vendor.partner", 5, "IT", "IT", "contractor", "public_only", 1),
        EnterpriseUser("U-GST-001", "Gary King (External Guest)", "guest.auditor@outside.org", 0, "External", "EXT", "contractor", "public_only", 1),
    ]
    return users
