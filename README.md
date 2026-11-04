# Network Debugging Agent

When a network "feels slow" or "doesn't work", finding the reason means picking the right test
(ping? a UDP stream? an MTU sweep? a DNS lookup?), adapting it to the machine in front of you,
running it on the right hosts, and reading the numbers correctly. This agent does that from a
plain-language request: it learns the system with read-only commands, writes a small test script
tailored to it, runs the script only after you approve it, and explains the most likely cause in
plain language. It uses **Meta Muse Spark 1.3 through the Meta Model API** (an OpenAI-compatible
endpoint, configured in `config.py`).

## How it works

1. **Discover** (`discover.py`): the model asks for read-only commands one at a time (`ip addr`,
   `ip route`, `cat /etc/resolv.conf`, `which ...`, ...). Each one is checked against a strict
   allowlist before it runs. The model then writes a system summary (OS, interfaces, IPs, routes,
   DNS, installed tools) to `system_summary.txt`.
2. **Generate** (`tool_builder.py`): given the summary and your request, the model writes a Python
   test script and marks it *one-sided* (runs in `ns1` only: latency, MTU, DNS) or *two-sided*
   (receiver in `ns2`, sender in `ns1`: speed, packet loss). Scripts are saved in `tools/` so they
   can be re-run.
3. **Approve and run**: you see the full script and exactly where and how it will run, then answer
   `y/n`. A two-sided test starts the receiver in `ns2` first and the sender in `ns1` one second
   later. If the script crashes, the error goes back to the model for one fix, which needs a
   fresh approval.
4. **Explain** (`explain.py`): the model reads the output and replies with a category, the most
   likely cause, the supporting evidence, a plain-language explanation, and a next step to confirm
   or fix it.

`agent.py` runs all four steps.

## Safety design

- **Allowlist for discovery.** Only exact commands or tight patterns (`ping -c <1-10> <host>`,
  `dig [+short] <name>`, ...) are accepted. Shell metacharacters, extra flags and extra whitespace
  are rejected before anything runs (`allowlist.py`, tested in `test_allowlist.py`).
- **No `shell=True` anywhere.** Every command is an argument list passed to `subprocess`, so model
  text is never interpreted by a shell. Generated scripts are told to follow the same rule.
- **Human approval.** No generated script runs until you have seen it and typed `y`. A missing
  terminal counts as "no". `--yes` exists only for automated testing (`run_faults.py`).
- **Timeouts.** Discovery commands are killed after 15 s. Generated scripts are hard-killed
  (`timeout -s KILL`) after 30 s, with a second Python-side timeout as backup.
- **Namespaces and least privilege.** Everything runs inside the `ns1`/`ns2` network namespaces of
  a throwaway lab, not on the host network. Generated scripts run as your normal user via
  `runuser`, never as root, with `python3 -I` (isolated mode). The agent uses only `sudo -n`
  (never prompts), and passwordless sudo is limited to `ip`, `tc` and `iptables`.
- **No secrets in the repo.** The API key is read only from the `MODEL_API_KEY` environment
  variable.

## How to run it

Requirements: Linux or WSL2, Python 3, `iproute2`, `iptables`, `dig`, and passwordless sudo for
`ip`, `tc` and `iptables`.

```bash
python3 -m venv .venv && .venv/bin/pip install openai
export MODEL_API_KEY=...            # Meta Model API key, never committed

lab/lab_up.sh                       # ns1 10.0.0.1 <-veth-> ns2 10.0.0.2, DNS server in ns2
lab/test_lab.sh                     # optional: check the lab and every fault
.venv/bin/python test_api.py        # optional: check the API

.venv/bin/python agent.py --discover "measure speed and packet loss from ns1 to ns2 with 1000 UDP packets"
.venv/bin/python agent.py "find the largest MTU that works from ns1 to ns2"
.venv/bin/python tool_builder.py --run tools/latency_jitter.py   # re-run a saved script

lab/fault.sh loss                   # inject a fault: loss|delay|firewall|mtu|dns|clear
.venv/bin/python run_faults.py      # full evaluation, writes results.md and eval_logs/
lab/lab_down.sh
```

## Results

Each fault is injected with `lab/fault.sh`, then the full agent runs (fresh discovery, new
script, auto-approved run, explanation). Full transcripts are in `eval_logs/`.

<!-- RESULTS START -->
Model: Meta Muse Spark 1.3 (Meta Model API). Run: 2026-11-04 15:49. Score: **5/6**.

Each run: `lab/fault.sh <fault>`, then the full agent (discovery, generate script, run, explain) with scripts auto-approved. *Correct* means the agent's CATEGORY matched the injected fault (expected category in brackets). Full transcripts: `eval_logs/<fault>.log`.

| Fault | Request | What the agent said | Correct |
|---|---|---|---|
| none [healthy] | measure speed and packet loss from ns1 to ns2 with 1000 UDP packets | **healthy**: No fault was found because the link delivered all test traffic at the expected rate. | yes |
| loss [packet loss] | measure speed and packet loss from ns1 to ns2 with 1000 UDP packets | **packet loss**: Random drops configured on the direct veth link, likely a tc netem loss rule, are discarding about 19% of packets. | yes |
| delay [high latency] | measure latency and jitter from ns1 to ns2 | **high latency**: An artificial delay of about 200 ms is configured on the directly connected veth link between ns1 and ns2. | yes |
| firewall [blocked by firewall] | measure speed and packet loss from ns1 to ns2 with 1000 UDP packets | **blocked by firewall**: A firewall in ns2 is dropping all UDP packets to port 5001 before they reach the receiver application. | yes |
| mtu [MTU problem] | find the largest MTU that works from ns1 to ns2 | (no explanation: ValueError: model reply missing TYPE or code block) | no |
| dns [DNS problem] | check if DNS resolution works for web.lab | **DNS problem**: The configured DNS server at 10.0.0.53 is unreachable and does not answer queries for web.lab. | yes |
<!-- RESULTS END -->

The injected faults: `loss` = netem 20 % loss on veth1; `delay` = netem 200 ms ± 20 ms;
`firewall` = ns2 drops all UDP except port 53 (ping still works); `mtu` = ns2's veth2 set to
1400 while ns1 stays at 1500; `dns` = ns1's resolver pointed at a dead address (10.0.0.53).
