from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.database import get_db
from app.dependencies import get_current_admin
from app.models.account import UserAccount
from app.models.record_type import RecordType
from app.models.user import User
from app.schemas.admin import (
    AccountCreate,
    AccountResponse,
    AccountUpdate,
    AdminUserResponse,
    OidcSettingsResponse,
    OidcSettingsUpdate,
    RecordTypeCreate,
    RecordTypeResponse,
    RecordTypeUpdate,
    ResetPasswordRequest,
    UserAccountAssign,
    UserCreateRequest,
    UserUpdateRequest,
)
from app.services import admin_service, audit_service
from app.services.auth_service import clear_oidc_cache, get_user_by_username

router = APIRouter(prefix="/api/admin", dependencies=[Depends(get_current_admin)])


# ── Users ─────────────────────────────────────────────────────────────────────


@router.get("/users", response_model=list[AdminUserResponse])
async def list_users(db: AsyncSession = Depends(get_db)) -> list:
    return await admin_service.list_users(db)


@router.post("/users", response_model=AdminUserResponse, status_code=201)
async def create_user(
    payload: UserCreateRequest,
    request: Request,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if await get_user_by_username(db, payload.username):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Nom d'utilisateur déjà utilisé",
        )
    if len(payload.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The password must contain at least 8 characters.",
        )
    user = await admin_service.create_local_user(
        db,
        username=payload.username,
        password=payload.password,
        email=payload.email,
        is_admin=payload.is_admin,
    )
    await audit_service.log_action(
        db,
        username=current_admin.username,
        user_id=current_admin.id,
        action="create",
        resource_type="user",
        resource_id=payload.username,
        ip_address=request.client.host if request.client else None,
    )
    accounts = await admin_service.get_user_account_names(db, user.id)  # type: ignore[arg-type]
    account_roles = await admin_service.get_user_account_roles(db, user.id)  # type: ignore[arg-type]
    return {**user.model_dump(), "accounts": accounts, "account_roles": account_roles}


