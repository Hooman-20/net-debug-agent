"""Step 5: the model reads the test output and explains the most likely cause in plain language."""
import re

from config import LOCAL_IP, NAMESPACE, PEER_IP, PEER_NAMESPACE
from model import ask_model

# A fixed list so answers can be compared across runs. It is deliberately broader than the
# faults the lab can inject, so the list itself does not give the answer away.
CATEGORIES = [
    "healthy", "packet loss", "high latency", "bandwidth limit", "blocked by firewall",
    "MTU problem", "DNS problem", "routing problem", "interface down", "other",
]

SYSTEM_PROMPT = f"""You are a network debugging agent. A test script was run on a Linux system:
{NAMESPACE} ({LOCAL_IP}) is directly connected to {PEER_NAMESPACE} ({PEER_IP}) over a veth pair, so any
loss, delay or size limit on this link comes from configuration, not from distance or congestion.

Read the system summary, the user's request and the test output. Decide whether the network is
healthy or broken and what the single most likely cause is. Base it only on the evidence shown.
Watch for script failures: a crash or timeout of the test itself is not proof of a network fault.

Reply in exactly this format:
CATEGORY: one of {', '.join(CATEGORIES)}
CAUSE: one sentence naming the most likely cause
EVIDENCE: the 1-3 numbers or lines from the output that support it
EXPLANATION: 2-4 sentences in plain language for a non-expert
NEXT STEP: one concrete command or check to confirm or fix it"""


def explain(request, output, summary):
    """Returns (category, full_reply)."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"System summary:\n{summary}\n\nRequest: {request}\n\n"
                                    f"Test output:\n{output[-6000:]}"},
    ]
    reply = ask_model(messages).strip()
    return parse_category(reply), reply


def parse_category(reply):
    m = re.search(r"CATEGORY:\s*([^\n]+)", reply)
    if not m:
        return "unknown"
    got = m.group(1).strip().strip("*").strip().lower()
    for c in CATEGORIES:
        if got.startswith(c.lower()):
            return c
    return got[:40]


def field(reply, name):
    """Pull one field (e.g. CAUSE) out of the reply."""
    m = re.search(rf"{name}:\s*(.*?)(?:\n[A-Z][A-Z ]+:|\Z)", reply, re.S)
    return " ".join(m.group(1).split()) if m else ""
