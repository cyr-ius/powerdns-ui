# User Management

Administrators manage users and accounts from **Administration → Users** / **Administration → Accounts**.

## Users

- **Create** a user (username, password, role) — see [Roles & Permissions](roles-permissions.md) for what each role grants.
- **Update** a user's profile, role, or account membership.
- **Reset password** — generates/sets a new password for a user, without requiring the old one (useful when a user is locked out).
- **Delete** a user.

The very first Super Admin account is created automatically at startup (`ADMIN_USERNAME`, default `admin`) with a one-time password printed to the container logs — see [Getting Started](../getting-started.md).

## Accounts

Accounts are the unit zones and users are grouped by:

- **Create / update** an account.
- **Assign users** to an account, each with their own role on that account (`Admin`, `Manager`, `Viewer`).
- **Delete** an account.

A user can belong to multiple accounts, potentially with a different role on each — the effective permissions for a given zone are derived from the account(s) that own it, plus any [Zone Admin](roles-permissions.md#zone-admin-a-per-zone-role) grant on that specific zone.

## Record types

Super Admins can curate the list of DNS record types offered when creating records, from **Administration → Record Types** — e.g. to hide record types not relevant to your organization, or to ensure the `LUA` type only appears where [Lua Records](../features/lua-records.md) has been enabled.

## OIDC

OIDC single sign-on is configured from **Administration → OIDC** — see [OIDC & Mail Connectors](../configuration/oidc-mail.md) for the full behaviour and safety guarantees.
