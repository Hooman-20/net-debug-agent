#!/usr/bin/env bash
# Inject one fault into the lab, or clear all faults.
# Usage: fault.sh loss|delay|firewall|mtu|dns|clear
set -e

clear_all() {
  sudo ip netns exec ns1 tc qdisc del dev veth1 root 2>/dev/null || true
  sudo ip netns exec ns2 tc qdisc del dev veth2 root 2>/dev/null || true
  sudo ip netns exec ns2 iptables -F INPUT 2>/dev/null || true
  sudo ip -n ns1 link set veth1 mtu 1500
  sudo ip -n ns2 link set veth2 mtu 1500
  sudo ip netns exec ns1 sh -c 'echo "nameserver 10.0.0.2" > /etc/netns/ns1/resolv.conf'
}

case "$1" in
  loss)     clear_all; sudo ip netns exec ns1 tc qdisc add dev veth1 root netem loss 20% ;;
  delay)    clear_all; sudo ip netns exec ns1 tc qdisc add dev veth1 root netem delay 200ms 20ms ;;
  firewall) clear_all; sudo ip netns exec ns2 iptables -A INPUT -p udp ! --dport 53 -j DROP ;;
  mtu)      clear_all; sudo ip -n ns2 link set veth2 mtu 1400 ;;
  dns)      clear_all; sudo ip netns exec ns1 sh -c 'echo "nameserver 10.0.0.53" > /etc/netns/ns1/resolv.conf' ;;
  clear)    clear_all ;;
  *) echo "Usage: $0 loss|delay|firewall|mtu|dns|clear"; exit 1 ;;
esac
echo "Fault: $1"
