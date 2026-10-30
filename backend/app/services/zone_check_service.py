"""Zone health checks: SOA serial sync across name servers and e-mail security."""

import asyncio
import re
from typing import Any

import dns.asyncquery
import dns.asyncresolver
import dns.exception
import dns.message
import dns.name as dns_name_mod
import dns.rdatatype
import dns.resolver


async def _query_ns_serial(ns: str, zone: str) -> dict[str, Any]:
    try:
        ns_hostname = ns.rstrip(".")
        answers = await dns.asyncresolver.resolve(ns_hostname, "A", lifetime=5)
        ns_ip = str(answers[0].address)
        qname = dns_name_mod.from_text(zone)
        request = dns.message.make_query(qname, dns.rdatatype.SOA)
        response = await dns.asyncquery.udp(request, ns_ip, timeout=3)
        for rrset in response.answer:
            if rrset.rdtype == dns.rdatatype.SOA:
                return {"ip": ns_ip, "serial": rrset[0].serial, "error": None}
        return {"ip": ns_ip, "serial": None, "error": "No SOA in response"}
    except dns.exception.Timeout:
        return {"ip": None, "serial": None, "error": "Timeout"}
    except dns.resolver.NXDOMAIN:
        return {"ip": None, "serial": None, "error": "NS hostname not found"}
    except Exception as exc:
        return {"ip": None, "serial": None, "error": str(exc)}


async def soa_sync_check(zone: dict[str, Any]) -> dict[str, Any]:
    """Compare the SOA serial of each name server with the authoritative one."""
    zone_name: str = zone.get("name", "")

    ns_names: list[str] = []
    authoritative_serial: int | None = None
    for rrset in zone.get("rrsets", []):
        if rrset["type"] == "SOA" and rrset["name"] == zone_name:
            try:
                authoritative_serial = int(rrset["records"][0]["content"].split()[2])
            except IndexError, ValueError, KeyError:
                pass
        if rrset["type"] == "NS" and rrset["name"] == zone_name:
            for rec in rrset["records"]:
                if not rec.get("disabled", False):
                    ns_names.append(rec["content"])

    raw = await asyncio.gather(*[_query_ns_serial(ns, zone_name) for ns in ns_names])

    nameservers = []
    for ns, result in zip(ns_names, raw):
        serial: int | None = result.get("serial")
        if serial is None:
            ns_status = "error"
        elif serial == authoritative_serial:
            ns_status = "synced"
        elif serial < (authoritative_serial or 0):
            ns_status = "outdated"
        else:
            ns_status = "ahead"
        nameservers.append(
            {
                "ns": ns,
                "ip": result.get("ip"),
                "serial": serial,
                "status": ns_status,
                "error": result.get("error"),
            }
        )

    return {
        "zone": zone_name,
        "authoritative_serial": authoritative_serial,
        "nameservers": nameservers,
    }


def _clean_txt(content: str) -> str:
    """Remove surrounding quotes and unescape semicolons from PDNS TXT content."""
    s = content.strip()
    # Strip wrapping quotes if present
    if s.startswith('"') and s.endswith('"'):
        s = s[1:-1]
    return s.replace("\\;", ";")


def _check_spf(apex_txt: list[str]) -> dict[str, Any]:
    spf = [r for r in apex_txt if r.startswith("v=spf1")]
    if not spf:
        return {
            "status": "missing",
            "record": None,
            "details": "No SPF record found at zone apex.",
        }
    if len(spf) > 1:
        return {
            "status": "error",
            "record": spf[0],
            "details": (
                f"{len(spf)} SPF records found — only one is allowed (RFC 7208)."
            ),
        }
    record = spf[0]
    if "-all" in record:
        return {
            "status": "ok",
            "record": record,
            "details": "Hard fail (-all): only listed senders are authorised.",
        }
    if "~all" in record:
        return {
            "status": "warning",
            "record": record,
            "details": (
                "Soft fail (~all): unauthorised senders are accepted but tagged. "
                "Consider -all."
            ),
        }
    if "?all" in record:
        return {
            "status": "warning",
            "record": record,
            "details": "Neutral (?all): no enforcement. Consider ~all or -all.",
        }
    if "+all" in record:
        return {
            "status": "error",
            "record": record,
            "details": "Permissive (+all): any server may send. This is insecure.",
        }
    return {
        "status": "warning",
        "record": record,
        "details": "No 'all' mechanism found. Specify ~all or -all.",
    }


