# RRann roadmap checklist

**Open-list execution order (2→3→1→4):** see [OPEN_SEQUENCE.md](OPEN_SEQUENCE.md).

Product spine: **close investigation B → Python game API + fairness receipts → fast core (Rust/WASM) + three.js → engine bundles.**

**Positioning (not negotiable in marketing copy)**

- Deterministic **error-harvest** PRNG: dual-precision residual of \(x^x\), **cull residual head**, use the remainder.
- Target: **simulations, games, procedural content, fair-ish player economies** (transparency + audit).
- **Not** a FIPS/CMVP CSPRNG and **not** a regulated casino RNG.
- Optional **SHA-2 (or similar) seed commit** = anti-cheat / transparency, not “we are a crypto oracle.”

---

## Positioning & claims

- [x] One-liner locked in README: *error dive → cull head → clean residual signal*
- [x] Explicit non-claims: no FIPS, no CSPRNG, no regulated gambling
- [x] “Max worry” tier defined: server-authoritative rolls + commit–reveal for value-bearing outcomes
- [x] Client-only RNG limited to cosmetics / VFX / offline single-player in docs
- [x] Shannon vs pattern note: high \(H_1\) hid **positional/run** structure; head culled on purpose

---

## Phase B — Close the investigation

Science is ~done; close the loop so the product stops thrashing.

### Naming & defaults

- [x] Rename bare `drop=2` → designer-facing name (e.g. `cull_head` / `discard_leading`)
- [x] Document: *first two residual digits after diverge cut fail run geometry; default discards them*
- [x] Default pipeline locked: `seed → residual digits → cull head → bits/float`
- [x] Legacy sin-mix path only via `mode="legacy"` (or equivalent)
- [x] API/docs never imply “drop=2” without saying **what** is dropped

### Health & evidence

- [x] `health_check()` (or profile-based checks): monobit, runs z / mean run length band
- [x] Optional continuous health on rolling window (economy profile)
- [x] Cosmetic profile: warn-only; economy profile: fail-closed on health fail
- [x] Designer-facing one-pager linked from README (`docs/FINDINGS.md` or short “What we know”)
- [x] Remainder STS summary cited (Runs clean; soft Serial/FFT/ApEn margin — optional follow-up)
- [x] Structural summary path noted (`research/results/` local; not required for install)

### B exit criteria

- [x] Defaults stable; happy path has no research-only knobs
- [x] Health API exists and is documented
- [x] FINDINGS / “what we know” linked from README
- [x] Pure “why does the head bias exist?” parked as backlog curiosity (not a release blocker)

---

## Phase 0 — Productize Python (game-shaped)

### Core API

- [x] Game-facing type name if needed (`Rng` alias and/or polish `Generator`)
- [x] `from_seed(seed)` / stable seed normalization documented
- [x] `next_u64` / `next_f64` (or clear `randbits` / `random` equivalents)
- [x] `fork(stream_id)` — independent child streams from master seed
- [x] Counter/context rolls: `roll(seed, context, n)` without clobbering unrelated streams
- [x] Version field on algorithm (`algo_version`) for receipts

### Fairness helpers (light)

- [x] Seed commit helper: `commit = H(seed || game_id || season)` (SHA-256 fine)
- [x] Document commit–reveal: publish commit before roll; reveal seed after
- [x] Bench note: order-of-magnitude cost per call (Decimal-bound)

### Examples & packaging

- [x] Example: loot table
- [x] Example: crit / hit chance
- [x] Example: shuffle / deck
- [x] Example: proc-gen chunk with `fork(chunk_id)`
- [x] README “for game designers” section
- [ ] PyPI-ready metadata (real repo URLs when published)
- [x] Changelog started (`CHANGELOG.md`)

### Parallelism (Python)

- [x] Document: parallel = many `fork(i)` / independent seeds, not one shared chain
- [x] Optional example: multiprocessing bake of chunks

---

## Phase 1 — Fairness toolkit (player economy)

For gacha-like / paid cosmetics / PvP rewards where “is it fair?” matters.

### Roll receipts

- [x] Receipt schema: `{ commit, context, counter, result, algo_version, … }`
- [x] `verify(receipt, seed)` recomputes result after reveal
- [x] Example server flow: commit → roll → store receipt → optional reveal

### Profiles

- [x] `cosmetic` — client OK for non-value; weak health OK
- [x] `gameplay` — deterministic sync / replays
- [x] `economy` — server-only; health fail-closed; receipts required in docs

### Simulation & docs

