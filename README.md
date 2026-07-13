# RRann

**Residual-harvest RNG** — deterministic randomness for games, sims, and
auditable rolls, built from where IEEE float and high-precision arithmetic
**disagree** on \(x^x\).

```text
seed ──►  x^x in float64  ──┐
                            ├── diverge at digit ~15–17
seed ──►  x^x in Decimal    ──┘
              │
              ▼
        residual digit string
              │
              ├── head (digits 0–1)  →  cull  (run-biased)
              └── remainder          →  signal  →  bits / float
```

Same seed → same stream. No network, no hardware TRNG, **stdlib Python core**.
Native ports (Rust MPFR / C / Go) match the Python residual on a 20-seed golden corpus.

---

## Why it exists

Most game PRNGs are fine black boxes (PCG, xorshift, system `random`). RRann is
for when you want:

1. **A story you can audit** — “we used the dual-precision residual of the
   published seed,” not an opaque LCG state.
2. **Commit–reveal** — publish `commit_seed(...)` before a season; later prove
   the seed you rolled with.
3. **Independent forks** — chunk A and chunk B don’t share a mutating counter
   (`fork(stream_id)` / `roll(seed, context, n)`).
4. **A known failure mode, fixed by design** — raw residual bits fail NIST
   **Runs** (too many short runs). **Culling the residual head** fixes that for
   the default path. See [Why cull the head?](#why-cull-the-head).

### What this is not

| Claim | Reality |
|--------|---------|
| Fun / sim / game PRNG with audit-friendly determinism | **Yes** |
| Seed commit for anti re-roll transparency | **Yes** (SHA-256) |
| **CSPRNG** / FIPS 140 / SP 800-90 | **No** |
| Regulated real-money casino RNG | **No** — different stack |
| Physical / “universe” entropy | **No** — pure math residual |

For secrecy under an adversary, seed from the OS and/or feed bits into a standard
DRBG. For **value-bearing** economies, **roll on the server** and keep receipts;
never trust the client alone.

---

## Install (Python)

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest -q
python examples/basic_usage.py
```

Requires **Python 3.9+**. Core library: **stdlib only** (`decimal`, `hashlib`, …).

---

## 30-second tour

```python
from rrann import Rng, roll, create_receipt, verify_receipt, health_check

g = Rng(seed=2.4)                    # remainder path, cull_head=2
print(g.random())                    # [0, 1)
print(g.next_u64())                  # 64 mixed residual bits
a, b = g.fork(0), g.fork(1)          # independent streams from one master
print(a.random(), b.random())

# Context-indexed roll (loot chest #0, spin #n, …)
print(roll(2.4, "loot.chest", 0))

# Commit–reveal receipt
r = create_receipt(2.4, "loot.chest", 0, game_id="mygame")
assert verify_receipt(r, 2.4, game_id="mygame")

print(health_check(2.4, profile="gameplay"))
```

CLI:

```bash
python -m rrann health --seed 2.4 --profile gameplay
python -m rrann roll   --seed 2.4 --context loot.chest -n 0 --game-id demo --out receipt.json
python -m rrann verify receipt.json --seed 2.4 --game-id demo
python -m rrann simulate --seed 2.4 --trials 10000
```

---

## Why cull the head?

Lab notes (not a paper) — full write-up in
[docs/FINDINGS.md](docs/FINDINGS.md) and
[docs/RESEARCH_HEAD_BIAS.md](docs/RESEARCH_HEAD_BIAS.md).

| Observation | Detail |
|-------------|--------|
| Diverge cut | Float vs high-precision \(x^x\) usually first disagree near **decimal index 15–17** |
| Residual head | Digits **0–1 after the cut** are **non-uniform** (positional bias) |
| Shannon \(H_1\) | Near max overall — the bug is **not** “no entropy,” it’s sequential structure |
| Raw residual → bits | **Too many short runs** (NIST STS Runs hard-fail on large samples) |
| Digits **2–9** (remainder) | Run geometry recovers; default library path |
| `cull_head=2` | Default; `drop=` is a compat alias |

**Working hypothesis:** the head is the *first symbol of disagreement* between
two expansions of the same real — a **conditioned** digit, not an i.i.d. sample.
Deeper digits behave more like ordinary fractional digits of a smooth map.

| Material | Runs (approx) |
|----------|----------------|
| Residual positions 0–1 only | **FAIL** |
| Full residual → 32 bits | **FAIL** |
| Digits pos **2–9** (remainder) | **ok** |
| Full residual + von Neumann | ok (~¼ bit rate) |

Default pipeline:

```text
harvest → cull residual head (2 digits) → map remainder → bits / float
```

Open science (optional): analytic model of the first residual digit, Benford-like
structure, whether `cull_head=4` buys Serial/FFT margin. Product path does **not**
block on those — cull and ship remainder.

---

## For game designers

| Need | Use |
|------|-----|
| Reproducible stream | `Rng(seed)` / `Generator(seed)` |
| Parallel chunks / regions | `g.fork(stream_id)` — **don’t** share one advancing chain |
| Loot / spin index | `roll(seed, context, n)` |
| Anti re-roll | `commit_seed` before the window → later `verify_receipt` |
| Diagnostics | `health_check(..., profile="cosmetic"\|"gameplay"\|"economy")` |

**Profiles:** `cosmetic` (soft), `gameplay` (default), `economy` (stricter; pair with server receipts).

```text
master_seed
   ├─ fork(0)  → region / worker 0
   ├─ fork(1)  → worker 1
   └─ roll(seed, "loot.chest", n)  → discrete event n
```

Longer notes (EV, pity, multiproc bake): [docs/GAME_DESIGNERS.md](docs/GAME_DESIGNERS.md).  
Fairness / cross-play: [docs/CROSS_PLAY.md](docs/CROSS_PLAY.md).  
HTTP sample: `python examples/server_roll.py` → `/v1/commit`, `/v1/roll`, `/v1/verify`.

---

## API map

| Symbol | Purpose |
|--------|---------|
| `harvest(seed)` | Raw residual `HarvestResult` (digits, diverge index, fallback flag) |
| `extract_float` / `extract_bits` | Culled remainder → unit float / bit list |
| `Rng` / `Generator` | Stateful stream: `random`, `next_u64`, `fork` |
| `roll` / `roll_seed` / `stream_seed` | Context rolls & portable stream mix |
| `commit_seed` / `create_receipt` / `verify_receipt` | Commit–reveal |
| `health_check` / `ContinuousHealth` | Monobit + runs diagnostics |
| `simulate_loot` / `expected_value` | Table Monte Carlo helpers |
| `generate(seed)` | **Legacy** sin-mixed float only (demos) |

`ALGO_VERSION` tags receipt material (`rrann-remainder-cull2-v1`).

---

## Multi-language ports

| Surface | Path | Harvest fidelity |
|---------|------|------------------|
| **Python** | `rrann/` | Reference (Decimal) |
| **Rust** | `rust/rrann-core` | **Native MPFR** exact vs vectors; WASM **soft** |
| **C / C++** | `cpp/rrann.h` + staticlib | Via Rust native |
| **Go** | `go/rrann` | cgo+MPFR exact; `CGO_ENABLED=0` soft |
| **JS/WASM** | `packages/rrann-js` | Soft harvest (demos) |

Golden vectors: `tests/vectors.json` (harvest + extract), `tests/vectors_commit.json` (commit/stream).  
Parity report: `python scripts/parity_rust_python.py` → `tests/parity_report.json` (**20/20 exact** on native).

```bash
# Rust
cd rust/rrann-core && cargo test && cargo build --release

# C smoke (needs libgmp + libmpfr)
cc -O2 -o cpp/rrann_c_smoke cpp/smoke_test.c -Icpp \
  rust/rrann-core/target/release/librrann_core.a \
  -lm -ldl -lpthread -lgmp -lmpfr
./cpp/rrann_c_smoke

# Go
cd go/rrann && go test ./...          # cgo + built staticlib
CGO_ENABLED=0 go test ./...           # pure-Go soft harvest

# WASM soft (optional)
# wasm-pack build rust/rrann-core --target web \
#   --out-dir packages/rrann-js/pkg --features wasm --no-default-features

# Browser demos
python3 -m http.server 8766
# → web/three_scatter_demo.html
# → web/seed_commit_demo.html
# → web/extract_float_demo.html
```

Use **Python or native MPFR** for economy / receipts parity. Soft paths (WASM,
pure-Go big.Float) are for client demos and offline tools — document the backend
if you mix them.

Port status history: [docs/OPEN_SEQUENCE.md](docs/OPEN_SEQUENCE.md).

---

## Examples & tooling

```bash
python examples/basic_usage.py
python examples/loot_table.py
python examples/crit_chance.py
python examples/shuffle_deck.py
python examples/procgen_chunks.py
python examples/mp_bake_chunks.py    # ProcessPool + fork
python examples/server_roll.py       # commit / roll / verify HTTP
python scripts/bench_rrann.py        # order-of-magnitude µs/call
```

Research lab (optional, bulk gitignored) — [research/README.md](research/README.md):

| Path | Role |
|------|------|
| `research/analysis/` | Zipf, compressibility, Markov, ACF |
| `research/sts/` | NIST STS + TestU01 harness |
| `research/results/` | Binary dumps + timestamped reports |

---

## Tests

```bash
pytest -q                                          # Python
cd rust/rrann-core && cargo test                   # Rust (needs gmp/mpfr for native)
cd go/rrann && go test ./...                       # Go
python scripts/parity_rust_python.py               # cross-lang residual parity
```

CI: `.github/workflows/ci.yml` — Python matrix, Rust, Go (cgo), C smoke.

---

## Limitations

1. **Slower** than PCG/xorshift — Decimal / MPFR dominate per draw. Fine for
   loot/crit; bake chunks offline if you need walls of bits.
2. **Deterministic** given the seed — not live entropy unless you inject OS
   randomness into the seed.
3. **Statistical remainder** is much cleaner than raw residual (Runs fixed on
   STS-scale remainder samples); that is empirical, not a crypto proof.
4. Soft harvest (WASM / pure-Go) is **not** bit-identical to Decimal/MPFR —
   keep one authority for multiplayer economies.
5. Cross-language `stream_seed` / `commit_seed` are designed for parity; exotic
   float `repr` edge cases should be validated against `vectors_commit.json`.

---

## Docs index

| Doc | Contents |
|-----|----------|
| [docs/FINDINGS.md](docs/FINDINGS.md) | STS / structure suite lab notes |
| [docs/RESEARCH_HEAD_BIAS.md](docs/RESEARCH_HEAD_BIAS.md) | Residual-head bias research backlog |
| [docs/GAME_DESIGNERS.md](docs/GAME_DESIGNERS.md) | Parallel model, receipts, EV |
| [docs/CROSS_PLAY.md](docs/CROSS_PLAY.md) | Cross-language / fairness notes |
| [docs/ROADMAP.md](docs/ROADMAP.md) | Milestone checklist |
| [docs/OPEN_SEQUENCE.md](docs/OPEN_SEQUENCE.md) | Port order 2→3→1→4 and status |
| [QUICKSTART.md](QUICKSTART.md) | Minimal install + snippet |
| [CHANGELOG.md](CHANGELOG.md) | Version history |
| [research/sts/STS_AND_TESTU01.md](research/sts/STS_AND_TESTU01.md) | Battery harness notes |
| [research/README.md](research/README.md) | Lab layout (STS / analysis / results) |

---

## License

MIT — see [LICENSE](LICENSE).