def _check_dmarc(dmarc_txt: list[str]) -> dict[str, Any]:
    dmarc = [r for r in dmarc_txt if r.startswith("v=DMARC1")]
    if not dmarc:
        return {
            "status": "missing",
            "record": None,
            "policy": None,
            "details": "No DMARC record found at _dmarc.<zone>.",
        }
    record = dmarc[0]
    p_match = re.search(r"\bp=(\w+)", record)
    policy = p_match.group(1).lower() if p_match else None
    has_rua = bool(re.search(r"\brua=", record))
    has_ruf = bool(re.search(r"\bruf=", record))

    if policy == "reject":
        status = "ok"
        detail = "Strict policy (reject): non-compliant messages are rejected."
    elif policy == "quarantine":
        status = "ok"
        detail = "Moderate policy (quarantine): non-compliant messages go to spam."
    elif policy == "none":
        status = "warning"
        detail = (
            "Monitoring only (p=none): no enforcement. Upgrade to quarantine or reject."
        )
    else:
        return {
            "status": "error",
            "record": record,
            "policy": None,
            "details": "Missing or unrecognised p= tag.",
        }

    extras = []
    if not has_rua:
        extras.append(
            "No rua= reporting address — you will not receive aggregate reports."
        )
        if status == "ok":
            status = "warning"
    if has_ruf:
        extras.append("ruf= forensic reporting configured.")
    if extras:
        detail += " " + " ".join(extras)

    return {"status": status, "record": record, "policy": policy, "details": detail}


def _check_dkim(rrsets: list[dict[str, Any]], zone_name: str) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    suffix = f"._domainkey.{zone_name}"
    for rrset in rrsets:
        if rrset.get("type") != "TXT":
            continue
        name: str = rrset.get("name", "")
        if not name.endswith(suffix):
            continue
        selector = name[: -len(suffix)]
        for rec in rrset.get("records", []):
            content = _clean_txt(rec.get("content", ""))
            if "v=DKIM1" not in content:
                results.append(
                    {
                        "selector": selector,
                        "status": "invalid",
                        "record": content,
                        "details": "Not a valid DKIM record (missing v=DKIM1).",
                    }
                )
                continue
            p_match = re.search(r"\bp=([^;\s]*)", content)
            p_value = p_match.group(1).strip() if p_match else ""
            if not p_value:
                results.append(
                    {
                        "selector": selector,
                        "status": "revoked",
                        "record": content,
                        "details": "Public key is empty — key has been revoked (p=).",
                    }
                )
            else:
                results.append(
                    {
                        "selector": selector,
                        "status": "ok",
                        "record": content,
                        "details": "DKIM key active and valid.",
                    }
                )
    return results


def email_security_check(zone: dict[str, Any]) -> dict[str, Any]:
    """Check the SPF, DMARC and DKIM records of a zone."""
    zone_name: str = zone.get("name", "")
    rrsets: list[dict[str, Any]] = zone.get("rrsets", [])

    apex_txt: list[str] = []
    dmarc_txt: list[str] = []
    dmarc_name = f"_dmarc.{zone_name}"

    for rrset in rrsets:
        if rrset.get("type") != "TXT":
            continue
        name = rrset.get("name", "")
        for rec in rrset.get("records", []):
            cleaned = _clean_txt(rec.get("content", ""))
            if name == zone_name:
                apex_txt.append(cleaned)
            elif name == dmarc_name:
                dmarc_txt.append(cleaned)

    return {
        "zone": zone_name,
        "spf": _check_spf(apex_txt),
        "dmarc": _check_dmarc(dmarc_txt),
        "dkim": _check_dkim(rrsets, zone_name),
    }
