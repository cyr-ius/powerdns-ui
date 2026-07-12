from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_audit_logger, get_current_admin
from app.schemas.acme import AcmeApiKeyAdminResponse
from app.services import acme_service
from app.services.audit_service import AuditLogger

router = APIRouter(
    prefix="/api/acme-keys",
    tags=["acme-keys"],
    dependencies=[Depends(get_current_admin)],
)


@router.get("/all", response_model=list[AcmeApiKeyAdminResponse])
async def list_all_acme_keys(db: AsyncSession = Depends(get_db)) -> list[dict]:
    """Vue d'ensemble (admin) de toutes les clés ACME, tous utilisateurs/zones confondus."""
    rows = await acme_service.list_all_keys(db)
    return [
        {**acme_service.key_to_response(key), "username": username, "user_id": uid}
        for key, username, uid in rows
    ]


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
