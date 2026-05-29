from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.database import get_db
from app.dependencies import get_audit_logger, get_current_admin
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
from app.services import admin_service
from app.services.audit_service import AuditLogger
from app.services.auth_service import clear_oidc_cache, get_user_by_username

router = APIRouter(prefix="/api/admin", dependencies=[Depends(get_current_admin)])


# ── Users ─────────────────────────────────────────────────────────────────────


@router.get("/users", response_model=list[AdminUserResponse])
async def list_users(db: AsyncSession = Depends(get_db)) -> list:
    return await admin_service.list_users(db)


@router.post("/users", response_model=AdminUserResponse, status_code=201)
async def create_user(
    payload: UserCreateRequest,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
    audit: AuditLogger = Depends(get_audit_logger),
) -> dict:
    if await get_user_by_username(db, payload.username):
        await audit.failure(
            "create",
            "user",
            payload.username,
            {"detail": "Nom d'utilisateur déjà utilisé"},
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Nom d'utilisateur déjà utilisé",
        )
    if len(payload.password) < 8:
        await audit.failure(
            "create",
            "user",
            payload.username,
            {"detail": "The password must contain at least 8 characters."},
        )
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
    await audit.success("create", "user", payload.username)
    accounts = await admin_service.get_user_account_names(db, user.id)  # type: ignore[arg-type]
    account_roles = await admin_service.get_user_account_roles(db, user.id)  # type: ignore[arg-type]
    return {**user.model_dump(), "accounts": accounts, "account_roles": account_roles}


@router.patch("/users/{user_id}", response_model=AdminUserResponse)
async def update_user(
    user_id: int,
    payload: UserUpdateRequest,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
    audit: AuditLogger = Depends(get_audit_logger),
) -> dict:
    user = await admin_service.get_user_by_id(db, user_id)
    if not user:
        await audit.failure(
            "update", "user", str(user_id), {"detail": "User not found"}
        )
        raise HTTPException(status_code=404, detail="User not found")
    data = payload.model_dump(exclude_none=True)
    if data.get("is_admin") is False and user.is_admin:
        if await admin_service.count_admins(db) <= 1:
            await audit.failure(
                "update",
                "user",
                user.username,
                {"detail": "Cannot demote the last super admin"},
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot demote the last super admin",
            )
    user = await admin_service.update_user(db, user, data)
    await audit.success("update", "user", user.username, data)
    accounts = await admin_service.get_user_account_names(db, user.id)  # type: ignore[arg-type]
    account_roles = await admin_service.get_user_account_roles(db, user.id)  # type: ignore[arg-type]
    return {**user.model_dump(), "accounts": accounts, "account_roles": account_roles}


@router.post("/users/{user_id}/reset-password", status_code=204)
async def reset_password(
    user_id: int,
    payload: ResetPasswordRequest,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
    audit: AuditLogger = Depends(get_audit_logger),
) -> None:
    user = await admin_service.get_user_by_id(db, user_id)
    if not user:
        await audit.failure(
            "reset_password", "user", str(user_id), {"detail": "User not found"}
        )
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_oidc:
        await audit.failure(
            "reset_password",
            "user",
            user.username,
            {"detail": "SSO users cannot have their password reset"},
        )
        raise HTTPException(
            status_code=400,
            detail="SSO users cannot have their password reset",
        )
    if len(payload.new_password) < 8:
        await audit.failure(
            "reset_password",
            "user",
            user.username,
            {"detail": "New password must contain at least 8 characters"},
        )
        raise HTTPException(
            status_code=422,
            detail="New password must contain at least 8 characters",
        )
    await admin_service.reset_password(db, user, payload.new_password)
    await audit.success("reset_password", "user", user.username)


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(
    user_id: int,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
    audit: AuditLogger = Depends(get_audit_logger),
) -> None:
    if current_admin.id == user_id:
        await audit.failure(
            "delete",
            "user",
            current_admin.username,
            {"detail": "Impossible to delete your own account"},
        )
        raise HTTPException(
            status_code=400, detail="Impossible to delete your own account"
        )
    user = await admin_service.get_user_by_id(db, user_id)
    if not user:
        await audit.failure(
            "delete", "user", str(user_id), {"detail": "User not found"}
        )
        raise HTTPException(status_code=404, detail="User not found")
    username_deleted = user.username
    await admin_service.delete_user(db, user)
    await audit.success("delete", "user", username_deleted)


# ── Accounts ──────────────────────────────────────────────────────────────────


@router.get("/accounts", response_model=list[AccountResponse])
async def list_accounts(db: AsyncSession = Depends(get_db)) -> list:
    return await admin_service.list_accounts(db)


@router.post("/accounts", response_model=AccountResponse, status_code=201)
async def create_account(
    payload: AccountCreate,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
    audit: AuditLogger = Depends(get_audit_logger),
) -> dict:
    if await admin_service.get_account_by_name(db, payload.name):
        await audit.failure(
            "create",
            "account",
            payload.name,
            {"detail": "An account with this name already exists"},
        )
        raise HTTPException(
            status_code=409, detail="An account with this name already exists"
        )
    account = await admin_service.create_account(db, payload.name, payload.description)
    await audit.success("create", "account", payload.name)
    return {**account.model_dump(), "user_count": 0}


