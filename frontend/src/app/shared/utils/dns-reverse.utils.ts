import { Zone } from "../models/pdns.model";

export function expandIPv6(ip: string): string {
  const halves = ip.split("::");
  if (halves.length === 2) {
    const left = halves[0] ? halves[0].split(":") : [];
    const right = halves[1] ? halves[1].split(":") : [];
    const fill = Array(8 - left.length - right.length).fill("0000");
    return [...left, ...fill, ...right].map((p) => p.padStart(4, "0")).join(":");
  }
  return ip
    .split(":")
    .map((p) => p.padStart(4, "0"))
    .join(":");
}

export function ipv4ToArpaName(ip: string): string {
  return ip.split(".").reverse().join(".") + ".in-addr.arpa.";
}

export function ipv6ToArpaName(ip: string): string {
  const nibbles = expandIPv6(ip).replace(/:/g, "").split("").reverse();
  return nibbles.join(".") + ".ip6.arpa.";
}

/**
 * Converts a CIDR network to the corresponding reverse DNS zone name.
 * IPv4: 192.168.1.0/24 → 1.168.192.in-addr.arpa.
 * IPv6: 2001:db8::/32   → 8.b.d.0.1.0.0.2.ip6.arpa.
 */
export function cidrToReverseZoneName(cidr: string): string | null {
  if (!cidr.includes("/")) return null;
  const [addr, prefixStr] = cidr.trim().split("/");
  const prefix = parseInt(prefixStr, 10);
  if (isNaN(prefix)) return null;

  if (addr.includes(":")) {
    return ipv6CidrToReverseZone(addr, prefix);
  }
  return ipv4CidrToReverseZone(addr, prefix);
}

function ipv4CidrToReverseZone(ip: string, prefix: number): string | null {
  const parts = ip.split(".").map(Number);
  if (parts.length !== 4 || parts.some(isNaN)) return null;
  if (prefix <= 8) return `${parts[0]}.in-addr.arpa.`;
  if (prefix <= 16) return `${parts[1]}.${parts[0]}.in-addr.arpa.`;
  // /17–/32: use parent /24 octets
  return `${parts[2]}.${parts[1]}.${parts[0]}.in-addr.arpa.`;
}

function ipv6CidrToReverseZone(ip: string, prefix: number): string | null {
  try {
    const allNibbles = expandIPv6(ip).replace(/:/g, "");
    const nibbleCount = Math.ceil(prefix / 4);
    if (nibbleCount < 1 || nibbleCount > 32) return null;
    const significant = allNibbles.substring(0, nibbleCount).split("").reverse();
    return significant.join(".") + ".ip6.arpa.";
  } catch {
    return null;
  }
}

/** Builds the full PTR record name (arpa FQDN) for a given IP address. */
export function buildPtrName(ip: string): string {
  return ip.includes(":") ? ipv6ToArpaName(ip) : ipv4ToArpaName(ip);
}

/** Finds the most-specific reverse zone matching the given IP among a list of zones. */
export function findBestReverseZone(ip: string, zones: Zone[]): Zone | null {
  let arpaName: string;
  try {
    arpaName = buildPtrName(ip);
  } catch {
    return null;
  }

  const reverseZones = zones.filter((z) => z.name.endsWith(".in-addr.arpa.") || z.name.endsWith(".ip6.arpa."));

  let best: Zone | null = null;
  for (const zone of reverseZones) {
    if (arpaName.endsWith(zone.name) && (!best || zone.name.length > best.name.length)) {
      best = zone;
    }
  }
  return best;
}

export function isReverseZone(name: string): boolean {
  return name.endsWith(".in-addr.arpa.") || name.endsWith(".ip6.arpa.");
}
