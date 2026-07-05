from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.account import Account, UserAccount, ZoneRole
from app.models.acme_key import AcmeApiKey
from app.models.oidc_settings import OidcSettings
from app.models.user import User
from app.services.auth_service import hash_password
from app.services.pdns_service import pdns_request

# ── Users ─────────────────────────────────────────────────────────────────────


async def list_users(db: AsyncSession) -> list[dict]:
    result = await db.exec(select(User))  # type: ignore[call-overload]
    users = result.all()
    output = []
    for user in users:
        accounts = await get_user_account_names(db, user.id)  # type: ignore[arg-type]
        account_roles = await get_user_account_roles(db, user.id)  # type: ignore[arg-type]
        output.append(
            {**user.model_dump(), "accounts": accounts, "account_roles": account_roles}
        )
    return output


async def count_admins(db: AsyncSession) -> int:
    result = await db.exec(select(User).where(User.is_admin == True))  # noqa: E712  # type: ignore[call-overload]
    return len(result.all())


async def count_active_oidc_admins(db: AsyncSession) -> int:
    """Count admins able to sign in through OIDC (active, admin, OIDC-provisioned).

    These are the only admins who can still authenticate once local login is
    disabled, so this count guards against locking everyone out.
    """
    result = await db.exec(  # type: ignore[call-overload]
        select(User).where(
            User.is_admin == True,  # noqa: E712
            User.is_active == True,  # noqa: E712
            User.is_oidc == True,  # noqa: E712
        )
    )
    return len(result.all())


async def list_users_basic(db: AsyncSession) -> list[dict]:
    result = await db.exec(select(User).where(User.is_active == True))  # noqa: E712  # type: ignore[call-overload]
    return [{"id": u.id, "username": u.username} for u in result.all()]


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    result = await db.exec(select(User).where(User.id == user_id))  # type: ignore[call-overload]
    return result.first()


