"""Unit tests for rrann — drive real public API only."""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import rrann
from rrann import (
    DEFAULT_CULL_HEAD,
    Generator,
    Rng,
    commit_seed,
    create_receipt,
    extract_bits,
    extract_float,
    generate,
    harvest,
    health_check,
    roll,
    verify_commit,
    verify_receipt,
)


def test_version():
    assert rrann.__version__
    assert rrann.ALGO_VERSION.startswith("rrann-")


def test_default_cull_head_is_two():
    assert DEFAULT_CULL_HEAD == 2
    assert rrann.DEFAULT_DROP == DEFAULT_CULL_HEAD


def test_harvest_deterministic():
    a = harvest(2.4)
    b = harvest(2.4)
    assert a.digits == b.digits
    assert a.divergence_index == b.divergence_index
    assert len(a.digits) >= 10


def test_harvest_divergence_near_double_precision():
    h = harvest(2.4)
    if not h.used_fallback and h.divergence_index is not None:
        assert 10 <= h.divergence_index <= 20


def test_remainder_cull_head():
    h = harvest(2.4)
    assert h.remainder(cull_head=2) == h.digits[2:]
    assert h.remainder(drop=2) == h.digits[2:]
    assert h.head == h.digits[:2]


def test_legacy_generate_range_and_deterministic():
    x = generate(2.4)
    assert 0.0 <= x < 1.0
    assert generate(2.4) == x


def test_extract_float_cull_head_and_drop_alias():
    a = extract_float(2.4, cull_head=2)
    b = extract_float(2.4, drop=2)
    assert a == b
    assert 0.0 <= a < 1.0


def test_extract_bits_length():
    bits = extract_bits(2.4, 64, cull_head=2)
    assert len(bits) == 64
    assert all(b in (0, 1) for b in bits)


def test_cull_head_drop_conflict():
    with pytest.raises(ValueError):
        extract_float(2.4, cull_head=2, drop=3)


def test_generator_random_sequence():
    g = Generator(seed=2.4, cull_head=2, mode="remainder")
    xs = [g.random() for _ in range(20)]
    assert all(0.0 <= x < 1.0 for x in xs)
    assert len(set(xs)) > 5


def test_generator_randbits_and_next_u64():
    g = Generator(seed=2.4)
    v = g.randbits(32)
    assert 0 <= v < 2**32
    u = Rng(seed=2.4).next_u64()
    assert 0 <= u < 2**64


def test_generator_legacy_mode_opt_in():
    g = Generator(seed=2.4, mode="legacy")
    x = g.random()
    assert 0.0 <= x < 1.0


def test_fork_independent_streams():
    g = Rng(seed=2.4)
    a = g.fork(0)
    b = g.fork(1)
    # Same fork id → same first values
    a2 = g.fork(0)
    assert a.random() == a2.random()
    # Different streams diverge
    a3 = g.fork(0)
    b3 = g.fork(1)
    seq_a = [a3.random() for _ in range(5)]
    seq_b = [b3.random() for _ in range(5)]
    assert seq_a != seq_b


def test_roll_deterministic_context_counter():
    r1 = roll(2.4, "loot.chest", 0)
    r2 = roll(2.4, "loot.chest", 0)
    r3 = roll(2.4, "loot.chest", 1)
    r4 = roll(2.4, "loot.other", 0)
    assert r1 == r2
    assert r1 != r3
    assert r1 != r4
    assert 0.0 <= r1 < 1.0


def test_roll_int_bits():
    v = roll(2.4, "damage", 3, kind="int", bits=16)
    assert isinstance(v, int)
    assert 0 <= v < 2**16
    assert v == roll(2.4, "damage", 3, kind="int", bits=16)


def test_commit_seed_roundtrip():
    seed = 2.4
    c = commit_seed(seed, game_id="demo", season="s1")
    assert len(c) == 64
    assert verify_commit(c, seed, game_id="demo", season="s1")
    assert not verify_commit(c, seed, game_id="other", season="s1")
    assert not verify_commit(c, 9.9, game_id="demo", season="s1")


