# 🛡️ Security Baseline & Defensive Hardening

> **Document:** `SECURITY_BASELINE.md`  
> **Status:** Approved Baseline  
> **Platform:** Abdullah Developer Core (`abdullah-dev-core`)

---

## 1. Defensive Philosophy & Threat Model

Given Abdullah's engineering background in **Defensive Cybersecurity and SOC Operations**, this platform is designed to be **secure by default**. Security controls are built directly into the foundational framework rather than retrofitted as an afterthought.

### Primary Threat Vectors Addressed:
1. **Credential Stuffing & Brute-Force Authentication:** Mitigated via Argon2id hashing, IP-based rate limiting, and refresh token rotation.
2. **SQL Injection (SQLi):** Mitigated by strict use of SQLAlchemy 2.0 ORM and parameterized queries. Raw SQL string concatenation is strictly banned.
3. **Cross-Site Scripting (XSS):** Mitigated by React's automatic JSX encoding, Content-Security-Policy (CSP) headers, and HTTP-only cookie isolation for session tokens.
4. **Cross-Site Request Forgery (CSRF):** Mitigated by `SameSite=Lax` cookie flags and requiring custom headers (`X-Requested-With` or JSON content-type) on state-changing API endpoints.
5. **Information Leakage & Verbose Stack Traces:** Production error handlers sanitize stack traces and output only generic error codes paired with internal correlation `X-Request-ID` logs.

---

## 2. OWASP Top 10 Mitigation Matrix

| OWASP Vulnerability | Technical Mitigation in Abdullah Dev Core | Verification Method |
| :--- | :--- | :--- |
| **A01: Broken Access Control** | FastAPI dependency guards (`require_role`, `get_current_active_user`). Users can only mutate resources matching their authenticated `user_id`. | Unit & API tests in `tests/api/test_auth.py` |
| **A02: Cryptographic Failures** | Argon2id for password hashing; SHA-256 for refresh token hashing; HMAC-SHA256 for JWT signing with 256-bit entropy secret keys. | `tests/unit/test_security.py` |
| **A03: Injection** | 100% SQLAlchemy 2.0 mapped statements. Input validation via Pydantic v2 with regex validation for emails, usernames, and phone numbers. | Static analysis via Ruff & CodeQL |
| **A04: Insecure Design** | Principle of Least Privilege: default user role is unprivileged `user`. Superadmin capabilities isolated to dedicated endpoints. | Architectural reviews in `.ai/DECISIONS.md` |
| **A05: Security Misconfiguration** | Centralized `Settings` class via Pydantic Settings. `DEBUG` mode forces failure in production if default secrets are detected. | Startup assertions in `main.py` |
| **A06: Vulnerable Components** | Minimal dependencies; pinned versions in `requirements.txt` and `package.json`; automated GitHub Dependabot alerts. | CI dependency audit step |
| **A07: Identification & Auth Failures** | Rate limiting on `/auth/login` (5/min); account lockout telemetry; refresh token rotation with immediate reuse detection. | Auth penetration test suites |
| **A08: Software & Data Integrity** | Database migrations strictly tracked in version control via Alembic; Docker builds use pinned SHA/version bases. | CI migration validation |
| **A09: Security Logging & Monitoring** | Structured JSON logging capturing client IP, user ID, method, path, status, and response time; persistent `audit_logs` table. | Log parsing and admin audit viewer |
| **A10: Server-Side Request Forgery** | External webhook requests (e.g. Telegram/WhatsApp) validated against allowlisted destination hosts; private RFC 1918 IPs blocked. | Network egress validation tests |

---

## 3. HTTP Security Headers Middleware

FastAPI automatically injects production-grade HTTP response headers on every route via custom Starlette middleware (`app/core/security.py`):

```python
# Security Headers enforced on all responses
HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
    "Content-Security-Policy": "default-src 'self'; img-src 'self' data: https:; script-src 'self'; style-src 'self' 'unsafe-inline';",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()"
}
```

---

## 4. Input Sanitization & Data Normalization

1. **Email Normalization:** All emails are lowercased and stripped of leading/trailing whitespace via Pydantic field validators before reaching database queries:
   ```python
   @field_validator("email")
   @classmethod
   def normalize_email(cls, v: str) -> str:
       return v.strip().lower()
   ```
2. **Arabic & Multilingual UTF-8 Integrity:**
   - All string columns in PostgreSQL use UTF-8 encoding.
   - Text inputs (names, descriptions, titles) are stripped of zero-width control characters or dangerous bidirection override Unicode spoofing attacks (`\u202E`).

---

## 5. Secret Management & Anti-Leak Safeguards

- **Never Commit Secrets:** `.env` is explicitly declared in `.gitignore`.
- **Pre-Flight Startup Guard:** When `ENVIRONMENT=production`, FastAPI inspects `SECRET_KEY` on startup. If the key matches default test strings (e.g., `change-me-in-production`), the application terminates immediately with a critical alert.
- **Sanitized Response Models:** Database entities (`User`) are never returned directly to API clients. Only explicit Pydantic schemas (`UserResponse`) are returned, guaranteeing that `hashed_password` and internal salts are physically excluded from the serialization payload.
