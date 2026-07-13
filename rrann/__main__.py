"""CLI: python -m rrann <command> ..."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _cmd_verify(args: argparse.Namespace) -> int:
    from .fairness import RollReceipt, verify_receipt

    path = Path(args.receipt)
    data = json.loads(path.read_text(encoding="utf-8"))
    receipt = RollReceipt.from_dict(data)
    seed = float(args.seed)
    ok = verify_receipt(
        receipt,
        seed,
        game_id=args.game_id,
        season=args.season,
    )
    print(json.dumps({"ok": ok, "commit": receipt.commit, "result": receipt.result}))
    return 0 if ok else 1


def _cmd_health(args: argparse.Namespace) -> int:
    from .health import health_check

    h = health_check(
        float(args.seed),
        n_bits=args.bits,
        profile=args.profile,
        cull_head=args.cull_head,
    )
    print(json.dumps(h.to_dict(), indent=2))
    if h.status == "fail":
        return 2
    if h.status == "warn":
        return 1
    return 0


def _cmd_roll(args: argparse.Namespace) -> int:
    from .fairness import create_receipt

    r = create_receipt(
        float(args.seed),
        args.context,
        int(args.n),
        kind=args.kind,
        bits=args.bits,
        game_id=args.game_id,
        season=args.season,
        cull_head=args.cull_head,
    )
    print(r.to_json())
    if args.out:
        Path(args.out).write_text(r.to_json() + "\n", encoding="utf-8")
    return 0


def _cmd_simulate(args: argparse.Namespace) -> int:
    from .simulate import expected_value, normalize_weights, simulate_loot

    # default demo table as weights
    weights = [
        ("common", 70),
        ("uncommon", 20),
        ("rare", 8),
        ("legendary", 2),
    ]
    if args.table:
        # JSON list of [name, weight]
        weights = [(a, float(b)) for a, b in json.loads(Path(args.table).read_text())]

    report = simulate_loot(
        float(args.seed),
        weights,
        trials=args.trials,
        context=args.context,
        cumulative=False,
        cull_head=args.cull_head,
    )
    out = report.to_dict()
    if args.values:
        values = json.loads(Path(args.values).read_text())
        out["expected_value"] = expected_value(report.rates, values)
        out["theoretical_ev"] = expected_value(report.expected_rates, values)
    print(json.dumps(out, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="python -m rrann",
        description="RRann CLI — health, rolls, receipt verify, loot simulation",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    v = sub.add_parser("verify", help="Verify a roll receipt JSON against a seed")
    v.add_argument("receipt", help="Path to receipt JSON")
    v.add_argument("--seed", required=True, type=float)
    v.add_argument("--game-id", default="")
    v.add_argument("--season", default="")
    v.set_defaults(func=_cmd_verify)

    h = sub.add_parser("health", help="Run health_check on remainder bits")
    h.add_argument("--seed", type=float, default=2.4)
    h.add_argument("--bits", type=int, default=4096)
    h.add_argument(
        "--profile",
        choices=("cosmetic", "gameplay", "economy"),
        default="gameplay",
    )
    h.add_argument("--cull-head", type=int, default=None)
    h.set_defaults(func=_cmd_health)

    r = sub.add_parser("roll", help="Create a receipt for one roll")
    r.add_argument("--seed", type=float, required=True)
    r.add_argument("--context", required=True)
    r.add_argument("-n", type=int, default=0)
    r.add_argument("--kind", choices=("float", "int"), default="float")
    r.add_argument("--bits", type=int, default=32)
    r.add_argument("--game-id", default="")
    r.add_argument("--season", default="")
    r.add_argument("--cull-head", type=int, default=None)
    r.add_argument("--out", default="", help="Write receipt JSON to path")
    r.set_defaults(func=_cmd_roll)

    s = sub.add_parser("simulate", help="Monte Carlo loot rates under roll()")
    s.add_argument("--seed", type=float, default=2.4)
    s.add_argument("--trials", type=int, default=5000)
    s.add_argument("--context", default="loot.sim")
    s.add_argument("--table", default="", help="JSON [[name, weight], ...]")
    s.add_argument("--values", default="", help="JSON {name: value} for EV")
    s.add_argument("--cull-head", type=int, default=None)
    s.set_defaults(func=_cmd_simulate)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