@router.patch("/accounts/{account_id}", response_model=AccountResponse)
async def update_account(
    account_id: int,
    payload: AccountUpdate,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
    audit: AuditLogger = Depends(get_audit_logger),
) -> dict:
    account = await admin_service.get_account_by_id(db, account_id)
    if not account:
        await audit.failure(
            "update", "account", str(account_id), {"detail": "Account not found"}
        )
        raise HTTPException(status_code=404, detail="Account not found")
    data = payload.model_dump(exclude_none=True)
    account = await admin_service.update_account(db, account, data)
    await audit.success("update", "account", account.name, data)
    count = await db.exec(  # type: ignore[call-overload]
        select(UserAccount).where(UserAccount.account_id == account.id)
    )
    return {**account.model_dump(), "user_count": len(count.all())}


@router.put("/accounts/{account_id}/users", status_code=204)
async def set_account_users(
    account_id: int,
    payload: UserAccountAssign,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
    audit: AuditLogger = Depends(get_audit_logger),
) -> None:
    account = await admin_service.get_account_by_id(db, account_id)
    if not account:
        await audit.failure(
            "assign_users", "account", str(account_id), {"detail": "Account not found"}
        )
        raise HTTPException(status_code=404, detail="Account not found")
    await admin_service.set_account_users(db, account_id, payload.user_ids)
    await audit.success(
        "assign_users", "account", account.name, {"user_ids": payload.user_ids}
    )


@router.delete("/accounts/{account_id}", status_code=204)
async def delete_account(
    account_id: int,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
    audit: AuditLogger = Depends(get_audit_logger),
) -> None:
    account = await admin_service.get_account_by_id(db, account_id)
    if not account:
        await audit.failure(
            "delete", "account", str(account_id), {"detail": "Account not found"}
        )
        raise HTTPException(status_code=404, detail="Account not found")
    account_name = account.name
    await admin_service.delete_account(db, account)
    await audit.success("delete", "account", account_name)


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
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
    audit: AuditLogger = Depends(get_audit_logger),
) -> OidcSettingsResponse:
    clear_oidc_cache()
    cfg = await admin_service.upsert_oidc_settings(db, payload.model_dump())
    await audit.success("update", "oidc_settings")
    return OidcSettingsResponse(**cfg.model_dump(exclude={"id"}))


# ── Record Types ──────────────────────────────────────────────────────────────


@router.get("/record-types", response_model=list[RecordTypeResponse])
async def list_record_types(db: AsyncSession = Depends(get_db)) -> list:
    result = await db.exec(select(RecordType).order_by(RecordType.name))  # type: ignore[call-overload]
    return result.all()


@router.post("/record-types", response_model=RecordTypeResponse, status_code=201)
async def create_record_type(
    payload: RecordTypeCreate,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
    audit: AuditLogger = Depends(get_audit_logger),
) -> RecordType:
    name = payload.name.upper()
    existing = await db.exec(  # type: ignore[call-overload]
        select(RecordType).where(RecordType.name == name)
    )
    if existing.first():
        await audit.failure(
            "create", "record_type", name, {"detail": "This record type already exists"}
        )
        raise HTTPException(status_code=409, detail="This record type already exists")
    rt = RecordType(
        name=name,
        enabled=payload.enabled,
        applicable_to=payload.applicable_to,
    )
    db.add(rt)
    await db.commit()
    await db.refresh(rt)
    await audit.success("create", "record_type", name)
    return rt


@router.patch("/record-types/{rt_id}", response_model=RecordTypeResponse)
async def update_record_type(
    rt_id: int,
    payload: RecordTypeUpdate,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
    audit: AuditLogger = Depends(get_audit_logger),
) -> RecordType:
    result = await db.exec(select(RecordType).where(RecordType.id == rt_id))  # type: ignore[call-overload]
    rt = result.first()
    if not rt:
        await audit.failure(
            "update", "record_type", str(rt_id), {"detail": "Record type not found"}
        )
        raise HTTPException(status_code=404, detail="Record type not found")
    data = payload.model_dump(exclude_none=True)
    for key, value in data.items():
        setattr(rt, key, value)
    db.add(rt)
    await db.commit()
    await db.refresh(rt)
    await audit.success("update", "record_type", rt.name, data)
    return rt


@router.delete("/record-types/{rt_id}", status_code=204)
async def delete_record_type(
    rt_id: int,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
    audit: AuditLogger = Depends(get_audit_logger),
) -> None:
    result = await db.exec(select(RecordType).where(RecordType.id == rt_id))  # type: ignore[call-overload]
    rt = result.first()
    if not rt:
        await audit.failure(
            "delete", "record_type", str(rt_id), {"detail": "Record type not found"}
        )
        raise HTTPException(status_code=404, detail="Record type not found")
    rt_name = rt.name
    await db.delete(rt)
    await db.commit()
    await audit.success("delete", "record_type", rt_name)
