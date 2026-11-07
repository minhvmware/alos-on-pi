#!/usr/bin/env python3
"""Minimal local HTTP CONNECT proxy that forces IPv4 upstream connections."""

import argparse
import asyncio
import socket


async def pipe(reader, writer):
    try:
        while True:
            data = await reader.read(65536)
            if not data:
                break
            writer.write(data)
            await writer.drain()
    except (ConnectionError, asyncio.CancelledError):
        pass
    finally:
        writer.close()


def connect_ipv4(host, port):
    infos = socket.getaddrinfo(host, port, socket.AF_INET, socket.SOCK_STREAM)
    last = None
    for family, socktype, proto, _, address in infos:
        try:
            sock = socket.socket(family, socktype, proto)
            sock.settimeout(30)
            sock.connect(address)
            sock.setblocking(False)
            return sock
        except OSError as error:
            last = error
    raise last or OSError("no IPv4 address")


async def handle(reader, writer):
    try:
        header = await reader.readline()
        if not header:
            writer.close()
            return
        parts = header.decode("latin1").strip().split()
        if len(parts) >= 2 and parts[0] == "CONNECT":
            host, _, port = parts[1].partition(":")
            port = int(port or "443")
            while True:
                line = await reader.readline()
                if line in (b"\r\n", b"\n", b""):
                    break
            sock = connect_ipv4(host, port)
            upstream_reader, upstream_writer = await asyncio.open_connection(sock=sock)
            writer.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
            await writer.drain()
            await asyncio.gather(pipe(reader, upstream_writer),
                                 pipe(upstream_reader, writer))
        else:
            # Plain HTTP: only forward the first line, then tunnel bytes.
            host = parts[1] if len(parts) > 1 else ""
            path = parts[2] if len(parts) > 2 else "/"
            hostname, _, port = host.partition(":")
            sock = connect_ipv4(hostname, int(port or "80"))
            upstream_reader, upstream_writer = await asyncio.open_connection(sock=sock)
            upstream_writer.write(f"GET {path} HTTP/1.1\r\n".encode())
            while True:
                line = await reader.readline()
                upstream_writer.write(line)
                if line in (b"\r\n", b"\n", b""):
                    break
            await upstream_writer.drain()
            await asyncio.gather(pipe(reader, upstream_writer),
                                 pipe(upstream_reader, writer))
    except Exception as error:  # noqa: BLE001 - proxy must not die on one client
        print(f"proxy error: {error}")
    finally:
        writer.close()


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8899)
    args = parser.parse_args()
    server = await asyncio.start_server(handle, args.host, args.port)
    print(f"proxy listening on {args.host}:{args.port}", flush=True)
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
