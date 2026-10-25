#!/usr/bin/env bash
# Commercial ERP - installer for a clean Ubuntu 22.04/24.04 VPS (run as root).
# Safe to re-run: every step checks state. It never drops a database or site, never edits an
# existing MariaDB/nginx/sshd configuration, and never enables the firewall by itself.
# Secrets are prompted (hidden) - nothing is stored in Git.
#
#   sudo SITE_NAME=erp.local COMPANY_NAME="اسم المحل" COMPANY_ABBR=SH bash deploy/install.sh
# APP_REPO defaults to the origin of the checkout this script lives in.
set -euo pipefail
cd "$(dirname "$0")"
# shellcheck source=versions.env
source ./versions.env

: "${SITE_NAME:?set SITE_NAME (internal label while you have no domain, e.g. erp.local)}"
APP_REPO="${APP_REPO:-https://github.com/Refaat1942/Commercial-ERP.git}"
APP_BRANCH="${APP_BRANCH:-deployment-ready}"
DEPLOY_KEY="/home/${BENCH_USER}/.ssh/deploy_key"
log(){ printf '\n\033[1;32m==> %s\033[0m\n' "$*"; }
die(){ printf '\033[1;31mERROR: %s\033[0m\n' "$*" >&2; exit 1; }
[ "$(id -u)" -eq 0 ] || die "run as root (sudo)"
[[ "$SITE_NAME" =~ ^[a-zA-Z0-9.-]+$ ]] || die "SITE_NAME may only contain letters, digits, dots and hyphens"

# ---- 0. Preflight (read-only) -----------------------------------------------
. /etc/os-release
case "${VERSION_ID}" in 22.04|24.04) ;; *) die "Ubuntu 22.04/24.04 required (found ${PRETTY_NAME})";; esac
[ "$(awk '/MemTotal/{print int($2/1024)}' /proc/meminfo)" -ge 3500 ] || die "need >= 4 GB RAM (add swap otherwise)"
if [ ! -d "${BENCH_DIR}" ] && ss -tlnH | grep -qE "[:.]${HTTP_PORT}\s"; then die "port ${HTTP_PORT} is already used by another service"; fi
SITE_EXISTS=0
if [ -f "${BENCH_DIR}/sites/${SITE_NAME}/site_config.json" ]; then SITE_EXISTS=1; log "Site ${SITE_NAME} already exists - it will not be touched"
elif [ -d "${BENCH_DIR}/sites/${SITE_NAME}" ]; then log "Removing half-created site directory from a failed attempt (no site_config.json)"; rm -rf "${BENCH_DIR}/sites/${SITE_NAME}"; fi
MARIADB_MARKER=/etc/mysql/.commercial-erp-installed   # written by this script after it installs MariaDB
MARIADB_PREEXISTING=0; if command -v mariadb >/dev/null && [ ! -e "$MARIADB_MARKER" ]; then MARIADB_PREEXISTING=1; fi

# ---- 1. System packages (apt only adds packages; no existing config is replaced) --------
log "System packages"
# shellcheck disable=SC2154
trap 'rc=$?; [ $rc -eq 0 ] || printf "\033[1;31mFAILED (exit %s) at line %s: %s\033[0m\n" "$rc" "$LINENO" "$BASH_COMMAND" >&2' EXIT
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq || log "apt-get update reported errors (often a third-party repo); continuing"
apt-get install -y -qq git curl ca-certificates gnupg xz-utils build-essential pkg-config \
	libffi-dev libssl-dev libmariadb-dev libjpeg-dev zlib1g-dev python3-venv python3-dev \
	redis-server nginx supervisor cron openssl wkhtmltopdf fontconfig libfontconfig1 \
	libxrender1 xfonts-75dpi xfonts-base fonts-noto-core

# ---- 2. MariaDB 11.8 ----------------------------------------------------------------
if [ "$MARIADB_PREEXISTING" -eq 0 ]; then
	log "Installing MariaDB ${MARIADB_SERIES} from the official MariaDB repository"
	install -d -m 0755 /etc/apt/keyrings
	curl -fsSL https://mariadb.org/mariadb_release_signing_key.pgp -o /etc/apt/keyrings/mariadb-keyring.pgp
	cat >/etc/apt/sources.list.d/mariadb.sources <<EOF
