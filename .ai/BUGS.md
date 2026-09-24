# 🐞 .ai/BUGS.md — Bug & Incident Registry

> **Document:** `.ai/BUGS.md`  
> **Status:** Active Registry  
> **Platform:** Abdullah Developer Core (`abdullah-dev-core`)

---

## 1. Registry Format

Whenever a bug, regression, or environment fault is identified, record it immediately using this schema:

```markdown
### 🐛 BUG-XXX: [Concise Title]
- **Date Discovered:** YYYY-MM-DD
- **Severity:** [Critical | High | Medium | Low]
- **Component:** [Backend Auth | Database | Frontend Bidi | Docker | CI/CD]
- **Symptoms:** [Exact error message or unexpected UI behavior]
- **Root Cause:** [Technical explanation of the defect]
- **Fix Applied:** [Summary of files modified and logic corrected]
- **Verification:** [Test executed confirming fix]
- **Status:** [Active | In Progress | Resolved]
```

---

## 2. Active Bugs

*No active bugs after Phase 2 verification (19 pytest tests, migration round-trip, lint, format, and dependency checks passed on 2026-09-24).*

---

## 3. Resolved Bugs

### 🐛 BUG-001: Phase 0 Docker runtime validation unavailable
- **Date Discovered:** 2026-09-24
- **Severity:** Medium
- **Component:** Docker / local development environment
- **Symptoms:** The first session could not run Compose or PostgreSQL; after Docker Desktop installation, the CLI was outside the session PATH and the engine initially was not running.
- **Root Cause:** Docker Desktop was initially unavailable. The installed per-user CLI and credential helper directory was not on this session's PATH.
- **Fix Applied:** Started Docker Desktop and included its installed `resources/bin` directory on the verification command's PATH. Updated `scripts/dev.ps1` to discover this per-user installation and include its credential helper automatically. No Compose change was required.
- **Verification:** `docker compose config --quiet` passed; `docker compose up -d --wait db` produced a healthy PostgreSQL container; `docker compose ps db` showed `Up (healthy)` on `127.0.0.1:5432`; `pg_isready` accepted connections; SQL returned `abdullah_core_dev|16.15`; `scripts/dev.ps1` started and awaited the healthy database.
- **Status:** Resolved

### 🐛 BUG-002: Bash startup script depended on unavailable `dirname`
- **Date Discovered:** 2026-09-24
- **Severity:** Low
- **Component:** Development script
- **Symptoms:** Git Bash reported `dirname: command not found` before the intended `.env` check.
- **Root Cause:** The first script version used an external utility to locate the repository root.
- **Fix Applied:** Replaced that call with Bash parameter expansion in `scripts/dev.sh`.
- **Verification:** `bash -n scripts/dev.sh` passed; invoking it without `.env` now reports only the expected missing configuration message, and with `.env` reports the expected missing Docker message.
- **Status:** Resolved
