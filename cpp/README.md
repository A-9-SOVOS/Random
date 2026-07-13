# RRann C/C++ engine surface

**OPEN_SEQUENCE step 3** (was open-list #3).

## Build Rust staticlib

```bash
export PATH="$HOME/.cargo/bin:$PATH"
cd ../rust/rrann-core
cargo build --release
# → target/release/librrann_core.a
```

## Smoke test

```bash
# Headers/libs for MPFR harvest (system or extracted -dev packages)
export CPATH=/path/to/gmp/include:/path/to/mpfr/include
export LIBRARY_PATH=/path/to/gmp/lib:/path/to/mpfr/lib:/lib/$(uname -m)-linux-gnu

cd ../rust/rrann-core && cargo build --release
cd ../../cpp
cc -O2 -o rrann_c_smoke smoke_test.c -I. \
  ../rust/rrann-core/target/release/librrann_core.a \
  -lm -ldl -lpthread -lgmp -lmpfr
./rrann_c_smoke
```

Expected: `stream0` ≈ `8.098…`, commit verifies, prints `ok`.

## Unity / Godot

- Copy `rrann.h` + platform `.a`/`.so`/`.dll` into the plugin folder.
- P/Invoke or GDExtension against the `rrann_*` symbols.
- Full residual harvest will appear on the same ABI later (sequence step 1 / 3rd).

## Header API

See `rrann.h`:

| Symbol | Role |
|--------|------|
| `rrann_stream_seed` | Independent fork seed |
| `rrann_commit_seed` / `verify_commit` | SHA-256 commit |
| `rrann_splitmix64` / `demo_u64` | Mixer / demo scatter |
| `rrann_extract_float` | Culled residual float (Rust harvest prototype) |
| `rrann_extract_u64` | Up to 64 residual bits |
| `rrann_harvest_digits` / `divergence_index` | Debug residual string |

**Parity:** residual extract is **not** guaranteed bit-identical to CPython `Decimal` yet
(see `tests/parity_report.json`). Economy servers should keep Python as reference until
soft-decimal parity lands.
