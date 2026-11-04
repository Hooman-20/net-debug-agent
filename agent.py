"""The full agent: discover the system, write a test script, approve it, run it, explain the result.

Usage (inside WSL, with the lab up and MODEL_API_KEY set):
  python agent.py "measure latency and jitter from ns1 to ns2"
  python agent.py --discover "check if DNS works for web.lab"   # re-learn the system first
  python agent.py --yes ...                                       # skip y/n approval (testing only)
"""
import os
import sys

from config import SUMMARY_FILE
from discover import discover
from explain import explain
from tool_builder import build_and_run, load_summary


def run_agent(request, rediscover=False, auto_approve=False, verbose=True):
    """Returns a dict: request, script, output, category, explanation (None fields if not run)."""
    result = {"request": request, "script": None, "output": None, "category": None, "explanation": None}

    print("\n### 1. Discovery")
    if rediscover or not os.path.exists(SUMMARY_FILE):
        summary = discover(verbose=verbose)
    else:
        summary = load_summary()
        print(f"Using saved summary ({SUMMARY_FILE}); pass --discover to refresh.\n{summary}")

    print("\n### 2-4. Generate script, approve, run")
    path, output = build_and_run(request, summary, auto_approve=auto_approve)
    result["script"] = path
    if output is None:
        print("Script was not run, so there is nothing to explain.")
        return result
    result["output"] = output

    print("\n### 5. Explanation")
    category, reply = explain(request, output, summary)
    result["category"], result["explanation"] = category, reply
    print(reply)
    return result


if __name__ == "__main__":
    args = sys.argv[1:]
    flags = {a for a in args if a.startswith("--")}
    unknown = flags - {"--yes", "--discover"}
    if unknown:
        sys.exit(f"Unknown option(s): {' '.join(sorted(unknown))}\n{__doc__}")
    req = " ".join(a for a in args if not a.startswith("--")) or input("What should I measure? ")
    run_agent(req, rediscover="--discover" in flags, auto_approve="--yes" in flags)
