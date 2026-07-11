from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import (
    get_audit_logger,
    get_current_admin,
    get_current_user,
    require_api_keys_enabled,
)
from app.models.user import User
from app.schemas.acme import (
    AcmeApiKeyAdminResponse,
    AcmeApiKeyCreate,
    AcmeApiKeyCreated,
    AcmeApiKeyResponse,
    AcmeApiKeyUpdate,
)
from app.services import acme_service
from app.services.audit_service import AuditLogger

router = APIRouter(
    prefix="/api/acme-keys",
    dependencies=[Depends(get_current_user), Depends(require_api_keys_enabled)],
)


@router.get("", response_model=list[AcmeApiKeyResponse])
async def list_acme_keys(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Liste les clés API (key_type=api) de l'utilisateur courant.
    Les clés ACME sont désormais gérées par zone via /api/zones/{zone_id}/acme-keys."""
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
    audit: AuditLogger = Depends(get_audit_logger),
) -> dict:
    """Crée une clé API (key_type=api) pour l'utilisateur courant.
    La création de clés ACME se fait désormais depuis l'onglet ACME Keys de la zone."""
    if payload.key_type == "acme":
        await audit.failure(
            "create",
            "acme_key",
            payload.name,
            {
                "detail": "Les clés ACME doivent être créées depuis la zone via /api/zones/{zone_id}/acme-keys"
            },
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Les clés ACME doivent être créées depuis la zone via /api/zones/{zone_id}/acme-keys",
        )
    key, raw = await acme_service.create_key(
        db,
        current_user.id,
        payload.name,
        payload.key or None,
        payload.key_type,
        payload.comment,
    )
    await audit.success("create", "acme_key", payload.name)
    return {**acme_service.key_to_response(key), "key": raw}


@router.patch("/{key_id}", response_model=AcmeApiKeyResponse)
async def update_acme_key(
    key_id: int,
    payload: AcmeApiKeyUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    audit: AuditLogger = Depends(get_audit_logger),
) -> dict:
    updated = await acme_service.update_key(
        db, key_id, current_user.id, payload.comment
    )
    if updated is None:
        await audit.failure(
            "update", "acme_key", str(key_id), {"detail": "Clé API introuvable"}
        )
        raise HTTPException(status_code=404, detail="Clé API introuvable")
    await audit.success("update", "acme_key", updated.name)
    return acme_service.key_to_response(updated)


@router.delete("/{key_id}", status_code=204)
async def delete_acme_key(
    key_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    audit: AuditLogger = Depends(get_audit_logger),
) -> None:
    if current_user.is_admin:
        deleted = await acme_service.delete_key_any(db, key_id)
    else:
        deleted = await acme_service.delete_key(db, key_id, current_user.id)
    if not deleted:
        await audit.failure(
            "delete", "acme_key", str(key_id), {"detail": "Clé API introuvable"}
        )
        raise HTTPException(status_code=404, detail="Clé API introuvable")
    await audit.success("delete", "acme_key", str(key_id))
