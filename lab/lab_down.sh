#!/usr/bin/env bash
# Tear down the test lab.
sudo ip netns pids ns2 2>/dev/null | xargs -r sudo ip netns exec ns2 kill 2>/dev/null
sudo ip netns del ns1 2>/dev/null
sudo ip netns del ns2 2>/dev/null
echo "Lab down"
