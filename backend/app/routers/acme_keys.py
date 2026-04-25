from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_admin, get_current_user
from app.models.user import User
from app.schemas.acme import (
    AcmeApiKeyAdminResponse,
    AcmeApiKeyCreate,
    AcmeApiKeyCreated,
    AcmeApiKeyResponse,
    AcmeApiKeyZonesUpdate,
)
from app.services import acme_service, admin_service

router = APIRouter(prefix="/api/acme-keys", dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[AcmeApiKeyResponse])
async def list_acme_keys(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    keys = await acme_service.list_keys(db, current_user.id)
    return [acme_service.key_to_response(k) for k in keys]


@router.get(
    "/all",
    response_model=list[AcmeApiKeyAdminResponse],
    dependencies=[Depends(get_current_admin)],
)
async def list_all_acme_keys(db: AsyncSession = Depends(get_db)) -> list[dict]:
    rows = await acme_service.list_all_keys(db)
    return [
        {**acme_service.key_to_response(key), "username": username, "user_id": uid}
        for key, username, uid in rows
    ]


@router.post("", response_model=AcmeApiKeyCreated, status_code=201)
async def create_acme_key(
    payload: AcmeApiKeyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if payload.key_type == "acme":
        if not current_user.is_admin and not await admin_service.user_is_account_admin(
            db,
            current_user.id,  # type: ignore[arg-type]
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account admin or super admin required to create ACME keys",
            )
    key, raw = await acme_service.create_key(
        db, current_user.id, payload.name, payload.key or None, payload.key_type
    )
    return {**acme_service.key_to_response(key), "key": raw}


@router.put("/{key_id}/zones", response_model=AcmeApiKeyResponse)
async def update_acme_key_zones(
    key_id: int,
    payload: AcmeApiKeyZonesUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    key = await acme_service.get_key(db, key_id, current_user.id)
    if key is None:
        raise HTTPException(status_code=404, detail="API key not found")
    if key.key_type != "acme":
        raise HTTPException(
            status_code=400, detail="Zone assignment is only available for ACME keys"
        )
    updated = await acme_service.update_zones(
        db, key_id, current_user.id, payload.zones
    )
    return acme_service.key_to_response(updated)  # type: ignore[arg-type]


@router.delete("/{key_id}", status_code=204)
async def delete_acme_key(
    key_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    if current_user.is_admin:
        deleted = await acme_service.delete_key_any(db, key_id)
    else:
        deleted = await acme_service.delete_key(db, key_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="API key not found")
