from bson import ObjectId
from fastapi import Depends, HTTPException, Request, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from .core.security import decode_access_token
from .db import get_master_db


async def get_db() -> AsyncIOMotorDatabase:
    return get_master_db()


async def get_current_admin(
    request: Request, db: AsyncIOMotorDatabase = Depends(get_db)
) -> dict:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")

    token = auth_header.split(" ", 1)[1]
    try:
        payload = decode_access_token(token)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    admin_id = payload.get("admin_id")
    org_id = payload.get("org_id")
    if not admin_id or not org_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Malformed token")

    try:
        admin_obj_id = ObjectId(admin_id)
        org_obj_id = ObjectId(org_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Malformed token")

    admin = await db["admins"].find_one({"_id": admin_obj_id, "org_id": org_obj_id})
    if not admin:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin not found")
    return admin

