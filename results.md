# Fault-injection results

**Not run yet.** This file is overwritten by `python run_faults.py` (see README, "How to run it").

| Fault | Request | What the agent said | Correct |
|---|---|---|---|
| none [healthy] | measure speed and packet loss from ns1 to ns2 with 1000 UDP packets | pending | pending |
| loss [packet loss] | measure speed and packet loss from ns1 to ns2 with 1000 UDP packets | pending | pending |
| delay [high latency] | measure latency and jitter from ns1 to ns2 | pending | pending |
| firewall [blocked by firewall] | measure speed and packet loss from ns1 to ns2 with 1000 UDP packets | pending | pending |
| mtu [MTU problem] | find the largest MTU that works from ns1 to ns2 | pending | pending |
| dns [DNS problem] | check if DNS resolution works for web.lab | pending | pending |
