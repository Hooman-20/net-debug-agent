"""Evaluation: inject each lab fault, run the full agent, check whether it named the right cause.

Scripts are AUTO-APPROVED here (testing only). Normal use (agent.py) still asks y/n.
Writes results.md and the full transcript of each run to eval_logs/<fault>.log.

Usage (inside WSL, lab up, MODEL_API_KEY set):
  python run_faults.py                 # all faults
  python run_faults.py mtu            # just one (or several); only those rows are updated
"""
import contextlib
import io
import os
import re
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


HEADER = [
    "# Fault-injection results",
    "",
    "Model: Meta Muse Spark 1.3 (Meta Model API). Run: (time). Score: **0/0**.",
    "",
    "Each run: `lab/fault.sh <fault>`, then the full agent (discovery, generate script, run, explain) "
    "with scripts auto-approved. *Correct* means the agent's CATEGORY matched the injected fault "
    "(expected category in brackets). Full transcripts: `eval_logs/<fault>.log`.",
    "",
    "| Fault | Request | What the agent said | Correct |",
    "|---|---|---|---|",
]
ROW = re.compile(r"^\| (\w+) \[")


def row_line(r):
    esc = lambda s: s.replace("|", "\\|").replace("\n", " ")
    return (f"| {r['fault']} [{r['expected']}] | {esc(r['request'])} | {esc(r['said'])} | "
            f"{'yes' if r['correct'] else 'no'} |")


def merge_rows(lines, rows):
    """Replace the table rows for the faults in `rows`; leave every other row as it is.
    Then recompute the score and timestamp from the whole table."""
    new = {r["fault"]: row_line(r) for r in rows}
    out, seen, last_row = [], set(), None
    for line in lines:
        m = ROW.match(line)
        if m and m.group(1) in new:
            line = new[m.group(1)]
            seen.add(m.group(1))
        out.append(line)
        if line.startswith("|"):
            last_row = len(out)
    missing = [new[f] for f, _, _ in CASES if f in new and f not in seen]
    if missing:
        at = last_row if last_row is not None else len(out)
        out[at:at] = missing
    table = [l for l in out if ROW.match(l)]
    done = [l for l in table if l.rstrip().endswith(("| yes |", "| no |"))]
    score = f"Score: **{sum(l.rstrip().endswith('| yes |') for l in done)}/{len(done)}**"
    when = time.strftime("%Y-%m-%d %H:%M")
    if len(rows) < len(CASES):
        when += f" (updated: {', '.join(r['fault'] for r in rows)})"
    for i, l in enumerate(out):
        if "Score:" in l:
            l = re.sub(r"Score: \*\*\d+/\d+\*\*", score, l)
            l = re.sub(r"(Run|Last updated): .*?\. ", f"Last updated: {when}. ", l, count=1)
            l = l.replace("**Not run yet.** ", "")
            out[i] = l
    return out


def write_results(rows):
    """Update only the rows for the faults in `rows`, in results.md and the README table."""
    lines = HEADER
    if os.path.exists(RESULTS):
        with open(RESULTS) as f:
            lines = f.read().splitlines()
        if not any("Score:" in l for l in lines):  # old placeholder file: start from the template
            lines = HEADER + [l for l in lines if ROW.match(l)]
    lines = merge_rows(lines, rows)
    with open(RESULTS, "w") as f:
        f.write("\n".join(lines) + "\n")
    update_readme(rows)


def update_readme(rows):
    """Update only those rows in the table between the RESULTS markers in README.md."""
    path = os.path.join(HERE, "README.md")
    start, end = "<!-- RESULTS START -->", "<!-- RESULTS END -->"
    if not os.path.exists(path):
        return
    with open(path) as f:
        text = f.read()
    if start not in text or end not in text:
        return
    head, rest = text.split(start, 1)
    block, tail = rest.split(end, 1)
    block = block.strip("\n").splitlines()
    if not any("Score:" in l for l in block):
        block = HEADER[2:] + [l for l in block if ROW.match(l)]
    block = merge_rows(block, rows)
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
