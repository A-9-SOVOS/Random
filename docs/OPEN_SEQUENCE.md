# Open work sequence (2 → 3 → 1 → 4)

Former “still open” list, **reordered** so scaffolding lands before the hard harvest port.

| Order | Was # | Work item | Why this position |
|------:|------:|-----------|-------------------|
| **1st** | **2** | WASM + three.js pack | Ship browser/game demos on helpers we already have; harvest plugs in later |
| **2nd** | **3** | C++ ABI / engine plugin skeleton | Engines can link stream/commit/mixer; same surface as WASM |
| **3rd** | **1** | Full residual harvest in Rust/Go | Hard Decimal \(x^x\) parity — do once ABI/WASM layout exists so we aren’t redoing glue |
| **4th** | **4** | Research residual-head bias | Science backlog; not blocking product ports |

**Rule:** Do not start deep head-bias research (4) or treat full harvest (1) as “blocked on curiosity.”  
When “doing 1,” it means **step 3 in this sequence** (after WASM + C++ surfaces).

## Checklist

### Step 2 — WASM + three.js (was #2)
- [ ] `rrann-core` builds to `wasm32-unknown-unknown` / `wasm-pack`
- [ ] npm package wraps WASM (`@rrann/core` or `packages/rrann-js`)
- [ ] three.js demo: seed + fork scatter / instance noise
- [ ] Seed-commit demo uses same WASM commit as Python vectors where possible

### Step 3 — C++ ABI (was #3)
- [ ] `c_api` / `rrann.h` + static/shared lib for stream_seed, commit_seed, splitmix64
- [ ] CMake or simple Makefile
- [ ] Smoke test vs `vectors_commit.json`
- [ ] Stub notes for Unity/Godot (load native plugin)

### Step 1 — Full harvest port (was #1, **now 3rd**)
- [ ] Rust: dual-precision residual harvest + cull_head extract_float/bits
- [ ] Golden tests vs `tests/vectors.json` (exact or documented tolerance)
- [ ] Wire harvest into WASM + C ABI
- [ ] Go: either call C ABI or pure-Go soft-decimal later

### Step 4 — Research (was #4)
- [ ] Notes only until 2–3–1 product path is green
- [ ] Head bias / diverge-index model (FINDINGS appendix)

## Status

| Step | Status |
|------|--------|
| 2 WASM + three.js | **Done** (wasm-pack, `@rrann/core`, three scatter + commit demos) |
| 3 C++ ABI | **Done** (`cpp/rrann.h`, Rust staticlib, `smoke_test` green) |
| 1 Full harvest (3rd) | **Done** — MPFR native matches Python on 20-seed corpus; WASM soft; Go cgo + pure-Go soft |
| 4 Research | **Documented** (FINDINGS + expanded `RESEARCH_HEAD_BIAS.md`); optional analytic model still open |

### Step 2 checklist
- [x] `rrann-core` builds to wasm via `wasm-pack`
- [x] npm package wraps WASM (`packages/rrann-js`)
- [x] three.js demo: seed + fork scatter
- [x] Seed-commit demo (web) + WASM commit path available after `build:wasm`
- [x] extractFloat / harvestDigits demo (`web/extract_float_demo.html`)

### Step 3 checklist
- [x] `rrann.h` + Rust `c_api` staticlib
- [x] Makefile-style smoke (`cpp/smoke_test.c`)
- [x] Smoke vs stream/commit vectors
- [x] Unity/Godot notes in `cpp/README.md`

### Step 1 checklist (was #1, run 3rd)
- [x] Rust dual-precision harvest (MPFR/`rug` native) + cull extract
- [x] Parity report vs Python (`scripts/parity_rust_python.py` → `tests/parity_report.json`) — **exact on vector seeds**
- [x] Wire harvest into C ABI + Go cgo + WASM (WASM uses soft-harvest; native uses MPFR)
- [x] Feature split: `native-harvest` vs `soft-harvest` for wasm32
- [x] Broader seed corpus (`tests/vectors.json` ≥20 seeds) + golden tests in Rust/Go
- [x] Pure-Go soft harvest without cgo (`harvest_soft.go`, `CGO_ENABLED=0`)
- [x] CI installs `libgmp-dev` + `libmpfr-dev` for Rust/Go/C jobs

### Step 4 checklist
- [x] Notes in `docs/RESEARCH_HEAD_BIAS.md` (hypothesis, bullseye table, open questions)
- [x] Empirical summary in `docs/FINDINGS.md` + linked from README
- [ ] Analytic model of first residual digit (optional later)
