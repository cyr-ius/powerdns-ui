import hashlib
import secrets

from sqlalchemy import select as sa_select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.token import PersonalAccessToken
from app.models.user import User

TOKEN_PREFIX = "pat_"  # noqa: S105


def _hash(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode()).hexdigest()


async def create_token(
    db: AsyncSession,
    user_id: int,
    name: str,
    raw: str | None = None,
    comment: str | None = None,
) -> tuple[PersonalAccessToken, str]:
    if not raw:
        raw = TOKEN_PREFIX + secrets.token_urlsafe(32)
    token = PersonalAccessToken(
        user_id=user_id,
        name=name,
        token_prefix=raw[:11],
        token_hash=_hash(raw),
        comment=comment,
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
    """Recherche un jeton par son hash SHA-256."""
    result = await db.exec(  # type: ignore[attr-defined]
        select(PersonalAccessToken).where(
            PersonalAccessToken.token_hash == _hash(raw_token)
        )
    )
    return result.first()


def token_to_response(token: PersonalAccessToken) -> dict:
    return {
        "id": token.id,
        "name": token.name,
        "token_prefix": token.token_prefix,
        "comment": token.comment,
        "created_at": token.created_at,
    }
