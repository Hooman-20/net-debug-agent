#!/usr/bin/env bash
# Build the test lab: ns1 (10.0.0.1) <--veth--> ns2 (10.0.0.2), plus a tiny DNS server in ns2.
set -e
cd "$(dirname "$0")"

./lab_down.sh >/dev/null 2>&1 || true

sudo ip netns add ns1
sudo ip netns add ns2
sudo ip link add veth1 type veth peer name veth2
sudo ip link set veth1 netns ns1
sudo ip link set veth2 netns ns2

sudo ip -n ns1 addr add 10.0.0.1/24 dev veth1
sudo ip -n ns2 addr add 10.0.0.2/24 dev veth2
for ns in ns1 ns2; do
  sudo ip -n $ns link set lo up
done
sudo ip -n ns1 link set veth1 up
sudo ip -n ns2 link set veth2 up

# Per-namespace resolv.conf: ip netns exec bind-mounts /etc/netns/<ns>/resolv.conf over /etc/resolv.conf.
# Written via "ip netns exec" because sudo is only allowed for ip/tc/iptables.
sudo ip netns exec ns1 sh -c 'mkdir -p /etc/netns/ns1 && echo "nameserver 10.0.0.2" > /etc/netns/ns1/resolv.conf'

# DNS server in ns2 (answers *.lab -> 10.0.0.2)
sudo ip netns exec ns2 sh -c "nohup python3 '$PWD/dns_server.py' > /tmp/lab_dns.log 2>&1 &"
sleep 0.5

echo "Lab up: ns1=10.0.0.1 (veth1), ns2=10.0.0.2 (veth2), DNS on 10.0.0.2:53"
