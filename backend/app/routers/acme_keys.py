from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import get_db
from app.dependencies import get_audit_logger, get_current_admin
from app.schemas.acme import AcmeApiKeyAdminResponse, AcmeApiKeyOwnerUpdate
from app.services import acme_service, admin_service
from app.services.audit_service import AuditLogger

router = APIRouter(
    prefix="/api/acme-keys",
    tags=["acme-keys"],
    dependencies=[Depends(get_current_admin)],
)


@router.get("/all", response_model=list[AcmeApiKeyAdminResponse])
async def list_all_acme_keys(
    db: AsyncSession = Depends(get_db),
) -> list[dict[str, Any]]:
    """Admin overview of all ACME keys, across all users/zones."""
    rows = await acme_service.list_all_keys(db)
    return [
        {**acme_service.key_to_response(key), "username": username, "user_id": uid}
        for key, username, uid in rows
    ]


@router.patch("/{key_id}/owner", response_model=AcmeApiKeyAdminResponse)
async def reassign_acme_key_owner(
    key_id: int,
    payload: AcmeApiKeyOwnerUpdate,
    db: AsyncSession = Depends(get_db),
    audit: AuditLogger = Depends(get_audit_logger),
) -> dict[str, Any]:
    user = await admin_service.get_user_by_id(db, payload.user_id)
    if not user:
        await audit.failure(
            "reassign_owner",
            "acme_key",
            str(key_id),
            {"detail": "Utilisateur introuvable"},
        )
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    key = await acme_service.reassign_key_owner(db, key_id, payload.user_id)
    if key is None:
        await audit.failure(
            "reassign_owner",
            "acme_key",
            str(key_id),
            {"detail": "Clé ACME introuvable"},
        )
        raise HTTPException(status_code=404, detail="Clé ACME introuvable")
    await audit.success(
        "reassign_owner", "acme_key", str(key_id), {"new_owner": user.username}
    )
    return {
        **acme_service.key_to_response(key),
        "username": user.username,
        "user_id": user.id,
    }


@router.delete("/{key_id}", status_code=204)
async def delete_acme_key(
    key_id: int,
    db: AsyncSession = Depends(get_db),
    audit: AuditLogger = Depends(get_audit_logger),
) -> None:
    deleted = await acme_service.delete_key_any(db, key_id)
    if not deleted:
        await audit.failure(
            "delete", "acme_key", str(key_id), {"detail": "Clé ACME introuvable"}
        )
        raise HTTPException(status_code=404, detail="Clé ACME introuvable")
    await audit.success("delete", "acme_key", str(key_id))
