"""Strict allowlist of read-only discovery commands, and a safe runner."""
import re
import subprocess

from config import CMD_TIMEOUT, MAX_OUTPUT_CHARS, NAMESPACE

# Commands that must match exactly
EXACT = {
    "uname -a",
    "ip addr",
    "ip route",
    "ss -tunap",
    "cat /etc/resolv.conf",
}

# Argument patterns. None may start with "-", so no extra flags can be smuggled in.
HOST = r"[A-Za-z0-9][A-Za-z0-9.-]{0,252}"
IFACE = r"[A-Za-z0-9][A-Za-z0-9_.-]{0,14}"
PROG = r"[A-Za-z0-9][A-Za-z0-9_.+-]{0,63}"

PATTERNS = [
    re.compile(rf"ping -c ([1-9]|10) {HOST}"),   # ping -c <1-10> <host>
    re.compile(rf"dig (\+short )?{HOST}"),       # dig [+short] <name>
    re.compile(rf"ethtool {IFACE}"),             # ethtool <iface>
    re.compile(rf"which {PROG}( {PROG}){{0,19}}"),  # which <prog> [prog ...]
]

ALLOWED_FORMS = sorted(EXACT) + [
    "ping -c <1-10> <host>",
    "dig [+short] <name>",
    "ethtool <interface>",
    "which <program> [program ...]",
]

# Only these characters may appear at all. Blocks ; | & $ ` > < ( ) quotes, newlines, etc.
SAFE_CHARS = re.compile(r"[A-Za-z0-9 ._/:+-]+")


def check_command(cmd):
    """Return (argv, None) if allowed, or (None, reason) if rejected."""
    if not cmd:
        return None, "empty command"
    if not SAFE_CHARS.fullmatch(cmd):
        bad = sorted(set(c for c in cmd if not SAFE_CHARS.fullmatch(c)))
        return None, f"forbidden characters: {' '.join(repr(c) for c in bad)}"
    if "  " in cmd or cmd != cmd.strip():
        return None, "extra whitespace"
    if cmd in EXACT or any(p.fullmatch(cmd) for p in PATTERNS):
        return cmd.split(" "), None
    return None, "not on the allowlist"


def run_command(argv):
    """Run an allowed argv inside the namespace. No shell. Returns output text."""
    full = ["sudo", "-n", "ip", "netns", "exec", NAMESPACE] + argv
    try:
        p = subprocess.run(full, capture_output=True, text=True, timeout=CMD_TIMEOUT)
        out = p.stdout + (("\n[stderr]\n" + p.stderr) if p.stderr.strip() else "")
        out += f"\n[exit code {p.returncode}]"
    except subprocess.TimeoutExpired as e:
        out = (e.stdout or b"").decode(errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
        out += f"\n[timed out after {CMD_TIMEOUT}s]"
    if len(out) > MAX_OUTPUT_CHARS:
        out = out[:MAX_OUTPUT_CHARS] + "\n[output truncated]"
    return out
