"""
seed.py
Populates the enterprise knowledge base with:
  - Default Admin, HR, Employee, and Manager accounts
  - 8 core corporate departments and 12 policy categories
  - 20 comprehensive enterprise policies across 30+ versions
  - Automatic compilation via KnowledgeCompilerPipeline (Facts, QA, Embeddings, BM25)
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from models import (db, User, UserRole, Department, PolicyCategory,
                    Policy, PolicyVersion, PolicyStatus, Tag)
from utils import generate_policy_id
from config import Config
from datetime import date

app = create_app(os.environ.get("FLASK_ENV", "development"))

DEPARTMENTS = [
    ("Human Resources", "HR"), ("Engineering", "ENG"), ("Finance", "FIN"),
    ("Legal", "LEG"), ("Operations", "OPS"), ("Marketing", "MKT"),
    ("Sales", "SAL"), ("IT", "IT"),
]

CATEGORIES = [
    ("Leave", "", "#2a4a38"), ("Attendance", "", "#4a2a38"),
    ("Remote Work", "", "#2a3a4a"), ("Security", "", "#4a3a2a"),
    ("Payroll", "", "#3a4a2a"), ("Travel", "", "#2a4a4a"),
    ("Benefits", "", "#4a2a4a"), ("Recruitment", "", "#3a2a4a"),
    ("Performance", "", "#4a4a2a"), ("POSH", "", "#4a2a2a"),
    ("IT Policy", "", "#2a2a4a"), ("Data Privacy", "", "#3a3a3a"),
]

SAMPLE_POLICIES = [
    {
        "title": "Remote Work Policy",
        "description": "Guidelines for working from home and remote locations.",
        "category": "Remote Work",
        "department": "Human Resources",
        "versions": [
            {
                "num": 1.0, "label": "v1.0",
                "content": """REMOTE WORK POLICY — v1.0\nEffective Date: 2022-01-10\n\n1. Eligibility\nEmployees with 12+ months tenure may apply for remote work, subject to manager approval.\n\n2. Schedule\nEmployees may work remotely up to 1 day per week. Minimum 4 in-office days required.\n\n3. Equipment\nEmployees must use personal equipment. Company does not provide home office equipment.\n\n4. VPN\nAll remote employees must use company VPN when accessing internal systems.\n\n5. Meetings\nEmployees must be available for all scheduled meetings during core hours (10 AM – 4 PM).""",
                "summary": "Initial remote work policy.", "reason": "New policy", "eff_date": date(2022, 1, 10),
            },
            {
                "num": 2.0, "label": "v2.0",
                "content": """REMOTE WORK POLICY — v2.0\nEffective Date: 2024-03-01\n\n1. Eligibility\nAll full-time employees may apply from day one, subject to manager approval and role suitability.\n\n2. Schedule\nEmployees may work remotely up to 3 days per week. Minimum 2 in-office days required for collaboration.\n\n3. Equipment\nCompany provides a standard laptop and peripherals for approved remote employees.\n\n4. Internet Allowance\nRs. 500/month internet reimbursement claimable via the expense portal.\n\n5. Security\nVPN + MFA mandatory for all remote access. Security incidents must be reported within 24 hours of discovery.\n\n6. Meetings\nMust be available during core hours (10 AM – 4 PM) and attend all mandatory meetings in person once per week.""",
                "summary": "Expanded remote work allowance from 1 to 3 days. Added equipment and internet allowance.", "reason": "Post-pandemic update", "eff_date": date(2024, 3, 1),
            },
        ],
        "tags": ["wfh", "remote", "hybrid"], "priority": "high", "is_mandatory": True,
    },
    {
        "title": "Leave Policy",
        "description": "Annual, sick, maternity, paternity and bereavement leave entitlements.",
        "category": "Leave",
        "department": "Human Resources",
        "versions": [
            {
                "num": 1.0, "label": "v1.0",
                "content": """LEAVE POLICY — v1.0\nEffective Date: 2023-01-01\n\n1. Annual Leave\n18 days paid annual leave per calendar year.\n\n2. Sick Leave\n8 days paid sick leave per year. Medical certificate needed for 2+ consecutive days.\n\n3. Carry-Forward\nUnused leave cannot be carried forward. Forfeited at year end.\n\n4. Application\nSubmit to manager via email, minimum 5 working days in advance.\n\n5. Maternity / Paternity\nMaternity: 12 weeks. Paternity: 5 days.""",
                "summary": "Initial leave policy.", "reason": "New policy", "eff_date": date(2023, 1, 1),
            },
            {
                "num": 2.0, "label": "v2.0",
                "content": """LEAVE POLICY — v2.0\nEffective Date: 2024-07-01\n\n1. Annual Leave\n24 days paid annual leave per calendar year, accrued at 2 days/month.\n\n2. Sick Leave\n12 days paid sick leave per year. Medical certificate needed for 2+ consecutive days.\n\n3. Carry-Forward\nUp to 5 days may be carried to next year. Balance beyond 5 days is forfeited.\n\n4. Application\nSubmit via HR Portal (hr.company.in) minimum 3 working days in advance.\n\n5. Maternity / Paternity\nMaternity: 26 weeks paid (Maternity Benefit Act 2017). Paternity: 10 days paid.\n\n6. Bereavement Leave\n3 days paid bereavement leave for immediate family members.""",
                "summary": "Increased annual leave from 18 to 24 days, sick leave from 8 to 12 days, maternity to 26 weeks.", "reason": "HR benefits benchmarking", "eff_date": date(2024, 7, 1),
            },
        ],
        "tags": ["leave", "vacation", "sick", "pto"], "priority": "high", "is_mandatory": True,
    },
    {
        "title": "Code of Conduct",
        "description": "Standards of ethical behaviour, conflict of interest and workplace respect.",
        "category": "POSH",
        "department": "Legal",
        "versions": [
            {
                "num": 1.0, "label": "v1.0",
                "content": """CODE OF CONDUCT — v1.0\nEffective Date: 2023-01-01\n\n1. Respectful Workplace\nZero tolerance for discrimination, harassment, or bullying of any kind.\n\n2. Conflicts of Interest\nEmployees must disclose any personal interest that may conflict with company duties to Legal within 14 days.\n\n3. Gifts and Bribery\nEmployees may not accept gifts worth more than Rs. 2,000 without written compliance approval. Bribery is strictly prohibited.\n\n4. Whistleblowing\nReports of misconduct can be made anonymously via ethics@company.com with complete protection against retaliation.""",
                "summary": "Foundational code of conduct.", "reason": "Baseline compliance", "eff_date": date(2023, 1, 1),
            }
        ],
        "tags": ["conduct", "ethics", "compliance"], "priority": "high", "is_mandatory": True,
    },
    {
        "title": "IT Security Policy",
        "description": "Password rules, data handling, device security and incident reporting.",
        "category": "Security",
        "department": "IT",
        "versions": [
            {
                "num": 1.0, "label": "v1.0",
                "content": """IT SECURITY POLICY — v1.0\nEffective Date: 2023-06-01\n\n1. Passwords\nMinimum 10 characters with uppercase, lowercase, numbers, and symbols. Change every 90 days. No password reuse for 5 cycles.\n\n2. Multi-Factor Authentication\nMFA is mandatory on all company systems without exception.\n\n3. Data Classification\nConfidential data must never be stored on unencrypted personal devices or public cloud drives.\n\n4. Incident Reporting\nReport any suspected breach to security@company.com within 2 hours of discovery.""",
                "summary": "Corporate IT security rules.", "reason": "ISO 27001 alignment", "eff_date": date(2023, 6, 1),
            }
        ],
        "tags": ["security", "password", "mfa"], "priority": "high", "is_mandatory": True,
    },
    {
        "title": "Travel & Expense Policy",
        "description": "Rules for business travel booking, per diem allowances, and expense reimbursement.",
        "category": "Travel",
        "department": "Finance",
        "versions": [
            {
                "num": 1.0, "label": "v1.0",
                "content": """TRAVEL & EXPENSE POLICY — v1.0\nEffective Date: 2023-04-01\n\n1. Booking Travel\nAll flights and intercity trains must be booked via the Corporate Travel Desk at least 7 days in advance.\n\n2. Lodging Limits\nMaximum Rs. 5,000 per night for domestic travel in metro cities; Rs. 3,500 in non-metro locations.\n\n3. Daily Allowance (Per Diem)\nRs. 1,500 per day for metro cities and Rs. 1,000 per day for non-metro cities to cover food and local conveyance.\n\n4. Expense Submission\nAll expense claims with itemized receipts must be submitted within 7 days of return.""",
                "summary": "Business travel guidelines.", "reason": "Standard finance policy", "eff_date": date(2023, 4, 1),
            }
        ],
        "tags": ["travel", "expense", "per-diem"], "priority": "medium", "is_mandatory": False,
    },
    {
        "title": "Health & Group Medical Insurance Policy",
        "description": "Comprehensive health insurance, dependent coverage, hospitalization, and OPD limits.",
        "category": "Benefits",
        "department": "Human Resources",
        "versions": [
            {
                "num": 1.0, "label": "v1.0",
                "content": """HEALTH & GROUP MEDICAL INSURANCE POLICY — v1.0\nEffective Date: 2024-01-01\n\n1. Coverage Scope\nAll full-time employees receive Rs. 5,00,000 base medical cover under the company group health insurance policy.\n\n2. Dependent Eligibility\nCoverage includes employee, legally married spouse, and up to 2 dependent children up to age 25.\n\n3. OPD Benefit\nEmployees may claim an OPD allowance of Rs. 15,000 per year for outpatient consultations and prescribed medicines.\n\n4. Cashless Hospitalization\nCashless claims are available across 6,000+ network hospitals. Pre-authorization must be submitted within 24 hours of emergency admission.\n\n5. Maternity Cover\nMaternity hospitalization expense is covered up to Rs. 75,000 for normal delivery and Rs. 1,00,000 for C-section.""",
                "summary": "Standard group medical cover.", "reason": "Annual insurance renewal", "eff_date": date(2024, 1, 1),
            }
        ],
        "tags": ["health", "insurance", "mediclaim", "opd"], "priority": "high", "is_mandatory": True,
    },
    {
        "title": "Performance Evaluation & Promotion Policy",
        "description": "Annual review cycle, rating scales, promotion criteria, and Performance Improvement Plans (PIP).",
        "category": "Performance",
        "department": "Human Resources",
        "versions": [
            {
                "num": 1.0, "label": "v1.0",
                "content": """PERFORMANCE EVALUATION & PROMOTION POLICY — v1.0\nEffective Date: 2023-05-01\n\n1. Review Cycle\nPerformance appraisals occur bi-annually in June (mid-year review) and December (annual appraisal).\n\n2. Rating Scale\nRatings range from 1 (Unsatisfactory) to 5 (Exceeds Expectations). Rating 3 represents Meets Expectations.\n\n3. Promotion Criteria\nPromotion requires a minimum of 18 months in the current role and consecutive ratings of 4 or 5.\n\n4. Performance Improvement Plan (PIP)\nEmployees receiving a rating of 1 or 2 are placed on a 60 days performance improvement plan with weekly manager milestones.\n\n5. Appeals\nEmployees may appeal appraisal ratings to the HR Talent Committee within 14 days of receipt.""",
                "summary": "Performance evaluation framework.", "reason": "Standard HR framework", "eff_date": date(2023, 5, 1),
            }
        ],
        "tags": ["appraisal", "promotion", "pip", "performance"], "priority": "high", "is_mandatory": True,
    },
    {
        "title": "Notice Period & Resignation Policy",
        "description": "Resignation procedure, notice periods, buyout terms, and handover requirements.",
        "category": "Leave",
        "department": "Human Resources",
        "versions": [
            {
                "num": 1.0, "label": "v1.0",
                "content": """NOTICE PERIOD & RESIGNATION POLICY — v1.0\nEffective Date: 2023-01-01\n\n1. Standard Notice Period\nConfirmed employees must serve a notice period of 2 months upon formal resignation.\n\n2. Probation Period Notice\nEmployees on probation must serve a notice period of 1 month.\n\n3. Notice Buyout\nNotice buyout is subject to business continuity approval by the Department Head and HR Director.\n\n4. Handover & Exit Clearance\nAll company property, laptops, access badges, and knowledge documentation must be handed over 3 days prior to the last working day.""",
                "summary": "Resignation and separation policy.", "reason": "Standard HR guidelines", "eff_date": date(2023, 1, 1),
            }
        ],
        "tags": ["resignation", "notice", "exit", "severance"], "priority": "high", "is_mandatory": True,
    },
    {
        "title": "Prevention of Sexual Harassment (POSH) Policy",
        "description": "Zero-tolerance anti-harassment policy, complaint mechanism, and Internal Complaints Committee.",
        "category": "POSH",
        "department": "Legal",
        "versions": [
            {
                "num": 1.0, "label": "v1.0",
                "content": """PREVENTION OF SEXUAL HARASSMENT (POSH) POLICY — v1.0\nEffective Date: 2023-01-01\n\n1. Policy Statement\nThe company maintains zero tolerance for sexual harassment and discriminatory behavior in the workplace.\n\n2. Internal Committee (IC)\nAn Internal Complaints Committee (ICC) presided over by a senior woman employee handles all formal complaints.\n\n3. Reporting Timeline\nComplaints must be submitted in writing to posh@company.com within 3 months of the incident date.\n\n4. Investigation SLA\nInvestigations must be completed within 90 days of complaint submission with full confidentiality.\n\n5. Anti-Retaliation\nStrict disciplinary action up to immediate termination will be taken against anyone attempting retaliation.""",
                "summary": "Mandatory POSH framework.", "reason": "Statutory compliance", "eff_date": date(2023, 1, 1),
            }
        ],
        "tags": ["posh", "harassment", "icc", "safety"], "priority": "high", "is_mandatory": True,
    },
    {
        "title": "Intellectual Property & Invention Policy",
        "description": "Ownership of company inventions, patent filings, moonlighting restrictions, and confidentiality.",
        "category": "Data Privacy",
        "department": "Legal",
        "versions": [
            {
                "num": 1.0, "label": "v1.0",
                "content": """INTELLECTUAL PROPERTY & INVENTION POLICY — v1.0\nEffective Date: 2023-03-01\n\n1. Ownership of Inventions\nAll code, designs, patents, documentation, and trade secrets developed using company time or resources belong solely to the company.\n\n2. Invention Disclosure\nEmployees must disclose any patentable invention to the Legal IP team within 14 days of creation.\n\n3. Moonlighting Restriction\nDual employment and external commercial freelance work in related industries is strictly prohibited without prior written VP approval.\n\n4. Post-Employment Non-Solicitation\nEmployees agree not to solicit company clients or employees for a period of 12 months following departure.""",
                "summary": "Intellectual property ownership guidelines.", "reason": "Corporate IP governance", "eff_date": date(2023, 3, 1),
            }
        ],
        "tags": ["ip", "patent", "moonlighting", "confidentiality"], "priority": "high", "is_mandatory": True,
    },
    {
        "title": "Data Privacy & DPDP Compliance Policy",
        "description": "Protection of employee and customer personal data, retention schedules, and breach notifications.",
        "category": "Data Privacy",
        "department": "Legal",
        "versions": [
            {
                "num": 1.0, "label": "v1.0",
                "content": """DATA PRIVACY & DPDP COMPLIANCE POLICY — v1.0\nEffective Date: 2024-02-01\n\n1. Principles of Data Processing\nPersonal data must be collected lawfully, processed transparently, and limited strictly to declared business purposes.\n\n2. Encryption Standards\nAll Customer Personally Identifiable Information (PII) must be encrypted using AES-256 at rest and TLS 1.3 in transit.\n\n3. Data Retention\nCustomer logs are retained for 180 days. Tax and financial transactional records are retained for 7 years.\n\n4. Breach Notification\nAny confirmed data breach involving PII must be notified to the Data Protection Officer (DPO) within 6 hours of discovery.""",
                "summary": "DPDP and GDPR data privacy standard.", "reason": "DPDP Act 2023 Compliance", "eff_date": date(2024, 2, 1),
            }
        ],
        "tags": ["privacy", "dpdp", "gdpr", "pii"], "priority": "high", "is_mandatory": True,
    },
    {
        "title": "Learning & Educational Assistance Policy",
        "description": "Annual training budgets, professional certification reimbursements, and skill development programs.",
        "category": "Benefits",
        "department": "Human Resources",
        "versions": [
            {
                "num": 1.0, "label": "v1.0",
                "content": """LEARNING & EDUCATIONAL ASSISTANCE POLICY — v1.0\nEffective Date: 2024-01-15\n\n1. Annual Learning Budget\nFull-time employees are eligible for an annual learning budget of Rs. 40,000 per year for technical books, courses, and conferences.\n\n2. Certification Reimbursement\n100% of examination fees for approved industry certifications (AWS, GCP, PMP, CISSP) are reimbursed upon passing.\n\n3. Service Commitment\nReimbursements exceeding Rs. 50,000 require a minimum 1-year service commitment following completion.\n\n4. Approval Flow\nCourse proposals must be submitted through the Learning Portal with manager sign-off prior to course registration.""",
                "summary": "Professional development and learning support.", "reason": "Employee upskilling incentive", "eff_date": date(2024, 1, 15),
            }
        ],
        "tags": ["learning", "training", "certifications", "budget"], "priority": "medium", "is_mandatory": False,
    },
    {
        "title": "Hardware, Laptop & BYOD Asset Policy",
        "description": "Company laptop issuance, replacement cycles, lost device protocols, and BYOD guidelines.",
        "category": "IT Policy",
        "department": "IT",
        "versions": [
            {
                "num": 1.0, "label": "v1.0",
                "content": """HARDWARE, LAPTOP & BYOD ASSET POLICY — v1.0\nEffective Date: 2023-08-01\n\n1. Device Issuance\nEvery engineer receives a company laptop (MacBook Pro or ThinkPad) with standard developer configurations.\n\n2. Hardware Refresh Cycle\nCompany laptops are eligible for a hardware refresh cycle every 3 years or upon reaching end-of-support.\n\n3. Lost / Stolen Devices\nLost or stolen hardware must be reported immediately to it-helpdesk@company.com within 1 hour for remote wiping.\n\n4. Asset Care & Negligence\nRepairs resulting from gross negligence are subject to an employee deductible of Rs. 1,000 per incident.\n\n5. BYOD Mobile Policy\nPersonal smartphones accessing corporate email must install the Company Mobile Device Management (MDM) profile.""",
                "summary": "IT asset and hardware management.", "reason": "Asset lifecycle management", "eff_date": date(2023, 8, 1),
            }
        ],
        "tags": ["hardware", "laptop", "byod", "asset"], "priority": "high", "is_mandatory": True,
    },
    {
        "title": "Employee Referral Bonus Policy",
        "description": "Incentives and payout structures for referring talent to open roles in the company.",
        "category": "Recruitment",
        "department": "Human Resources",
        "versions": [
            {
                "num": 1.0, "label": "v1.0",
                "content": """EMPLOYEE REFERRAL BONUS POLICY — v1.0\nEffective Date: 2023-09-01\n\n1. Bonus Structure\nSuccessful candidate referrals pay Rs. 25,000 for junior roles and Rs. 50,000 for senior roles (Lead/Manager level).\n\n2. Payout Schedule\n50% of the referral bonus is paid in the month of joining; remaining 50% is paid after 90 days of continuous employment.\n\n3. Candidate Eligibility\nReferred candidates must not have applied to the company within the preceding 6 months.\n\n4. Ineligible Referrers\nHiring managers, HR Talent Acquisition recruiters, and Executive Committee members are excluded from referral bonus payouts.""",
                "summary": "Talent referral incentive program.", "reason": "Recruitment acceleration", "eff_date": date(2023, 9, 1),
            }
        ],
        "tags": ["referral", "bonus", "recruitment", "hiring"], "priority": "medium", "is_mandatory": False,
    },
    {
        "title": "Relocation & Domestic Transfer Policy",
        "description": "Financial and logistical assistance for employees relocating for company office transfers.",
        "category": "Benefits",
        "department": "Human Resources",
        "versions": [
            {
                "num": 1.0, "label": "v1.0",
                "content": """RELOCATION & DOMESTIC TRANSFER POLICY — v1.0\nEffective Date: 2024-01-01\n\n1. Relocation Allowance\nEmployees relocating across cities receive a relocation package up to Rs. 1,00,000 against packing and moving receipts.\n\n2. Temporary Accommodation\nThe company provides 15 days corporate guest house accommodation upon arrival in the new city.\n\n3. Moving Leave\nEmployees are granted 3 days paid relocation leave to organize housing and family settlement.\n\n4. Clawback Clause\nIf an employee resigns voluntarily within 12 months of relocation, 100% of the relocation allowance must be repaid.""",
                "summary": "Employee relocation assistance.", "reason": "Multi-city office expansion", "eff_date": date(2024, 1, 1),
            }
        ],
        "tags": ["relocation", "transfer", "moving", "accommodation"], "priority": "medium", "is_mandatory": False,
    },
    {
        "title": "Gifts, Hospitality & Anti-Bribery Policy",
        "description": "Rules on accepting vendor gifts, entertainment, and anti-corruption guidelines.",
        "category": "Security",
        "department": "Legal",
        "versions": [
            {
                "num": 1.0, "label": "v1.0",
                "content": """GIFTS, HOSPITALITY & ANTI-BRIBERY POLICY — v1.0\nEffective Date: 2023-01-01\n\n1. Gift Threshold\nEmployees may only accept modest promotional items up to a gift limit of Rs. 2,000. Cash or cash-equivalents are strictly prohibited.\n\n2. Government Officials\nOffering or giving any gift, meal, or benefit to government officials is strictly prohibited under the Prevention of Corruption Act.\n\n3. Gift Register\nAny gift received exceeding Rs. 2,000 must be declared in the Compliance Gift Register within 5 working days.\n\n4. Vendor Meals\nBusiness lunches hosted by vendors must be customary, reasonable, and not timed around active procurement tenders.""",
                "summary": "Anti-bribery and gift thresholds.", "reason": "Corporate compliance governance", "eff_date": date(2023, 1, 1),
            }
        ],
        "tags": ["gifts", "anti-bribery", "compliance", "ethics"], "priority": "high", "is_mandatory": True,
    },
    {
        "title": "Attendance & Punctuality Policy",
        "description": "Working hours, check-in rules, grace periods, and unauthorized absence protocols.",
        "category": "Attendance",
        "department": "Human Resources",
        "versions": [
            {
                "num": 1.0, "label": "v1.0",
                "content": """ATTENDANCE & PUNCTUALITY POLICY — v1.0\nEffective Date: 2023-02-01\n\n1. Working Schedule\nStandard work day consists of 9 hours including a 1-hour lunch and rest break.\n\n2. Arrival Grace Period\nEmployees are granted a 30 minutes grace period from 9:00 AM to 9:30 AM for morning office swipe-in.\n\n3. Half-Day Threshold\nSwipe-ins recorded after 11:00 AM without prior manager approval are automatically deducted as a half-day leave.\n\n4. Unauthorized Absence\n3 consecutive days of unexcused absence without communication constitutes job abandonment and triggers formal enquiry.""",
                "summary": "Office attendance and check-in guidelines.", "reason": "Standard workplace discipline", "eff_date": date(2023, 2, 1),
            }
        ],
        "tags": ["attendance", "punctuality", "shift", "grace-period"], "priority": "high", "is_mandatory": True,
    },
    {
        "title": "Overtime & On-Call Engineering Policy",
        "description": "Compensation and rest protocols for after-hours engineering shifts, on-call standby, and weekend support.",
        "category": "Payroll",
        "department": "Engineering",
        "versions": [
            {
                "num": 1.0, "label": "v1.0",
                "content": """OVERTIME & ON-CALL ENGINEERING POLICY — v1.0\nEffective Date: 2023-10-01\n\n1. On-Call Standby Allowance\nEngineers scheduled for primary weekend on-call rotation receive Rs. 2,000 per day standby allowance.\n\n2. Incident Response Compensation\nActive production incident triage performed outside working hours is compensated at 1.5x hourly rate or equivalent compensatory off.\n\n3. Compensatory Off Validity\nCompensatory off days earned through weekend releases or production incidents must be utilized within 60 days.\n\n4. Mandatory Rest Period\nEngineers responding to severe night incidents (between 12 AM and 6 AM) are required to take a mandatory 6-hour morning rest period.""",
                "summary": "Engineering shift and on-call compensation.", "reason": "SRE and DevOps support guidelines", "eff_date": date(2023, 10, 1),
            }
        ],
        "tags": ["overtime", "on-call", "sre", "comp-off"], "priority": "medium", "is_mandatory": False,
    },
    {
        "title": "Workplace Health & Emergency Safety Policy",
        "description": "Emergency evacuation protocols, accident reporting, and occupational safety measures.",
        "category": "Security",
        "department": "Operations",
        "versions": [
            {
                "num": 1.0, "label": "v1.0",
                "content": """WORKPLACE HEALTH & EMERGENCY SAFETY POLICY — v1.0\nEffective Date: 2023-01-01\n\n1. Emergency Drills\nFire evacuation drills are conducted quarterly across all office facilities. Mandatory participation is required.\n\n2. Accident Reporting\nAny workplace injury or hazardous spill must be reported to the Safety Officer within 1 hour of occurrence.\n\n3. First Aid & Medical Room\nFully equipped First Aid kits and a paramedic are stationed on Floor 2 during all standard office hours.\n\n4. Ergonomic Support\nEmployees may request ergonomic chairs or vertical mice by submitting an assessment ticket to facilities@company.com.""",
                "summary": "Workplace safety standards.", "reason": "Occupational health & safety", "eff_date": date(2023, 1, 1),
            }
        ],
        "tags": ["safety", "emergency", "fire", "first-aid"], "priority": "high", "is_mandatory": True,
    },
    {
        "title": "Social Media & Public Communications Policy",
        "description": "Rules for external public speaking, media interviews, and corporate brand representations.",
        "category": "Data Privacy",
        "department": "Marketing",
        "versions": [
            {
                "num": 1.0, "label": "v1.0",
                "content": """SOCIAL MEDIA & PUBLIC COMMUNICATIONS POLICY — v1.0\nEffective Date: 2023-03-15\n\n1. Authorized Spokespersons\nOnly the CEO, CMO, and authorized PR leads may make public statements on behalf of the company.\n\n2. Personal Social Media Disclaimer\nWhen discussing industry topics online, employees must include the disclaimer: 'Views expressed are personal and not of my employer.'\n\n3. Confidential Information\nPosting screenshots of internal Slack channels, repositories, roadmaps, or unreleased financials is grounds for immediate dismissal.\n\n4. Media Inquiries\nAll journalist and media inquiries must be forwarded immediately to press@company.com without comment.""",
                "summary": "External branding and public communications policy.", "reason": "Brand reputation management", "eff_date": date(2023, 3, 15),
            }
        ],
        "tags": ["social-media", "pr", "marketing", "communications"], "priority": "medium", "is_mandatory": False,
    },
]

def seed():
    with app.app_context():
        db.create_all()

        # Admin user
        admin = User.query.filter_by(email=Config.DEFAULT_ADMIN_EMAIL).first()
        if not admin:
            admin = User(name="System Administrator", email=Config.DEFAULT_ADMIN_EMAIL,
                         role=UserRole.ADMIN, email_verified=True, is_active=True)
            admin.set_password(Config.DEFAULT_ADMIN_PASSWORD)
            db.session.add(admin)
            db.session.flush()
            print(f"[ok] Admin user created: {admin.email}")
        else:
            print(f"  Admin already exists: {admin.email}")

        # HR user
        hr = User.query.filter_by(email="hr@company.com").first()
        if not hr:
            hr = User(name="HR Director", email="hr@company.com", role=UserRole.HR,
                      email_verified=True, is_active=True)
            hr.set_password("HR@1234")
            db.session.add(hr)
            db.session.flush()
            print(f"[ok] HR user created: hr@company.com")

        # Employee user
        emp = User.query.filter_by(email="employee@company.com").first()
        if not emp:
            emp = User(name="Sample Employee", email="employee@company.com", role=UserRole.EMPLOYEE,
                       email_verified=True, is_active=True)
            emp.set_password("Emp@1234")
            db.session.add(emp)
            print(f"[ok] Employee created: employee@company.com")

        db.session.commit()

        # Departments
        dept_map = {}
        for name, code in DEPARTMENTS:
            dept = Department.query.filter_by(name=name).first()
            if not dept:
                dept = Department(name=name, code=code)
                db.session.add(dept)
                db.session.flush()
            dept_map[name] = dept
        db.session.commit()
        print(f"[ok] {len(DEPARTMENTS)} departments ready")

        # Categories
        cat_map = {}
        for name, icon, color in CATEGORIES:
            cat = PolicyCategory.query.filter_by(name=name).first()
            if not cat:
                cat = PolicyCategory(name=name, icon=icon, color=color)
                db.session.add(cat)
                db.session.flush()
            cat_map[name] = cat
        db.session.commit()
        print(f"[ok] {len(CATEGORIES)} categories ready")

        # Policies and Compilations
        from rag.compiler.pipeline import KnowledgeCompilerPipeline
        compiler = KnowledgeCompilerPipeline()

        total_policies = 0
        total_versions = 0
        total_facts = 0
        total_qa = 0
        total_chunks = 0

        for pd in SAMPLE_POLICIES:
            policy = Policy.query.filter_by(title=pd["title"]).first()
            if not policy:
                policy = Policy(
                    policy_id=generate_policy_id(),
                    title=pd["title"],
                    description=pd["description"],
                    category_id=cat_map.get(pd["category"], PolicyCategory.query.first()).id,
                    department_id=dept_map.get(pd["department"]).id if pd["department"] in dept_map else None,
                    author_id=hr.id,
                    status=PolicyStatus.ACTIVE,
                    priority=pd.get("priority", "medium"),
                    is_mandatory=pd.get("is_mandatory", False),
                    confidentiality="internal",
                )
                for tn in pd.get("tags", []):
                    tag = Tag.query.filter_by(name=tn).first() or Tag(name=tn)
                    if not tag.id:
                        db.session.add(tag)
                    policy.tags.append(tag)

                db.session.add(policy)
                db.session.flush()

                versions = pd["versions"]
                for i, vd in enumerate(versions):
                    is_last = (i == len(versions) - 1)
                    ver = PolicyVersion(
                        policy_id=policy.id,
                        version_num=vd["num"],
                        version_label=vd["label"],
                        content=vd["content"],
                        summary=vd["summary"],
                        change_reason=vd["reason"],
                        created_by_id=hr.id,
                        approved_by_id=admin.id,
                        is_active=is_last,
                        status="approved" if is_last else "superseded",
                        effective_date=vd["eff_date"],
                    )
                    db.session.add(ver)

                policy.current_version = versions[-1]["label"]
                policy.effective_date = versions[-1]["eff_date"]
                db.session.commit()
                total_policies += 1

            # Compile all versions through the KnowledgeCompilerPipeline
            for ver in policy.versions:
                total_versions += 1
                job = compiler.compile(policy.id, ver.id)
                total_facts += job.fact_count
                total_qa += job.qa_count
                total_chunks += job.chunk_count
                print(f"[compiled] {policy.title} (v{ver.version_number}): {job.chunk_count} chunks, {job.fact_count} facts, {job.qa_count} QA pairs")

        print(f"\n=======================================================")
        print(f"KNOWLEDGE COMPILATION COMPLETE:")
        print(f"  Total Policies: {len(SAMPLE_POLICIES)}")
        print(f"  Total Policy Versions: {total_versions}")
        print(f"  Total Facts Extracted: {total_facts}")
        print(f"  Total Precomputed Canonical Q&As: {total_qa}")
        print(f"  Total Semantic Chunks: {total_chunks}")
        print(f"=======================================================\n")

        # Complete enterprise production seed (workflows, meetings, action items, notifications, frameworks)
        try:
            from scripts.seed_production_ready import seed_production
            seed_production()
        except Exception as e:
            print(f"[notice] Enterprise production extensions: {e}")

if __name__ == "__main__":
    seed()