@router.patch("/users/{user_id}", response_model=AdminUserResponse)
async def update_user(
    user_id: int,
    payload: UserUpdateRequest,
    request: Request,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    user = await admin_service.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    data = payload.model_dump(exclude_none=True)
    user = await admin_service.update_user(db, user, data)
    await audit_service.log_action(
        db,
        username=current_admin.username,
        user_id=current_admin.id,
        action="update",
        resource_type="user",
        resource_id=user.username,
        details=data,
        ip_address=request.client.host if request.client else None,
    )
    accounts = await admin_service.get_user_account_names(db, user.id)  # type: ignore[arg-type]
    account_roles = await admin_service.get_user_account_roles(db, user.id)  # type: ignore[arg-type]
    return {**user.model_dump(), "accounts": accounts, "account_roles": account_roles}


@router.post("/users/{user_id}/reset-password", status_code=204)
async def reset_password(
    user_id: int,
    payload: ResetPasswordRequest,
    request: Request,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    user = await admin_service.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_oidc:
        raise HTTPException(
            status_code=400,
            detail="SSO users cannot have their password reset",
        )
    if len(payload.new_password) < 8:
        raise HTTPException(
            status_code=422,
            detail="New password must contain at least 8 characters",
        )
    await admin_service.reset_password(db, user, payload.new_password)
    await audit_service.log_action(
        db,
        username=current_admin.username,
        user_id=current_admin.id,
        action="reset_password",
        resource_type="user",
        resource_id=user.username,
        ip_address=request.client.host if request.client else None,
    )


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(
    user_id: int,
    request: Request,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    if current_admin.id == user_id:
        raise HTTPException(
            status_code=400, detail="Impossible to delete your own account"
        )
    user = await admin_service.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    username_deleted = user.username
    await admin_service.delete_user(db, user)
    await audit_service.log_action(
        db,
        username=current_admin.username,
        user_id=current_admin.id,
        action="delete",
        resource_type="user",
        resource_id=username_deleted,
        ip_address=request.client.host if request.client else None,
    )


# ── Accounts ──────────────────────────────────────────────────────────────────


@router.get("/accounts", response_model=list[AccountResponse])
async def list_accounts(db: AsyncSession = Depends(get_db)) -> list:
    return await admin_service.list_accounts(db)


@router.post("/accounts", response_model=AccountResponse, status_code=201)
async def create_account(
    payload: AccountCreate,
    request: Request,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if await admin_service.get_account_by_name(db, payload.name):
        raise HTTPException(
            status_code=409, detail="An account with this name already exists"
        )
    account = await admin_service.create_account(db, payload.name, payload.description)
    await audit_service.log_action(
        db,
        username=current_admin.username,
        user_id=current_admin.id,
        action="create",
        resource_type="account",
        resource_id=payload.name,
        ip_address=request.client.host if request.client else None,
    )
    return {**account.model_dump(), "user_count": 0}


@router.patch("/accounts/{account_id}", response_model=AccountResponse)
async def update_account(
    account_id: int, payload: AccountUpdate, db: AsyncSession = Depends(get_db)
) -> dict:
    account = await admin_service.get_account_by_id(db, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    data = payload.model_dump(exclude_none=True)
    account = await admin_service.update_account(db, account, data)
    count = await db.exec(  # type: ignore[call-overload]
        select(UserAccount).where(UserAccount.account_id == account.id)
    )
    return {**account.model_dump(), "user_count": len(count.all())}


@router.put("/accounts/{account_id}/users", status_code=204)
async def set_account_users(
    account_id: int, payload: UserAccountAssign, db: AsyncSession = Depends(get_db)
) -> None:
    account = await admin_service.get_account_by_id(db, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    await admin_service.set_account_users(db, account_id, payload.user_ids)


@router.delete("/accounts/{account_id}", status_code=204)
async def delete_account(
    account_id: int,
    request: Request,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> None:
    account = await admin_service.get_account_by_id(db, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    account_name = account.name
    await admin_service.delete_account(db, account)
    await audit_service.log_action(
        db,
        username=current_admin.username,
        user_id=current_admin.id,
        action="delete",
        resource_type="account",
        resource_id=account_name,
        ip_address=request.client.host if request.client else None,
    )


# ── OIDC Settings ─────────────────────────────────────────────────────────────


@router.get("/oidc", response_model=OidcSettingsResponse)
async def get_oidc_settings(db: AsyncSession = Depends(get_db)) -> OidcSettingsResponse:
    db_cfg = await admin_service.get_oidc_settings(db)
    if db_cfg:
        return OidcSettingsResponse(**db_cfg.model_dump(exclude={"id"}))
    return OidcSettingsResponse(
        enabled=False,
        client_id="",
        client_secret="",
        discovery_url="",
        redirect_uri="http://localhost:8080/api/auth/oidc/callback",
        scopes="openid email profile",
        local_login_disabled=False,
    )


@router.put("/oidc", response_model=OidcSettingsResponse)
async def update_oidc_settings(
    payload: OidcSettingsUpdate,
    request: Request,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
) -> OidcSettingsResponse:
    clear_oidc_cache()
    cfg = await admin_service.upsert_oidc_settings(db, payload.model_dump())
    await audit_service.log_action(
        db,
        username=current_admin.username,
        user_id=current_admin.id,
        action="update",
        resource_type="oidc_settings",
        ip_address=request.client.host if request.client else None,
    )
    return OidcSettingsResponse(**cfg.model_dump(exclude={"id"}))


# ── Record Types ──────────────────────────────────────────────────────────────


@router.get("/record-types", response_model=list[RecordTypeResponse])
async def list_record_types(db: AsyncSession = Depends(get_db)) -> list:
    result = await db.exec(select(RecordType).order_by(RecordType.name))  # type: ignore[call-overload]
    return result.all()


@router.post("/record-types", response_model=RecordTypeResponse, status_code=201)
async def create_record_type(
    payload: RecordTypeCreate, db: AsyncSession = Depends(get_db)
) -> RecordType:
    existing = await db.exec(  # type: ignore[call-overload]
        select(RecordType).where(RecordType.name == payload.name.upper())
    )
    if existing.first():
        raise HTTPException(status_code=409, detail="This record type already exists")
    rt = RecordType(
        name=payload.name.upper(),
        enabled=payload.enabled,
        applicable_to=payload.applicable_to,
    )
    db.add(rt)
    await db.commit()
    await db.refresh(rt)
    return rt


@router.patch("/record-types/{rt_id}", response_model=RecordTypeResponse)
async def update_record_type(
    rt_id: int, payload: RecordTypeUpdate, db: AsyncSession = Depends(get_db)
) -> RecordType:
    result = await db.exec(select(RecordType).where(RecordType.id == rt_id))  # type: ignore[call-overload]
    rt = result.first()
    if not rt:
        raise HTTPException(status_code=404, detail="Record type not found")
    data = payload.model_dump(exclude_none=True)
    for key, value in data.items():
        setattr(rt, key, value)
    db.add(rt)
    await db.commit()
    await db.refresh(rt)
    return rt


@router.delete("/record-types/{rt_id}", status_code=204)
async def delete_record_type(rt_id: int, db: AsyncSession = Depends(get_db)) -> None:
    result = await db.exec(select(RecordType).where(RecordType.id == rt_id))  # type: ignore[call-overload]
    rt = result.first()
    if not rt:
        raise HTTPException(status_code=404, detail="Record type not found")
    await db.delete(rt)
    await db.commit()
