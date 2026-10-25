#!/usr/bin/env bash
# Read-only inspection of the VPS. Changes nothing. Run:  sudo bash vps_discovery.sh
set -u
echo "== OS";        lsb_release -ds 2>/dev/null || cat /etc/os-release | head -2
echo "== CPU/RAM/disk"; nproc; free -h | sed -n 2p; df -h / | tail -1
echo "== Listening ports (public vs local)"; ss -tlnH | awk '{print $4}' | sort -u
echo "== Port 15161 in use?"; ss -tlnH | grep -q ':15161 ' && echo "YES - already in use" || echo "free"
echo "== Existing services"; systemctl list-units --type=service --state=running --no-legend 2>/dev/null | awk '{print $1}' | grep -E 'nginx|apache|mariadb|mysql|redis|docker|supervisor|ssh' || true
echo "== Existing versions"; mariadb --version 2>/dev/null || mysql --version 2>/dev/null || echo "no mariadb/mysql"
nginx -v 2>&1 | head -1 || true; redis-server --version 2>/dev/null || echo "no redis"; python3 --version; node --version 2>/dev/null || echo "no node"
echo "== Firewall"; ufw status 2>/dev/null | head -5 || echo "ufw not installed"
echo "== SSH port"; sshd -T 2>/dev/null | grep -i '^port ' || grep -i '^Port' /etc/ssh/sshd_config || echo 22
echo "== Existing bench/sites"; ls -d /home/*/fes-bench 2>/dev/null || echo "none"
