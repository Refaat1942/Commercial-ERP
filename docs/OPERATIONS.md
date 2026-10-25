# Operations

## Daily
| Task | Command |
|---|---|
| Health | `bash deploy/healthcheck.sh 15161` |
| Processes | `sudo supervisorctl status` |
| Restart all | `sudo supervisorctl restart all && sudo systemctl reload nginx` |
| Logs | `~/frappe-bench/logs/*.log` (web, worker, schedule), `/var/log/nginx/*.log`, `/var/log/mysql/`, `/var/log/commercial-erp-backup.log` |

## Backup (automatic 02:30; manual anytime)
```bash
sudo -u frappe SITE=erp.local BENCH_DIR=/home/frappe/frappe-bench /usr/local/bin/commercial-erp-backup
ls -la /var/backups/commercial-erp
```
Contains DB (`*-database.sql.gz`), public/private files, `site_config` backup. Copy them **off the VPS** regularly (e.g. `rsync`/`rclone` to storage you control). The `site_config` backup holds the encryption key - protect it.

## Restore (always into a separate test site first)
```bash
sudo -u frappe bash deploy/restore.sh restore-check.local /var/backups/commercial-erp/<ts>-<site>-database.sql.gz [public.tar] [private.tar]
```
Verified locally: backup of `test.local` restored into `restore-test.local` with identical company, 98 accounts, Arabic settings, print format and role profiles.
Disaster recovery on the live site: take a fresh backup of the broken state first, then `bench --site SITE --force restore <db.sql.gz> --with-files...` after explicit confirmation.

## Troubleshooting
- 502 / blank page: `supervisorctl status`; `tail ~/frappe-bench/logs/web.error.log`.
- Port 15161 not reachable: `ss -tlnp | grep 15161`, `sudo nginx -t`, `ufw status`, Hostinger panel firewall.
- Assets/Arabic fonts missing after update: `bench build` then restart.
- DB connection errors: `systemctl status mariadb`; `bench --site SITE mariadb`.
- After editing site config / nginx port: `bench setup nginx --yes && sudo systemctl reload nginx`.
