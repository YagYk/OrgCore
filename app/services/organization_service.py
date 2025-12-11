import re
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from ..core.security import create_access_token, hash_password, verify_password
from ..schemas import (
    AdminLoginRequest,
    OrganizationCreateRequest,
    OrganizationResponse,
    OrganizationUpdateRequest,
    TokenResponse,
)


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", name.strip().lower()).strip("_")
    return slug or "org"


async def ensure_indexes(db: AsyncIOMotorDatabase) -> None:
    await db["organizations"].create_index("name", unique=True)
    await db["admins"].create_index(
        [("email", 1), ("org_id", 1)], unique=True, name="admin_email_org_unique"
    )


async def create_organization(
    db: AsyncIOMotorDatabase, payload: OrganizationCreateRequest
) -> OrganizationResponse:
    existing = await db["organizations"].find_one({"name": payload.organization_name})
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Organization exists")

    org_collection_name = f"org_{slugify(payload.organization_name)}"

    org_doc = {
        "name": payload.organization_name,
        "collection_name": org_collection_name,
        "created_at": datetime.now(tz=timezone.utc),
    }
    org_result = await db["organizations"].insert_one(org_doc)

    # Create admin linked to org
    admin_doc = {
        "email": payload.email,
        "password_hash": hash_password(payload.password),
        "org_id": org_result.inserted_id,
    }
    admin_result = await db["admins"].insert_one(admin_doc)

    await db["organizations"].update_one(
        {"_id": org_result.inserted_id}, {"$set": {"admin_id": admin_result.inserted_id}}
    )

    # Initialize dynamic collection
    await db.create_collection(org_collection_name)
    await db[org_collection_name].insert_one(
        {"_meta": "initialized", "org_id": org_result.inserted_id}
    )

    return OrganizationResponse(
        organization_name=payload.organization_name,
        collection_name=org_collection_name,
        admin_email=payload.email,
        created_at=org_doc["created_at"],
    )


async def get_organization(db: AsyncIOMotorDatabase, name: str) -> OrganizationResponse:
    org = await db["organizations"].find_one({"name": name})
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    admin = await db["admins"].find_one({"_id": org["admin_id"]})
    return OrganizationResponse(
        organization_name=org["name"],
        collection_name=org["collection_name"],
        admin_email=admin["email"] if admin else "unknown",
        created_at=org["created_at"],
    )


async def update_organization(
    db: AsyncIOMotorDatabase, payload: OrganizationUpdateRequest, current_admin: dict
) -> OrganizationResponse:
    org = await db["organizations"].find_one({"name": payload.organization_name})
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    if org["admin_id"] != current_admin["_id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    update_doc: dict = {}

    # Handle rename and collection sync
    new_name: Optional[str] = payload.new_organization_name
    if new_name and new_name != org["name"]:
        existing = await db["organizations"].find_one({"name": new_name})
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="New name exists")

        new_collection_name = f"org_{slugify(new_name)}"
        old_collection = db[org["collection_name"]]
        await old_collection.rename(new_collection_name, dropTarget=True)

        update_doc["name"] = new_name
        update_doc["collection_name"] = new_collection_name

    # Update admin email/password
    admin_updates: dict = {}
    if payload.new_email:
        admin_updates["email"] = payload.new_email
    if payload.new_password:
        admin_updates["password_hash"] = hash_password(payload.new_password)
    if admin_updates:
        await db["admins"].update_one({"_id": org["admin_id"]}, {"$set": admin_updates})

    if update_doc:
        await db["organizations"].update_one({"_id": org["_id"]}, {"$set": update_doc})
        org.update(update_doc)
    admin = await db["admins"].find_one({"_id": org["admin_id"]})

    return OrganizationResponse(
        organization_name=org["name"],
        collection_name=org["collection_name"],
        admin_email=admin["email"] if admin else "unknown",
        created_at=org["created_at"],
    )


async def delete_organization(db: AsyncIOMotorDatabase, org_name: str, current_admin: dict) -> None:
    org = await db["organizations"].find_one({"name": org_name})
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    if org["admin_id"] != current_admin["_id"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    await db.drop_collection(org["collection_name"])
    await db["admins"].delete_one({"_id": org["admin_id"]})
    await db["organizations"].delete_one({"_id": org["_id"]})


async def admin_login(db: AsyncIOMotorDatabase, payload: AdminLoginRequest) -> TokenResponse:
    admin = await db["admins"].find_one({"email": payload.email})
    if not admin or not verify_password(payload.password, admin["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    org = await db["organizations"].find_one({"_id": admin["org_id"]})
    if not org:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Organization missing")

    token = create_access_token({"admin_id": str(admin["_id"]), "org_id": str(org["_id"])})
    return TokenResponse(access_token=token)

