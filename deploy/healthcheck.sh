#!/usr/bin/env bash
# Usage: healthcheck.sh [port]   (exit 0 = healthy)
PORT="${1:-15161}"; rc=0
ok(){ echo "OK   $*"; }; bad(){ echo "FAIL $*"; rc=1; }
code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "http://127.0.0.1:${PORT}/api/method/ping")
[ "$code" = "200" ] && ok "HTTP ping on :$PORT" || bad "HTTP ping on :$PORT (got $code)"
for p in 3306 6379 11000 13000; do
	if ss -tlnH | awk '{print $4}' | grep -E "^(0\.0\.0\.0|\*|\[::\]):$p$" >/dev/null; then bad "port $p listens on ALL interfaces"; else ok "port $p not public"; fi
done
systemctl is-active --quiet mariadb && ok mariadb || bad mariadb
command -v supervisorctl >/dev/null && supervisorctl status 2>/dev/null | grep -v RUNNING | grep -q . && bad "supervisor has non-running programs" || ok "supervisor programs"
exit $rc
