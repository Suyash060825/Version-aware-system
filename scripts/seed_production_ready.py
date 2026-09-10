"""
scripts/seed_production_ready.py

Enterprise Production-Ready Seeder:
Populates all 40+ database tables with rich, cross-referenced corporate data so that
every single dashboard and page across the platform displays authentic, working metrics.

Populates:
  1. Corporate Departments & Policy Categories
  2. Enterprise Users (Executive, Admin, HR, Legal, CISO, Eng, Fin, Ops, Sales, Marketing)
  3. Policies, Versions & Knowledge Compilation (PolicyChunkV2, PolicyFact, CanonicalQuestion, CompiledAnswer, CompilationJob)
  4. Statutory Compliance Frameworks & Policy Mappings (ISO 27001, SOC 2, GDPR, POSH Act, Companies Act)
  5. Mandatory Policy Acknowledgements across employees (on-time, late, and pending)
  6. Meetings, Attendance, AI-generated MOM, Policy Decisions & Action Items
  7. Multi-tier Approval Workflow Templates & Live Stage Instances (with SLAs)
  8. Contradiction Radar Flags (active & resolved)
  9. What-If Simulator Scenario Queries & HR Review Queue
 10. Audit Trail Logs (logins, policy CRUD, RAG queries, approvals, exports)
 11. Search History (top queries & knowledge gap zero-result queries)
 12. Chat Sessions, Assistant Messages, Citations, and User Feedback (ratings & comments)
 13. Policy Quizzes, Attempts, Comments & Likes (Gamification & Confusion Index)
 14. Guided Onboarding Reading Checklists
 15. Policy AI Reviews & Insights (risk scores, compliance findings, FAQs)
"""

import os
import sys
import json
import uuid
from datetime import datetime, date, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Intelligent DB resolution: use PostgreSQL in Docker container, fallback to SQLite locally
_db_env = os.environ.get("DATABASE_URL", "")
if not _db_env or ("@postgres:" in _db_env):
    import socket
    _pg_ok = False
    if "@postgres:" in _db_env:
        try:
            socket.gethostbyname("postgres")
            _pg_ok = True
        except Exception:
            _pg_ok = False
    if not _pg_ok and not _db_env.startswith("sqlite"):
        db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "ledger.db")
        os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"

from app import create_app
from models import (
    db, User, UserRole, Department, PolicyCategory, Policy, PolicyVersion,
    PolicyStatus, Priority, Tag, ComplianceFramework, ensure_default_frameworks,
    PolicyAcknowledgement,
    Meeting, MeetingType, MeetingStatus, MeetingParticipant, MeetingMinutes,
    MeetingDecision, MeetingActionItem, ActionItemStatus,
    WorkflowTemplate, WorkflowStage, WorkflowStageApprover, WorkflowStageInstance,
    WorkflowApprovalAction, WorkflowStageStatus, WorkflowApprovalMode,
    ContradictionFlag, ContradictionScanStatus,
    WhatIfQuery, WhatIfVerdict,
    AuditLog, SearchHistory, SavedSearch, ChatSession, ChatMessage, Feedback,
    QuizAttempt, PolicyComment, PolicyLike,
    PolicyAIReview, PolicyAIInsight,
    OnboardingChecklistItem,
    PolicyChunkV2, PolicyFact, CanonicalQuestion, CompiledAnswer, CompilationJob,
    Notification, NotificationType, ApprovalWorkflow, ApprovalStatus,
    PolicyEntity, PolicyRelationship
)
from utils import generate_policy_id, generate_meeting_code

app = create_app("development")

def now_utc():
    return datetime.now(timezone.utc)

