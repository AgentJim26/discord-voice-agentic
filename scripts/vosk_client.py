#!/usr/bin/env python3
import json
import socket
import sys

sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
sock.settimeout(30)
sock.connect(sys.argv[1])
sock.sendall((json.dumps({"path": sys.argv[2]}) + "\n").encode("utf-8"))
data = b""
while not data.endswith(b"\n"):
    chunk = sock.recv(65536)
    if not chunk:
        break
    data += chunk
sock.close()
result = json.loads(data.decode("utf-8"))
if "error" in result:
    raise SystemExit(result["error"])
print(result.get("text", ""))
