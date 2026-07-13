#!/usr/bin/env python3
"""
Minimal roll middleware: commit seed, roll with receipt, verify.

  python examples/server_roll.py
  curl -s localhost:8765/healthz
  curl -s -X POST localhost:8765/v1/commit -H 'content-type: application/json' \\
    -d '{"seed":2.4,"game_id":"demo","season":"s1"}'
  curl -s -X POST localhost:8765/v1/roll -H 'content-type: application/json' \\
    -d '{"seed":2.4,"context":"loot.chest","n":0,"game_id":"demo","season":"s1"}'
"""

from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from rrann import (  # noqa: E402
    ALGO_VERSION,
    commit_seed,
    create_receipt,
    health_check,
    verify_receipt,
)

HOST = "127.0.0.1"
PORT = 8765


def _json_body(handler: BaseHTTPRequestHandler) -> dict[str, Any]:
    length = int(handler.headers.get("Content-Length") or 0)
    raw = handler.rfile.read(length) if length else b"{}"
    if not raw:
        return {}
    return json.loads(raw.decode("utf-8"))


def _send(handler: BaseHTTPRequestHandler, code: int, payload: dict[str, Any]) -> None:
    data = json.dumps(payload).encode("utf-8")
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(data)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.end_headers()
    handler.wfile.write(data)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path in ("/healthz", "/"):
            _send(
                self,
                200,
                {
                    "ok": True,
                    "service": "rrann-roll",
                    "algo_version": ALGO_VERSION,
                },
            )
            return
        if path == "/v1/health":
            # optional query ignored; fixed seed diagnostic
            h = health_check(2.4, n_bits=2048, profile="gameplay")
            _send(self, 200, h.to_dict())
            return
        _send(self, 404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        try:
            body = _json_body(self)
        except json.JSONDecodeError:
            _send(self, 400, {"error": "invalid json"})
            return

        if path == "/v1/commit":
            seed = float(body.get("seed", 0))
            game_id = str(body.get("game_id", ""))
            season = str(body.get("season", ""))
            commit = commit_seed(seed, game_id=game_id, season=season)
            _send(
                self,
                200,
                {
                    "commit": commit,
                    "game_id": game_id,
                    "season": season,
                    "algo_version": ALGO_VERSION,
                    "note": "Publish commit before rolling; keep seed secret until reveal",
                },
            )
            return

        if path == "/v1/roll":
            seed = float(body["seed"])
            context = str(body.get("context", "loot"))
            n = int(body.get("n", 0))
            kind = str(body.get("kind", "float"))
            bits = int(body.get("bits", 32))
            game_id = str(body.get("game_id", ""))
            season = str(body.get("season", ""))
            receipt = create_receipt(
                seed,
                context,
                n,
                kind=kind,
                bits=bits,
                game_id=game_id,
                season=season,
            )
            _send(self, 200, receipt.to_dict())
            return

        if path == "/v1/verify":
            seed = float(body["seed"])
            game_id = str(body.get("game_id", ""))
            season = str(body.get("season", ""))
            receipt = body.get("receipt") or body
            ok = verify_receipt(receipt, seed, game_id=game_id, season=season)
            _send(self, 200, {"ok": ok})
            return

        _send(self, 404, {"error": "not found"})


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"rrann roll server on http://{HOST}:{PORT}", flush=True)
    print("  GET  /healthz", flush=True)
    print("  POST /v1/commit  /v1/roll  /v1/verify", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nbye", flush=True)


if __name__ == "__main__":
    main()
