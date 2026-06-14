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
    # Les clés ACME appartenant à une zone ont zone_name comme zone autorisée
    if key.zone_name:
        return [key.zone_name]
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


async def create_zone_key(
    db: AsyncSession,
    zone_name: str,
    user_id: int,
    name: str,
    raw: str | None = None,
    comment: str | None = None,
) -> tuple[AcmeApiKey, str]:
    """Créer une clé ACME appartenant à une zone spécifique."""
    if not raw:
        raw = "ak_" + secrets.token_urlsafe(32)
    normalized = zone_name.rstrip(".") + "."
    key = AcmeApiKey(
        user_id=user_id,
        zone_name=normalized,
        name=name,
        key_prefix=raw[:11],
        key_hash=_hash(raw),
        key_type="acme",
        comment=comment,
        zones=json.dumps([normalized]),
    )
    db.add(key)
    await db.commit()
    await db.refresh(key)
    return key, raw


async def list_keys(db: AsyncSession, user_id: int) -> list[AcmeApiKey]:
    """Liste les clés API (key_type=api) de l'utilisateur. Les clés ACME appartiennent aux zones."""
    result = await db.exec(  # type: ignore[attr-defined]
        select(AcmeApiKey).where(
            AcmeApiKey.user_id == user_id,
            AcmeApiKey.key_type == "api",
        )
    )
    return list(result.all())


async def list_zone_keys(db: AsyncSession, zone_name: str) -> list[AcmeApiKey]:
    """Liste les clés ACME d'une zone spécifique."""
    normalized = zone_name.rstrip(".") + "."
    result = await db.exec(  # type: ignore[attr-defined]
        select(AcmeApiKey).where(
            AcmeApiKey.zone_name == normalized,
            AcmeApiKey.key_type == "acme",
        )
    )
    return list(result.all())


async def get_key(db: AsyncSession, key_id: int, user_id: int) -> AcmeApiKey | None:
    result = await db.exec(  # type: ignore[attr-defined]
        select(AcmeApiKey).where(AcmeApiKey.id == key_id, AcmeApiKey.user_id == user_id)
    )
    return result.first()


async def get_zone_key(
    db: AsyncSession, key_id: int, zone_name: str
) -> AcmeApiKey | None:
    """Récupère une clé ACME par ID et zone."""
    normalized = zone_name.rstrip(".") + "."
    result = await db.exec(  # type: ignore[attr-defined]
        select(AcmeApiKey).where(
            AcmeApiKey.id == key_id,
            AcmeApiKey.zone_name == normalized,
            AcmeApiKey.key_type == "acme",
        )
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


async def update_zone_key(
    db: AsyncSession, key_id: int, zone_name: str, comment: str | None
) -> AcmeApiKey | None:
    """Met à jour le commentaire d'une clé ACME de zone."""
    key = await get_zone_key(db, key_id, zone_name)
    if key is None:
        return None
    key.comment = comment
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


async def delete_zone_key(db: AsyncSession, key_id: int, zone_name: str) -> bool:
    """Supprime une clé ACME d'une zone."""
    key = await get_zone_key(db, key_id, zone_name)
    if key is None:
        return False
    await db.delete(key)
    await db.commit()
    return True


async def list_all_keys(db: AsyncSession) -> list[tuple[AcmeApiKey, str, int]]:
    """Retourne toutes les clés avec le nom d'utilisateur du créateur (usage admin)."""
    rows = await db.execute(
        sa_select(AcmeApiKey, User.username, User.id)  # type: ignore[call-overload]
        .join(User, AcmeApiKey.user_id == User.id, isouter=True)
        .order_by(AcmeApiKey.created_at)
    )
    return [(key, username, uid) for key, username, uid in rows.all()]


async def delete_key_any(db: AsyncSession, key_id: int) -> bool:
    """Supprime n'importe quelle clé par ID (usage admin)."""
    result = await db.exec(select(AcmeApiKey).where(AcmeApiKey.id == key_id))  # type: ignore[attr-defined]
    key = result.first()
    if key is None:
        return False
    await db.delete(key)
    await db.commit()
    return True


async def verify_key(db: AsyncSession, raw_key: str) -> AcmeApiKey | None:
    """Recherche une clé par son hash SHA-256."""
    result = await db.exec(  # type: ignore[attr-defined]
        select(AcmeApiKey).where(AcmeApiKey.key_hash == _hash(raw_key))
    )
    return result.first()


def key_to_response(key: AcmeApiKey) -> dict:
    return {
        "id": key.id,
        "name": key.name,
        "key_prefix": key.key_prefix,
        "zones": _decode_zones(key),
        "zone_name": key.zone_name,
        "key_type": key.key_type,
        "comment": key.comment,
        "created_at": key.created_at,
    }
