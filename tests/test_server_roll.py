"""In-process smoke test for examples/server_roll HTTP API."""

from __future__ import annotations

import json
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "examples"))


def _post(url: str, payload: dict) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _get(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=5) as resp:
        return json.loads(resp.read().decode("utf-8"))


@pytest.fixture(scope="module")
def server_url():
    import server_roll

    # Bind ephemeral port
    from http.server import ThreadingHTTPServer

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server_roll.Handler)
    port = httpd.server_address[1]
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    base = f"http://127.0.0.1:{port}"
    # wait ready
    for _ in range(50):
        try:
            _get(base + "/healthz")
            break
        except Exception:
            time.sleep(0.05)
    yield base
    httpd.shutdown()


def test_server_healthz(server_url):
    body = _get(server_url + "/healthz")
    assert body["ok"] is True
    assert "algo_version" in body


def test_server_commit_roll_verify(server_url):
    seed = 2.4
    commit_body = _post(
        server_url + "/v1/commit",
        {"seed": seed, "game_id": "demo", "season": "s1"},
    )
    assert len(commit_body["commit"]) == 64

    roll_body = _post(
        server_url + "/v1/roll",
        {
            "seed": seed,
            "context": "loot.chest",
            "n": 0,
            "game_id": "demo",
            "season": "s1",
        },
    )
    assert "result" in roll_body
    assert roll_body["commit"] == commit_body["commit"]

    verify_body = _post(
        server_url + "/v1/verify",
        {
            "seed": seed,
            "game_id": "demo",
            "season": "s1",
            "receipt": roll_body,
        },
    )
    assert verify_body["ok"] is True

    bad = _post(
        server_url + "/v1/verify",
        {
            "seed": 9.9,
            "game_id": "demo",
            "season": "s1",
            "receipt": roll_body,
        },
    )
    assert bad["ok"] is False
