import socket
import time

# Checks if a TCP connection can be established between client-server
# This process is called Three-Way Handshake for TCP connections
def check_tcp(host, port, timeout=3.0):
    if not port:
        return {"status": "OFFLINE", "response_time": None}

    try:
        start_time = time.perf_counter()
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as cs:
            cs.settimeout(timeout)
            cs.connect((host, port))
            latency = (time.perf_counter() - start_time) * 1000
            return {"status": "ONLINE", "response_time": round(latency, 2)}
    except (socket.timeout, socket.error, OSError):
        return {"status": "OFFLINE", "response_time": None}

if __name__ == "__main__":
    print("Testing Google HTTP:")
    print(check_tcp("142.250.190.238", 80))