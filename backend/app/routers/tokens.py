from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import (
    get_audit_logger,
    get_current_admin,
    get_current_user,
    require_tokens_enabled,
)
from app.models.user import User
from app.schemas.token import (
    TokenAdminResponse,
    TokenCreate,
    TokenCreated,
    TokenResponse,
    TokenUpdate,
)
from app.services import token_service
from app.services.audit_service import AuditLogger

router = APIRouter(
    prefix="/api/tokens",
    tags=["tokens"],
    dependencies=[Depends(get_current_user), Depends(require_tokens_enabled)],
)


@router.get("", response_model=list[TokenResponse])
async def list_tokens(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Liste les jetons d'accès personnels de l'utilisateur courant."""
    tokens = await token_service.list_tokens(db, current_user.id)  # type: ignore[arg-type]
    return [token_service.token_to_response(t) for t in tokens]


@router.get(
    "/all",
    response_model=list[TokenAdminResponse],
    dependencies=[Depends(get_current_admin)],
)
async def list_all_tokens(db: AsyncSession = Depends(get_db)) -> list[dict]:
    rows = await token_service.list_all_tokens(db)
    return [
        {**token_service.token_to_response(token), "username": username, "user_id": uid}
        for token, username, uid in rows
    ]


@router.post("", response_model=TokenCreated, status_code=201)
async def create_token(
    payload: TokenCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    audit: AuditLogger = Depends(get_audit_logger),
) -> dict:
    """Crée un jeton d'accès personnel pour l'utilisateur courant.

    Le secret n'est renvoyé qu'ici : seul son hash est conservé.
    """
    token, raw = await token_service.create_token(
        db,
        current_user.id,  # type: ignore[arg-type]
        payload.name,
        payload.token or None,
        payload.comment,
    )
    await audit.success("create", "token", payload.name)
    return {**token_service.token_to_response(token), "token": raw}


@router.patch("/{token_id}", response_model=TokenResponse)
async def update_token(
    token_id: int,
    payload: TokenUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    audit: AuditLogger = Depends(get_audit_logger),
) -> dict:
    updated = await token_service.update_token(
        db,
        token_id,
        current_user.id,
        payload.comment,  # type: ignore[arg-type]
    )
    if updated is None:
        await audit.failure(
            "update", "token", str(token_id), {"detail": "Jeton introuvable"}
        )
        raise HTTPException(status_code=404, detail="Jeton introuvable")
    await audit.success("update", "token", updated.name)
    return token_service.token_to_response(updated)


@router.delete("/{token_id}", status_code=204)
async def delete_token(
    token_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    audit: AuditLogger = Depends(get_audit_logger),
) -> None:
    if current_user.is_admin:
        deleted = await token_service.delete_token_any(db, token_id)
    else:
        deleted = await token_service.delete_token(
            db,
            token_id,
            current_user.id,  # type: ignore[arg-type]
        )
    if not deleted:
        await audit.failure(
            "delete", "token", str(token_id), {"detail": "Jeton introuvable"}
        )
        raise HTTPException(status_code=404, detail="Jeton introuvable")
    await audit.success("delete", "token", str(token_id))