Types: deb
URIs: https://deb.mariadb.org/${MARIADB_SERIES}/ubuntu
Suites: ${VERSION_CODENAME}
Components: main
Signed-By: /etc/apt/keyrings/mariadb-keyring.pgp
EOF
	apt-get update -qq || true
	apt-get install -y -qq mariadb-server mariadb-client
	cat >/etc/mysql/mariadb.conf.d/99-commercial-erp.cnf <<'EOF'
[mysqld]
bind-address = 127.0.0.1
character-set-client-handshake = FALSE
character-set-server = utf8mb4
collation-server = utf8mb4_unicode_ci
[mysql]
default-character-set = utf8mb4
EOF
	systemctl enable --now mariadb && systemctl restart mariadb
	touch "$MARIADB_MARKER"
else
	INSTALLED="$(mariadb --version | grep -oE 'Distrib [0-9]+\.[0-9]+' | cut -d' ' -f2)"
	log "MariaDB ${INSTALLED} already installed: configuration and service left untouched"
	[ "$(printf '%s\n%s\n' "${MARIADB_SERIES}" "${INSTALLED}" | sort -V | sed -n 1p)" = "${MARIADB_SERIES}" ] || \
		die "Existing MariaDB ${INSTALLED} is older than ${MARIADB_SERIES}. Upgrade it deliberately (backup first); this script will not."
fi
if ss -tlnH | awk '{print $4}' | grep -qE '^(0\.0\.0\.0|\*|\[::\]):3306$'; then
	die "MariaDB listens on ALL interfaces. Set 'bind-address = 127.0.0.1' yourself (existing services may depend on it), then re-run."
fi

# ---- 3. Node.js (checksum-verified, isolated in /opt/node24) ---------------------------
if [ ! -x /opt/node24/bin/node ] || [ "$(/opt/node24/bin/node -v)" != "v${NODE_VERSION}" ]; then
	log "Node.js ${NODE_VERSION}"
	T="$(mktemp -d)"; F="node-v${NODE_VERSION}-linux-x64.tar.xz"
	curl -fsSL "https://nodejs.org/dist/v${NODE_VERSION}/${F}" -o "$T/$F"
	curl -fsSL "https://nodejs.org/dist/v${NODE_VERSION}/SHASUMS256.txt" -o "$T/SHASUMS256.txt"
	(cd "$T" && grep " ${F}\$" SHASUMS256.txt | sha256sum -c -) || die "Node checksum mismatch"
	mkdir -p /opt/node24 && tar -xJf "$T/$F" -C /opt/node24 --strip-components=1
	rm -rf "$T"
fi
if [ ! -x /opt/node24/bin/yarn ]; then   # npm 11 blocks yarn's install script in global installs: unpack the tarball instead
	Y="$(mktemp -d)"
	(cd "$Y" && env -u npm_config_prefix /opt/node24/bin/npm pack "yarn@${YARN_VERSION}" --silent >/dev/null && tar -xzf "yarn-${YARN_VERSION}.tgz")
	rm -rf /opt/node24/lib/node_modules/yarn && mv "$Y/package" /opt/node24/lib/node_modules/yarn
	ln -sfn ../lib/node_modules/yarn/bin/yarn.js /opt/node24/bin/yarn
	ln -sfn ../lib/node_modules/yarn/bin/yarn.js /opt/node24/bin/yarnpkg
	rm -rf "$Y"
fi
[ -x /opt/node24/bin/yarn ] || die "yarn installation failed"

