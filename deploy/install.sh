#!/usr/bin/env bash
# Commercial ERP - production installer for Ubuntu 22.04/24.04 (run as root on the VPS).
# Idempotent: every step checks state first. Never drops databases or sites.
# Secrets are prompted interactively (or read from root-only files); none are stored in Git.
#
#   sudo SITE_NAME=erp.local COMPANY_NAME="My Shop" COMPANY_ABBR=MS \
#        APP_REPO=https://github.com/<you>/commercial_erp.git APP_BRANCH=main bash deploy/install.sh
set -euo pipefail
cd "$(dirname "$0")"
source ./versions.env

: "${SITE_NAME:?set SITE_NAME (a hostname-like label; use your domain later, e.g. erp.example.com)}"
: "${APP_REPO:?set APP_REPO (git URL or local path of the commercial_erp repository)}"
APP_BRANCH="${APP_BRANCH:-main}"
SKIP_FIREWALL="${SKIP_FIREWALL:-0}"
log(){ printf '\n\033[1;32m==> %s\033[0m\n' "$*"; }
die(){ printf '\033[1;31mERROR: %s\033[0m\n' "$*" >&2; exit 1; }
[ "$(id -u)" -eq 0 ] || die "run as root (sudo)"

# ---- 0. Preflight -----------------------------------------------------------
. /etc/os-release
case "${VERSION_ID}" in 22.04|24.04) ;; *) die "Ubuntu 22.04/24.04 required (found ${PRETTY_NAME})";; esac
[ "$(free -m | awk '/Mem:/{print $2}')" -ge 3500 ] || die "need >= 4 GB RAM (add swap otherwise)"
if ss -tlnH | grep -q ":${HTTP_PORT} " && [ ! -d "${BENCH_DIR}" ]; then die "port ${HTTP_PORT} already in use by another service"; fi
if [ -d "${BENCH_DIR}/sites/${SITE_NAME}" ]; then log "Site ${SITE_NAME} already exists - will NOT recreate it"; SITE_EXISTS=1; else SITE_EXISTS=0; fi

# ---- 1. System packages -----------------------------------------------------
log "System packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq git curl ca-certificates gnupg xz-utils build-essential pkg-config \
	libffi-dev libssl-dev libmariadb-dev libjpeg-dev zlib1g-dev python3-venv python3-dev \
	redis-server nginx supervisor cron openssl wkhtmltopdf fontconfig xvfb libfontconfig1 \
	libxrender1 xfonts-75dpi xfonts-base ufw fail2ban fonts-noto-core fonts-noto-ui-core

# ---- 2. MariaDB 11.8 (official MariaDB repo) --------------------------------
if ! command -v mariadb >/dev/null; then
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
	apt-get update -qq && apt-get install -y -qq mariadb-server mariadb-client
else
	INSTALLED="$(mariadb --version | grep -oE 'Distrib [0-9]+\.[0-9]+' | cut -d' ' -f2)"
	log "MariaDB already installed (${INSTALLED}); leaving it untouched"
	[ "$(printf '%s\n%s\n' "${MARIADB_SERIES}" "${INSTALLED}" | sort -V | head -1)" = "${MARIADB_SERIES}" ] || \
		die "Existing MariaDB ${INSTALLED} is older than the required ${MARIADB_SERIES}. Upgrade it deliberately (backup first) - this script will not."
fi
cat >/etc/mysql/mariadb.conf.d/99-commercial-erp.cnf <<'EOF'
[mysqld]
bind-address = 127.0.0.1
character-set-client-handshake = FALSE
character-set-server = utf8mb4
collation-server = utf8mb4_unicode_ci
skip-name-resolve
[mysql]
default-character-set = utf8mb4
EOF
systemctl enable --now mariadb && systemctl restart mariadb

# ---- 3. Node.js (checksum-verified tarball in /opt; does not touch system node) ----
if [ ! -x /opt/node24/bin/node ] || [ "$(/opt/node24/bin/node -v)" != "v${NODE_VERSION}" ]; then
	log "Node.js ${NODE_VERSION}"
	T="$(mktemp -d)"; F="node-v${NODE_VERSION}-linux-x64.tar.xz"
	curl -fsSL "https://nodejs.org/dist/v${NODE_VERSION}/${F}" -o "$T/$F"
	curl -fsSL "https://nodejs.org/dist/v${NODE_VERSION}/SHASUMS256.txt" -o "$T/SHASUMS256.txt"
	(cd "$T" && grep " ${F}\$" SHASUMS256.txt | sha256sum -c -) || die "Node checksum mismatch"
	rm -rf /opt/node24 && mkdir -p /opt/node24 && tar -xJf "$T/$F" -C /opt/node24 --strip-components=1
	/opt/node24/bin/npm install -g "yarn@${YARN_VERSION}" >/dev/null
	rm -rf "$T"
fi

# ---- 4. uv (pinned) + bench user --------------------------------------------
[ -x /opt/uv-venv/bin/uv ] || { python3 -m venv /opt/uv-venv && /opt/uv-venv/bin/pip install -q "uv==${UV_VERSION}"; }
id "${BENCH_USER}" >/dev/null 2>&1 || useradd -m -s /bin/bash "${BENCH_USER}"
RUN="sudo -H -u ${BENCH_USER} env PATH=/opt/node24/bin:/opt/uv-venv/bin:/home/${BENCH_USER}/.local/bin:/usr/local/bin:/usr/bin:/bin"

