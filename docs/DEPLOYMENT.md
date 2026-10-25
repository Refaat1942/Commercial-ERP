# Commercial ERP - Deployment guide (Hostinger Ubuntu VPS, port 15161)

Not yet executed on the real VPS (no access from the build environment). `deploy/install.sh` has been
syntax- and shellcheck-validated only; the application itself was built and tested on a Bench
(see "What was verified" in `docs/PROGRESS.md`). Run on a fresh/non-critical window first.

## Version matrix (pinned in `deploy/versions.env`)
| Component | Version | Source |
|---|---|---|
| ERPNext | `v16.52.1` (`version-16`) | github.com/frappe/erpnext tags |
| Frappe | `v16.53.0` (`version-16`) | github.com/frappe/frappe tags (ERPNext requires `>=16.50,<17`) |
| Python | 3.14 (frappe: `>=3.14,<3.15`), via pinned `uv` | frappe `pyproject.toml` |
| Node.js / Yarn | 24.22.1 / 1.22.22 (frappe: `>=24`) | frappe `package.json` |
| MariaDB | 11.8 (official docs for v16) | Frappe install docs. **Local tests used 10.11** (see limitations) |
| Redis | 6+ (bench-managed instances, localhost only) | Frappe docs |
| Bench | 5.31.1 | PyPI |
| OS | Ubuntu 22.04 / 24.04 | script preflight |

## 1. Inspect the VPS (read-only)
```bash
sudo bash deploy/vps_discovery.sh
```
Send me the output if anything looks unexpected (existing nginx/MariaDB/Docker, port 15161 in use, <4 GB RAM).

## 2. Push the app to a private Git repo
`commercial_erp/` is a self-contained app. Move it to its own private repo (keep `license.txt` and `NOTICE`):
```bash
git subtree split -P commercial_erp -b commercial-erp-only
git push git@github.com:<you>/commercial_erp.git commercial-erp-only:main
```

## 3. Install (one command, interactive for secrets)
```bash
sudo SITE_NAME=erp.local COMPANY_NAME="اسم المحل" COMPANY_ABBR=SH \
     APP_REPO=git@github.com:<you>/commercial_erp.git APP_BRANCH=main \
     bash deploy/install.sh
```
- Prompts (hidden) for the MariaDB root password and the new ERP Administrator password (>=12 chars). Nothing is written to Git or shell history.
- Creates user `frappe`, installs pinned versions, creates the site and **its database via `bench new-site`**, runs the Arabic/Egypt setup, configures nginx on **15161** + supervisor, UFW (SSH + 15161 only; asks before enabling), and a daily 02:30 backup.
- Refuses to continue if: not Ubuntu 22.04/24.04, <4 GB RAM, port 15161 used by another service, or existing MariaDB older than 11.8. It never drops databases or sites; an existing site is left alone.
- `SITE_NAME` is only an internal label while you have no domain; nginx on 15161 answers any Host and routes to this site. Use your real domain later (see HTTPS).
- Hostinger also has a panel firewall: allow TCP 15161 and your SSH port there too if enabled.

## 4. Verify
```bash
bash deploy/healthcheck.sh 15161      # HTTP ping, DB/Redis not publicly bound, supervisor, mariadb
curl -i http://<server-ip>:15161/api/method/ping
```
Login as `Administrator`; create users with Role Profiles `Shop Owner`, `Cashier`, `Storekeeper`, `Accountant`.

## 5. Manual equivalents (if you prefer not to use the script)
`install.sh` is the reference; each step is a labelled block (packages -> MariaDB -> Node -> uv/bench user -> `bench init --frappe-branch v16.53.0` -> `bench get-app erpnext --branch v16.52.1` -> `bench get-app commercial_erp <repo>` -> `bench new-site` -> `bench set-nginx-port SITE 15161` -> `sudo bench setup production frappe` -> ufw).

## 6. Security model
- MariaDB bound to `127.0.0.1` (`/etc/mysql/mariadb.conf.d/99-commercial-erp.cnf`); bench Redis instances bind localhost. `healthcheck.sh` fails if 3306/6379/11000/13000 listen publicly.
- Only SSH and 15161 are opened. HTTP on 15161 is **unencrypted**: do not use real customer logins over the internet until HTTPS is set up.
- Administrator password: strong, unique; enable 2FA for owner/admin in *System Settings*.

## 7. Domain + HTTPS (later; requires a real domain)
1. Point an `A` record (e.g. `erp.example.com`) to the VPS IP; wait for DNS.
2. `sudo -u frappe bench rename-site erp.local erp.example.com` (take a backup first) and `bench setup nginx --yes`.
3. Open ports 80/443 in UFW and the Hostinger panel, then `sudo bench setup lets-encrypt erp.example.com` (needs port 80 reachable). Keep or close 15161 afterwards.
Nothing here is configured or claimed as secure until you complete this with a real domain.

## 8. Upgrade
```bash
sudo -u frappe bash -c 'cd ~/frappe-bench && bench --site SITE backup --with-files'   # always first
# bump pins in deploy/versions.env, test on a restored copy, then:
sudo -u frappe bash -c 'cd ~/frappe-bench && bench update --pull'   # or: git checkout new tag in each app, bench migrate, bench build
```
Upgrade the app only: `cd apps/commercial_erp && git pull && cd ../.. && bench --site SITE migrate && sudo supervisorctl restart all`.

## 9. Rollback
1. Take a backup **before** every change (`commercial-erp-backup`).
2. App-only problem: `cd apps/commercial_erp && git checkout <previous-tag> && bench --site SITE migrate && sudo supervisorctl restart all`.
3. Data problem: restore the pre-change backup into a **new** site (`deploy/restore.sh`), check it, then switch (rename sites) - never restore over the live site without a fresh backup of it.
4. Failed first install: nothing existing was modified; remove `/home/frappe/frappe-bench` and `/etc/nginx/conf.d/frappe-bench.conf`, `/etc/supervisor/conf.d/frappe-bench.conf`, then re-run. (Dropping the site DB is destructive: `bench drop-site` needs your explicit decision.)
