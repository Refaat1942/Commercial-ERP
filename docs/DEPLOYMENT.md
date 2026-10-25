# Commercial ERP - Deployment guide (Hostinger Ubuntu VPS, port 15161)

Not yet executed on the real VPS (no access from the build environment). `deploy/install.sh` has been
syntax- and shellcheck-validated only (nginx port 15161 output of `bench setup nginx` was inspected locally); the application itself was built and tested on a Bench
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

## 2. Repository
The deployable app lives on branch **`deployment-ready`** of `Refaat1942/Commercial-ERP` (root = `pyproject.toml`, app, `deploy/`, `docs/`; no ERPNext source). **Make the repo Private** (GitHub -> Settings -> General -> Danger Zone -> Change visibility) - the deploy key below works for private repos.

## 3. Install on the clean VPS (nothing needs to exist beforehand)
Access to the private repo uses a **read-only deploy key** created on the VPS (no personal tokens):
```bash
sudo apt-get update && sudo apt-get install -y git openssh-client
sudo id frappe >/dev/null 2>&1 || sudo useradd -m -s /bin/bash frappe
sudo -u frappe mkdir -p -m 700 /home/frappe/.ssh
sudo -u frappe test -f /home/frappe/.ssh/deploy_key || sudo -u frappe ssh-keygen -t ed25519 -N "" -C commercial-erp-deploy -f /home/frappe/.ssh/deploy_key
sudo cat /home/frappe/.ssh/deploy_key.pub     # add as a Deploy key (leave "Allow write" UNchecked): repo -> Settings -> Deploy keys
```
Then fetch the installer and run it (port **15161**):
```bash
sudo -u frappe GIT_SSH_COMMAND="ssh -i /home/frappe/.ssh/deploy_key -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new" \
  git clone --branch deployment-ready --single-branch git@github.com:Refaat1942/Commercial-ERP.git /home/frappe/commercial_erp_src
sudo bash /home/frappe/commercial_erp_src/deploy/vps_discovery.sh                         # read-only look first
sudo APP_BRANCH=deployment-ready SITE_NAME=erp.local COMPANY_NAME="اسم المحل" COMPANY_ABBR=SH \
  bash /home/frappe/commercial_erp_src/deploy/install.sh
```
- `StrictHostKeyChecking=accept-new` trusts GitHub's key on first contact; compare with https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/githubs-ssh-key-fingerprints if you want to be strict.
- Prompts (hidden) for the MariaDB root password (a **new** one on a fresh server; the existing one if MariaDB is already installed) and the ERP Administrator password (both >= 12 chars). Nothing is stored in Git or history.
- Creates user `frappe`, pinned Frappe/ERPNext, the site and **its database through `bench new-site`**, Arabic/Egypt setup, supervisor + nginx on **15161** (own files `commercial-erp.conf`), and a daily 02:30 backup.
- Safety: refuses if Ubuntu is not 22.04/24.04, RAM < 4 GB, port 15161 is taken, existing MariaDB < 11.8 or listening publicly. An existing MariaDB/nginx/sshd config is never edited; an existing site is never touched; the firewall is never enabled automatically (it prints the exact `ufw` commands - allow SSH first). Re-running is safe.
- `SITE_NAME` is only a label until you have a domain; nginx on 15161 answers any Host.
- If the Hostinger panel firewall is on, allow TCP 15161 and SSH there too.

## 4. Verify
```bash
bash /home/frappe/commercial_erp_src/deploy/healthcheck.sh 15161
curl -i http://<server-ip>:15161/api/method/ping
```
Log in as `Administrator`; create users with Role Profiles `Shop Owner`, `Cashier`, `Storekeeper`, `Accountant`.

## 5. Manual equivalent
`install.sh` is the reference; each step is a labelled block (packages -> MariaDB -> Node -> uv/bench user -> `bench init --frappe-branch v16.53.0` -> `bench get-app erpnext --branch v16.52.1` -> `bench get-app commercial_erp <repo>` -> `bench new-site` -> `bench set-nginx-port SITE 15161` -> `bench setup supervisor/nginx` and symlink -> ufw).
**Note:** `bench setup nginx` writes a server block for *every* site in the bench; extra test sites (e.g. from `restore.sh`) default to port 80. Drop test sites (or `bench set-nginx-port <site> 15162`) before re-running it.

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
