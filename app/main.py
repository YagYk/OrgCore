from fastapi import Depends, FastAPI, HTTPException, status

from .dependencies import get_current_admin, get_db
from .schemas import (
    AdminLoginRequest,
    OrganizationCreateRequest,
    OrganizationResponse,
    OrganizationUpdateRequest,
    TokenResponse,
)
from .services.organization_service import (
    admin_login,
    create_organization,
    delete_organization,
    ensure_indexes,
    get_organization,
    update_organization,
)

app = FastAPI(title="Organization Management Service", version="1.0.0")


@app.on_event("startup")
async def startup_event() -> None:
    db = await get_db()
    await ensure_indexes(db)


@app.post("/org/create", response_model=OrganizationResponse)
async def org_create(payload: OrganizationCreateRequest, db=Depends(get_db)):
    return await create_organization(db, payload)


@app.get("/org/get", response_model=OrganizationResponse)
async def org_get(organization_name: str, db=Depends(get_db)):
    return await get_organization(db, organization_name)


@app.put("/org/update", response_model=OrganizationResponse)
async def org_update(
    payload: OrganizationUpdateRequest,
    db=Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    if payload.organization_name != await _resolve_org_name(db, current_admin["_id"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    return await update_organization(db, payload, current_admin)


@app.delete("/org/delete", status_code=status.HTTP_204_NO_CONTENT)
async def org_delete(
    organization_name: str,
    db=Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    if organization_name != await _resolve_org_name(db, current_admin["_id"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    await delete_organization(db, organization_name, current_admin)
    return None


@app.post("/admin/login", response_model=TokenResponse)
async def admin_login_route(payload: AdminLoginRequest, db=Depends(get_db)):
    return await admin_login(db, payload)


async def _resolve_org_name(db, admin_id) -> str | None:
    org = await db["organizations"].find_one({"admin_id": admin_id})
    return org["name"] if org else None

