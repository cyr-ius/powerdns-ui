import hashlib
import json
import secrets

from sqlalchemy import select as sa_select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.acme_key import AcmeApiKey
from app.models.user import User


def _hash(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


def _decode_zones(key: AcmeApiKey) -> list[str]:
    try:
        return json.loads(key.zones)
    except ValueError, TypeError:
        return []


async def create_key(
    db: AsyncSession,
    user_id: int,
    name: str,
    raw: str | None = None,
    key_type: str = "acme",
    comment: str | None = None,
) -> tuple[AcmeApiKey, str]:
    if not raw:
        prefix = "apk_" if key_type == "api" else "ak_"
        raw = prefix + secrets.token_urlsafe(32)
    key = AcmeApiKey(
        user_id=user_id,
        name=name,
        key_prefix=raw[:11],
        key_hash=_hash(raw),
        key_type=key_type,
        comment=comment,
    )
    db.add(key)
    await db.commit()
    await db.refresh(key)
    return key, raw


async def list_keys(db: AsyncSession, user_id: int) -> list[AcmeApiKey]:
    result = await db.exec(select(AcmeApiKey).where(AcmeApiKey.user_id == user_id))
    return list(result.all())


async def get_key(db: AsyncSession, key_id: int, user_id: int) -> AcmeApiKey | None:
    result = await db.exec(
        select(AcmeApiKey).where(AcmeApiKey.id == key_id, AcmeApiKey.user_id == user_id)
    )
    return result.first()


async def update_zones(
    db: AsyncSession, key_id: int, user_id: int, zones: list[str]
) -> AcmeApiKey | None:
    key = await get_key(db, key_id, user_id)
    if key is None:
        return None
    key.zones = json.dumps(zones)
    db.add(key)
    await db.commit()
    await db.refresh(key)
    return key


async def delete_key(db: AsyncSession, key_id: int, user_id: int) -> bool:
    key = await get_key(db, key_id, user_id)
    if key is None:
        return False
    await db.delete(key)
    await db.commit()
    return True


async def list_all_keys(db: AsyncSession) -> list[tuple[AcmeApiKey, str, int]]:
    """Return all keys with their owner's username and user_id (admin use)."""
    rows = await db.execute(
        sa_select(AcmeApiKey, User.username, User.id)
        .join(User, AcmeApiKey.user_id == User.id)
        .order_by(User.username, AcmeApiKey.created_at)
    )
    return [(key, username, uid) for key, username, uid in rows.all()]


async def delete_key_any(db: AsyncSession, key_id: int) -> bool:
    """Delete any key by id regardless of owner (admin use)."""
    result = await db.exec(select(AcmeApiKey).where(AcmeApiKey.id == key_id))
    key = result.first()
    if key is None:
        return False
    await db.delete(key)
    await db.commit()
    return True


async def verify_key(db: AsyncSession, raw_key: str) -> AcmeApiKey | None:
    """Look up a key by its SHA-256 hash (constant-time safe for random keys)."""
    result = await db.exec(
        select(AcmeApiKey).where(AcmeApiKey.key_hash == _hash(raw_key))
    )
    return result.first()


async def update_key(
    db: AsyncSession, key_id: int, user_id: int, comment: str | None
) -> AcmeApiKey | None:
    key = await get_key(db, key_id, user_id)
    if key is None:
        return None
    key.comment = comment
    db.add(key)
    await db.commit()
    await db.refresh(key)
    return key


def key_to_response(key: AcmeApiKey) -> dict:
    return {
        "id": key.id,
        "name": key.name,
        "key_prefix": key.key_prefix,
        "zones": _decode_zones(key),
        "key_type": key.key_type,
        "comment": key.comment,
        "created_at": key.created_at,
    }
