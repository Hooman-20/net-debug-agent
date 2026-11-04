"""Tiny DNS server for the lab: answers A queries for *.lab with 10.0.0.2, NXDOMAIN otherwise."""
import socket
import struct

ANSWER_IP = "10.0.0.2"


def parse_qname(data, off):
    labels = []
    while data[off] != 0:
        n = data[off]
        labels.append(data[off + 1:off + 1 + n].decode())
        off += n + 1
    return ".".join(labels), off + 1


def handle(data):
    tid = data[:2]
    name, off = parse_qname(data, 12)
    qtype, _ = struct.unpack("!HH", data[off:off + 4])
    question = data[12:off + 4]
    if name.lower().endswith(".lab") and qtype == 1:
        header = tid + struct.pack("!HHHHH", 0x8580, 1, 1, 0, 0)
        answer = b"\xc0\x0c" + struct.pack("!HHIH", 1, 1, 60, 4) + socket.inet_aton(ANSWER_IP)
        return header + question + answer
    rcode = 3 if not name.lower().endswith(".lab") else 0  # NXDOMAIN or empty answer
    return tid + struct.pack("!HHHHH", 0x8580 | rcode, 1, 0, 0, 0) + question


sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("10.0.0.2", 53))
print("DNS server on 10.0.0.2:53", flush=True)
while True:
    data, addr = sock.recvfrom(512)
    try:
        sock.sendto(handle(data), addr)
    except Exception as e:
        print("bad query from", addr, e, flush=True)
