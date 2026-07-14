# RRann

**Residual-harvest RNG** for games, sims, and auditable rolls.

Same seed → same results. Built from where IEEE float64 and high-precision
arithmetic **disagree** on \(x^x\), then **throwing away the biased head** of
that residual and using only the rest.

```text
seed ──►  x^x  (float64)     ──┐
                               ├── first disagreeing digit (~15–17)
seed ──►  x^x  (Decimal/MPFR)──┘
                 │
                 ▼
          residual digits
                 │
    ┌────────────┴────────────┐
    │ head (pos 0–1)          │ remainder (pos 2…)
    │ DROP — run-biased       │ KEEP — default signal
    └─────────────────────────┘
                 │
                 ▼
          bits / float  ←  this is what Rng, roll, extract_* emit
```

**Python core is stdlib-only.** Native ports (Rust MPFR / C / Go) match Python
on a 20-seed golden corpus. Soft WASM / pure-Go paths are approximate demos.

---

## Status of randomness quality (read this)

The library’s **default path already culls**. You are not shipping the run-broken
head unless you dig into raw `harvest()` digits yourself.

| Material | NIST STS **Runs** | Notes |
|----------|-------------------|--------|
| Full residual (no cull) → bits | **Hard fail** (~911/1000 on 1e6×1000) | Lab / historical; **not** the default API |
| Residual head only (digits 0–1) | **Fail** | Why we cull |
| **Default: cull 2, remainder → bits** | **Pass** (200/200 on 1e6×200) | What `Rng` / `extract_*` / `roll` use |
| Soft STS margins on remainder | FFT / Serial / ApEn soft `*` on that run | Not “Runs still broken” |

So: **Runs is fixed for the product path.** That is not a full STS green light,
not a crypto proof, and not a casino certification.

Lab detail: [docs/FINDINGS.md](docs/FINDINGS.md),
[docs/RESEARCH_HEAD_BIAS.md](docs/RESEARCH_HEAD_BIAS.md).

### Non-claims

| Claim | Reality |
|--------|---------|
| Deterministic game/sim PRNG with audit-friendly seed story | **Yes** |
| Seed commit for anti re-roll transparency | **Yes** (SHA-256) |
| Default path fixes residual **Runs** defect | **Yes** (see table) |
| Passes entire NIST STS / TestU01 | **No** — soft fails remain |
| **CSPRNG** / FIPS / SP 800-90 | **No** |
| Regulated real-money casino RNG | **No** |
| Physical / “universe” entropy | **No** — pure math residual |

For secrecy under an adversary: OS seed and/or a standard DRBG.  
For **value-bearing** economies: roll on the **server**, keep receipts; never
trust the client alone.

---

## Install (Python)

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest -q
python examples/basic_usage.py
```

Requires **Python 3.9+**. Core: **stdlib only**.

---

## 30-second tour

```python
from rrann import Rng, roll, create_receipt, verify_receipt, health_check

g = Rng(seed=2.4)                    # remainder path, cull_head=2
print(g.random())                    # [0, 1)
print(g.next_u64())
a, b = g.fork(0), g.fork(1)          # independent streams
print(a.random(), b.random())

print(roll(2.4, "loot.chest", 0))    # same seed+context+n → same result

r = create_receipt(2.4, "loot.chest", 0, game_id="mygame")
assert verify_receipt(r, 2.4, game_id="mygame")

print(health_check(2.4, profile="gameplay"))
```

```bash
python -m rrann health --seed 2.4 --profile gameplay
python -m rrann roll   --seed 2.4 --context loot.chest -n 0 --game-id demo --out receipt.json
python -m rrann verify receipt.json --seed 2.4 --game-id demo
python -m rrann simulate --seed 2.4 --trials 10000
```

---

## Why cull the head? (mechanism)

1. Evaluate \(x^x\) in binary64 and in high precision.
2. Take digits of the high-precision result starting at the first disagreement
   with float — the **residual**.
3. The **first two residual digits** are position-biased (conditioned “first
   split” symbols). Packed into bits they produce **too many short runs**.
4. Shannon entropy of the residual string can still look fine — the defect is
   **sequential / positional**, not “empty bits.”
5. **Drop those two digits.** Map the **remainder** to bits/float. That is
   `cull_head=2` (alias: `drop=`).

```text
harvest → cull head (2) → remainder → bits / float     ← default
```

`harvest(seed)` still returns the **full** residual string for research; extraction
APIs apply the cull. Don’t pack `h.digits` yourself and expect Runs to pass.

Optional science (not product blockers): analytic model of the first residual
digit; whether `cull_head=4` helps FFT/Serial/ApEn.

---

## For game designers

| Need | Use |
|------|-----|
| Reproducible stream | `Rng(seed)` / `Generator(seed)` |
| Parallel chunks / regions | `g.fork(stream_id)` — don’t share one advancing chain |
| Loot / spin index | `roll(seed, context, n)` |
| Anti re-roll | `commit_seed` before the window → later `verify_receipt` |
| Diagnostics | `health_check(..., profile="cosmetic"\|"gameplay"\|"economy")` |

**Profiles:** `cosmetic` (soft) · `gameplay` (default) · `economy` (stricter + server receipts).

```text
master_seed
   ├─ fork(0)  → region / worker 0
   ├─ fork(1)  → worker 1
   └─ roll(seed, "loot.chest", n)  → discrete event n
