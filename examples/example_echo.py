from typing import Any
from subpar_async.scheduler import sched
import socket

def handle_client(client_sock: socket.socket, addr: Any):
    while True:
        data = yield from sched.sock_recv(client_sock, 1024)
        if data == b"":
            print(f"Client connection closed by {addr}")
            client_sock.close()
            break
        yield from sched.sock_send(client_sock, data)


def echo_server(port: int):
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # IMPORTANT: We disable blocking on the socket so that the run loop doesn't
    # get stuck.
    server_sock.setblocking(False)
    server_sock.bind(("0.0.0.0", port))
    server_sock.listen()
    print(f"Echo server listening on port {port}")

    while True:
        client_sock, addr = yield from sched.sock_accept(server_sock)
        print(f"Accepted connection from {addr}")
        client_sock.setblocking(False) # IMPORTANT: Do not block run loop
        sched.add_task(handle_client(client_sock, addr))

sched.add_task(echo_server(2000))
sched.run()

# How to connect:
#
#  $ nc localhost 2000
#
# Type something and hit return, you should see it echoed back.
# To exit, hit Ctrl-C.
