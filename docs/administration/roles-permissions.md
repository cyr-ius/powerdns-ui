# Roles & Permissions

Users are grouped by **accounts**. Each account is associated with zones and with users who each hold a role on that account.

| Role              | Zones       | Records      | Members            | Zone Settings (Lua Records, Record Types) |
| ----------------- | ----------- | ------------ | ------------------ | ----------------------------------------- |
| **Super Admin**   | All         | Read / Write | Full management    | :material-check: All zones                |
| **Account Admin** | Own account | Read / Write | Account management | —                                         |
| **Manager**       | Own account | Read / Write | —                  | —                                         |
| **Viewer**        | Own account | Read only    | —                  | —                                         |
| **Zone Admin**    | Own zone    | Read / Write | Zone management    | :material-check: Own zone                 |

## Account-level roles

- **Super Admin** — global administrator, unrestricted access to every zone, account and administration screen, including [user management](user-management.md), [OIDC/Mail configuration](../configuration/oidc-mail.md) and the [audit log](audit-log.md).
- **Account Admin** — full read/write on the account's zones and can manage which users belong to the account and with which role.
- **Manager** — full read/write on the account's zones, without user-management rights.
- **Viewer** — read-only access to the account's zones.

## Zone Admin — a per-zone role

**Zone Admin** is assignable from an individual zone's **Members** tab, independently of the assignee's account-level role. It grants full control over that specific zone's settings, including:

- Enabling [Lua Records](../features/lua-records.md) for that zone.
- Customizing the zone's available record types.
- Managing that zone's member list (who else has access to it).

This lets an Account Admin delegate fine-grained ownership of a single zone (e.g. to a team that only owns one subdomain) without granting them account-wide Manager/Admin rights.

## How permissions are scoped

Most read endpoints (zones, catalogs, search) filter results to the accounts the calling user belongs to, unless the user is a Super Admin — in which case no filtering is applied. Views and Networks management, TSIG keys, and Autoprimaries are administrator-only, since they affect server-wide or cross-zone behaviour rather than a single account's zones.
