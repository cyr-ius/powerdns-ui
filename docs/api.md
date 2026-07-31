# API Reference

PowerDNS UI's backend is a FastAPI application, and interactive API documentation is generated automatically from the running instance — this documentation site does not duplicate the endpoint reference, it links to it.

## Swagger UI

- **http://localhost:8080/api/docs**

The OpenAPI schema declares the Bearer scheme used by [Personal Access Tokens](features/acme-pat.md#personal-access-tokens-pat), so you can authorize Swagger UI's "Try it out" requests with a token generated from your profile.

Set [`SWAGGER_ENABLED=false`](configuration/environment-variables.md) to disable the Swagger UI and OpenAPI schema in production deployments where you don't want the API surface publicly documented.

## Authentication schemes

| Scheme                | Header                                      | Scope                                  | Details                                                    |
| --------------------- | ------------------------------------------- | -------------------------------------- | ---------------------------------------------------------- |
| Personal Access Token | `Authorization: Bearer <token>`             | Same permissions as the issuing user   | [ACME Keys & Personal Access Tokens](features/acme-pat.md) |
| ACME Key              | `X-API-Key: <key>`                          | Scoped to specific zone(s)             | [ACME Keys & Personal Access Tokens](features/acme-pat.md) |
| Session cookie        | Set on `/api/auth/login` (or OIDC callback) | Same permissions as the logged-in user | Used by the web interface itself                           |

## Health check

`GET /api/health` is exempt from the [rate limiter](configuration/rate-limiting.md) and requires no authentication — use it for container liveness/readiness probes.
