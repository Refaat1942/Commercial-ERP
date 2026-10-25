#!/usr/bin/env bash
# Second, separate site with FAKE demo data for showing the system to prospective customers
# (own database, own port 15162; the real site is untouched).
#   sudo DEMO_SITE=demo.local bash /home/fes/commercial_erp_src/deploy/create_demo_site.sh
# Needs: the main install already done, MariaDB root password (hidden prompt).
set -euo pipefail
cd "$(dirname "$0")"
# shellcheck source=versions.env
source ./versions.env
DEMO_SITE="${DEMO_SITE:-demo.local}"
DEMO_PORT="${DEMO_PORT:-15162}"
log(){ printf '\n\033[1;32m==> %s\033[0m\n' "$*"; }
die(){ printf '\033[1;31mERROR: %s\033[0m\n' "$*" >&2; exit 1; }
[ "$(id -u)" -eq 0 ] || die "run as root (sudo)"
[[ "$DEMO_SITE" =~ ^[a-zA-Z0-9.-]+$ ]] || die "bad DEMO_SITE"
[ -d "${BENCH_DIR}/apps/commercial_erp" ] || die "run install.sh first"
[ ! -e "${BENCH_DIR}/sites/${DEMO_SITE}/site_config.json" ] || die "${DEMO_SITE} already exists (to rebuild its data: bench --site ${DEMO_SITE} execute commercial_erp.setup.demo.clear, then ...demo.seed)"
ss -tlnH | grep -qE "[:.]${DEMO_PORT}\s" && die "port ${DEMO_PORT} already in use"
RUN=(sudo -H -u "${BENCH_USER}" env "PATH=/opt/commercial-erp-shims:/opt/node24/bin:/opt/uv-venv/bin:/home/${BENCH_USER}/.local/bin:/usr/local/bin:/usr/bin:/bin")

read -rsp "MariaDB root password (hidden): " DBROOT; echo
ADMINPW="$(openssl rand -hex 12)"; DEMOPW="${DEMO_PASSWORD:-$(openssl rand -hex 5)Aa1}"
case "$DBROOT" in *\'*|*\\*) die "password must not contain ' or \\";; esac
CRED="$(mktemp)"; chmod 600 "$CRED"; printf 'DBROOT=%q\nADMINPW=%q\n' "$DBROOT" "$ADMINPW" >"$CRED"; chown "${BENCH_USER}" "$CRED"
log "creating ${DEMO_SITE}"
"${RUN[@]}" bash -c ". '$CRED'; cd ${BENCH_DIR} && bench new-site '${DEMO_SITE}' --mariadb-root-username root --mariadb-root-password \"\$DBROOT\" --admin-password \"\$ADMINPW\" --install-app erpnext --install-app commercial_erp" \
	|| { shred -u "$CRED"; die "new-site failed"; }
shred -u "$CRED"; unset DBROOT ADMINPW
log "company, Arabic/Egypt defaults, UI, fake data, demo logins"
"${RUN[@]}" bash -c "cd ${BENCH_DIR} && bench --site '${DEMO_SITE}' execute commercial_erp.setup.wizard.run --kwargs '{\"company_name\": \"شركة العرض التجريبي\", \"company_abbr\": \"DM\"}' && bench --site '${DEMO_SITE}' execute commercial_erp.setup.update.run && bench --site '${DEMO_SITE}' execute commercial_erp.setup.demo.seed && bench --site '${DEMO_SITE}' execute commercial_erp.setup.demo.create_users --kwargs '{\"password\": \"${DEMOPW}\"}' && bench --site '${DEMO_SITE}' enable-scheduler && bench --site '${DEMO_SITE}' set-config allow_demo_links 1"

log "nginx: ${DEMO_SITE} on port ${DEMO_PORT} (main site stays on ${HTTP_PORT})"
cp -a "${BENCH_DIR}/config/nginx.conf" "${BENCH_DIR}/config/nginx.conf.before-demo"
"${RUN[@]}" bash -c "cd ${BENCH_DIR} && bench set-nginx-port '${DEMO_SITE}' ${DEMO_PORT} && bench setup nginx --yes"
sed -i -E 's#access_log +[^;]+;#access_log /var/log/nginx/commercial-erp.access.log combined;#; s#error_log +[^;]+;#error_log /var/log/nginx/commercial-erp.error.log;#' "${BENCH_DIR}/config/nginx.conf"
if ! nginx -t; then cp -a "${BENCH_DIR}/config/nginx.conf.before-demo" "${BENCH_DIR}/config/nginx.conf"; die "nginx config invalid; restored previous config (demo site exists but is not exposed)"; fi
systemctl reload nginx
if command -v ufw >/dev/null && ufw status | grep -q '^Status: active'; then ufw allow "${DEMO_PORT}/tcp" >/dev/null && log "ufw: allowed ${DEMO_PORT}/tcp"; else echo "ufw not active: open TCP ${DEMO_PORT} in your firewall / Hostinger panel if needed"; fi

OUTF=/root/commercial-erp-demo-credentials.txt
( umask 077; { echo "DEMO SITE (fake data) - http://<server-ip>:${DEMO_PORT}/login"; echo "Password for all demo users: ${DEMOPW}";
  for u in owner cashier store accountant; do echo "demo-${u}@demo.example.com"; done; } >"$OUTF" )
log "Done. Credentials (root-only): sudo cat $OUTF   Guide: docs/DEMO.md"
