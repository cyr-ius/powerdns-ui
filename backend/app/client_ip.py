"""Trusted-proxy aware client IP resolution.

``X-Forwarded-For`` is attacker-controlled: any client can set it. We therefore
only honour it when the *direct* peer (the TCP source) is a configured trusted
proxy, walking the header right-to-left and skipping trusted hops to recover the
real client address. Without ``trusted_proxies`` configured the header is
ignored entirely and the direct peer is used, which prevents IP spoofing.
"""

import ipaddress
from functools import lru_cache

from fastapi import Request

from app.config import settings

_Networks = tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, ...]


@lru_cache(maxsize=8)
def _parse_networks(raw: str) -> _Networks:
    networks: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        try:
            networks.append(ipaddress.ip_network(token, strict=False))
        except ValueError:
            continue  # ignore malformed entries rather than crash at startup
    return tuple(networks)


def _in_trusted(ip: str, networks: _Networks) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return any(addr in net for net in networks)


def get_client_ip(request: Request) -> str | None:
    """Return the real client IP, honouring X-Forwarded-For only via trusted proxies."""
    peer = request.client.host if request.client else None
    networks = _parse_networks(settings.trusted_proxies)
    if not networks or peer is None or not _in_trusted(peer, networks):
        return peer

    forwarded_for = request.headers.get("x-forwarded-for")
    if not forwarded_for:
        return peer
    parts = [p.strip() for p in forwarded_for.split(",") if p.strip()]
    # Right-to-left: the first hop that is not itself a trusted proxy is the client.
    for candidate in reversed(parts):
        if not _in_trusted(candidate, networks):
            return candidate
    return parts[0] if parts else peer
