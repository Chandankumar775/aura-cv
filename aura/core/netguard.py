"""In-process outbound-network guard (R-CON-1, A3 rule 1).

AURA-CV has no code path that needs the network, but third-party libraries sometimes
try (weight auto-downloads, telemetry, update checks). ``install()`` patches the socket
layer so any connection or DNS lookup to a non-loopback destination raises
``OutboundNetworkBlocked`` *before* a packet is sent. The CLI and API server install it
at start-up; ``aura selfcheck`` confirms it is active.

This is defence in depth, not the air gap itself: the air gap is the host having no
network route, which ``route_exists()`` probes without sending any packet.
"""

from __future__ import annotations

import ipaddress
import socket
import threading
from typing import Any

PROBE_ADDRESS = ("192.0.2.1", 9)  # TEST-NET-1 (RFC 5737): reserved, never routed publicly
_LOCAL_NAMES = {"localhost", "localhost.localdomain", "ip6-localhost", ""}

_lock = threading.Lock()
_installed = False
_orig: dict[str, Any] = {}


class OutboundNetworkBlocked(ConnectionRefusedError):
    """Raised instead of opening a non-loopback connection."""


def is_local_host(host: Any) -> bool:
    if host is None:
        return True
    if isinstance(host, bytes):
        host = host.decode("ascii", "ignore")
    host = str(host).strip("[]").split("%")[0].lower()
    if host in _LOCAL_NAMES:
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _address_host(address: Any) -> Any:
    # AF_INET/AF_INET6 addresses are tuples; AF_UNIX addresses are paths (always local).
    if isinstance(address, tuple) and address:
        return address[0]
    return "localhost"


def _check(address: Any) -> None:
    host = _address_host(address)
    if not is_local_host(host):
        raise OutboundNetworkBlocked(f"AURA-CV is offline-only: outbound connection to {host!r} blocked")


def _guarded_connect(self: socket.socket, address: Any) -> Any:
    _check(address)
    return _orig["connect"](self, address)


def _guarded_connect_ex(self: socket.socket, address: Any) -> Any:
    _check(address)
    return _orig["connect_ex"](self, address)


def _guarded_sendto(self: socket.socket, data: Any, *args: Any) -> Any:
    _check(args[-1])
    return _orig["sendto"](self, data, *args)


def _guarded_getaddrinfo(host: Any, *args: Any, **kwargs: Any) -> Any:
    if not is_local_host(host):
        raise OutboundNetworkBlocked(f"AURA-CV is offline-only: DNS lookup of {host!r} blocked")
    return _orig["getaddrinfo"](host, *args, **kwargs)


def install() -> None:
    """Idempotently install the guard for the whole process."""
    global _installed
    with _lock:
        if _installed:
            return
        _orig.update(
            connect=socket.socket.connect,
            connect_ex=socket.socket.connect_ex,
            sendto=socket.socket.sendto,
            getaddrinfo=socket.getaddrinfo,
        )
        socket.socket.connect = _guarded_connect  # type: ignore[method-assign]
        socket.socket.connect_ex = _guarded_connect_ex  # type: ignore[method-assign]
        socket.socket.sendto = _guarded_sendto  # type: ignore[method-assign]
        socket.getaddrinfo = _guarded_getaddrinfo  # type: ignore[assignment]
        _installed = True


def is_installed() -> bool:
    return _installed


def guard_blocks_outbound() -> bool:
    """True if a connection attempt to a non-local address is refused by the guard."""
    try:
        _check(PROBE_ADDRESS)
    except OutboundNetworkBlocked:
        return _installed and socket.socket.connect is _guarded_connect
    return False


def route_exists() -> tuple[bool, str]:
    """Does the host have a route to a non-local address? Sends no packets.

    ``connect()`` on a UDP socket only asks the OS routing table for a route and
    records the peer; no datagram is transmitted. The unpatched connect is used so
    the guard does not mask the answer.
    """
    connect = _orig.get("connect", socket.socket.connect)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        connect(sock, PROBE_ADDRESS)
        local_ip = sock.getsockname()[0]
    except OSError as exc:
        return False, f"no route to non-local addresses ({exc.__class__.__name__})"
    finally:
        sock.close()
    if is_local_host(local_ip) or local_ip == "0.0.0.0":
        return False, "only loopback routes present"
    return True, f"host has a route to non-local addresses via {local_ip}"