# ---- 5. Bench + apps (pinned tags) ------------------------------------------
if [ ! -d "${BENCH_DIR}/apps/frappe" ]; then
	log "bench init (Frappe ${FRAPPE_VERSION}) - takes several minutes"
	$RUN uv python install "${PYTHON_VERSION}"
	$RUN uv tool install "frappe-bench==${BENCH_VERSION}"
	$RUN bash -c "cd ~ && bench init --frappe-branch ${FRAPPE_VERSION} --python \$(uv python find ${PYTHON_VERSION}) frappe-bench"
fi
[ -d "${BENCH_DIR}/apps/erpnext" ] || { log "ERPNext ${ERPNEXT_VERSION}"; $RUN bash -c "cd ${BENCH_DIR} && bench get-app erpnext --branch ${ERPNEXT_VERSION} https://github.com/frappe/erpnext"; }
[ -d "${BENCH_DIR}/apps/commercial_erp" ] || { log "commercial_erp"; $RUN bash -c "cd ${BENCH_DIR} && bench get-app commercial_erp '${APP_REPO}' --branch '${APP_BRANCH}'"; }

# ---- 6. Site + database (bench-managed; passwords prompted, never stored in Git) --------
if [ "$SITE_EXISTS" -eq 0 ]; then
	log "Creating site ${SITE_NAME} (new database created by bench)"
	read -rsp "MariaDB root password (input hidden; leave empty to use unix_socket root auth): " DBROOT; echo
	read -rsp "New ERP Administrator password, min 12 chars (input hidden): " ADMINPW; echo
	[ ${#ADMINPW} -ge 12 ] || die "Administrator password must be at least 12 characters"
	# Hand the secrets to the bench user via a 0600 temp file (not argv / shell history), then delete it.
	CRED="$(mktemp)"; chown "${BENCH_USER}" "$CRED"; chmod 600 "$CRED"
	printf 'DBROOT=%q\nADMINPW=%q\n' "$DBROOT" "$ADMINPW" >"$CRED"
	DBARG='--mariadb-root-password "$DBROOT"'; [ -n "$DBROOT" ] || DBARG=''
	$RUN bash -c ". '$CRED'; cd ${BENCH_DIR} && bench new-site '${SITE_NAME}' ${DBARG} --admin-password \"\$ADMINPW\" --install-app erpnext --install-app commercial_erp --set-default" \
		|| { shred -u "$CRED"; die "bench new-site failed (nothing existing was modified)"; }
	shred -u "$CRED"; unset DBROOT ADMINPW
fi

# ---- 7. Company / Arabic-Egypt defaults (only on a fresh, un-setup site) ---------------
if [ -n "${COMPANY_NAME:-}" ] && [ -n "${COMPANY_ABBR:-}" ]; then
	$RUN bash -c "cd ${BENCH_DIR} && bench --site '${SITE_NAME}' execute commercial_erp.setup.wizard.run --kwargs '{\"company_name\": \"${COMPANY_NAME}\", \"company_abbr\": \"${COMPANY_ABBR}\"}'"
else
	log "COMPANY_NAME/COMPANY_ABBR not set: finish the setup wizard in the browser (choose Egypt / EGP / Arabic)."
fi

# ---- 8. Production processes: supervisor + nginx on ${HTTP_PORT} --------------------------
log "Production configuration (nginx on port ${HTTP_PORT}, supervisor)"
$RUN bash -c "cd ${BENCH_DIR} && bench set-nginx-port '${SITE_NAME}' ${HTTP_PORT} && bench --site '${SITE_NAME}' enable-scheduler"
if [ ! -L /etc/nginx/conf.d/frappe-bench.conf ] && [ ! -e /etc/nginx/conf.d/frappe-bench.conf ]; then
	( cd "${BENCH_DIR}" && /home/${BENCH_USER}/.local/bin/bench setup production "${BENCH_USER}" --yes ) \
		|| die "bench setup production failed (run it manually; see docs/DEPLOYMENT.md)"
else
	( cd "${BENCH_DIR}" && /home/${BENCH_USER}/.local/bin/bench setup nginx --yes && /home/${BENCH_USER}/.local/bin/bench setup supervisor --yes ) || true
fi
nginx -t && systemctl reload nginx
supervisorctl reread >/dev/null && supervisorctl update >/dev/null

# ---- 9. Firewall: SSH + ${HTTP_PORT} only -------------------------------------------------
if [ "$SKIP_FIREWALL" != "1" ]; then
	SSHP="$(sshd -T 2>/dev/null | awk '/^port /{print $2; exit}')"; SSHP="${SSHP:-22}"
	ufw allow "${SSHP}/tcp" >/dev/null
	ufw allow "${HTTP_PORT}/tcp" >/dev/null
	if ufw status | grep -q inactive; then
		read -rp "Enable ufw now? SSH port ${SSHP} is already allowed. Type YES to enable: " A
		[ "$A" = "YES" ] && ufw --force enable || log "ufw left disabled"
	fi
fi

# ---- 10. Daily backup (02:30) -------------------------------------------------------------
install -d -o "${BENCH_USER}" -m 700 /var/backups/commercial-erp
install -m 755 backup.sh /usr/local/bin/commercial-erp-backup
cat >/etc/cron.d/commercial-erp-backup <<EOF
30 2 * * * ${BENCH_USER} SITE=${SITE_NAME} BENCH_DIR=${BENCH_DIR} /usr/local/bin/commercial-erp-backup >> /var/log/commercial-erp-backup.log 2>&1
EOF
touch /var/log/commercial-erp-backup.log && chown "${BENCH_USER}" /var/log/commercial-erp-backup.log

log "Done. Verify with:  bash deploy/healthcheck.sh ${HTTP_PORT}"
echo "Open http://<server-ip>:${HTTP_PORT}  (HTTP only; see docs/HTTPS.md before handling real customer data)"
