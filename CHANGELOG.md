# Changelog

## 0.2.0

### Added
- `cull_head` naming (default 2); `drop` kept as compat alias
- `health_check` / `diagnose_bits` / `ContinuousHealth` (rolling window)
- profiles: cosmetic, gameplay, economy
- `Rng` alias for `Generator`; `fork(stream_id)`, `next_u64`, `next_f64`
- `roll(seed, context, n)`, `roll_seed`, `stream_seed`
- `commit_seed`, `create_receipt`, `verify_receipt`, `RollReceipt`, `ALGO_VERSION`
- `simulate_loot`, `expected_value`, `pity_effective_rate`
- CLI: `python -m rrann {health,roll,verify,simulate}`
- Examples: loot, crit, shuffle, proc-gen chunks, multiprocessing bake
- Docs: FINDINGS, ROADMAP, GAME_DESIGNERS; `tests/vectors.json`; `scripts/bench_rrann.py`

### Default path
- residual digits → cull head → bits/float (`mode="remainder"`)
- legacy sin-mix only via `generate()` / `mode="legacy"`

### Also
- HTTP roll middleware sample (`examples/server_roll.py`)
- GitHub Actions CI (Python matrix + Rust + Go + C smoke)
- Go/Rust portable `stream_seed` + `commit_seed` with golden vectors
- Browser seed-commit + three.js scatter demos; WASM harvest extract
- C ABI: extract_float / extract_u64 / harvest_digits
- Rust harvest via MPFR (`rug`) — exact residual match on Python vector seeds
- WASM soft-harvest feature-split; native `native-harvest` default
- C/Go/WASM extract_float + harvest digits; parity report all-green on vectors
- OPEN_SEQUENCE 2→3→1→4 for remaining open work
- Expanded `tests/vectors.json` to 20 seeds; Rust/Go golden tests vs full corpus
- Pure-Go soft harvest (`harvest_soft.go`) when `CGO_ENABLED=0`
- Fallback SHA digit path aligned with Python `:.18g`; extract_bits digit count parity
- Browser `web/extract_float_demo.html` for WASM soft residual harvest
- Repo tidy: lab harnesses/artifacts under `research/`; product root thinned
