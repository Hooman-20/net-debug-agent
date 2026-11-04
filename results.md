# Fault-injection results

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
