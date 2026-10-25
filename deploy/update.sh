#!/usr/bin/env bash
# Update an installed site to the latest commercial_erp (UI, navigation, branding, translations).
# Takes a backup first, never touches business data, never drops anything.
#   sudo SITE_NAME=erp.local bash /home/fes/commercial_erp_src/deploy/update.sh
set -euo pipefail
cd "$(dirname "$0")"
# shellcheck source=versions.env
source ./versions.env
: "${SITE_NAME:?set SITE_NAME}"
APP_BRANCH="${APP_BRANCH:-deployment-ready}"
log(){ printf '\n\033[1;32m==> %s\033[0m\n' "$*"; }
[ "$(id -u)" -eq 0 ] || { echo "run as root (sudo)"; exit 1; }
[ -d "${BENCH_DIR}/sites/${SITE_NAME}" ] || { echo "site ${SITE_NAME} not found in ${BENCH_DIR}"; exit 1; }
# shellcheck disable=SC2154
trap 'rc=$?; [ $rc -eq 0 ] || printf "\033[1;31mFAILED (exit %s) at line %s: %s\033[0m\nYour backup is in /var/backups/commercial-erp\n" "$rc" "$LINENO" "$BASH_COMMAND" >&2' EXIT
RUN=(sudo -H -u "${BENCH_USER}" env "PATH=/opt/commercial-erp-shims:/opt/node24/bin:/opt/uv-venv/bin:/home/${BENCH_USER}/.local/bin:/usr/local/bin:/usr/bin:/bin")

log "1/5 backup"
"${RUN[@]}" env "SITE=${SITE_NAME}" "BENCH_DIR=${BENCH_DIR}" /usr/local/bin/commercial-erp-backup
log "2/5 fetch new code (${APP_BRANCH})"
"${RUN[@]}" git -C "${BENCH_DIR}/apps/commercial_erp" fetch origin "${APP_BRANCH}"
"${RUN[@]}" git -C "${BENCH_DIR}/apps/commercial_erp" merge --ff-only FETCH_HEAD
log "3/5 migrate + build assets"
"${RUN[@]}" bash -c "cd ${BENCH_DIR} && bench --site '${SITE_NAME}' migrate && bench build --app commercial_erp"
log "4/5 apply UI/navigation/branding (idempotent; keeps your later manual changes)"
"${RUN[@]}" bash -c "cd ${BENCH_DIR} && bench --site '${SITE_NAME}' execute commercial_erp.setup.update.run && bench --site '${SITE_NAME}' clear-cache"
log "5/5 restart services"
supervisorctl restart all >/dev/null
sleep 5
bash ./healthcheck.sh "${HTTP_PORT}" || true
log "Updated. Hard-refresh the browser (Ctrl+F5)."
