# VERITAS — Comprehensive Application Security and Authorization Review

## 1. Executive Security Assessment

Veritas was audited across all layers of the application stack, including HTTP entry points, background worker tasks, RAG context assembly, and database interactions.

The platform enforces **defense-in-depth**:
- Authentication and MFA protection.
- Granular Role-Based Access Control (RBAC).
- Attribute-Based Access Control (ABAC) with confidentiality clearances.
- Context-level evidence filtering preventing unauthorized data leakage into LLM prompts.
- Zero external cloud inference dependencies, eliminating cloud-based data exfiltration vectors.

---

## 2. Authentication and Session Security

| Security Control | Implementation | Verification Outcome |
| :--- | :--- | :--- |
| **Password Storage** | `bcrypt` adaptive hashing with randomized salt | PASS |
| **Session Integrity** | Server-side cryptographic session cookie with `HttpOnly` and `SameSite=Lax` | PASS |
| **Multi-Factor Auth (MFA)** | TOTP with standard QR code setup (`blueprints/auth.py`) | PASS |
| **Anonymous User Rejection** | `@login_required` decorator redirects unauthenticated requests to `/auth/login` | PASS |
| **Credential Masking** | `Config.get_safe_diagnostics()` masks database passwords (`postgres:******@`) | PASS |

---

## 3. Role-Based Access Control (RBAC) & Endpoint Authorization

The application defines 4 core organizational roles:
- `admin`: Full administrative access to policies, users, workflows, settings, and logs.
- `hr`: Human resources management, compliance tracking, and policy approval.
- `manager`: Departmental policy review and team workflow management.
- `employee`: Standard policy browsing, search, acknowledgements, quizzes, and what-if simulation.

### Endpoint Protection Matrix:
- `/admin/*` routes enforce `@role_required(UserRole.ADMIN, UserRole.HR)`.
- Employee attempts to access administrative endpoints return **HTTP 403 Forbidden**.
- Anonymous requests return **HTTP 302 Redirect** to `/auth/login`.

---

## 4. Clearance Scoping and Evidence Isolation

To prevent unauthorized corporate information leakage, policies are categorized by `ConfidentialityLevel`:
1. `INTERNAL`: Accessible to all authenticated employees.
2. `CONFIDENTIAL`: Restricted to members of the policy's assigned department, HR, Legal, and Admins.
3. `RESTRICTED`: Strictly restricted to Admins, Legal, and designated Executive roles.

### Grounding and Evidence Isolation:
- Scoping is enforced at the database query level in `blueprints/employee.py` and inside the RAG retrieval pipeline via `rag.authorization.evidence_filter.EvidenceFilter`.
- If an employee queries a topic covered by a `RESTRICTED` policy, the retrieval pipeline intercepts and filters out the restricted chunks *before* context formatting.
- The LLM prompt never receives restricted passage text, guaranteeing that the model cannot inadvertently leak unauthorized policy details in its answer or citations.

---

## 5. Injection Defense & Input Validation

- **SQL Injection**: All database operations use SQLAlchemy ORM or parameterized queries (`text("... :param")`). No raw string concatenations exist in SQL statements.
- **Cross-Site Scripting (XSS)**: Jinja2 auto-escaping is active across all HTML templates. Dynamic user comments and descriptions are sanitized.
- **Prompt Injection Defense**:
  - Context passages supplied to Ollama are encapsulated within strict structural XML/markdown delimiters.
  - The system prompt instructs `qwen3:4b-q4_K_M` to treat passage contents as passive reference data rather than instructions.
- **External Network Isolation**:
  - Completely excised all `LMSTUDIO_BASE_URL` and `host.docker.internal` host gateway mappings from `docker-compose.yml`.
  - Veritas functions fully in an air-gapped or offline container network with no external HTTP egress required.
