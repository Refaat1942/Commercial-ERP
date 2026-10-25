#!/usr/bin/env bash
# Restore a backup into a SEPARATE test site (never over production).
# Usage: restore.sh <site-to-create> <db.sql.gz> [public-files.tar] [private-files.tar]
set -euo pipefail
TARGET="${1:?target site name (must not exist)}"; SQL="${2:?sql.gz path}"
PUB="${3:-}"; PRIV="${4:-}"
BENCH_DIR="${BENCH_DIR:-/home/frappe/frappe-bench}"
export PATH="/opt/node24/bin:$HOME/.local/bin:$PATH"
cd "$BENCH_DIR"
[ -e "sites/$TARGET" ] && { echo "Refusing: site $TARGET already exists. Restoring over an existing site must be done manually after a fresh backup."; exit 1; }
read -rsp "MariaDB root password: " ROOTPW; echo
bench new-site "$TARGET" --mariadb-root-password "$ROOTPW" --admin-password "$(openssl rand -base64 18)"
bench --site "$TARGET" --force restore "$SQL" --mariadb-root-password "$ROOTPW" ${PUB:+--with-public-files "$PUB"} ${PRIV:+--with-private-files "$PRIV"}
bench --site "$TARGET" migrate
echo "Restored into $TARGET (not exposed by nginx unless you run bench setup nginx; drop it when done: bench drop-site $TARGET - destructive, your decision)."
