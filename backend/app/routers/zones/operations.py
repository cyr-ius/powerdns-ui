"""Zone operations: notify, AXFR, rectify, import and export."""

from typing import Any

import dns.name
import dns.rdatatype
import dns.zone
import httpx
from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile

from app.dependencies import get_audit_logger
from app.routers.zones.access import SERVER, pdns_error_handler, zone_access
from app.services.audit_service import AuditLogger
from app.services.pdns_service import pdns_request, pdns_request_text

router = APIRouter()

# Largest zone file accepted by the import, in bytes.
MAX_ZONE_FILE_SIZE = 10 * 1024 * 1024


@router.put(
    "/{zone_id}/notify", status_code=200, dependencies=[Depends(zone_access("admin"))]
)
async def notify_slaves(zone_id: str) -> dict[str, Any]:
    try:
        return await pdns_request("PUT", f"{SERVER}/zones/{zone_id}/notify")  # type: ignore[no-any-return]
    except httpx.HTTPStatusError as exc:
        raise pdns_error_handler(exc) from exc


@router.put(
    "/{zone_id}/axfr-retrieve",
    status_code=200,
    dependencies=[Depends(zone_access("admin"))],
)
async def axfr_retrieve(zone_id: str) -> dict[str, Any]:
    try:
        return await pdns_request("PUT", f"{SERVER}/zones/{zone_id}/axfr-retrieve")  # type: ignore[no-any-return]
    except httpx.HTTPStatusError as exc:
        raise pdns_error_handler(exc) from exc


@router.put(
    "/{zone_id}/rectify", status_code=200, dependencies=[Depends(zone_access("admin"))]
)
async def rectify_zone(zone_id: str) -> dict[str, Any]:
    try:
        return await pdns_request("PUT", f"{SERVER}/zones/{zone_id}/rectify")  # type: ignore[no-any-return]
    except httpx.HTTPStatusError as exc:
        raise pdns_error_handler(exc) from exc


@router.post(
    "/{zone_id}/import",
    status_code=204,
    dependencies=[Depends(zone_access("admin", "import"))],
)
async def import_zone(
    zone_id: str,
    file: UploadFile,
    audit: AuditLogger = Depends(get_audit_logger),
) -> None:
    # Read one byte past the limit to tell a full file from a truncated one.
    raw = await file.read(MAX_ZONE_FILE_SIZE + 1)
    if len(raw) > MAX_ZONE_FILE_SIZE:
        detail = f"Zone file larger than {MAX_ZONE_FILE_SIZE // (1024 * 1024)} MiB"
        await audit.failure("import", "zone", zone_id, {"detail": detail})
        raise HTTPException(status_code=413, detail=detail)
    try:
        content = raw.decode("utf-8")
        imported_rrsets = _parse_zone_file(zone_id, content)
    except Exception as exc:
        await audit.failure(
            "import", "zone", zone_id, {"detail": f"Invalid zone file: {exc}"}
        )
        raise HTTPException(
            status_code=422, detail=f"Invalid zone file: {exc}"
        ) from exc
    try:
        current_zone = await pdns_request("GET", f"{SERVER}/zones/{zone_id}")
        current_rrsets = current_zone.get("rrsets", [])
        # SOA and NS are managed by PowerDNS — never touch them during import.
        safe_rrsets = [r for r in imported_rrsets if r["type"] not in ("SOA", "NS")]
        imported_keys = {(r["name"], r["type"]) for r in safe_rrsets}
        patch: list[dict[str, Any]] = [
            {"changetype": "REPLACE", **r} for r in safe_rrsets
        ]
        for rrset in current_rrsets:
            if rrset["type"] in ("SOA", "NS"):
                continue
            if (rrset["name"], rrset["type"]) not in imported_keys:
                patch.append(
                    {
                        "changetype": "DELETE",
                        "name": rrset["name"],
                        "type": rrset["type"],
                    }
                )
        await pdns_request("PATCH", f"{SERVER}/zones/{zone_id}", json={"rrsets": patch})
        await audit.success("import", "zone", zone_id)
    except httpx.HTTPStatusError as exc:
        http_exc = pdns_error_handler(exc)
        await audit.failure("import", "zone", zone_id, {"detail": http_exc.detail})
        raise http_exc from exc


def _parse_zone_file(zone_name: str, content: str) -> list[dict[str, Any]]:
    origin = dns.name.from_text(zone_name)
    zone = dns.zone.from_text(content, origin=origin, check_origin=False)
    rrsets = []
    for rel_name, node in zone.nodes.items():
        fqdn = str(rel_name.derelativize(origin))
        for rdataset in node.rdatasets:
            rrsets.append(
                {
                    "name": fqdn,
                    "type": dns.rdatatype.to_text(rdataset.rdtype),
                    "ttl": rdataset.ttl,
                    "records": [
                        {"content": r.to_text(), "disabled": False} for r in rdataset
                    ],
                }
            )
    return rrsets


@router.get("/{zone_id}/export", dependencies=[Depends(zone_access("viewer"))])
async def export_zone(zone_id: str) -> Response:
    try:
        content = await pdns_request_text("GET", f"{SERVER}/zones/{zone_id}/export")
        filename = zone_id.rstrip(".") + ".zone"
        return Response(
            content=content,
            media_type="text/plain",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except httpx.HTTPStatusError as exc:
        raise pdns_error_handler(exc) from exc
