# Development

## Prerequisites

- Python 3.12+, [uv](https://docs.astral.sh/uv/)
- Node.js 22+

## Backend

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --port 8080
```

### Database migrations

The schema is managed by [Alembic](https://alembic.sqlalchemy.org/): the application applies
the pending revisions (`backend/app/migrations/versions/`) at startup. After changing a model,
generate a revision from the repository root, review it, and commit it with the model:

```bash
uv run alembic revision --autogenerate -m "add user locale"
uv run alembic check   # no difference left between the models and the revisions
```

A published revision is never modified: fix it with a new one.

## Frontend

```bash
cd frontend
npm install
npm run start   # proxy to localhost:8080
```

## This documentation site

This site is built with [MkDocs](https://www.mkdocs.org/) and the [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/) theme, from the `docs/` directory and `mkdocs.yml` at the repository root.

```bash
pip install -r docs/requirements.txt
mkdocs serve      # live preview at http://127.0.0.1:8000
mkdocs build      # static site in ./site
```

Pushes to `master` that touch `docs/**` or `mkdocs.yml` are published automatically to GitHub Pages — see `.github/workflows/docs.yml`.

## Continuous integration and releases

| Workflow | Trigger | Role |
| --- | --- | --- |
| `lint.yml` | push on `dev`, pull requests | Ruff (lint and format) on the backend, production build of the frontend |
| `docker.yml` | pull requests | Builds the image and checks that `/api/health` answers |
| `docs.yml` | push on `master`, pull requests touching the docs | Builds this site (`--strict`) and publishes it to GitHub Pages |
| `release-please.yml` | push on `master` | Opens the release pull request, then starts `publish.yml` on the new tag |
| `publish.yml` | `X.Y.Z` tag | Lint, tag/version check, Docker images on GHCR and Docker Hub, GitHub release |
| `stale.yaml` | daily | Marks and closes inactive issues and pull requests |

A version is a `X.Y.Z` tag on `master`, created by [Release Please](https://github.com/googleapis/release-please) from the [Conventional Commits](https://www.conventionalcommits.org/): `fix:` bumps `Z`, `feat:` bumps `Y`, `feat!:` or a `BREAKING CHANGE:` footer bumps `X`.

1. Merge `dev` into `master`.
2. Release Please opens (or updates) the release pull request: it writes `CHANGELOG.md` and sets the version in `pyproject.toml`, `uv.lock`, `frontend/package.json` and `frontend/package-lock.json`.
3. Merging that pull request creates the tag and a draft GitHub release, then runs `publish.yml` on the tag. A tag created with the workflow token triggers no workflow: `release-please.yml` starts `publish.yml` itself, with `workflow_dispatch` on the tag.

After a release, `release-please.yml` merges `master` into `dev`: pull `dev` before working on it again. A tag pushed by hand still triggers `publish.yml`.

Publishing to Docker Hub needs the repository secret `DOCKERHUB_TOKEN` (access token with read/write scope on `cyrius44/powerdns-ui`).
