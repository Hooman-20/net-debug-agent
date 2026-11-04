"""Evaluation: inject each lab fault, run the full agent, check whether it named the right cause.

Scripts are AUTO-APPROVED here (testing only). Normal use (agent.py) still asks y/n.
Writes results.md and the full transcript of each run to eval_logs/<fault>.log.

Usage (inside WSL, lab up, MODEL_API_KEY set):
  python run_faults.py                 # all faults
  python run_faults.py loss dns        # just some
"""
import contextlib
import io
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
os.environ.setdefault("AGENT_TOOLS_DIR", os.path.join(HERE, "tools", "eval"))  # keep eval scripts apart

from agent import run_agent  # noqa: E402
from explain import field  # noqa: E402

SPEED = "measure speed and packet loss from ns1 to ns2 with 1000 UDP packets"
CASES = [  # fault, request, expected category
    ("none", SPEED, "healthy"),
    ("loss", SPEED, "packet loss"),
    ("delay", "measure latency and jitter from ns1 to ns2", "high latency"),
    ("firewall", SPEED, "blocked by firewall"),
    ("mtu", "find the largest MTU that works from ns1 to ns2", "MTU problem"),
    ("dns", "check if DNS resolution works for web.lab", "DNS problem"),
]
LOG_DIR = os.path.join(HERE, "eval_logs")
RESULTS = os.path.join(HERE, "results.md")


class Tee(io.TextIOBase):
    def __init__(self, *streams):
        self.streams = streams

    def write(self, s):
        for st in self.streams:
            st.write(s)
            st.flush()
        return len(s)


def set_fault(fault):
    out = subprocess.run(["bash", os.path.join(HERE, "lab", "fault.sh"), "clear" if fault == "none" else fault],
                         capture_output=True, text=True, timeout=30)
    if out.returncode != 0:
        raise RuntimeError(f"fault.sh {fault} failed: {out.stdout}{out.stderr}")


def run_case(fault, request, expected):
    os.makedirs(LOG_DIR, exist_ok=True)
    with open(os.path.join(LOG_DIR, f"{fault}.log"), "w") as log, \
            contextlib.redirect_stdout(Tee(sys.__stdout__, log)):
        print(f"##### FAULT: {fault}   expected: {expected}\n##### REQUEST: {request}")
        set_fault(fault)
        start = time.time()
        try:
            r = run_agent(request, rediscover=True, auto_approve=True)
        except Exception as e:  # one broken case must not stop the others
            print(f"[agent error] {type(e).__name__}: {e}")
            r = {"category": None, "explanation": None, "error": f"{type(e).__name__}: {e}"}
        print(f"\n##### took {time.time() - start:.0f}s")
    if r.get("explanation"):
        said = f"**{r['category']}**: {field(r['explanation'], 'CAUSE')}"
    else:
        said = f"(no explanation: {r.get('error') or 'script did not run'})"
    return {"fault": fault, "request": request, "said": said,
            "correct": r.get("category") == expected, "expected": expected}


def write_results(rows):
    esc = lambda s: s.replace("|", "\\|").replace("\n", " ")
    lines = [
        "# Fault-injection results",
        "",
        f"Model: Meta Muse Spark 1.3 (Meta Model API). Run: {time.strftime('%Y-%m-%d %H:%M')}. "
        f"Score: **{sum(r['correct'] for r in rows)}/{len(rows)}**.",
        "",
        "Each run: `lab/fault.sh <fault>`, then the full agent (discovery, generate script, run, explain) "
        "with scripts auto-approved. *Correct* means the agent's CATEGORY matched the injected fault "
        "(expected category in brackets). Full transcripts: `eval_logs/<fault>.log`.",
        "",
        "| Fault | Request | What the agent said | Correct |",
        "|---|---|---|---|",
    ]
    for r in rows:
        lines.append(f"| {r['fault']} [{r['expected']}] | {esc(r['request'])} | {esc(r['said'])} | "
                     f"{'yes' if r['correct'] else 'no'} |")
    with open(RESULTS, "w") as f:
        f.write("\n".join(lines) + "\n")
    update_readme(lines[2:])


def update_readme(block):
    """Replace the text between the RESULTS markers in README.md with the new table."""
    path = os.path.join(HERE, "README.md")
    start, end = "<!-- RESULTS START -->", "<!-- RESULTS END -->"
    if not os.path.exists(path):
        return
    with open(path) as f:
        text = f.read()
    if start not in text or end not in text:
        return
    head, rest = text.split(start, 1)
    tail = rest.split(end, 1)[1]
    with open(path, "w") as f:
        f.write(f"{head}{start}\n" + "\n".join(block) + f"\n{end}{tail}")


if __name__ == "__main__":
    wanted = sys.argv[1:]
    cases = [c for c in CASES if not wanted or c[0] in wanted]
    if not cases:
        sys.exit(f"Unknown fault(s). Choose from: {' '.join(c[0] for c in CASES)}")
    if not os.environ.get("MODEL_API_KEY"):
        sys.exit("MODEL_API_KEY is not set. Run: export MODEL_API_KEY=...")
    rows = []
    try:
        for case in cases:
            rows.append(run_case(*case))
            write_results(rows)  # keep partial results if a later case hangs
    finally:
        set_fault("none")
    print(f"\nWrote {RESULTS}")
    for r in rows:
        print(f"  {r['fault']:9} {'yes' if r['correct'] else 'NO ':3}  {r['said']}")
