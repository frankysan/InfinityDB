"""Local development server; the application also works with other WSGI servers."""

import errno
from pathlib import Path
from socket import AF_INET, SOCK_STREAM, socket
from socketserver import ThreadingMixIn
from wsgiref.simple_server import WSGIServer, make_server

from .app import create_app


class ThreadingWSGIServer(ThreadingMixIn, WSGIServer):
    daemon_threads = True


def _ensure_port_is_available(host: str, port: int) -> None:
    """Fail early with an actionable error when the requested binding is occupied."""

    with socket(AF_INET, SOCK_STREAM) as probe:
        try:
            probe.bind((host, port))
        except OSError as exc:
            if exc.errno == errno.EADDRINUSE:
                raise OSError(
                    f"Port {port} is already in use on {host}. "
                    "Stop the other server or choose another port with --port."
                ) from exc
            raise


def serve(database_path: Path, *, host: str = "0.0.0.0", port: int = 8000) -> None:
    _ensure_port_is_available(host, port)
    app = create_app(database_path)
    with make_server(host, port, app, server_class=ThreadingWSGIServer) as server:
        print(f"InfinityDB: http://{host}:{server.server_port}", flush=True)
        print("Press Ctrl+C to stop.", flush=True)
        server.serve_forever()
