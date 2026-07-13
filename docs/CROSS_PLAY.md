# Cross-play & platform notes

## Default recommendation

For multiplayer or paid economies: **server authority**. Clients may predict with
the same seed for cosmetics; value-bearing results come from the server (see
`examples/server_roll.py`).

## What can differ across platforms

| Path | Risk |
|------|------|
| Culled residual via Python `Decimal` | Stable within CPython versions if algo_version fixed |
| Native IEEE float for `seed**seed` (diverge index) | Rounding / libm differences rare but possible |
| `stream_seed` / `commit_seed` (f64 + SHA-256) | Designed for port parity (Rust/Go tests vs Python vectors) |
| `roll()` full result | Uses residual extract → Python-ref until soft-decimal ports |

## Bit-identical policy

1. Pin `algo_version` (`rrann-remainder-cull2-v1`) and `cull_head`.
2. Prefer **server rolls** + receipts for anything that affects economy.
3. Cross-lang helpers with golden tests: `tests/vectors_commit.json` (commit + stream_seed).
4. Full harvest parity: native MPFR (Rust/C/cgo) matches Python on `tests/vectors.json`;
   WASM/pure-Go soft harvest is approximate (demos only).

## Offline bake / online sessions

- **Offline world gen:** `examples/mp_bake_chunks.py` — one `fork(chunk_id)` per worker.
- **Online:** one stream per session/region: `Rng(master).fork(session_id)`.

## Mixer (optional)

`examples/mixer_u64.py` applies splitmix64 as a **finalizer** after residual u64
blocks — not a new entropy source. Same idea in Rust: `rrann_core::splitmix64`.
