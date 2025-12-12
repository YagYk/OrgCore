# Organization Management Service (FastAPI + MongoDB)

Minimal multi-tenant style backend for creating and managing organizations with per-org collections and admin authentication.

## Quickstart
- Prerequisites: Python 3.11+, MongoDB running locally (default `mongodb://localhost:27017`).
- Install deps:
  ```
  python -m venv .venv
  .venv\Scripts\activate  # Windows
  pip install -r requirements.txt
  ```
- Configure env (optional): copy `.env.example` to `.env` and adjust values.
- Run:
  ```
  uvicorn app.main:app --reload
  ```
- Docs: http://localhost:8000/docs

## Configuration
Environment variables (see `.env.example`):
- `MONGODB_URI` – Mongo connection string (default `mongodb://localhost:27017`).
- `MASTER_DB_NAME` – database holding org metadata and admin users (`master_db`).
- `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `JWT_EXPIRES_MINUTES` – token settings.

## API Outline
- `POST /org/create` – create org + admin; dynamic collection `org_<slug>`.
- `GET /org/get?organization_name=` – fetch org metadata.
- `PUT /org/update` – rename org/collection, update admin (auth required).
- `DELETE /org/delete?organization_name=` – delete org + collection (auth required).
- `POST /admin/login` – get JWT for admin.

## High-level Design
```
[FastAPI]
   |
   |-- dependencies (auth, db)
   |-- services/organization_service.py
   |
[Master MongoDB]
   |-- organizations (name, collection_name, admin_id, created_at)
   |-- admins (email, password_hash, org_id)
   |-- org_<name> (dynamic per org data)
```
- Master Database stores metadata and admin credentials (bcrypt hashed).
- JWT embeds `admin_id` and `org_id` for authorization.
- Dynamic collection created per org; rename on org name change.
- Indexes enforce unique org names and admin email per org.

## Trade-offs and Notes
- Single Mongo database keeps setup simple; for larger scale, move per-org databases/collections to separate clusters.
- Renaming uses Mongo collection rename; for heavy data, consider background copy + switch.
- JWT secret must be strong and rotated; add refresh tokens and RBAC for production.
- Add rate limiting and request validation layers if exposed publicly.

## Example Requests
Create org:
```
POST /org/create
{ "organization_name": "acme", "email": "admin@acme.com", "password": "secret123" }
```
Login:
```
POST /admin/login
{ "email": "admin@acme.com", "password": "secret123" }
```
Use returned `Authorization: Bearer <token>` for update/delete calls.

