"""Local development server; the application also works with other WSGI servers."""

from pathlib import Path
from socketserver import ThreadingMixIn
from wsgiref.simple_server import WSGIServer, make_server

from .app import create_app


class ThreadingWSGIServer(ThreadingMixIn, WSGIServer):
    daemon_threads = True


def serve(database_path: Path, *, host: str = "0.0.0.0", port: int = 8000) -> None:
    app = create_app(database_path)
    with make_server(host, port, app, server_class=ThreadingWSGIServer) as server:
        print(f"InfinityDB: http://{host}:{server.server_port}", flush=True)
        print("Press Ctrl+C to stop.", flush=True)
        server.serve_forever()
