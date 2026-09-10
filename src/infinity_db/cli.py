"""Application commands built on the existing data ingestion tools."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

from infinity_army_data.cli import add_data_commands
from infinity_army_data.cli import cmd_build as build_dataset

from . import __version__
from .database import export_database

DEFAULT_DATABASE = Path("data/generated/infinity.db")


def _export(source: Path, destination: Path) -> None:
    with source.open(encoding="utf-8") as handle:
        normalized = json.load(handle)
    export_database(normalized, destination)
    print(f"Database ready: {destination}")


def cmd_build(args: argparse.Namespace) -> int:
    build_dataset(args)
    _export(args.output_dir / "normalized.json", args.output_dir / "infinity.db")
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    _export(args.input, args.output)
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    from .web.server import serve

    serve(args.database, host=args.host, port=args.port)
    return 0


def _port(value: str) -> int:
    port = int(value)
    if not 1 <= port <= 65535:
        raise argparse.ArgumentTypeError("port must be between 1 and 65535")
    return port


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="infinity-db",
        description="Build the Infinity database and browse units on the web",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    add_data_commands(sub, build_handler=cmd_build)

    p_export = sub.add_parser("export", help="Import validated normalized JSON into SQLite")
    p_export.add_argument("input", type=Path, help="normalized.json input")
    p_export.add_argument("output", nargs="?", type=Path, default=DEFAULT_DATABASE)
    p_export.set_defaults(func=cmd_export)

    p_serve = sub.add_parser("serve", help="Start the local unit browser and read-only API")
    p_serve.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", type=_port, default=8000)
    p_serve.set_defaults(func=cmd_serve)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\nServer stopped.")
        return 0
    except (OSError, ValueError, KeyError, TypeError, sqlite3.Error) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
