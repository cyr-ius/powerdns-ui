from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import get_current_user
from app.schemas.pdns import PatchRRsets, Record, RRsetChange
from app.services.pdns_service import pdns_request

router = APIRouter(prefix="/nic")

_SERVER = "/servers/localhost"


def _pdns_error_handler(exc: httpx.HTTPStatusError) -> HTTPException:
    if exc.response.status_code == 404:
        return HTTPException(status_code=404, detail="Resource not found")
    try:
        detail = exc.response.json().get("error", str(exc))
    except Exception:
        detail = str(exc)
    return HTTPException(status_code=exc.response.status_code, detail=detail)


@router.get("/update", description="Dynamic DNS update endpoint")
async def dyndns(
    myip: str, hostname: str, ttl: int = 3600, _=Depends(get_current_user)
) -> Any:
    """Update record to zone."""

    zones: list = await pdns_request("GET", f"{_SERVER}/zones")

    myips = myip.split(",")

    if not hostname.endswith("."):
        hostname += "."

    host_list = hostname.split(".")
    if len(host_list) <= 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid hostname provided",
        )

    host_list.pop(0)
    domain_name = ".".join(host_list)

    if domain_name == "":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No domain name found in hostname",
        )

    for zone in zones:
        zone_id = zone["id"]
        if zone_id == domain_name:
            zone: dict = await pdns_request("GET", f"{_SERVER}/zones/{zone_id}")
            if not zone["rrsets"]:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"No records found for zone {domain_name}",
                )

            found_records = [
                next(Record(**r) for r in rrset["records"])
                for rrset in zone["rrsets"]
                if rrset["name"] == hostname and rrset["type"] == "A"
            ]
            records = [Record(content=ip, disabled=False) for ip in myips]
            if found_records and found_records == records:
                return {
                    "status": "nochange",
                    "message": f"Record {hostname} is already set to {myip} in zone {domain_name}",
                }

            payload = PatchRRsets(
                rrsets=[
                    RRsetChange(
                        changetype="REPLACE",
                        name=hostname,
                        type="A",
                        ttl=ttl,
                        records=records,
                    )
                ]
            )

            try:
                await pdns_request(
                    "PATCH", f"{_SERVER}/zones/{zone_id}", json=payload.model_dump()
                )
            except httpx.HTTPStatusError as exc:
                raise _pdns_error_handler(exc) from exc

            return {
                "status": "success",
                "message": f"Record {hostname} updated to {myip} in zone {domain_name}",
            }
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Zone not found",
        )
