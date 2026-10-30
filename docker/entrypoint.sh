#!/bin/sh
# Start the application as the unprivileged powerdns-ui user.
#
# Releases up to 2.x ran as root, so an existing data volume is owned by root.
# When started as root, hand the data directory over to powerdns-ui once, then
# drop the privileges. Started with --user, run the command as is.
set -eu

APP_USER=powerdns-ui
DATA_DIR="${DATA_DIR:-/var/lib/powerdns-ui}"

if [ "$(id -u)" = "0" ]; then
    mkdir -p "$DATA_DIR"
    if [ -n "$(find "$DATA_DIR" ! -user "$APP_USER" | head -n 1)" ]; then
        echo "entrypoint: giving $DATA_DIR to $APP_USER" >&2
        chown -R -h "$APP_USER:$APP_USER" "$DATA_DIR"
    fi
    exec su-exec "$APP_USER" "$@"
fi

exec "$@"
