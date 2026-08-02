# Audit Log

Every action performed through PowerDNS UI is tracked — logins, zone/record modifications, user and account management, connector configuration changes — in an append-only audit log, accessible from **Administration → Audit Log** to Super Admins.

## What is recorded

Each entry captures:

| Field                  | Description                                                                 |
| ---------------------- | --------------------------------------------------------------------------- |
| `username` / `user_id` | Who performed the action                                                    |
| `action`               | What was done, e.g. `create`, `update`, `delete`, `login`, `reassign_owner` |
| `resource_type`        | The kind of object affected, e.g. `zone`, `acme_key`, `user`                |
| `resource_id`          | The affected object's identifier                                            |
| `details`              | Additional context (e.g. previous/new values)                               |
| `ip_address`           | Source IP of the request                                                    |
| `status`               | `success` or `failure`                                                      |
| `created_at`           | Timestamp                                                                   |

The log can be filtered by username, action, resource type, status, and date range.

## PDNS logs

The Audit Log page also surfaces relevant PowerDNS server-side log entries alongside PowerDNS UI's own audit trail, giving a single place to correlate a user action with what PowerDNS itself did as a result.

These entries are read from PowerDNS's own `logmessages` ring buffer (via the API's `?includerings=true` statistics) and parsed as structured logs — timestamp, level, subsystem, and message are shown as separate fields, with a badge colored by level (Error/Warning/Notice/Debug/Info).

For this parsing to work, the PowerDNS Authoritative Server must be configured with:

```
logging-structured=yes
loglevel=6
loglevel-show=yes
```

- `logging-structured=yes` makes PowerDNS emit `key="value"` structured log lines instead of free-form text.
- `loglevel=6` (or higher) is needed for a useful level of verbosity — lower levels omit most `Info`/`Notice` entries.
- `loglevel-show=yes` includes the `prio` (level) field in each structured log line, used here to color-code entries by severity.

See the [PowerDNS settings documentation](https://doc.powerdns.com/authoritative/settings.html#logging-facility) for details. Without `logging-structured=yes`, log lines are still displayed, but only as raw, unparsed text.

## Syslog export

From the Audit Log page (**Syslog: active/inactive** button), audit events can be forwarded to an external syslog server:

- Host and port
- Protocol: UDP or TCP
- Syslog facility
- Application name tag

This is the recommended way to retain audit history beyond the local database and to feed it into a central SIEM/log pipeline.

## E-mail alerting

Independently of syslog export, the [Mail connector](../configuration/oidc-mail.md#mail-smtp-connector) can send e-mail notifications for a filtered subset of audit events (by action, resource type, or status) — configured via `SMTP_ALERT_ACTIONS`, `SMTP_ALERT_RESOURCES` and `SMTP_ALERT_STATUSES`, or from **Administration → Mail**.
