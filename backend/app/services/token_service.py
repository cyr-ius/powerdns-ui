import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import select as sa_select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.token import PersonalAccessToken
from app.models.user import User

TOKEN_PREFIX = "pat_"  # noqa: S105


def _hash(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode()).hexdigest()


def is_expired(token: PersonalAccessToken) -> bool:
    """True once `expires_at` is in the past (never, for unlimited tokens).

    SQLite round-trips datetimes as naive (see database.py), but a token
    still held in the identity map right after creation, in the same
    session, keeps the aware value it was assigned in Python — so match
    `now`'s awareness to whatever `expires_at` turns out to be.
    """
    if token.expires_at is None:
        return False
    now = datetime.now(UTC)
    if token.expires_at.tzinfo is None:
        now = now.replace(tzinfo=None)
    return token.expires_at < now


async def create_token(
    db: AsyncSession,
    user_id: int,
    name: str,
    raw: str | None = None,
    comment: str | None = None,
    duration_days: int | None = None,
) -> tuple[PersonalAccessToken, str]:
    if not raw:
        raw = TOKEN_PREFIX + secrets.token_urlsafe(32)
    expires_at = (
        datetime.now(UTC) + timedelta(days=duration_days) if duration_days else None
    )
    token = PersonalAccessToken(
        user_id=user_id,
        name=name,
        token_prefix=raw[:11],
        token_hash=_hash(raw),
        comment=comment,
        expires_at=expires_at,
    )
    db.add(token)
    await db.commit()
    await db.refresh(token)
    return token, raw


async def list_tokens(db: AsyncSession, user_id: int) -> list[PersonalAccessToken]:
    result = await db.exec(  # type: ignore[attr-defined]
        select(PersonalAccessToken)
        .where(PersonalAccessToken.user_id == user_id)
        .order_by(PersonalAccessToken.created_at)  # type: ignore[arg-type]
    )
    return list(result.all())


async def list_all_tokens(
    db: AsyncSession,
) -> list[tuple[PersonalAccessToken, str, int]]:
    """Retourne tous les jetons avec leur propriétaire (usage admin)."""
    rows = await db.execute(
        sa_select(PersonalAccessToken, User.username, User.id)  # type: ignore[call-overload]
        .join(User, PersonalAccessToken.user_id == User.id)
        .order_by(PersonalAccessToken.created_at)
    )
    return [(token, username, uid) for token, username, uid in rows.all()]


async def get_token(
    db: AsyncSession, token_id: int, user_id: int
) -> PersonalAccessToken | None:
    result = await db.exec(  # type: ignore[attr-defined]
        select(PersonalAccessToken).where(
            PersonalAccessToken.id == token_id,
            PersonalAccessToken.user_id == user_id,
        )
    )
    return result.first()


async def update_token(
    db: AsyncSession, token_id: int, user_id: int, comment: str | None
) -> PersonalAccessToken | None:
    token = await get_token(db, token_id, user_id)
    if token is None:
        return None
    token.comment = comment
    db.add(token)
    await db.commit()
    await db.refresh(token)
    return token


async def delete_token(db: AsyncSession, token_id: int, user_id: int) -> bool:
    token = await get_token(db, token_id, user_id)
    if token is None:
        return False
    await db.delete(token)
    await db.commit()
    return True


async def delete_token_any(db: AsyncSession, token_id: int) -> bool:
    """Supprime n'importe quel jeton par ID (usage admin)."""
    result = await db.exec(  # type: ignore[attr-defined]
        select(PersonalAccessToken).where(PersonalAccessToken.id == token_id)
    )
    token = result.first()
    if token is None:
        return False
    await db.delete(token)
    await db.commit()
    return True


async def delete_user_tokens(db: AsyncSession, user_id: int) -> None:
    """Supprime tous les jetons d'un utilisateur (appelé à sa suppression)."""
    result = await db.exec(  # type: ignore[attr-defined]
        select(PersonalAccessToken).where(PersonalAccessToken.user_id == user_id)
    )
    for token in result.all():
        await db.delete(token)


async def verify_token(db: AsyncSession, raw_token: str) -> PersonalAccessToken | None:
    """Recherche un jeton par son hash SHA-256 et rejette les jetons expirés."""
    result = await db.exec(  # type: ignore[attr-defined]
        select(PersonalAccessToken).where(
            PersonalAccessToken.token_hash == _hash(raw_token)
        )
    )
    token = result.first()
    if token is None or is_expired(token):
        return None
    return token


def token_to_response(token: PersonalAccessToken) -> dict:
    return {
        "id": token.id,
        "name": token.name,
        "token_prefix": token.token_prefix,
        "comment": token.comment,
        "created_at": token.created_at,
        "expires_at": token.expires_at,
        "is_expired": is_expired(token),
    }
