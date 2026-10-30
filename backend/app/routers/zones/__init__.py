"""Zone routes, served under /api/zones and split by domain."""

from fastapi import APIRouter

from app.routers.zones import (
    acme_keys,
    checks,
    dnssec,
    members,
    metadata,
    operations,
    zones,
)

router = APIRouter()
for _module in (zones, members, metadata, dnssec, operations, checks, acme_keys):
    # The prefix goes on the include: the zone list is served at the bare prefix.
    router.include_router(_module.router, prefix="/api/zones")