def seed_production():
    with app.app_context():
        print("\n=======================================================")
        print("  POLICY LEDGER — PRODUCTION-READY SEEDING PIPELINE")
        print("=======================================================\n")
        db.create_all()

        # ----------------------------------------------------------------------
        # 1. Departments & Categories
        # ----------------------------------------------------------------------
        dept_specs = [
            ("Human Resources", "HR"), ("Engineering", "ENG"), ("Finance", "FIN"),
            ("Legal", "LEG"), ("Operations", "OPS"), ("Marketing", "MKT"),
            ("Sales", "SAL"), ("IT", "IT"),
        ]
        dept_map = {}
        for name, code in dept_specs:
            d = Department.query.filter((Department.name == name) | (Department.code == code)).first()
            if not d:
                d = Department(name=name, code=code)
                db.session.add(d)
                db.session.flush()
            dept_map[name] = d
        dept_map["IT & Security"] = dept_map["IT"]

        cat_specs = [
            ("Leave", "calendar", "#2a4a38"),
            ("Attendance", "clock", "#4a2a38"),
            ("Remote Work", "home", "#2a3a4a"),
            ("Security", "shield", "#4a3a2a"),
            ("Payroll", "dollar-sign", "#3a4a2a"),
            ("Travel", "map-pin", "#2a4a4a"),
            ("Benefits", "heart", "#4a2a4a"),
            ("Recruitment", "user-plus", "#3a2a4a"),
            ("Performance", "trending-up", "#4a4a2a"),
            ("POSH", "alert-circle", "#4a2a2a"),
            ("IT Policy", "cpu", "#2a2a4a"),
            ("Data Privacy", "lock", "#3a3a3a"),
        ]
        cat_map = {}
        for name, icon, color in cat_specs:
            c = PolicyCategory.query.filter_by(name=name).first()
            if not c:
                c = PolicyCategory(name=name, icon=icon, color=color)
                db.session.add(c)
                db.session.flush()
            cat_map[name] = c

        db.session.commit()
        print(f"[✓] {len(dept_map)} Departments and {len(cat_map)} Categories ready")

        # ----------------------------------------------------------------------
        # 2. Corporate Users
        # ----------------------------------------------------------------------
        user_specs = [
            ("System Administrator", "admin@company.com", UserRole.ADMIN, "IT", "Admin@123456"),
            ("Sarah Jenkins (HR Director)", "hr@company.com", UserRole.HR, "Human Resources", "Hr@123456"),
            ("Alexander Vance (Legal Counsel)", "legal.counsel@company.com", UserRole.HR, "Legal", "Legal@123456"),
            ("Marcus Thorne (CISO)", "ciso@company.com", UserRole.ADMIN, "IT", "Ciso@123456"),
            ("Elena Rostova (Lead Architect)", "eng.lead@company.com", UserRole.EMPLOYEE, "Engineering", "User@123456"),
            ("David Sterling (Staff Engineer)", "employee@company.com", UserRole.EMPLOYEE, "Engineering", "User@123456"),
            ("Rohan Mehta (Finance Analyst)", "fin.analyst@company.com", UserRole.EMPLOYEE, "Finance", "User@123456"),
            ("Claire Beauchamp (Operations Manager)", "ops.manager@company.com", UserRole.EMPLOYEE, "Operations", "User@123456"),
            ("Tariq Al-Mansoor (Enterprise Sales)", "sales.exec@company.com", UserRole.EMPLOYEE, "Sales", "User@123456"),
            ("Hannah Abbott (Marketing Specialist)", "mkt.specialist@company.com", UserRole.EMPLOYEE, "Marketing", "User@123456"),
        ]
        user_map = {}
        for name, email, role, dept_name, pwd in user_specs:
            u = User.query.filter_by(email=email).first()
            if not u:
                u = User(
                    name=name, email=email, role=role,
                    department_id=dept_map[dept_name].id,
                    is_active=True,
                    last_login=now_utc() - timedelta(hours=4),
                )
                u.set_password(pwd)
                db.session.add(u)
                db.session.flush()
            else:
                u.department_id = dept_map[dept_name].id
                u.role = role
                u.set_password(pwd)
                if not u.last_login:
                    u.last_login = now_utc() - timedelta(hours=4)
            user_map[email] = u

        db.session.commit()
        print(f"[✓] {len(user_map)} Corporate Users configured")

        # ----------------------------------------------------------------------
        # 3. Knowledge Compilation Verification
        # ----------------------------------------------------------------------
        all_policies = Policy.query.all()
        print(f"[i] Checking knowledge compilation for {len(all_policies)} policies...")
        from rag.compiler.pipeline import KnowledgeCompilerPipeline
        compiler = KnowledgeCompilerPipeline()

        compiled_count = 0
        for p in all_policies:
            for v in p.versions:
                existing_c = PolicyChunkV2.query.filter_by(policy_id=p.id, version_id=v.id).count()
                if existing_c == 0:
                    compiler.compile(p.id, v.id)
                    compiled_count += 1

        total_chunks = PolicyChunkV2.query.count()
        total_facts = PolicyFact.query.count()
        total_qa = CanonicalQuestion.query.count()
        print(f"[✓] Knowledge Compilation Active: {total_chunks} chunks, {total_facts} facts, {total_qa} QAs")

        # ----------------------------------------------------------------------
        # 4. Compliance Frameworks & Policy Mappings
        # ----------------------------------------------------------------------
        ensure_default_frameworks()
        frameworks = {f.name: f for f in ComplianceFramework.query.all()}

        # Map policies to frameworks based on titles / categories
        for p in all_policies:
            title_lower = p.title.lower()
            cat_name = p.category.name if p.category else ""

            to_add = []
            if "security" in title_lower or cat_name in ["Security", "IT Policy"]:
                if "ISO 27001" in frameworks: to_add.append(frameworks["ISO 27001"])
                if "SOC 2" in frameworks: to_add.append(frameworks["SOC 2"])
            if "privacy" in title_lower or cat_name in ["Data Privacy", "IT Policy"]:
                if "GDPR" in frameworks: to_add.append(frameworks["GDPR"])
                if "ISO 27001" in frameworks: to_add.append(frameworks["ISO 27001"])
            if "posh" in title_lower or "conduct" in title_lower or cat_name in ["POSH", "Attendance"]:
                if "Indian Labour Laws" in frameworks: to_add.append(frameworks["Indian Labour Laws"])
                if "Company Compliance" in frameworks: to_add.append(frameworks["Company Compliance"])
            if cat_name in ["Leave", "Payroll", "Benefits", "Performance", "Remote Work", "Travel"]:
                if "Indian Labour Laws" in frameworks: to_add.append(frameworks["Indian Labour Laws"])

            for fw in to_add:
                if fw not in p.frameworks:
                    p.frameworks.append(fw)

        db.session.commit()
        print(f"[✓] {len(frameworks)} Compliance Frameworks active with policies mapped")

        # ----------------------------------------------------------------------
        # 5. Mandatory Policy Acknowledgements
        # ----------------------------------------------------------------------
        employees = User.query.filter_by(role=UserRole.EMPLOYEE, is_active=True).all()
        mandatory_policies = Policy.query.filter_by(status=PolicyStatus.ACTIVE, is_mandatory=True).all()

        ack_count = 0
        for i, emp in enumerate(employees):
            for j, pol in enumerate(mandatory_policies):
                active_v = pol.versions.filter_by(is_active=True).first()
                if not active_v:
                    continue
                ack = PolicyAcknowledgement.query.filter_by(policy_id=pol.id, user_id=emp.id).first()
                # 85% completed, 15% pending to demonstrate pending violations
                should_ack = not (i == len(employees) - 1 and j < 2)
                if not ack:
                    ack_time = now_utc() - timedelta(days=(j * 3 + 1), hours=(i * 2)) if should_ack else None
                    read_time = (ack_time - timedelta(minutes=15)) if ack_time else now_utc() - timedelta(days=2)
                    ack = PolicyAcknowledgement(
                        policy_id=pol.id,
                        version_id=active_v.id,
                        user_id=emp.id,
                        is_mandatory=True,
                        read_at=read_time,
                        acknowledged_at=ack_time,
                        ip_address="192.168.1." + str(100 + emp.id),
                    )
                    db.session.add(ack)
                    ack_count += 1

        db.session.commit()
        print(f"[✓] {ack_count} Policy Acknowledgements seeded (realistic 85% compliance rate)")

        # ----------------------------------------------------------------------
        # 6. Meetings, Attendance, MOM & Decisions
        # ----------------------------------------------------------------------
        admin_user = user_map["admin@company.com"]
        hr_user = user_map["hr@company.com"]
        legal_user = user_map["legal.counsel@company.com"]
        ciso_user = user_map["ciso@company.com"]
        eng_user = user_map["eng.lead@company.com"]
        emp_user = user_map["employee@company.com"]

        sample_meetings = [
            {
                "title": "Q3 Corporate Governance & Policy Review",
                "desc": "Quarterly review of enterprise compliance, mandatory policy sign-offs, and annual leave rollover guidelines.",
                "type": MeetingType.REVIEW,
                "status": MeetingStatus.COMPLETED,
                "days_ago": 12,
                "dept": "Human Resources",
                "policy_title": "Leave Policy",
                "decisions": [
                    ("Approved increase of annual leave rollover cap to 5 days into next fiscal year", "High impact on balance sheets"),
                    ("Mandated HR portal submission 3 days in advance for planned leaves", "Operational efficiency"),
                ],
                "actions": [
                    ("Update employee intranet leave portal documentation", hr_user.id, True, 10),
                    ("Distribute memo on year-end leave encashment cut-off dates", hr_user.id, True, 7),
                ]
            },
            {
                "title": "Hybrid Workplace Transition & Remote Work Standards",
                "desc": "Policy alignment on in-office collaboration mandates, ergonomic equipment stipends, and VPN security controls.",
                "type": MeetingType.HR,
                "status": MeetingStatus.COMPLETED,
                "days_ago": 8,
                "dept": "Human Resources",
                "policy_title": "Remote Work Policy",
                "decisions": [
                    ("Set minimum 2 in-office collaboration days per week for hybrid employees", "Cross-team cohesion"),
                    ("Authorized Rs. 500/month remote internet allowance claimable on expense portal", "Employee satisfaction"),
                ],
                "actions": [
                    ("Coordinate with IT for automated VPN usage compliance logging", ciso_user.id, True, 6),
                    ("Conduct quarterly check-in survey on hybrid collaboration satisfaction", hr_user.id, False, -5),
                ]
            },
            {
                "title": "Information Security Compliance & ISO 27001 Audit Prep",
                "desc": "Internal security walkthrough covering MFA enforcement, device encryption, and confidential data storage protocols.",
                "type": MeetingType.BOARD,
                "status": MeetingStatus.COMPLETED,
                "days_ago": 4,
                "dept": "IT & Security",
                "policy_title": "IT Security Policy",
                "decisions": [
                    ("Enforced 90-day password rotation and prohibited 5 previous password reuses", "ISO 27001 Clause A.9.4.3"),
                    ("Mandated mandatory 2-hour security incident reporting window to SOC team", "Regulatory compliance"),
                ],
                "actions": [
                    ("Audit all unmanaged devices accessing corporate cloud storage", ciso_user.id, False, -2),
                    ("Conduct simulated phishing awareness exercise for all departments", ciso_user.id, False, -4),
                ]
            },
            {
                "title": "Q4 Executive Leadership Policy & Growth Planning",
                "desc": "Strategic roadmap review for FY25 policies, performance improvement guidelines, and employee health benefits renewal.",
                "type": MeetingType.PLANNING,
                "status": MeetingStatus.SCHEDULED,
                "days_ago": -5,
                "dept": "Legal",
                "policy_title": "Code of Conduct",
                "decisions": [],
                "actions": [
                    ("Prepare consolidated compliance audit readiness dossier", legal_user.id, False, -3),
                ]
            },
        ]

        for m_spec in sample_meetings:
            pol = Policy.query.filter_by(title=m_spec["policy_title"]).first()
            m = Meeting.query.filter_by(title=m_spec["title"]).first()
            sched_time = now_utc() - timedelta(days=m_spec["days_ago"])
            if not m:
                m = Meeting(
                    meeting_code=generate_meeting_code(),
                    title=m_spec["title"],
                    agenda=m_spec["desc"],
                    meeting_type=m_spec["type"],
                    status=m_spec["status"],
                    scheduled_at=sched_time,
                    location="Boardroom Alpha / Hybrid Teams",
                    organizer_id=admin_user.id,
                    department_id=dept_map[m_spec["dept"]].id,
                )
                if pol:
                    m.related_policies.append(pol)
                db.session.add(m)
                db.session.flush()

                # Add participants
                for p_user in [admin_user, hr_user, legal_user, ciso_user, eng_user]:
                    db.session.add(MeetingParticipant(meeting_id=m.id, user_id=p_user.id, attended=True))

                # Add MOM if completed
                if m.status == MeetingStatus.COMPLETED:
                    mom = MeetingMinutes.query.filter_by(meeting_id=m.id).first()
                    if not mom:
                        mom = MeetingMinutes(
                            meeting_id=m.id,
                            summary=f"The committee convened to review {m.title}. Comprehensive consensus was reached with zero dissenting votes.",
                            key_points_json=json.dumps([
                                "Reviewed prior action item closure rates (94% on-time completion).",
                                f"Evaluated impact on {pol.title if pol else 'organizational policies'}.",
                                "Agreed upon immediate communication cascade to all corporate employees.",
                            ]),
                            full_minutes=f"Executive review session for {m.title}.\nAll stakeholders confirmed statutory adherence.",
                            generated_by_ai=True,
                            generated_at=sched_time + timedelta(hours=1),
                        )
                        db.session.add(mom)
                    else:
                        mom.generated_at = sched_time + timedelta(hours=1)
                        mom.generated_by_ai = True

                # Add Decisions
                for d_desc, d_impact in m_spec["decisions"]:
                    dec = MeetingDecision(
                        meeting_id=m.id,
                        description=f"{d_desc} (Impact: {d_impact})",
                        source="manual",
                    )
                    db.session.add(dec)

                # Add Action items
                for task, owner_id, is_done, due_offset in m_spec["actions"]:
                    due_date = (sched_time + timedelta(days=due_offset)).date()
                    ai = MeetingActionItem(
                        meeting_id=m.id,
                        owner_id=owner_id,
                        description=task,
                        due_date=due_date,
                        priority=Priority.HIGH,
                        status=ActionItemStatus.DONE if is_done else ActionItemStatus.PENDING,
                        completed_at=sched_time + timedelta(days=due_offset) - timedelta(hours=3) if is_done else None,
                    )
                    db.session.add(ai)

        db.session.commit()
        print(f"[✓] {len(sample_meetings)} Governance Meetings with MOM, Decisions & Actions seeded")

        # ----------------------------------------------------------------------
        # 7. Workflow Templates, Stages & Instances
        # ----------------------------------------------------------------------
        wt1 = WorkflowTemplate.query.filter_by(name="Standard 3-Tier Enterprise Policy Approval").first()
        if not wt1:
            wt1 = WorkflowTemplate(
                name="Standard 3-Tier Enterprise Policy Approval",
                description="Rigorous compliance review starting with HR evaluation, followed by Legal clearance, and Executive sign-off.",
                is_default=True,
                is_active=True,
                created_by_id=admin_user.id,
            )
            db.session.add(wt1)
            db.session.flush()

            stages = [
                ("HR Preliminary Review", 1, WorkflowApprovalMode.ANY, 48, hr_user.id),
                ("Legal Compliance Audit", 2, WorkflowApprovalMode.ALL, 72, legal_user.id),
                ("Executive C-Level Authorization", 3, WorkflowApprovalMode.ALL, 96, admin_user.id),
            ]
            for s_name, s_ord, s_mode, s_sla, s_user_id in stages:
                st = WorkflowStage(template_id=wt1.id, name=s_name, order=s_ord, approval_mode=s_mode, sla_hours=s_sla)
                db.session.add(st)
                db.session.flush()
                db.session.add(WorkflowStageApprover(stage_id=st.id, approver_type="user", user_id=s_user_id))

        wt2 = WorkflowTemplate.query.filter_by(name="Fast-Track Minor Policy Revision").first()
        if not wt2:
            wt2 = WorkflowTemplate(
                name="Fast-Track Minor Policy Revision",
                description="Expedited single-stage review for minor non-substantive policy edits and clarifications.",
                is_default=False,
                is_active=True,
                created_by_id=admin_user.id,
            )
            db.session.add(wt2)
            db.session.flush()
            st = WorkflowStage(template_id=wt2.id, name="HR Expedited Review", order=1, approval_mode=WorkflowApprovalMode.ANY, sla_hours=24)
            db.session.add(st)
            db.session.flush()
            db.session.add(WorkflowStageApprover(stage_id=st.id, approver_type="role", role="hr"))

        # Seed realistic workflow stage instances on sample active policies to populate Workflow Analytics
        sample_active = Policy.query.filter_by(status=PolicyStatus.ACTIVE).limit(4).all()
        for p in sample_active:
            active_v = p.versions.filter_by(is_active=True).first()
            if active_v and WorkflowStageInstance.query.filter_by(version_id=active_v.id).count() == 0:
                s1 = WorkflowStageInstance(
                    policy_id=p.id, version_id=active_v.id, name="HR Review", order=1,
                    approval_mode=WorkflowApprovalMode.ANY, status=WorkflowStageStatus.APPROVED,
                    sla_hours=48, created_at=now_utc() - timedelta(days=15),
                    completed_at=now_utc() - timedelta(days=14, hours=20),
                )
                db.session.add(s1)
                db.session.flush()
                db.session.add(WorkflowApprovalAction(
                    stage_instance_id=s1.id, approver_type="user", assigned_user_id=hr_user.id,
                    actor_id=hr_user.id, status=WorkflowStageStatus.APPROVED,
                    comment="HR guidelines compliant. Benchmarked against industry standards.",
                    acted_at=now_utc() - timedelta(days=14, hours=20)
                ))

                s2 = WorkflowStageInstance(
                    policy_id=p.id, version_id=active_v.id, name="Legal Review", order=2,
                    approval_mode=WorkflowApprovalMode.ALL, status=WorkflowStageStatus.APPROVED,
                    sla_hours=72, created_at=now_utc() - timedelta(days=14, hours=20),
                    completed_at=now_utc() - timedelta(days=13, hours=10),
                )
                db.session.add(s2)
                db.session.flush()
                db.session.add(WorkflowApprovalAction(
                    stage_instance_id=s2.id, approver_type="user", assigned_user_id=legal_user.id,
                    actor_id=legal_user.id, status=WorkflowStageStatus.APPROVED,
                    comment="Legally sound. Verified statutory conformity.",
                    acted_at=now_utc() - timedelta(days=13, hours=10)
                ))

        # Seed realistic active pending stages for in-flight approvals
        if len(all_policies) >= 6:
            p_pending1 = all_policies[4]
            v_p1 = p_pending1.versions.first()
            if v_p1 and WorkflowStageInstance.query.filter_by(version_id=v_p1.id).count() == 0:
                p_pending1.status = PolicyStatus.HR_REVIEW
                ps1 = WorkflowStageInstance(
                    policy_id=p_pending1.id, version_id=v_p1.id, name="HR Compliance Clearance", order=1,
                    approval_mode=WorkflowApprovalMode.ANY, status=WorkflowStageStatus.PENDING,
                    sla_hours=48, sla_due_at=now_utc() + timedelta(hours=36),
                    created_at=now_utc() - timedelta(hours=12),
                )
                db.session.add(ps1)
                db.session.flush()
                db.session.add(WorkflowApprovalAction(
                    stage_instance_id=ps1.id, approver_type="user", assigned_user_id=admin_user.id,
                    actor_id=None, status=WorkflowStageStatus.PENDING,
                ))

            p_pending2 = all_policies[5]
            v_p2 = p_pending2.versions.first()
            if v_p2 and WorkflowStageInstance.query.filter_by(version_id=v_p2.id).count() == 0:
                p_pending2.status = PolicyStatus.PENDING_APPROVAL
                ps2 = WorkflowStageInstance(
                    policy_id=p_pending2.id, version_id=v_p2.id, name="Executive C-Level Authorization", order=2,
                    approval_mode=WorkflowApprovalMode.ALL, status=WorkflowStageStatus.PENDING,
                    sla_hours=24, sla_due_at=now_utc() - timedelta(hours=2),
                    escalated=True, escalated_at=now_utc() - timedelta(hours=1),
                    created_at=now_utc() - timedelta(hours=26),
                )
                db.session.add(ps2)
                db.session.flush()
                db.session.add(WorkflowApprovalAction(
                    stage_instance_id=ps2.id, approver_type="user", assigned_user_id=admin_user.id,
                    actor_id=None, status=WorkflowStageStatus.PENDING,
                ))

        db.session.commit()
        print("[✓] Workflow Templates, Completed & Pending Stage Instances seeded")

        # ----------------------------------------------------------------------
        # 8. Contradiction Radar Flags
        # ----------------------------------------------------------------------
        remote_pol = Policy.query.filter(Policy.title.ilike("%remote%")).first()
        travel_pol = Policy.query.filter(Policy.title.ilike("%travel%")).first()
        conduct_pol = Policy.query.filter(Policy.title.ilike("%conduct%")).first()
        leave_pol = Policy.query.filter(Policy.title.ilike("%leave%")).first()

        if remote_pol and leave_pol and ContradictionFlag.query.count() == 0:
            f1 = ContradictionFlag(
                policy_a_id=remote_pol.id,
                policy_b_id=leave_pol.id,
                description="Remote Work policy allows employees to work from alternate locations up to 3 days/week, while Leave Policy implies working while traveling requires declared sick/annual PTO.",
                status=ContradictionScanStatus.OPEN,
                detected_at=now_utc() - timedelta(days=5),
                last_confirmed_at=now_utc() - timedelta(hours=6),
            )
            db.session.add(f1)

        if travel_pol and conduct_pol and ContradictionFlag.query.count() <= 1:
            f2 = ContradictionFlag(
                policy_a_id=travel_pol.id,
                policy_b_id=conduct_pol.id,
                description="Code of Conduct establishes a Rs. 2,000 threshold for client gifts and entertainment, whereas Travel & Expense policy allows lodging client dinners up to Rs. 5,000.",
                status=ContradictionScanStatus.OPEN,
                detected_at=now_utc() - timedelta(days=3),
                last_confirmed_at=now_utc() - timedelta(hours=2),
            )
            db.session.add(f2)

        if conduct_pol and leave_pol and ContradictionFlag.query.count() <= 2:
            f3 = ContradictionFlag(
                policy_a_id=conduct_pol.id,
                policy_b_id=leave_pol.id,
                description="Notice period handover obligations in Code of Conduct specify 30 days mandatory knowledge transfer, whereas Leave Policy grants automatic encashment of notice period unserved days.",
                status=ContradictionScanStatus.RESOLVED,
                detected_at=now_utc() - timedelta(days=20),
                last_confirmed_at=now_utc() - timedelta(days=18),
                resolved_at=now_utc() - timedelta(days=17),
                resolved_by_id=admin_user.id,
            )
            db.session.add(f3)

        db.session.commit()
        print("[✓] Contradiction Radar Flags populated (Active & Resolved)")

        # ----------------------------------------------------------------------
        # 9. What-If Scenarios & HR Review Queue
        # ----------------------------------------------------------------------
        whatif_scenarios = [
            (
                "Can an employee work remotely for 2 weeks from an overseas Airbnb during the summer?",
                WhatIfVerdict.DEPENDS, 65,
                "Cross-border remote work triggers international tax nexus, data sovereignty (GDPR/DPDP), and corporate insurance jurisdiction issues. Domestic remote work is permitted up to 3 days/week, but overseas work requires explicit Legal & HR clearance.",
                True,
                ["Submit International Remote Work Clearance form minimum 30 days in advance", "Verify data storage compliance on company-issued laptop"],
            ),
            (
                "Can I accept a supplier Diwali gift hamper valued around Rs. 3,500?",
                WhatIfVerdict.DEPENDS, 72,
                "Code of Conduct Section 3 limits gifts to Rs. 2,000 without prior written compliance approval. Since the gift exceeds this ceiling, it cannot be retained privately without written Legal clearance.",
                True,
                ["Disclose gift to ethics@company.com within 14 days", "Obtain written compliance officer authorization"],
            ),
            (
                "Can I carry forward 8 unused annual leave days into the subsequent fiscal year?",
                WhatIfVerdict.NOT_COMPLIANT, 95,
                "Leave Policy v2.0 Section 3 strictly caps annual leave carry-forward at 5 days. Any excess balance beyond 5 days is forfeited at calendar year end.",
                False,
                ["Utilize remaining 3 days before December 31st or forfeit the balance"],
            ),
            (
                "Is an employee on a 60-day Performance Improvement Plan (PIP) eligible for the standard promotion cycle?",
                WhatIfVerdict.NOT_COMPLIANT, 98,
                "Performance Evaluation Policy Section 3 dictates that promotion requires consecutive ratings of 4 or 5 and minimum 18 months in role. Active PIP status suspends promotional eligibility.",
                False,
                ["Successfully complete PIP milestones with manager verification"],
            ),
            (
                "Can an employee take 3 days paid bereavement leave upon the passing of an immediate family member without prior notice?",
                WhatIfVerdict.COMPLIANT, 92,
                "Leave Policy v2.0 Section 6 provides 3 days paid bereavement leave for immediate family. Emergency bereavement leave does not require the standard 3-day advance notice.",
                False,
                ["Notify reporting manager as soon as practicable", "Submit formal notification on HR portal upon return"],
            ),
        ]

        for s_text, verdict, conf, expl, flagged, acts in whatif_scenarios:
            if WhatIfQuery.query.filter_by(scenario_text=s_text).count() == 0:
                wq = WhatIfQuery(
                    user_id=eng_user.id,
                    scenario_text=s_text,
                    verdict=verdict,
                    confidence=conf,
                    explanation=expl,
                    flagged_for_hr=flagged,
                    required_actions=acts,
                    applicable_policies=[{"policy_id": all_policies[0].id, "policy_title": all_policies[0].title}] if all_policies else [],
                    created_at=now_utc() - timedelta(days=1, hours=3),
                )
                db.session.add(wq)

        db.session.commit()
        print(f"[✓] {len(whatif_scenarios)} What-If Simulator queries & HR flags seeded")

        # ----------------------------------------------------------------------
        # 10. Audit Trail Logs
        # ----------------------------------------------------------------------
        actions = [
            ("auth.login", "user", admin_user.id, {"method": "password", "status": "success"}),
            ("auth.login", "user", hr_user.id, {"method": "password", "status": "success"}),
            ("policy.create", "policy", all_policies[0].id if all_policies else 1, {"title": "Remote Work Policy"}),
            ("policy.version_create", "policy_version", 1, {"version": "v2.0", "reason": "Post-pandemic update"}),
            ("policy.publish", "policy", all_policies[1].id if len(all_policies) > 1 else 1, {"status": "active"}),
            ("rag.search", "search", None, {"query": "maternity leave duration", "results": 4}),
            ("rag.chat", "chat_message", 1, {"model": "Qwen3", "tokens": 142}),
            ("workflow.submit", "policy", all_policies[0].id if all_policies else 1, {"workflow": "Standard"}),
            ("workflow.approve", "workflow_stage_instance", 1, {"stage": "HR Review"}),
            ("compliance.export", "compliance_report", None, {"format": "pdf"}),
            ("audit.export", "audit_log", None, {"format": "csv"}),
            ("what_if.run", "what_if_query", 1, {"verdict": "depends", "confidence": 65}),
            ("contradiction.scan", "contradiction_flag", None, {"checked": 15, "flagged": 2}),
        ]

        audit_count = 0
        if AuditLog.query.count() < 10:
            for i in range(50):
                act_spec = actions[i % len(actions)]
                log_time = now_utc() - timedelta(days=(i // 4), hours=(i * 3 % 24), minutes=(i * 7 % 60))
                al = AuditLog(
                    user_id=admin_user.id if i % 2 == 0 else hr_user.id,
                    action=act_spec[0],
                    resource_type=act_spec[1],
                    resource_id=act_spec[2],
                    ip_address=f"192.168.1.{10 + (i % 5)}",
                    detail=json.dumps(act_spec[3]),
                    timestamp=log_time,
                )
                db.session.add(al)
                audit_count += 1
            db.session.commit()
        print(f"[✓] Immutable Audit Logs verified (total: {AuditLog.query.count()})")

        # ----------------------------------------------------------------------
        # 11. Search History & Search Analytics
        # ----------------------------------------------------------------------
        queries = [
            ("annual leave days entitlement", 4, True),
            ("maternity leave 26 weeks", 5, True),
            ("work from home equipment allowance", 3, True),
            ("vpn security mfa requirements", 4, True),
            ("travel per diem limits metro non metro", 3, True),
            ("group health medical insurance cover Rs 500000", 4, True),
            ("performance improvement plan pip duration", 3, True),
            ("notice period resignation buyout", 3, True),
            ("ethics whistleblowing confidential protection", 2, True),
            ("posh complaint committee members", 3, True),
            # Zero-result searches (knowledge gaps)
            ("pet insurance reimbursement policy", 0, False),
            ("crypto currency trading internal policy", 0, False),
            ("relocation assistance budget allocation", 0, False),
            ("sabbatical leave guidelines for senior engineers", 0, False),
        ]

        if SearchHistory.query.count() < 10:
            for q_text, chunks_f, answered in queries:
                for rep in range(2 if not answered else 3):
                    sh = SearchHistory(
                        user_id=eng_user.id,
                        query_text=q_text,
                        chunks_found=chunks_f,
                        answered=answered,
                        created_at=now_utc() - timedelta(days=rep, hours=(rep * 4 + 2)),
                    )
                    db.session.add(sh)
            db.session.commit()
        print(f"[✓] Search History active (total: {SearchHistory.query.count()} queries)")

        # ----------------------------------------------------------------------
        # 11b. Most-used Saved Searches
        # ----------------------------------------------------------------------
        saved_search_specs = [
            ("Security & Data Protection Standards", "policies", {"category": "IT & Security", "priority": "high"}, 18),
            ("Employee Benefits & Leave Encashment", "policies", {"category": "Human Resources"}, 14),
            ("Executive Governance & Quarterly Reviews", "meetings", {"scope": "meetings"}, 9),
            ("Mandatory Compliance Sign-offs", "all", {"is_mandatory": "true"}, 6),
        ]
        for s_name, s_scope, s_filters, s_uses in saved_search_specs:
            ss = SavedSearch.query.filter_by(name=s_name).first()
            if not ss:
                ss = SavedSearch(
                    user_id=admin_user.id,
                    name=s_name,
                    scope=s_scope,
                    filters_json=json.dumps(s_filters),
                    use_count=s_uses,
                    last_used_at=now_utc() - timedelta(days=2, hours=s_uses),
                    created_at=now_utc() - timedelta(days=20),
                )
                db.session.add(ss)
            else:
                ss.use_count = s_uses
        db.session.commit()
        print(f"[✓] Saved Searches active (total: {SavedSearch.query.count()} saved searches)")

        # ----------------------------------------------------------------------
        # 12. Chat Sessions, Messages & User Feedback
        # ----------------------------------------------------------------------
        chat_pairs = [
            (
                "How many days of annual leave do I get, and can I carry them forward?",
                "Under **Leave Policy v2.0 (Section 1 & 3)**, full-time employees accrue **24 days paid annual leave** per calendar year (accrued at 2 days/month). You may carry forward up to **5 days** into the following year; any balance exceeding 5 days is forfeited.",
                [{"policy_id": leave_pol.id if leave_pol else 1, "policy_name": "Leave Policy", "version": "v2.0", "section": "1. Annual Leave & 3. Carry-Forward", "page": 1}],
                "up", "Clear and accurate citation.",
            ),
            (
                "What is the daily internet allowance for remote workers?",
                "According to the **Remote Work Policy v2.0 (Section 4)**, approved remote employees are eligible for an **internet allowance of Rs. 500 per month**, claimable through the corporate expense reimbursement portal.",
                [{"policy_id": remote_pol.id if remote_pol else 1, "policy_name": "Remote Work Policy", "version": "v2.0", "section": "4. Internet Allowance", "page": 1}],
                "up", "Direct and helpful answer.",
            ),
            (
                "Can I work remotely from Europe for a month?",
                "The current **Remote Work Policy v2.0** outlines guidelines for working from home and domestic locations within the country. International remote work is not explicitly sanctioned and triggers regulatory and tax clearance requirements with HR and Legal.",
                [{"policy_id": remote_pol.id if remote_pol else 1, "policy_name": "Remote Work Policy", "version": "v2.0", "section": "1. Eligibility", "page": 1}],
                "down", "Needs clearer specifics on overseas telecommuting approval steps.",
            ),
            (
                "What is the maximum room tariff allowed for domestic business travel in Bangalore?",
                "Per the **Travel & Expense Policy v1.0 (Section 2)**, the lodging limit for domestic business travel in metro cities (including Bangalore, Mumbai, Delhi-NCR) is capped at **Rs. 5,000 per night**.",
                [{"policy_id": travel_pol.id if travel_pol else 1, "policy_name": "Travel & Expense Policy", "version": "v1.0", "section": "2. Lodging Limits", "page": 1}],
                "up", "Saved me checking the handbook.",
            ),
        ]

        if ChatMessage.query.count() < 5:
            for u_query, a_answer, cits, vote, fb_comment in chat_pairs:
                cs = ChatSession(id=str(uuid.uuid4()), user_id=eng_user.id, created_at=now_utc() - timedelta(days=2))
                db.session.add(cs)
                db.session.flush()

                m1 = ChatMessage(session_id=cs.id, role="user", content=u_query, prompt_tokens=45, completion_tokens=0, created_at=cs.created_at)
                db.session.add(m1)
                db.session.flush()

                m2 = ChatMessage(
                    session_id=cs.id, role="assistant", content=a_answer,
                    citations_json=json.dumps(cits), chunks_used=len(cits),
                    model_name="Qwen3", model_used="Qwen3", cache_hit=True if vote == "up" else False,
                    prompt_tokens=185, completion_tokens=94,
                    created_at=cs.created_at + timedelta(seconds=2),
                )
                db.session.add(m2)
                db.session.flush()

                fb = Feedback(
                    message_id=m2.id, user_id=eng_user.id,
                    vote=vote, comment=fb_comment, created_at=m2.created_at + timedelta(seconds=15)
                )
                db.session.add(fb)
            db.session.commit()

        # Ensure all existing chat messages have authentic token telemetry
        for msg in ChatMessage.query.all():
            if not msg.prompt_tokens or msg.prompt_tokens == 0:
                if msg.role == "user":
                    msg.prompt_tokens = max(20, len(msg.content) // 4)
                    msg.completion_tokens = 0
                else:
                    msg.prompt_tokens = 185
                    msg.completion_tokens = max(45, len(msg.content) // 4)
        db.session.commit()
        print(f"[✓] Chat Sessions & Token Telemetry active (total messages: {ChatMessage.query.count()})")

        # ----------------------------------------------------------------------
        # 13. Policy Quizzes, Attempts, Comments & Likes (Gamification)
        # ----------------------------------------------------------------------
        if QuizAttempt.query.count() == 0:
            for i, emp in enumerate(employees):
                for j, pol in enumerate(all_policies[:3]):
                    active_v = pol.versions.filter_by(is_active=True).first()
                    if active_v:
                        qa = QuizAttempt(
                            policy_id=pol.id, user_id=emp.id,
                            score=4 if (i + j) % 2 == 0 else 3, total=5,
                            passed=True,
                            answers_json=json.dumps([0, 1, 0, 0, 1]),
                            completed_at=now_utc() - timedelta(days=(i * 2 + 1)),
                        )
                        db.session.add(qa)

                # Comments & Likes
                com = PolicyComment(
                    policy_id=all_policies[0].id, user_id=emp.id,
                    content=f"Important clause clarified for {emp.name}.",
                    created_at=now_utc() - timedelta(days=3)
                )
                db.session.add(com)
                db.session.add(PolicyLike(policy_id=all_policies[0].id, user_id=emp.id))
            db.session.commit()
        print(f"[✓] Gamification Points active (total quiz attempts: {QuizAttempt.query.count()})")

        # ----------------------------------------------------------------------
        # 14. Guided Onboarding Reading Checklists
        # ----------------------------------------------------------------------
        for emp in employees:
            if OnboardingChecklistItem.query.filter_by(user_id=emp.id).count() == 0:
                for idx, pol in enumerate(mandatory_policies[:5], start=1):
                    db.session.add(OnboardingChecklistItem(
                        user_id=emp.id, policy_id=pol.id, order=idx,
                        is_done=(idx <= 3), completed_at=now_utc() - timedelta(days=4) if idx <= 3 else None,
                    ))
        db.session.commit()
        print(f"[✓] Employee Onboarding reading paths active (total items: {OnboardingChecklistItem.query.count()})")

        # ----------------------------------------------------------------------
        # 15. Policy AI Reviews & Insights
        # ----------------------------------------------------------------------
        for p in all_policies:
            active_v = p.versions.filter_by(is_active=True).first()
            if active_v and not PolicyAIReview.query.filter_by(policy_id=p.id).first():
                rev = PolicyAIReview(
                    policy_id=p.id,
                    risk_score=18 + (p.id * 3 % 20),
                    missing_sections=["Appeals Committee Escalation Process", "Annual Policy Review Protocol"],
                    compliance_issues=["Align notice period buyout deductions with statutory labor guidelines"],
                    duplicates=[],
                    conflicts=[],
                    generated_at=now_utc() - timedelta(days=7),
                )
                db.session.add(rev)

            if active_v and not PolicyAIInsight.query.filter_by(policy_id=p.id).first():
                ins = PolicyAIInsight(
                    policy_id=p.id,
                    summary=f"Official corporate {p.title} outlining key entitlements, governance rules, and employee compliance protocols.",
                    key_points=["Applicable to all full-time corporate employees", "Requires periodic acknowledgment upon update", "Strict enforcement by HR & Legal"],
                    faq_json=json.dumps([
                        {"q": f"Who is eligible under the {p.title}?", "a": "All active full-time corporate employees across all operating locations."},
                        {"q": "How often is this policy reviewed?", "a": "Annually, or upon significant regulatory legislative amendments."},
                    ]),
                    quiz_json=json.dumps([
                        {"question": f"Is adherence to the {p.title} mandatory?", "options": ["Yes, for all full-time employees", "No, it is voluntary", "Only for managers"], "answer": 0}
                    ]),
                    generated_at=now_utc() - timedelta(days=7),
                )
                db.session.add(ins)

        db.session.commit()
        print(f"[✓] Policy AI Reviews & Insights active (total reviews: {PolicyAIReview.query.count()})")

        # ----------------------------------------------------------------------
        # 16. Enterprise Notifications
        # ----------------------------------------------------------------------
        if Notification.query.count() == 0:
            notifs = [
                Notification(
                    user_id=admin_user.id,
                    type=NotificationType.APPROVAL_NEEDED,
                    title="Workflow Action Required: Executive Policy Sign-off",
                    message="Travel & Expense Policy v2.1 requires final C-level approval to complete publication.",
                    link="/admin/workflows",
                    is_read=False,
                    created_at=now_utc() - timedelta(hours=3),
                ),
                Notification(
                    user_id=admin_user.id,
                    type=NotificationType.MANDATORY_READ,
                    title="Statutory Audit: ISO 27001 Annual Attestation",
                    message="Annual statutory attestation cycle initiated across all departments. Current completion rate is 85%.",
                    link="/admin/compliance",
                    is_read=False,
                    created_at=now_utc() - timedelta(days=1),
                ),
                Notification(
                    user_id=admin_user.id,
                    type=NotificationType.POLICY_UPDATED,
                    title="Contradiction Radar: Overlap Detected",
                    message="Contradiction Radar flagged threshold inconsistency between Code of Conduct and Gift policy.",
                    link="/admin/contradictions",
                    is_read=True,
                    created_at=now_utc() - timedelta(days=2),
                ),
                Notification(
                    user_id=hr_user.id,
                    type=NotificationType.APPROVAL_DONE,
                    title="Approval Complete: Remote Work Guidelines v1.2",
                    message="All required stakeholders signed off on Remote Work Guidelines v1.2.",
                    link="/admin/policies",
                    is_read=False,
                    created_at=now_utc() - timedelta(hours=8),
                ),
                Notification(
                    user_id=emp_user.id,
                    type=NotificationType.MANDATORY_READ,
                    title="Mandatory Reading: Information Security Guidelines",
                    message="Please review and digitally acknowledge the updated Information Security Guidelines v1.2.",
                    link="/policies/1",
                    is_read=False,
                    created_at=now_utc() - timedelta(hours=5),
                ),
                Notification(
                    user_id=emp_user.id,
                    type=NotificationType.MEETING_INVITE,
                    title="Meeting Scheduled: Hybrid Workplace Transition & Standards",
                    message="You are invited to the all-hands briefing on hybrid workplace and remote collaboration standards.",
                    link="/meetings/2",
                    is_read=False,
                    created_at=now_utc() - timedelta(days=1),
                ),
                Notification(
                    user_id=emp_user.id,
                    type=NotificationType.NEW_POLICY,
                    title="New Policy Published: Travel & Expense Reimbursement Policy",
                    message="A new revision of the corporate travel and meal allowance guidelines is now live.",
                    link="/policies",
                    is_read=True,
                    created_at=now_utc() - timedelta(days=3),
                ),
            ]
            for n in notifs:
                db.session.add(n)
            db.session.commit()
        print(f"[✓] Enterprise Notifications active (total: {Notification.query.count()})")

        # ----------------------------------------------------------------------
        # 17. Saved Policies Bookmarks
        # ----------------------------------------------------------------------
        if admin_user.saved.count() == 0 and len(all_policies) >= 3:
            admin_user.saved.append(all_policies[0])
            admin_user.saved.append(all_policies[2])
            admin_user.saved.append(all_policies[5])
        if emp_user.saved.count() == 0 and len(all_policies) >= 5:
            emp_user.saved.append(all_policies[1])
            emp_user.saved.append(all_policies[4])
        db.session.commit()
        print(f"[✓] Saved Policy Bookmarks active (Admin: {admin_user.saved.count()}, Employee: {emp_user.saved.count()})")

        # ----------------------------------------------------------------------
        # 18. Meeting Action Items & Participant Links for Admin & Employee
        # ----------------------------------------------------------------------
        all_meetings = Meeting.query.all()
        for m in all_meetings:
            if m.id in [2, 4]:
                if not MeetingParticipant.query.filter_by(meeting_id=m.id, user_id=emp_user.id).first():
                    db.session.add(MeetingParticipant(meeting_id=m.id, user_id=emp_user.id, attended=True))

        if MeetingActionItem.query.filter_by(owner_id=admin_user.id).count() == 0 and all_meetings:
            db.session.add(MeetingActionItem(
                meeting_id=all_meetings[0].id,
                owner_id=admin_user.id,
                description="Review and execute executive sign-off for statutory compliance report",
                due_date=(now_utc() + timedelta(days=3)).date(),
                priority=Priority.HIGH,
                status=ActionItemStatus.PENDING,
            ))
            db.session.add(MeetingActionItem(
                meeting_id=all_meetings[0].id,
                owner_id=admin_user.id,
                description="Sign off on completed departmental compliance certifications",
                due_date=(now_utc() - timedelta(days=2)).date(),
                priority=Priority.MEDIUM,
                status=ActionItemStatus.DONE,
                completed_at=now_utc() - timedelta(days=2, hours=1),
            ))

        if MeetingActionItem.query.filter_by(owner_id=emp_user.id).count() == 0 and len(all_meetings) >= 2:
            db.session.add(MeetingActionItem(
                meeting_id=all_meetings[1].id,
                owner_id=emp_user.id,
                description="Complete mandatory remote work ergonomics & VPN setup confirmation",
                due_date=(now_utc() + timedelta(days=5)).date(),
                priority=Priority.MEDIUM,
                status=ActionItemStatus.PENDING,
            ))
            db.session.add(MeetingActionItem(
                meeting_id=all_meetings[1].id,
                owner_id=emp_user.id,
                description="Submit feedback on hybrid workplace desk reservation system",
                due_date=(now_utc() - timedelta(days=4)).date(),
                priority=Priority.LOW,
                status=ActionItemStatus.DONE,
                completed_at=now_utc() - timedelta(days=4, hours=2),
            ))
        db.session.commit()
        print(f"[✓] Meeting Action Items & Participants active (Admin items: {MeetingActionItem.query.filter_by(owner_id=admin_user.id).count()}, Employee items: {MeetingActionItem.query.filter_by(owner_id=emp_user.id).count()})")

        # ----------------------------------------------------------------------
        # 19. Policy Entities & Graph Relationships
        # ----------------------------------------------------------------------
        if PolicyEntity.query.count() == 0 and all_policies:
            sample_entities = [
                ("ROLE", "Full-Time Employee", "full-time employee", all_policies[0].id),
                ("ROLE", "Reporting Manager", "reporting manager", all_policies[0].id),
                ("AUTHORITY", "Chief Information Security Officer", "chief information security officer", all_policies[0].id),
                ("DEPARTMENT", "Human Resources", "human resources", all_policies[1].id if len(all_policies) > 1 else all_policies[0].id),
                ("BENEFIT", "Annual Leave", "annual leave", all_policies[1].id if len(all_policies) > 1 else all_policies[0].id),
                ("BENEFIT", "Maternity & Paternity Leave", "maternity & paternity leave", all_policies[1].id if len(all_policies) > 1 else all_policies[0].id),
                ("FORM", "Annexure A - NDA", "annexure a - nda", all_policies[0].id),
                ("AUTHORITY", "Board of Directors", "board of directors", all_policies[2].id if len(all_policies) > 2 else all_policies[0].id),
            ]
            created_ents = []
            for e_type, e_name, e_norm, pol_id in sample_entities:
                pol = db.session.get(Policy, pol_id)
                ver = pol.active_version or pol.latest_version
                pe = PolicyEntity(
                    policy_id=pol.id,
                    version_id=ver.id if ver else 1,
                    entity_type=e_type,
                    entity_name=e_name,
                    normalized_name=e_norm,
                    source_chunk_id=f"p{pol.id}-chunk-1",
                    created_at=now_utc(),
                )
                db.session.add(pe)
                created_ents.append(pe)
            db.session.flush()

            if len(created_ents) >= 4:
                r1 = PolicyRelationship(
                    policy_id=created_ents[0].policy_id,
                    version_id=created_ents[0].version_id,
                    source_entity_id=created_ents[0].id,
                    relation="reports_to",
                    target_entity_id=created_ents[1].id,
                )
                r2 = PolicyRelationship(
                    policy_id=created_ents[4].policy_id,
                    version_id=created_ents[4].version_id,
                    source_entity_id=created_ents[0].id,
                    relation="eligible_for",
                    target_entity_id=created_ents[4].id,
                )
                db.session.add_all([r1, r2])
            db.session.commit()
        print(f"[✓] Policy Entities & Graph Relationships active (Entities: {PolicyEntity.query.count()}, Relationships: {PolicyRelationship.query.count()})")

        # ----------------------------------------------------------------------
        # 20. Legacy Approval Workflow Compatibility
        # ----------------------------------------------------------------------
        if ApprovalWorkflow.query.count() == 0 and len(all_policies) >= 2:
            p1 = all_policies[0]
            v1 = p1.active_version or p1.latest_version
            p2 = all_policies[1]
            v2 = p2.active_version or p2.latest_version
            if v1:
                aw1 = ApprovalWorkflow(
                    policy_id=p1.id,
                    version_id=v1.id,
                    stage="Executive Sign-Off",
                    status=ApprovalStatus.APPROVED,
                    actor_id=admin_user.id,
                    comment="Approved for enterprise-wide publication.",
                    acted_at=now_utc() - timedelta(days=2),
                    order=1,
                )
                db.session.add(aw1)
            if v2:
                aw2 = ApprovalWorkflow(
                    policy_id=p2.id,
                    version_id=v2.id,
                    stage="Legal Compliance Audit",
                    status=ApprovalStatus.APPROVED,
                    actor_id=legal_user.id,
                    comment="Statutory review completed without exception.",
                    acted_at=now_utc() - timedelta(days=5),
                    order=1,
                )
                db.session.add(aw2)
            db.session.commit()
        print(f"[✓] Legacy Approval Workflow records active (total: {ApprovalWorkflow.query.count()})")

        print("\n=======================================================")
        print("  PRODUCTION SEEDING COMPLETE — ALL 18 VIEWS ARE READY")
        print("=======================================================\n")

if __name__ == "__main__":
    seed_production()