# ---- 4. Bench user, uv, deploy key ---------------------------------------------------------
[ -x /opt/uv-venv/bin/uv ] || { python3 -m venv /opt/uv-venv && /opt/uv-venv/bin/pip install -q "uv==${UV_VERSION}"; }
id "${BENCH_USER}" >/dev/null 2>&1 || useradd -m -s /bin/bash "${BENCH_USER}"
chmod o+x "/home/${BENCH_USER}"   # nginx must traverse the home dir to serve /assets (no read of its contents)
# bench tries "sudo supervisorctl restart" after init/get-app, which prompts for a password the
# bench user does not have. A shim answering "not found" (exit 127) makes bench skip that restart.
install -d -m 755 /opt/commercial-erp-shims
printf '#!/bin/sh\nexit 127\n' >/opt/commercial-erp-shims/supervisorctl; chmod 755 /opt/commercial-erp-shims/supervisorctl
RUN=(sudo -H -u "${BENCH_USER}" env "PATH=/opt/commercial-erp-shims:/opt/node24/bin:/opt/uv-venv/bin:/home/${BENCH_USER}/.local/bin:/usr/local/bin:/usr/bin:/bin")
if [ -f "$DEPLOY_KEY" ]; then
	"${RUN[@]}" git config --global core.sshCommand "ssh -i ${DEPLOY_KEY} -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new"
fi

