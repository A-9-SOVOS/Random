#!/usr/bin/env python3
"""Compare Python reference residual extract vs Rust native harvest."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from rrann import extract_bits, extract_float, harvest  # noqa: E402


def rust_cases() -> list[dict]:
    env = os.environ.copy()
    env["PATH"] = str(Path.home() / ".cargo" / "bin") + ":" + env.get("PATH", "")
    # Prefer system /tmp gmp headers when present (local dev without apt packages)
    for key, val in (
        ("CPATH", "/tmp/gmpdev/usr/include:/tmp/mpfrdev/usr/include"),
        ("LIBRARY_PATH", "/tmp/gmpdev/usr/lib/aarch64-linux-gnu:/tmp/mpfrdev/usr/lib/aarch64-linux-gnu"),
        ("PKG_CONFIG_PATH", "/tmp/gmpdev/usr/lib/aarch64-linux-gnu/pkgconfig:/tmp/mpfrdev/usr/lib/aarch64-linux-gnu/pkgconfig"),
    ):
        if Path(val.split(":")[0]).exists() or Path("/tmp/gmpdev").exists():
            env[key] = val + (":" + env[key] if env.get(key) else "")
    proc = subprocess.run(
        ["cargo", "run", "--quiet", "--release", "--example", "parity_print"],
        cwd=str(ROOT / "rust" / "rrann-core"),
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )
    raw = proc.stdout.strip()
    for line in reversed(raw.splitlines()):
        line = line.strip()
        if line.startswith("["):
            return json.loads(line)
    return json.loads(raw)


def load_vector_seeds() -> list[float]:
    path = ROOT / "tests" / "vectors.json"
    data = json.loads(path.read_text())
    return [float(c["seed"]) for c in data["cases"]]


def main() -> None:
    rust_list = rust_cases()
    rust_map = {float(c["seed"]): c for c in rust_list}
    seeds = load_vector_seeds()
    report = {
        "note": (
            "Native Rust harvest uses MPFR (rug). Expected exact match vs Python "
            "Decimal residual on all vectors.json seeds (including SHA fallbacks)."
        ),
        "cases": [],
        "summary": {"n": 0, "digits_equal": 0, "div_equal": 0, "float_exact": 0},
    }
    for seed in seeds:
        h = harvest(seed)
        py = {
            "divergence_index": h.divergence_index,
            "digits": h.digits,
            "used_fallback": h.used_fallback,
            "extract_float_cull2": extract_float(seed, cull_head=2),
            "extract_bits32_cull2": extract_bits(seed, 32, cull_head=2),
        }
        rs = rust_map.get(seed)
        if rs is None:
            # f64 key noise: find nearest
            rs = min(rust_map.items(), key=lambda kv: abs(kv[0] - seed))[1]
        case = {
            "seed": seed,
            "python": py,
            "rust": {
                k: rs[k]
                for k in (
                    "divergence_index",
                    "digits",
                    "used_fallback",
                    "extract_float_cull2",
                    "extract_bits32_cull2",
                )
            },
            "digits_equal": py["digits"] == rs["digits"],
            "div_index_equal": py["divergence_index"] == rs["divergence_index"],
            "float_abs_delta": abs(py["extract_float_cull2"] - rs["extract_float_cull2"]),
            "fallback_equal": py["used_fallback"] == rs["used_fallback"],
        }
        report["cases"].append(case)
        report["summary"]["n"] += 1
        report["summary"]["digits_equal"] += int(case["digits_equal"])
        report["summary"]["div_equal"] += int(case["div_index_equal"])
        report["summary"]["float_exact"] += int(case["float_abs_delta"] < 1e-15)
        status = "OK" if case["digits_equal"] and case["div_index_equal"] else "MISMATCH"
        print(
            f"[{status}] seed={seed} dig_eq={case['digits_equal']} "
            f"div_eq={case['div_index_equal']} fb_eq={case['fallback_equal']} "
            f"Δfloat={case['float_abs_delta']:.6g}"
        )

    out = ROOT / "tests" / "parity_report.json"
    out.write_text(json.dumps(report, indent=2) + "\n")
    s = report["summary"]
    print(
        f"wrote {out} — {s['digits_equal']}/{s['n']} digits, "
        f"{s['div_equal']}/{s['n']} div, {s['float_exact']}/{s['n']} float exact"
    )
    if s["digits_equal"] != s["n"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
