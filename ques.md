
  We conducted a deep architectural diagnosis across the entire backend, RAG pipelines, and AI simulator components. Here are the core issues found and fixed:
  ──────
  #### 1. The "Department Isolation" Authorization Bug (Why Answers Were "Data Not Found")

  • Root Cause: In evidence_filter.py, any policy with department_id assigned (e.g. HR owning Leave Policy, IT owning Security Policy) blocked all employees
  outside that authoring department. As a result, non-HR employees were barred from reading company-wide Leave, Remote Work, or IT policies.
  • Fix: Scoped departmental restrictions strictly to policies marked CONFIDENTIAL. Standard internal company-wide policies are now universally accessible to
  all employees.
  #### 2. What-If Simulator Pipeline Breakage & Signature Mismatch
  • Root Cause: In whatif_ai.py, vector retrieval passed deprecated keyword arguments (query_embedding=..., allowed_departments=...), throwing uncaught
  TypeErrors that forced the simulator into fallback errors.
  • Fix: Upgraded whatif_ai.py to use hybrid retrieval + cross-encoder reranking, supporting both mock unit test signatures and real database queries.

  #### 3. LLM Provider Read Timeouts & Hanging Fallbacks

  • Root Cause: llm_provider.py had a 180s/30s blocking timeout without active liveness checks. If Ollama was offline or loading weights, queries hung for
  minutes before failing.
  • Fix: Implemented active liveness caching and a 6-second timeout with immediate zero-latency failover to deterministic extractive generation.
  ──────
  ### Knowledge Base Scaled to 20 Enterprise Policies

  We expanded seed.py from 5 narrow sample policies to 20 comprehensive corporate policies across 8 departments and 12 categories:

   #         | Policy Domain                | Dept      | Key Covered Rules & Limits
  -----------|------------------------------|-----------|-----------------------------------------------------------------------------------------------------
   1         | Remote Work Policy (v1, v2)  | HR        | Up to 3 days WFH, laptop provided, Rs. 500 internet allowance, 10 AM–4 PM core hours
   2         | Leave Policy (v1, v2)        | HR        | 24 days annual leave, 12 days sick leave, 26 weeks maternity, 10 days paternity, 3 days bereavement
   3         | Code of Conduct              | Legal     | Anti-discrimination, conflict of interest disclosure in 14 days, whistleblower protection
   4         | IT Security Policy           | IT        | 10-char password rotated every 90 days, MFA mandatory, incident reporting within 2 hours
   5         | Travel & Expense Policy      | Finance   | Rs. 5,000 metro hotel ceiling, Rs. 1,500 metro per diem, expense submission in 7 days
   6         | Group Medical Insurance      | HR        | Rs. 5,00,000 base medical cover, spouse + 2 kids, Rs. 15,000 OPD allowance
   7         | Performance & PIP Policy     | HR        | Bi-annual appraisals (June/Dec), 1–5 rating scale, 60-day PIP timeline
   8         | Notice Period & Resignation  | HR        | 2 months for confirmed staff, 1 month probation, 3-day asset handover
   9         | POSH & Anti-Harassment       | Legal     | Internal Complaints Committee, complaint within 3 months, 90-day investigation SLA
   10        | IP & Inventions Policy       | Legal     | Company owns all IP, disclosure in 14 days, moonlighting prohibited without written VP sign-off
   11        | Data Privacy (DPDP/GDPR)     | Legal     | AES-256 encryption, 7-year financial record retention, breach notification in 6 hours
   12        | Learning & Education         | HR        | Rs. 40,000 annual learning budget, 100% certification reimbursement
   13        | Hardware & BYOD Asset Policy | IT        | 3-year laptop refresh cycle, lost device reporting within 1 hour, MDM on mobile
   14        | Employee Referral Bonus      | HR        | Rs. 25,000 junior roles / Rs. 50,000 senior roles (50% at joining, 50% post-probation)
   15        | Relocation & Transfer Policy | HR        | Up to Rs. 1,00,000 relocation package, 15 days guest house, 3 days moving leave
   16        | Gifts & Anti-Bribery Policy  | Legal     | Rs. 2,000 gift limit per occasion, strict ban on government gifts
   17        | Attendance & Punctuality     | HR        | 9-hour workday, 30-min grace period (until 9:30 AM), swipe-in after 11 AM is half-day
   18        | Overtime & On-Call Policy    | Eng       | Rs. 2,000/day weekend on-call standby, 1.5x incident rate, 60-day comp-off validity
   19        | Workplace Safety & Emergency | Ops       | Quarterly fire drills, injury reporting within 1 hour, ergonomic equipment requests
   20        | Social Media & Public PR     | Mktg      | Designated spokespersons only, personal disclaimer requirement

  Compiled Knowledge Base Stats:

  • Total Policies: 20
  • Total Versions: 22
  • Structured Facts: 33
  • Precomputed Canonical Q&As: 100
  • Semantic Vector Chunks: 22
  ──────
  ### Live Benchmark & Verification

  #### 1. AI Assistant (Level 0 Fast-Path Facts)

  All 10 test queries answered with 100% confidence in <300ms:

    Q: What is the base health insurance cover?
       Ans: According to Health & Group Medical Insurance Policy (v1.0), Medical Insurance Cover is Rs. 5,00,000 (family floater coverage).
    
    Q: What is the annual learning budget for an employee?
       Ans: According to Learning & Educational Assistance Policy (v1.0), Annual Learning Budget is Rs. 40,000 (professional development).
    
    Q: How much is the senior employee referral bonus?
       Ans: According to Employee Referral Bonus Policy (v1.0), Senior Referral Bonus is Rs. 50,000 (talent acquisition referral).
    
    Q: What is the standard notice period for confirmed staff?
       Ans: According to Notice Period & Resignation Policy (v1.0), Notice Period is 2 months (resignation & termination).
    
    Q: What is the maximum domestic hotel limit per night?
       Ans: According to Travel & Expense Policy (v1.0), Travel Hotel is Rs. 5,000 (domestic travel).
    
    Q: What is the arrival grace period for morning check-in?
       Ans: According to Attendance & Punctuality Policy (v1.0), Arrival Grace Period is 30 minutes (attendance check-in).
    
    Q: What is the password rotation period?
       Ans: According to IT Security Policy (v1.0), Password Expiration is 90 days (password security policy).

  #### 2. What-If Policy Impact Simulator

    Scenario: "I want to work remotely for 2 days next week."
      Verdict: compliant / depends
      Explanation: Schedule allows working remotely up to 3 days per week with manager coordination.
      Citations: ['Remote Work Policy']

    Scenario: "I have a headache and want to take 1 day of sick leave without a medical certificate."
      Verdict: compliant (100% confidence)
      Explanation: Leave Policy v2.0 states a medical certificate is required only for 2+ consecutive days.
      Citations: ['Leave Policy']

    Scenario: "I want to book a hotel in Mumbai for Rs. 4,500 per night for a client meeting."
      Verdict: compliant (100% confidence)
      Explanation: Hotel cost of Rs. 4,500 is within the Rs. 5,000 domestic metro limit under Travel & Expense Policy.
      Citations: ['Travel & Expense Policy']
  ──────
  ### Test Suite Execution

  All unit and integration tests are passing:

    ================== 22 passed, 9 warnings in 126.58s ==================