# ---- 5. Bench + pinned apps ------------------------------------------------------------------
# A half-finished earlier init (no marker, no site yet) is safe to discard and redo.
if [ -d "${BENCH_DIR}" ] && [ ! -e "${BENCH_DIR}/.init-complete" ] && ! ls "${BENCH_DIR}"/sites/*/site_config.json >/dev/null 2>&1; then
	log "Discarding incomplete bench directory from an earlier attempt (no site data in it)"
	rm -rf "${BENCH_DIR}"
fi
if [ ! -d "${BENCH_DIR}/apps/frappe" ]; then
	log "bench init (Frappe ${FRAPPE_VERSION}) - several minutes"
	"${RUN[@]}" uv python install "${PYTHON_VERSION}"
	"${RUN[@]}" uv tool install "frappe-bench==${BENCH_VERSION}"
	"${RUN[@]}" bash -c "cd ~ && bench init --frappe-branch ${FRAPPE_VERSION} --python \$(uv python find ${PYTHON_VERSION}) $(basename "${BENCH_DIR}")"
	touch "${BENCH_DIR}/.init-complete" && chown "${BENCH_USER}" "${BENCH_DIR}/.init-complete"
fi
[ -d "${BENCH_DIR}/apps/erpnext" ] || { log "ERPNext ${ERPNEXT_VERSION}"; "${RUN[@]}" bash -c "cd ${BENCH_DIR} && bench get-app erpnext --branch ${ERPNEXT_VERSION} https://github.com/frappe/erpnext"; }
[ -d "${BENCH_DIR}/apps/commercial_erp" ] || { log "commercial_erp from ${APP_REPO}"; "${RUN[@]}" bash -c "cd ${BENCH_DIR} && bench get-app commercial_erp '${APP_REPO}' --branch '${APP_BRANCH}'"; }

# ---- 5b. Private internal ports (uncommon, to avoid clashing with other services on the VPS) ----------
REDIS_CACHE_PORT=16379; REDIS_QUEUE_PORT=16380; WEB_PORT=18000; SOCKETIO_PORT=19000
for P in "$REDIS_CACHE_PORT" "$REDIS_QUEUE_PORT" "$WEB_PORT" "$SOCKETIO_PORT"; do
	if ss -tlnH | grep -qE "[:.]${P}\s" && [ "$(redis-cli -p "$P" ping 2>/dev/null || true)" != "PONG" ] && ! supervisorctl status 2>/dev/null | grep -q RUNNING; then
		die "internal port ${P} is used by another service; free it or edit the ports in install.sh"
	fi
done
"${RUN[@]}" bash -c "cd ${BENCH_DIR} && bench set-config -g redis_cache redis://127.0.0.1:${REDIS_CACHE_PORT} && bench set-config -g redis_queue redis://127.0.0.1:${REDIS_QUEUE_PORT} && bench set-config -g redis_socketio redis://127.0.0.1:${REDIS_QUEUE_PORT} && bench set-config -g webserver_port ${WEB_PORT} && bench set-config -g socketio_port ${SOCKETIO_PORT} && bench setup redis"
if [ "$SITE_EXISTS" -eq 0 ]; then   # temporary Redis (localhost only) so new-site/wizard can run before supervisor takes over
	for C in redis_queue redis_cache; do
		"${RUN[@]}" bash -c "cd ${BENCH_DIR} && redis-server config/${C}.conf --daemonize yes >/dev/null"
	done
	sleep 2
	[ "$(redis-cli -p "$REDIS_QUEUE_PORT" ping)" = "PONG" ] && [ "$(redis-cli -p "$REDIS_CACHE_PORT" ping)" = "PONG" ] || die "temporary Redis did not start"
fi

# ---- 6. Site + database (created by bench; passwords prompted, never stored) ---------------------
if [ "$SITE_EXISTS" -eq 0 ]; then
	log "Creating site ${SITE_NAME} and its database"
	if [ "${AUTO_PASSWORDS:-0}" = "1" ]; then
		# Generated on this server only; saved to a root-only file, never printed or committed.
		[ "$MARIADB_PREEXISTING" -eq 0 ] || die "AUTO_PASSWORDS needs a fresh MariaDB; with an existing one, run without AUTO_PASSWORDS and type its root password"
		CREDS_FILE=/root/commercial-erp-credentials.txt
		if [ -e "$CREDS_FILE" ]; then   # re-run after a partial install: reuse what was generated
			ADMINPW="$(sed -n 's/^ERP Administrator password: //p' "$CREDS_FILE")"; DBROOT="$(sed -n 's/^MariaDB root password: //p' "$CREDS_FILE")"
		else
			DBROOT="$(openssl rand -hex 16)"; ADMINPW="$(openssl rand -hex 12)"
			( umask 077; printf 'ERP site: %s\nERP Administrator password: %s\nMariaDB root password: %s\n' "$SITE_NAME" "$ADMINPW" "$DBROOT" >"$CREDS_FILE" )
		fi
		log "Generated passwords saved to $CREDS_FILE (root only). Read with: sudo cat $CREDS_FILE"
	else
		read -rsp "MariaDB root password (input hidden; $( [ "$MARIADB_PREEXISTING" -eq 1 ] && echo 'EXISTING root password' || echo 'choose a NEW strong one - it will be set now')): " DBROOT; echo
		[ ${#DBROOT} -ge 12 ] || die "MariaDB root password must be at least 12 characters"
		read -rsp "ERP Administrator password, min 12 chars (input hidden): " ADMINPW; echo
		[ ${#ADMINPW} -ge 12 ] || die "Administrator password must be at least 12 characters"
	fi
	case "$DBROOT$ADMINPW" in *\'*|*\\*) die "passwords must not contain ' or \\";; esac
	if [ "$MARIADB_PREEXISTING" -eq 0 ]; then
		# fresh install: root is socket-auth only; add a password login for bench (socket login kept)
		printf "ALTER USER 'root'@'localhost' IDENTIFIED VIA unix_socket OR mysql_native_password USING PASSWORD('%s'); FLUSH PRIVILEGES;\n" "$DBROOT" | mariadb
	fi
	CRED="$(mktemp)"; chmod 600 "$CRED"
	printf 'DBROOT=%q\nADMINPW=%q\n' "$DBROOT" "$ADMINPW" >"$CRED"
	chown "${BENCH_USER}" "$CRED"   # after writing: /tmp refuses root writes into files owned by others
	"${RUN[@]}" bash -c ". '$CRED'; cd ${BENCH_DIR} && bench new-site '${SITE_NAME}' --mariadb-root-username root --mariadb-root-password \"\$DBROOT\" --admin-password \"\$ADMINPW\" --install-app erpnext --install-app commercial_erp --set-default" \
		|| { shred -u "$CRED"; die "bench new-site failed; nothing pre-existing was modified"; }
	shred -u "$CRED"; unset DBROOT ADMINPW
fi

# ---- 7. Arabic / Egypt company setup (skipped if the wizard already ran) -----------------------------
if [ -n "${COMPANY_NAME:-}" ] && [ -n "${COMPANY_ABBR:-}" ]; then
	[[ "$COMPANY_ABBR" =~ ^[A-Za-z0-9]{1,5}$ ]] || die "COMPANY_ABBR must be 1-5 letters/digits"
	KW="$(python3 -c 'import json,sys;print(json.dumps({"company_name":sys.argv[1],"company_abbr":sys.argv[2]}))' "$COMPANY_NAME" "$COMPANY_ABBR")"
	"${RUN[@]}" bash -c "cd ${BENCH_DIR} && bench --site '${SITE_NAME}' execute commercial_erp.setup.wizard.run --kwargs '${KW}'"
else
	log "COMPANY_NAME/COMPANY_ABBR not set: complete the setup wizard in the browser (Egypt / EGP / Arabic)."
fi

# stop the temporary Redis; supervisor runs the permanent ones on the same ports
redis-cli -p "$REDIS_QUEUE_PORT" shutdown nosave 2>/dev/null || true; redis-cli -p "$REDIS_CACHE_PORT" shutdown nosave 2>/dev/null || true
sleep 1

# ---- 8. Processes + nginx on ${HTTP_PORT} (own, uniquely named config files) ----------------------------
log "supervisor + nginx on port ${HTTP_PORT}"
"${RUN[@]}" bash -c "cd ${BENCH_DIR} && bench set-nginx-port '${SITE_NAME}' ${HTTP_PORT} && bench --site '${SITE_NAME}' enable-scheduler && bench setup supervisor --yes --skip-supervisord && bench setup nginx --yes"
# bench's nginx template uses a "main" log format that a stock/shared nginx.conf does not define:
# use the built-in "combined" format and our own log files instead (does not touch other sites' logs).
sed -i -E 's#access_log +[^;]+;#access_log /var/log/nginx/commercial-erp.access.log combined;#; s#error_log +[^;]+;#error_log /var/log/nginx/commercial-erp.error.log;#' "${BENCH_DIR}/config/nginx.conf"
ln -sfn "${BENCH_DIR}/config/supervisor.conf" /etc/supervisor/conf.d/commercial-erp.conf
ln -sfn "${BENCH_DIR}/config/nginx.conf" /etc/nginx/conf.d/commercial-erp.conf
systemctl enable --now supervisor nginx >/dev/null 2>&1 || true
nginx -t || { rm -f /etc/nginx/conf.d/commercial-erp.conf; die "nginx config invalid; link removed, existing nginx unchanged"; }
systemctl reload nginx
supervisorctl reread >/dev/null && supervisorctl update >/dev/null

# ---- 9. Firewall: never enabled automatically ---------------------------------------------------------------
SSHP="$(sshd -T 2>/dev/null | awk '/^port /{p=$2} END{print p}')"; SSHP="${SSHP:-22}"
if command -v ufw >/dev/null && ufw status | grep -q '^Status: active'; then
	ufw deny "${SOCKETIO_PORT}/tcp" >/dev/null   # Frappe realtime (node) binds all interfaces; keep it internal
	ufw allow "${HTTP_PORT}/tcp" >/dev/null && log "ufw (already active): allowed ${HTTP_PORT}/tcp"
else
	log "ufw is not active - left unchanged. To lock the server down yourself (SSH first!):"
	echo "  sudo apt-get install -y ufw && sudo ufw allow ${SSHP}/tcp && sudo ufw allow ${HTTP_PORT}/tcp && sudo ufw enable"
	echo "  (also allow ${HTTP_PORT} in the Hostinger panel firewall if you use one)"
fi

# ---- 10. Daily backup 02:30 ----------------------------------------------------------------------------------------
install -d -o "${BENCH_USER}" -m 700 /var/backups/commercial-erp
install -m 755 backup.sh /usr/local/bin/commercial-erp-backup
cat >/etc/cron.d/commercial-erp-backup <<EOF
30 2 * * * ${BENCH_USER} SITE=${SITE_NAME} BENCH_DIR=${BENCH_DIR} /usr/local/bin/commercial-erp-backup >> /var/log/commercial-erp-backup.log 2>&1
EOF
touch /var/log/commercial-erp-backup.log && chown "${BENCH_USER}" /var/log/commercial-erp-backup.log

log "Finished. Check:  bash deploy/healthcheck.sh ${HTTP_PORT}   then open http://<server-ip>:${HTTP_PORT}"
echo "HTTP only: set up a domain + HTTPS (docs/DEPLOYMENT.md) before real customer data / passwords go over the internet."