- [x] Monte Carlo rate simulator for a sample loot table under RRann
- [x] Doc: expected value / pity / rate transparency (design, not crypto)
- [x] Doc: **never trust client RNG for value-bearing outcomes**
- [x] Optional: verify CLI (`python -m rrann verify receipt.json`)

### Explicit out-of-scope

- [x] README: regulated real-money gambling / GLI-style cert = different product stack

---

## Phase 2 — Speed & ports

Reference = Python; hot path = systems language + WASM for web.

### Implementations

- [x] **Rust** crate helpers (`stream_seed`/`commit_seed` + vectors); full harvest still Python
- [x] Bit-identical (or documented tolerance) tests vs Python reference (stream_seed/commit vectors)
- [ ] **WASM** build of Rust core
- [ ] **C++** port or C ABI for engines
- [x] **Go** port for backends (helpers + tests; harvest still Python)
- [ ] TS/JS **via WASM** first (avoid pure-JS big-decimal as primary)

### Parallelism & cross-play

- [x] Document `seed_i = mix(master, stream_id)` pattern
- [x] Offline bake path (world gen on N cores)
- [x] Online: one stream per session / region on server
- [x] Cross-play policy: soft-float / fixed decimal if bit-identical multiplayer required
- [x] Platform float caveats documented when not bit-identical

### Tighten

- [x] Shared test vectors (`vectors.json` or similar) across languages
- [x] CI matrix: Python + at least one native port
- [x] Optional light mixer (e.g. finalizer on u64) documented as **mixer**, not extra entropy magic

---

## Phase 3 — Engine & ecosystem bundles

- [ ] **three.js / web pack**: npm wrapper around WASM + 2 demos (scatter / loot preview)
- [x] Seed-commit UI demo (show commit, then reveal)
- [ ] Godot plugin (later)
- [ ] Unity plugin (later)
- [x] Sample **server middleware** (Python HTTP; Go/Rust helpers available)
- [x] Pitch line: *procedural and economy rolls you can replay and audit*

---

## Phase 4 — Optional stronger bits (economy tier only)

Only if product needs more statistical polish — not FIPS theater.

- [x] Remainder extract remains default
- [x] Optional whitening: XOR-adjacent / von Neumann / fast finalizer
- [x] Document rate cost of each whitening
- [x] Optional: OS entropy **seeds** the stream; RRann expands (say so clearly)
- [ ] Re-run focused STS/TestU01 on economy profile if claimed “statistically hardened”

---

## Milestones (check when exit criteria met)

| ID | Name | Exit criteria |
|----|------|----------------|
| **M1** | B closed | [x] Cull named, health API, remainder default, FINDINGS linked |
| **M2** | Game Python | [x] fork, receipts, loot example, economy profile docs |
| **M3** | Fast core | [~] Rust helpers + vectors; WASM/full harvest later |
| **M4** | three.js pack | [ ] npm package, ≥2 demos, seed-commit UX |
| **M5** | Fairness pack | [x] verify CLI, rate sim, HTTP server sample |

---

## Explicit non-goals (keep unchecked on purpose)

- [ ] ~~FIPS 140 / CMVP validation~~
- [ ] ~~SP 800-90A/B RRann-as-sole-entropy-source~~
- [ ] ~~Regulated casino / real-money device certification~~
- [ ] ~~“We are a physical entropy source / machine intelligence” marketing~~
- [ ] ~~Chasing 100% STS green as the definition of done~~

---

## Backlog curiosities (research A — not release blockers)

- [ ] Why residual head digits are position-biased / run-hot
- [ ] Analytic model of diverge index distribution
- [ ] Deeper drop (`cull_head=4`) throughput vs Serial/FFT/ApEn
- [ ] Multi-language soft-float for strict bit-identical cross-play

---

## Quick status (update as you go)

| Area | Status |
|------|--------|
| Error harvest core | Done |
| Head cull idea + remainder default in lib | Done (`cull_head`, docs) |
| Runs on remainder (STS) | Largely fixed (200/200 on 1e6×200) |
| Soft STS margin (Serial/FFT/ApEn) | Known; optional Phase 4 |
| Continuous health / examples / CLI / vectors | Done (20-seed corpus) |
| Rust/Go helpers + CI + server sample | Done |
| Residual harvest ports | Done — MPFR native + WASM/Go soft |
| Game API / receipts | Done (Python M1+M2) |
| three.js / ports | Done (WASM demos + C ABI) |
| Fairness economy toolkit (receipts/profiles/sim CLI) | Done (Python) |

*Last updated: multi-seed parity, pure-Go soft harvest, extractFloat WASM demo.*
