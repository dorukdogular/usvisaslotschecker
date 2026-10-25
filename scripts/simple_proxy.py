#!/usr/bin/env python3
"""Minimal HTTP/HTTPS forward proxy for local testing (no Docker required).

Usage:
  python scripts/simple_proxy.py --port 8888
"""

from __future__ import annotations

import argparse
import select
import socket
import socketserver
import threading


class ProxyHandler(socketserver.StreamRequestHandler):
    timeout = 30

    def handle(self) -> None:
        try:
            request_line = self.rfile.readline(65537)
        except Exception:
            return
        if not request_line:
            return
        try:
            method, target, version = request_line.decode("latin1").split()
        except ValueError:
            return

        # Drain headers
        headers = []
        content_length = 0
        while True:
            line = self.rfile.readline(65537)
            if line in (b"\r\n", b"\n", b""):
                break
            headers.append(line)
            if line.lower().startswith(b"content-length:"):
                try:
                    content_length = int(line.split(b":", 1)[1].strip())
                except ValueError:
                    content_length = 0

        body = self.rfile.read(content_length) if content_length else b""

        if method.upper() == "CONNECT":
            self._handle_connect(target)
            return

        self._handle_http(method, target, version, headers, body)

    def _handle_connect(self, target: str) -> None:
        host, _, port_s = target.partition(":")
        port = int(port_s or "443")
        try:
            remote = socket.create_connection((host, port), timeout=20)
        except OSError:
            self.wfile.write(b"HTTP/1.1 502 Bad Gateway\r\n\r\n")
            return

        self.wfile.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
        self._tunnel(self.connection, remote)
        remote.close()

    def _handle_http(self, method, target, version, headers, body) -> None:
        # Absolute-form URL expected by proxies: http://host/path
        if not target.startswith("http://"):
            self.wfile.write(b"HTTP/1.1 400 Bad Request\r\n\r\n")
            return
        without_scheme = target[len("http://") :]
        host_port, _, path = without_scheme.partition("/")
        path = "/" + path
        host, _, port_s = host_port.partition(":")
        port = int(port_s or "80")

        try:
            remote = socket.create_connection((host, port), timeout=20)
        except OSError:
            self.wfile.write(b"HTTP/1.1 502 Bad Gateway\r\n\r\n")
            return

        req = f"{method} {path} {version}\r\n".encode("latin1")
        remote.sendall(req)
        for h in headers:
            # Drop hop-by-hop Proxy-Connection
            if h.lower().startswith(b"proxy-connection:"):
                continue
            remote.sendall(h)
        remote.sendall(b"\r\n")
        if body:
            remote.sendall(body)

        while True:
            data = remote.recv(8192)
            if not data:
                break
            self.wfile.write(data)
        remote.close()

    def _tunnel(self, client: socket.socket, remote: socket.socket) -> None:
        sockets = [client, remote]
        while True:
            readable, _, errored = select.select(sockets, [], sockets, 30)
            if errored or not readable:
                break
            for sock in readable:
                other = remote if sock is client else client
                try:
                    data = sock.recv(8192)
                except OSError:
                    return
                if not data:
                    return
                try:
                    other.sendall(data)
                except OSError:
                    return


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main() -> None:
    parser = argparse.ArgumentParser(description="Simple forward proxy")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8888)
    args = parser.parse_args()

    server = ThreadedTCPServer((args.host, args.port), ProxyHandler)
    print(f"Simple proxy listening on {args.host}:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopping proxy", flush=True)
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
