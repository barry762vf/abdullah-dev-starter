# 📐 .ai/ARCHITECTURE.md — AI Quick Reference Guide

> **Document:** `.ai/ARCHITECTURE.md`  
> **Status:** Active Reference  
> **Platform:** Abdullah Developer Core (`abdullah-dev-core`)

---

## 1. System Topology & Pattern Rules

```
[Browser / Client] 
       │ (HTTPS / JSON REST API)
       ▼
[FastAPI Backend (Uvicorn)]
  ├── app/core/          -> config, database.get_db, logging, exceptions, security
  ├── app/api/deps.py    -> current DB identity and role guards
  ├── app/api/v1/        -> auth.py, users.py, health.py (admin.py in Phase 5)
  ├── app/schemas/       -> Pydantic v2 validation contracts
  ├── app/services/      -> Pure business logic
  ├── app/models/        -> SQLAlchemy 2.0 ORM entities
  └── app/integrations/  -> Pluggable slots (AI, Telegram, Storage)
       │ (SQLAlchemy 2.0 Async / asyncpg)
       ▼
[PostgreSQL 16 / Supabase Database]
```

---

## 2. Mandatory Coding Conventions for Agents

### Backend Patterns:
1. **Dependency Injection:** Database sessions must ALWAYS be acquired through `db: AsyncSession = Depends(get_db)`. Never instantiate engines or sessions inside route handlers.
2. **Permission Guarding:** Restrict endpoints using `User = Depends(require_role(["admin", "superadmin"]))`.
3. **Data Sanitization:** Never return ORM instances directly. Always use `response_model=UserResponse` in route decorators.
4. **Error Handling:** Raise `AppException` or subclasses from `app.core.exceptions`. Never let raw unhandled Python exceptions bubble up to users without translation.

### Frontend Patterns:
1. **API Calls:** Use `lib/api.ts` (configured Axios instance). Do not use raw browser `fetch()` directly in components.
2. **Server Data:** Wrap all GET queries in `useQuery` from `@tanstack/react-query` and mutations in `useMutation`.
3. **Bilingual Styling:** Never hardcode left/right margins. Use Tailwind logical classes:
   - Use `ms-4` instead of `ml-4`
   - Use `me-4` instead of `mr-4`
   - Use `ps-3` instead of `pl-3`
   - Use `pe-3` instead of `pr-3`
4. **Translations:** Wrap all UI strings in `t('common.login')` using `useTranslation()`.
