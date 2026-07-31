# Autoprimaries

[Autoprimaries](https://doc.powerdns.com/authoritative/modes-of-operation.html#autoprimary) let a PowerDNS secondary server automatically accept and provision new zones notified by a trusted primary, without pre-creating each secondary zone by hand.

## How it works

Once a primary server's IP (and its nameserver name, as sent in the `NOTIFY`) is registered as an autoprimary, that primary can `NOTIFY` the secondary about a **new** zone it hasn't seen before, and the secondary will automatically create it as a `Slave` zone and pull it via AXFR — instead of the `NOTIFY` being rejected because no matching zone exists yet.

## Management

From **Autoprimaries** (administrators only), you can:

- List registered autoprimaries.
- Add an autoprimary by IP address and nameserver name (and an optional account label).
- Remove an autoprimary.

This is most useful for large or dynamic estates where zones are frequently added on the primary and manually pre-creating each `Slave` zone on every secondary would not scale.