async def create_local_user(
    db: AsyncSession,
    username: str,
    password: str,
    email: str | None = None,
    is_admin: bool = False,
) -> User:
    user = User(
        username=username,
        email=email,
        hashed_password=hash_password(password),
        is_oidc=False,
        is_admin=is_admin,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def update_user(db: AsyncSession, user: User, data: dict) -> User:
    for key, value in data.items():
        if value is not None:
            setattr(user, key, value)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def reset_password(db: AsyncSession, user: User, new_password: str) -> None:
    user.hashed_password = hash_password(new_password)
    db.add(user)
    await db.commit()


async def delete_user(db: AsyncSession, user: User) -> None:
    # Remove account memberships first
    assoc = await db.exec(  # type: ignore[call-overload]
        select(UserAccount).where(UserAccount.user_id == user.id)
    )
    for row in assoc.all():
        await db.delete(row)
    # Detach ACME keys from their creator: they stay valid (authorization is
    # carried by the zone) but no longer point to a deleted user.
    keys = await db.exec(  # type: ignore[call-overload]
        select(AcmeApiKey).where(AcmeApiKey.user_id == user.id)
    )
    for key in keys.all():
        key.user_id = None
        db.add(key)
    await db.delete(user)
    await db.commit()


# ── Accounts ──────────────────────────────────────────────────────────────────


async def list_accounts(db: AsyncSession) -> list[dict]:
    result = await db.exec(select(Account))  # type: ignore[call-overload]
    accounts = result.all()
    output = []
    for acc in accounts:
        count_result = await db.exec(  # type: ignore[call-overload]
            select(UserAccount).where(UserAccount.account_id == acc.id)
        )
        output.append({**acc.model_dump(), "user_count": len(count_result.all())})
    return output


async def get_account_by_id(db: AsyncSession, account_id: int) -> Account | None:
    result = await db.exec(select(Account).where(Account.id == account_id))  # type: ignore[call-overload]
    return result.first()


async def get_account_by_name(db: AsyncSession, name: str) -> Account | None:
    result = await db.exec(select(Account).where(Account.name == name))  # type: ignore[call-overload]
    return result.first()


async def create_account(
    db: AsyncSession, name: str, description: str | None = None
) -> Account:
    account = Account(name=name, description=description)
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return account


async def update_account(db: AsyncSession, account: Account, data: dict) -> Account:
    for key, value in data.items():
        if value is not None:
            setattr(account, key, value)
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return account


async def delete_account(db: AsyncSession, account: Account) -> None:
    # Detach PowerDNS zones still referencing this account by name, otherwise
    # they would keep pointing to an account that no longer exists.
    await _clear_account_on_zones(account.name)
    assoc = await db.exec(  # type: ignore[call-overload]
        select(UserAccount).where(UserAccount.account_id == account.id)
    )
    for row in assoc.all():
        await db.delete(row)
    await db.delete(account)
    await db.commit()


async def _clear_account_on_zones(account_name: str) -> None:
    """Reset the `account` field on every PowerDNS zone bound to this account."""
    zones = await pdns_request("GET", "/servers/localhost/zones")
    for zone in zones:
        if (zone.get("account") or "") == account_name:
            await pdns_request(
                "PUT",
                f"/servers/localhost/zones/{zone['id']}",
                json={"account": ""},
            )


async def set_account_users(
    db: AsyncSession,
    account_id: int,
    user_ids: list[int],
    role: ZoneRole = ZoneRole.admin,
) -> None:
    existing = await db.exec(  # type: ignore[call-overload]
        select(UserAccount).where(UserAccount.account_id == account_id)
    )
    for row in existing.all():
        await db.delete(row)
    for uid in user_ids:
        db.add(UserAccount(user_id=uid, account_id=account_id, role=role))
    await db.commit()


async def get_user_account_names(db: AsyncSession, user_id: int) -> list[str]:
    result = await db.exec(  # type: ignore[call-overload]
        select(Account.name)
        .join(UserAccount, UserAccount.account_id == Account.id)  # type: ignore[arg-type]
        .where(UserAccount.user_id == user_id)
    )
    return list(result.all())


async def get_user_account_roles(db: AsyncSession, user_id: int) -> dict[str, str]:
    uas_result = await db.exec(  # type: ignore[call-overload]
        select(UserAccount).where(UserAccount.user_id == user_id)
    )
    uas = uas_result.all()
    output: dict[str, str] = {}
    for ua in uas:
        acc_result = await db.exec(  # type: ignore[call-overload]
            select(Account).where(Account.id == ua.account_id)
        )
        acc = acc_result.first()
        if acc:
            output[acc.name] = (
                ua.role.value if hasattr(ua.role, "value") else str(ua.role)
            )
    return output


async def user_is_account_admin(db: AsyncSession, user_id: int) -> bool:
    result = await db.exec(
        select(UserAccount).where(
            UserAccount.user_id == user_id,
            UserAccount.role == ZoneRole.admin,
        )
    )
    return result.first() is not None


async def get_user_role_for_account(
    db: AsyncSession, user_id: int, account_name: str
) -> UserAccount | None:
    account = await get_account_by_name(db, account_name)
    if account is None:
        return None
    result = await db.exec(  # type: ignore[call-overload]
        select(UserAccount).where(
            UserAccount.user_id == user_id,
            UserAccount.account_id == account.id,
        )
    )
    return result.first()


async def list_account_members(db: AsyncSession, account_name: str) -> list[dict]:
    account = await get_account_by_name(db, account_name)
    if account is None:
        return []
    uas_result = await db.exec(  # type: ignore[call-overload]
        select(UserAccount).where(UserAccount.account_id == account.id)
    )
    uas = uas_result.all()
    output = []
    for ua in uas:
        user_result = await db.exec(  # type: ignore[call-overload]
            select(User).where(User.id == ua.user_id)
        )
        user = user_result.first()
        if user:
            output.append(
                {
                    "user_id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "role": ua.role.value if hasattr(ua.role, "value") else ua.role,
                }
            )
    return output


async def upsert_account_member(
    db: AsyncSession, account_name: str, user_id: int, role: ZoneRole
) -> None:
    account = await get_account_by_name(db, account_name)
    if account is None or account.id is None:
        return
    result = await db.exec(  # type: ignore[call-overload]
        select(UserAccount).where(
            UserAccount.user_id == user_id, UserAccount.account_id == account.id
        )
    )
    ua = result.first()
    if ua:
        ua.role = role
        db.add(ua)
    else:
        db.add(UserAccount(user_id=user_id, account_id=account.id, role=role))
    await db.commit()


async def remove_account_member(
    db: AsyncSession, account_name: str, user_id: int
) -> bool:
    account = await get_account_by_name(db, account_name)
    if account is None or account.id is None:
        return False
    result = await db.exec(  # type: ignore[call-overload]
        select(UserAccount).where(
            UserAccount.user_id == user_id, UserAccount.account_id == account.id
        )
    )
    ua = result.first()
    if not ua:
        return False
    await db.delete(ua)
    await db.commit()
    return True


# ── OIDC Settings ─────────────────────────────────────────────────────────────


async def get_oidc_settings(db: AsyncSession) -> OidcSettings | None:
    result = await db.exec(select(OidcSettings).where(OidcSettings.id == 1))  # type: ignore[call-overload]
    return result.first()


async def upsert_oidc_settings(db: AsyncSession, data: dict) -> OidcSettings:
    existing = await get_oidc_settings(db)
    if existing:
        for key, value in data.items():
            setattr(existing, key, value)
        db.add(existing)
    else:
        existing = OidcSettings(id=1, **data)
        db.add(existing)
    await db.commit()
    await db.refresh(existing)
    return existing
