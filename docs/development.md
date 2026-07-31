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
