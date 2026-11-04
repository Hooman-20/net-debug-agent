"""Step 3: the model learns the system by asking for allowlisted commands, then writes a summary."""
import re

from allowlist import ALLOWED_FORMS, check_command, run_command
from config import MAX_BAD_REPLIES, MAX_DISCOVERY_STEPS, NAMESPACE, SUMMARY_FILE
from model import ask_model

SYSTEM_PROMPT = f"""You are a Linux network debugging agent. Learn this system by running read-only commands.

You may ONLY use these command forms, written exactly like this:
{chr(10).join('  ' + f for f in ALLOWED_FORMS)}
No pipes, no extra flags, no other commands. You can run at most {MAX_DISCOVERY_STEPS} commands.

Each reply must be exactly ONE of (nothing else, no commentary):
  RUN: <command>
  SUMMARY:
  <summary>

Ask for one command per reply. When you know enough, reply with SUMMARY: and a short plain-text
system summary with these headings: OS, Interfaces, IPs, Routes, DNS, Installed tools.
Include interface names, MTUs, and the nameserver. Under Installed tools, list which network tools
(ping, dig, iperf3, tc, ss, ethtool, python3, nc, traceroute, tcpdump) are present or missing."""


def parse_reply(reply):
    """Return ("run", cmd), ("summary", text) or ("bad", None).

    The model often adds a sentence before RUN:, so take the last RUN: line.
    Whatever is extracted still has to pass the strict allowlist check.
    """
    text = reply.strip()
    m = re.search(r"SUMMARY:\s*(.*)", text, re.S)
    if m and m.group(1).strip():
        return "summary", m.group(1).strip()
    runs = re.findall(r"RUN:[ \t]*([^\n]*)", text)
    if runs:
        return "run", runs[-1].strip().strip("`").strip()
    return "bad", None


def discover(verbose=True):
    log = print if verbose else (lambda *a, **k: None)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "Start discovery."},
    ]
    steps = bad = 0
    while True:
        reply = ask_model(messages)
        messages.append({"role": "assistant", "content": reply})
        kind, value = parse_reply(reply)

        if kind == "summary":
            break

        if steps >= MAX_DISCOVERY_STEPS or bad >= MAX_BAD_REPLIES:
            # Cap reached: one forced request for the summary, then give up.
            messages.append({"role": "user", "content": "Command limit reached. Reply with SUMMARY: now."})
            kind, value = parse_reply(ask_model(messages))
            if kind != "summary":
                value = "Discovery did not produce a summary."
            break

        if kind == "bad":
            bad += 1
            log(f"[bad reply {bad}/{MAX_BAD_REPLIES}] not understood: {reply[:100]!r}")
            feedback = "Reply format not understood. Reply with 'RUN: <command>' or 'SUMMARY:'."
        else:
            steps += 1
            argv, why = check_command(value)
            if argv is None:
                log(f"[{steps}/{MAX_DISCOVERY_STEPS}] REJECTED {value!r}: {why}")
                feedback = f"REJECTED '{value}': {why}. Use only the allowed forms."
            else:
                log(f"[{steps}/{MAX_DISCOVERY_STEPS}] $ {value}")
                out = run_command(argv)
                log("    " + out.strip().replace("\n", "\n    ")[:600])
                feedback = f"Output of '{value}':\n{out}"
        messages.append({"role": "user", "content": feedback})

    with open(SUMMARY_FILE, "w") as f:
        f.write(value + "\n")
    log(f"\n=== System summary ({steps} commands, namespace {NAMESPACE}) ===\n{value}")
    log(f"\nSaved to {SUMMARY_FILE}")
    return value


if __name__ == "__main__":
    discover()
