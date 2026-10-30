"""Test settings: an isolated data directory, without the developer's .env."""

import os
import secrets
import tempfile

# Set before the app is imported: the settings and the database engine are
# built at import time.
_DATA_DIR = tempfile.mkdtemp(prefix="powerdns-ui-tests-")
os.environ["DATA_DIR"] = _DATA_DIR
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_DATA_DIR}/database.db"
os.environ["PDNS_AUTH_API_URL"] = "http://pdns.test:8081"
os.environ["PDNS_AUTH_API_KEY"] = secrets.token_urlsafe(16)
os.environ["SECRET_KEY"] = secrets.token_urlsafe(32)
os.environ["RATE_LIMIT_ENABLED"] = "false"

# The settings read ".env" from the working directory: import the app from the
# empty data directory so the developer's .env is ignored.
_cwd = os.getcwd()
os.chdir(_DATA_DIR)
try:
    import app.main  # noqa: E402, F401
finally:
    os.chdir(_cwd)
