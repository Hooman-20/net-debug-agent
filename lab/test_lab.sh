#!/usr/bin/env bash
# Verify the lab and every fault. Run after lab_up.sh.
cd "$(dirname "$0")"
N1="sudo ip netns exec ns1"

udp_test() {  # send 50 UDP packets ns1 -> ns2:5001 and count how many arrive
  sudo ip netns exec ns2 python3 udp_count.py &
  sleep 0.5
  $N1 python3 -c 'import socket; s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM); [s.sendto(b"x", ("10.0.0.2", 5001)) for _ in range(50)]'
  wait
}

echo "=== baseline"; ./fault.sh clear
$N1 ping -c 20 -i 0.05 -q 10.0.0.2 | grep -E "loss|rtt"; $N1 dig +short web.lab; udp_test

echo "=== loss (netem loss 20%)"; ./fault.sh loss
$N1 tc qdisc show dev veth1
$N1 ping -c 100 -i 0.02 -q 10.0.0.2 | grep loss

echo "=== delay (netem 200ms)"; ./fault.sh delay
$N1 ping -c 5 -i 0.2 -q 10.0.0.2 | grep rtt

echo "=== firewall (ns2 drops UDP except 53)"; ./fault.sh firewall
$N1 ping -c 3 -i 0.2 -q 10.0.0.2 | grep loss; udp_test

echo "=== mtu (ns2 veth2 mtu 1400)"; ./fault.sh mtu
echo -n "small 1400B: "; $N1 ping -c 2 -W 1 -M do -s 1372 -q 10.0.0.2 | grep loss
echo -n "large 1500B: "; $N1 ping -c 2 -W 1 -M do -s 1472 -q 10.0.0.2 | grep loss

echo "=== dns (wrong nameserver)"; ./fault.sh dns
$N1 cat /etc/resolv.conf; $N1 dig +time=1 +tries=1 web.lab | grep -E "timed out|no servers|status" | head -1

echo "=== clear"; ./fault.sh clear
$N1 ping -c 20 -i 0.05 -q 10.0.0.2 | grep -E "loss|rtt"; $N1 dig +short web.lab; udp_test
