# Package contents

## Product (install & ship)

| Path | Role |
|------|------|
| `rrann/` | Python package (harvest, extract, Rng, receipts, health, sim) |
| `RRann.py` | Compat re-export (`import RRann`) |
| `pyproject.toml` | Packaging |
| `tests/` | pytest + golden vectors |
| `examples/` | Loot, crit, shuffle, proc-gen, server middleware, terminal demo |
| `scripts/` | Bench + Rust/Python parity |
| `docs/` | FINDINGS, designers, roadmap, head-bias research notes |
| `rust/rrann-core` | MPFR harvest, C ABI, WASM soft |
| `go/rrann` | commit/stream + cgo or soft harvest |
| `cpp/` | `rrann.h` + smoke |
| `packages/rrann-js` | npm / WASM façade |
| `web/` | Browser demos (scatter, commit, extractFloat, legacy demo) |
| `README.md`, `LICENSE`, `CHANGELOG.md` | Front door |

## Research lab (optional)

| Path | Role |
|------|------|
| `research/analysis/` | Structure suite, validate, sample dumps |
| `research/sts/` | STS export, runners, TestU01 harness, battery notes |
| `research/results/` | Binary dumps + reports (**gitignored** bulk) |
| `research/third_party/` | NIST STS / TestU01 trees (**gitignored**) |
| `research/vendor/` | Local `.deb` header extracts (**gitignored**) |

See [research/README.md](research/README.md).