```

More: [docs/GAME_DESIGNERS.md](docs/GAME_DESIGNERS.md) ·
[docs/CROSS_PLAY.md](docs/CROSS_PLAY.md) ·
`python examples/server_roll.py` (`/v1/commit`, `/v1/roll`, `/v1/verify`).

---

## API map

| Symbol | Purpose |
|--------|---------|
| `harvest(seed)` | Raw residual (`HarvestResult`) — includes head; research |
| `extract_float` / `extract_bits` | **Culled** remainder → float / bits |
| `Rng` / `Generator` | Stateful stream (`random`, `next_u64`, `fork`) |
| `roll` / `roll_seed` / `stream_seed` | Context rolls & portable stream mix |
| `commit_seed` / `create_receipt` / `verify_receipt` | Commit–reveal |
| `health_check` / `ContinuousHealth` | Monobit + runs diagnostics |
| `simulate_loot` / `expected_value` | Table Monte Carlo helpers |
| `generate(seed)` | **Legacy** sin-mixed float (demos only) |

Receipts tag `ALGO_VERSION` = `rrann-remainder-cull2-v1`.

---

## Multi-language ports

| Surface | Path | Harvest fidelity |
|---------|------|------------------|
| **Python** | `rrann/` | Reference (Decimal) |
| **Rust** | `rust/rrann-core` | **MPFR** exact vs vectors; WASM **soft** |
| **C / C++** | `cpp/rrann.h` + staticlib | Via Rust native |
| **Go** | `go/rrann` | cgo+MPFR exact; `CGO_ENABLED=0` soft |
| **JS/WASM** | `packages/rrann-js` | Soft harvest (demos) |

Vectors: `tests/vectors.json`, `tests/vectors_commit.json`.  
Parity: `python scripts/parity_rust_python.py` → **20/20 exact** on native MPFR.

```bash
cd rust/rrann-core && cargo test && cargo build --release

cc -O2 -o cpp/rrann_c_smoke cpp/smoke_test.c -Icpp \
  rust/rrann-core/target/release/librrann_core.a \
  -lm -ldl -lpthread -lgmp -lmpfr && ./cpp/rrann_c_smoke

cd go/rrann && go test ./...
CGO_ENABLED=0 go test ./...

# WASM (optional soft harvest):
# wasm-pack build rust/rrann-core --target web \
#   --out-dir packages/rrann-js/pkg --features wasm --no-default-features

python3 -m http.server 8766
# web/three_scatter_demo.html · seed_commit_demo.html · extract_float_demo.html
```

Economy / multiplayer: use **Python or native MPFR** as one authority. Soft
paths are demos. Port history: [docs/OPEN_SEQUENCE.md](docs/OPEN_SEQUENCE.md).

---

## Examples & research lab

```bash
python examples/basic_usage.py
python examples/loot_table.py
python examples/crit_chance.py
python examples/shuffle_deck.py
python examples/procgen_chunks.py
python examples/mp_bake_chunks.py
python examples/server_roll.py
python scripts/bench_rrann.py
```

Statistical harnesses and large dumps live under **`research/`** (optional,
mostly gitignored) — see [research/README.md](research/README.md).

---

## Tests

```bash
pytest -q
cd rust/rrann-core && cargo test
cd go/rrann && go test ./...
python scripts/parity_rust_python.py
```

CI: `.github/workflows/ci.yml`.

---

## Limitations

1. **Slower** than PCG/xorshift (Decimal/MPFR cost per draw).
2. **Deterministic** — inject OS entropy into the seed if you need unpredictability.
3. **Runs fixed on default path**; other STS soft margins and TestU01 failures can
   still appear. Empirical lab, not a certification.
4. Soft harvest ≠ Decimal/MPFR bit-identical.
5. Exotic float `repr` for commits: check `tests/vectors_commit.json`.

---

## Docs

| Doc | Contents |
|-----|----------|
| [docs/FINDINGS.md](docs/FINDINGS.md) | STS / structure lab notes |
| [docs/RESEARCH_HEAD_BIAS.md](docs/RESEARCH_HEAD_BIAS.md) | Head-bias backlog |
| [docs/GAME_DESIGNERS.md](docs/GAME_DESIGNERS.md) | Forks, receipts, EV |
| [docs/CROSS_PLAY.md](docs/CROSS_PLAY.md) | Cross-language fairness |
| [docs/ROADMAP.md](docs/ROADMAP.md) | Milestones |
| [docs/OPEN_SEQUENCE.md](docs/OPEN_SEQUENCE.md) | Port status |
| [research/README.md](research/README.md) | Lab layout |
| [research/sts/STS_AND_TESTU01.md](research/sts/STS_AND_TESTU01.md) | Battery harness |

---

## License

MIT — see [LICENSE](LICENSE).
