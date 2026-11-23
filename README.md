# Multi-Tenant Task & Workspace Manager

A secure, testable, and observable B2B backend API built with **FastAPI**, **SQLAlchemy 2.x**, **PostgreSQL / SQLite**, **Redis**, **Argon2id**, and **PyJWT**.

## Architecture & Key Features
- **Pure OOP Domain Layer (`app/domain/`)**: Encapsulated task state machine (`TODO -> IN_PROGRESS -> DONE -> ARCHIVED`), workspace ownership verification, and role inheritance (`BaseUser`, `StandardUser`, `AdminUser`).
- **Security & OWASP Mitigations (`app/core/security.py`, `app/api/deps.py`)**:
  - Salted Argon2id password hashing (`argon2-cffi`).
  - Short-lived HS256 JWT tokens (`sub`, `role`, `iat`, `exp`).
  - Strict multi-tenant isolation (`owner_id == current_user.id`) to prevent IDOR.
  - Role-Based Access Control (`require_admin`) protecting `/api/admin/*` endpoints.
  - Pydantic v2 response schemas (`UserPublic`, `TaskResponse`) stripping sensitive fields.
- **Caching & Background Jobs (`app/services/`)**:
  - 60-second Redis cache-aside on `GET /api/tasks/analytics` (with automatic in-memory TTL fallback) and immediate invalidation on task mutations.
  - Non-blocking background alert dispatching when tasks are created or updated with `URGENT` priority.
- **Observability (`app/core/logging_config.py`)**: Environment-aware structured logging (`DEBUG`, `INFO`, `WARNING`, `ERROR`) with automatic redaction of passwords, Bearer tokens, and DB credentials.

---

## Local Setup Instructions

1. **Create and activate virtual environment:**
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
2. **Install dependencies:**
   ```powershell
   pip install fastapi uvicorn "pydantic[email]" pydantic-settings sqlalchemy "psycopg[binary]" argon2-cffi pyjwt redis pytest httpx
   ```
3. **Configure environment variables:**
    Copy .env.example to .env and generate a 256-bit **JWT_SECRET_KEY**:
    ```powershell
    pip install fastapi uvicorn "pydantic[email]" pydantic-settings sqlalchemy "psycopg[binary]" argon2-cffi pyjwt redis pytest httpx
    ```
4. **Run the API server:**
  ```powershell
  uvicorn app.main:app --reload --port 8888
  Open interactive Swagger UI at http://127.0.0.1:8888/docs.
  ```
5. **Run the automated test suite:**
  ```powershell
  pytest -v
  ```
**JWT Secret Key Rotation Drill**
  To rotate a compromised or scheduled **JWT_SECRET_KEY** safely:
  
1. Generate a new **256-bit** cryptographic hex key**
      ```bash
      python -c "import secrets; print(secrets.token_hex(32))"
      ```
2. Replace **JWT_SECRET_KEY** in **.env (or production secret manager)** with the newly generated key.

3. Restart all FastAPI / Uvicorn worker processes so **settings.JWT_SECRET_KEY** reloads the new secret.

4.Verification: Call any protected route (e.g., **GET /api/tasks**) using a token signed with the previous key — the server immediately rejects it with **401 Unauthorized** (**InvalidSignatureError**), forcing clients to re-authenticate via **POST /api/auth/login.**    

### Day 25: 4-Layer API Debugging & Security Audit Checklist
  During the Day 25 capstone audit, all endpoints and domain layers were systematically inspected across four engineering layers:
  ## 🛡️ Engineering & Security Audit

| Audit Layer | Vulnerability / Bug Pattern Audited | Root-Cause Prevention Implemented |
| :--- | :--- | :--- |
| **1. Security** | Missing auth dependencies, IDOR via un-scoped ID lookups (`WHERE id = :id`), leaked `password_hash`, or exposed secrets in logs/Git. | Enforced `Depends(get_current_user)` & `Depends(require_admin)`, scoped queries by `owner_id == current_user.id`, stripped hashes via `UserPublic`, added `SensitiveDataFilter` log redaction, and excluded `.env` via `.gitignore`. |
| **2. Validation** | Blank task titles, weak passwords (`<10` chars), invalid priority enums, or arbitrary status strings in `PATCH`. | Enforced strict Pydantic v2 field constraints (`min_length`, `Literal` enums) at HTTP boundaries (`422`) and constructor invariants inside `Task` and `Workspace` domain classes (`400`). |
| **3. Logic** | Inverted ownership checks or illegal state jumps (e.g., reopening an `ARCHIVED` task back to `IN_PROGRESS`). | Routed all state mutations through `Task.transition_to()` using an explicit transition graph (`VALID_TRANSITIONS`), raising `StateConflictError` mapped to `409 Conflict`. |
| **4. Performance** | Repeated heavy SQL aggregations on analytics refreshes and synchronous blocking notifications on `URGENT` tasks. | Implemented 60-second per-user Redis cache-aside (`analytics:user:{id}`) with mutation-triggered invalidation, composite DB index `(owner_id, status)`, and FastAPI `BackgroundTasks` for urgent alerts. |

---

### Step 6: Run Final Test Suite, Export Passing Report & Final Git Commit

VS Code terminal mein yeh commands run karein taake saare **26 automated tests** pass hon aur green test report **`test_report.txt`** file mein export ho jaye:

```powershell
pytest -v | Tee-Object -FilePath test_report.txt