def test_receipt_create_verify_success_and_failure():
    seed = 2.4
    receipt = create_receipt(seed, "loot.chest", 0, game_id="g1", season="s1")
    assert receipt.algo_version == rrann.ALGO_VERSION
    assert verify_receipt(receipt, seed, game_id="g1", season="s1")
    # wrong seed
    assert not verify_receipt(receipt, 3.1, game_id="g1", season="s1")
    # wrong game_id breaks commit
    assert not verify_receipt(receipt, seed, game_id="nope", season="s1")
    # dict path
    assert verify_receipt(receipt.to_dict(), seed, game_id="g1", season="s1")


def test_health_check_shape_and_status():
    h = health_check(2.4, n_bits=4096, profile="gameplay")
    assert h.status in ("pass", "warn", "fail")
    assert h.profile == "gameplay"
    assert isinstance(h.ok, bool)
    assert h.n_bits == 4096
    assert 0.0 <= h.p1 <= 1.0
    assert isinstance(h.monobit_z, float)
    assert isinstance(h.runs_z, float)
    d = h.to_dict()
    assert "status" in d and "messages" in d


def test_health_profiles_exist():
    for profile in ("cosmetic", "gameplay", "economy"):
        h = health_check(2.4, n_bits=2048, profile=profile)
        assert h.profile == profile
        assert h.status in ("pass", "warn", "fail")


def test_random_bits_bytes():
    b = rrann.random_bits(128, seed=2.4)
    assert isinstance(b, (bytes, bytearray))
    assert len(b) == 16


def test_von_neumann_shorter():
    bits = extract_bits(2.4, 256, cull_head=2)
    vn = rrann.von_neumann(bits)
    assert len(vn) <= len(bits) // 2
    assert all(b in (0, 1) for b in vn)


def test_compat_module():
    import RRann as old

    assert math.isclose(old.generate(2.4), generate(2.4))
    assert hasattr(old, "health_check")
    assert hasattr(old, "create_receipt")


def test_continuous_health_ingest_and_check():
    from rrann import ContinuousHealth, extract_bits

    mon = ContinuousHealth(window_bits=2048, profile="gameplay")
    bits = extract_bits(2.4, 4096, cull_head=2)
    mon.ingest(bits)
    assert mon.ready()
    assert mon.total_ingested >= 4096
    r = mon.check()
    assert r.status in ("pass", "warn", "fail")
    assert r.n_bits == 2048  # window capped


def test_simulate_loot_rates_near_table():
    from rrann import simulate_loot, expected_value

    weights = [("common", 70), ("uncommon", 20), ("rare", 8), ("legendary", 2)]
    report = simulate_loot(2.4, weights, trials=5000, cumulative=False)
    assert report.trials == 5000
    assert abs(sum(report.rates.values()) - 1.0) < 1e-9
    # crude: max error should be small-ish at 5k trials
    assert report.max_abs_error < 0.05
    ev = expected_value(report.expected_rates, {"common": 1, "uncommon": 5, "rare": 20, "legendary": 100})
    assert ev > 1.0


def test_vectors_json_matches_reference():
    import json
    from pathlib import Path

    data = json.loads(Path("tests/vectors.json").read_text())
    assert data["cull_head"] == 2
    assert len(data["cases"]) >= 20
    for case in data["cases"]:
        seed = case["seed"]
        h = harvest(seed)
        assert h.digits == case["digits"]
        assert h.used_fallback == case["used_fallback"]
        assert h.divergence_index == case["divergence_index"]
        assert extract_float(seed, cull_head=2) == case["extract_float_cull2"]
        assert extract_bits(seed, 32, cull_head=2) == case["extract_bits32_cull2"]
        assert float(roll(seed, "loot", 0)) == case["roll_loot_0"]


def test_cli_verify_and_health(tmp_path):
    import json
    import subprocess
    import sys

    seed = 2.4
    receipt = create_receipt(seed, "cli.loot", 0, game_id="g")
    path = tmp_path / "r.json"
    path.write_text(receipt.to_json())
    proc = subprocess.run(
        [sys.executable, "-m", "rrann", "verify", str(path), "--seed", str(seed), "--game-id", "g"],
        cwd=str(Path(__file__).resolve().parents[1]),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert json.loads(proc.stdout)["ok"] is True
    proc2 = subprocess.run(
        [sys.executable, "-m", "rrann", "health", "--seed", "2.4", "--bits", "1024"],
        cwd=str(Path(__file__).resolve().parents[1]),
        capture_output=True,
        text=True,
    )
    assert proc2.returncode in (0, 1, 2)
    assert "status" in json.loads(proc2.stdout)

