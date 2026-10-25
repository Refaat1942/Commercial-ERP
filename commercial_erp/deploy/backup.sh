#!/usr/bin/env bash
# Daily backup (database + files) with 14-day retention. Run as the bench user (cron: see DEPLOYMENT.md).
set -euo pipefail
source "$(dirname "$0")/versions.env" 2>/dev/null || true
BENCH_DIR="${BENCH_DIR:-/home/fes/fes-bench}"
SITE="${SITE:?set SITE, e.g. SITE=erp.local}"
DEST="${BACKUP_DEST:-/var/backups/commercial-erp}"
KEEP_DAYS="${KEEP_DAYS:-3}"   # days of backups to keep (bench keeps its own copy too: both are pruned)
umask 077
mkdir -p "$DEST"
cd "$BENCH_DIR"
export PATH="/opt/node24/bin:$HOME/.local/bin:$PATH"
bench --site "$SITE" backup --with-files
cp -n "sites/$SITE/private/backups/"*"$(date +%Y%m%d)"* "$DEST"/ 2>/dev/null || cp -n "sites/$SITE/private/backups/"* "$DEST"/
find "$DEST" -type f -mtime "+$KEEP_DAYS" -delete
# bench keeps every backup it ever made inside the site: prune those too, otherwise each backup is stored twice and forever
find "sites/$SITE/private/backups" -type f -mtime "+$KEEP_DAYS" -delete 2>/dev/null || true
echo "backup ok: $(date -Is) -> $DEST"
