"""Count UDP packets arriving on 10.0.0.2:5001 until 2 s of silence (used by test_lab.sh)."""
import socket

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.bind(("10.0.0.2", 5001))
s.settimeout(2)
n = 0
try:
    while True:
        s.recv(100)
        n += 1
except socket.timeout:
    pass
print(f"UDP received {n} / 50")
