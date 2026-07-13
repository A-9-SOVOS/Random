# NIST STS + TestU01 harness for RRann

All paths below are relative to the **repo root** unless noted.

Layout:

```text
research/
  sts/           # this folder — export + runners
  results/       # binary dumps + timestamped reports
  third_party/   # NIST STS tree, TestU01 source (gitignored)
```

## Comprehensive NIST SP 800-22 profile

| Parameter | Value |
|-----------|-------|
| Bits per stream (`n`) | 1 000 000 |
| Number of streams | 1000 |
| Total bits | 1 000 000 000 |
| Binary dump size | 125 000 000 bytes (~119 MiB) |
| Format | packed binary, 8 bits/byte, MSB-first |

### Generate dump

```bash
python3 research/sts/export_sts_input.py \
  -o research/results/rrann_sts_1e6x1000.bin \
  --bits-per-stream 1000000 --streams 1000 --workers 18
```

Independent streams (different seeds) are generated in parallel. Memory stays
small; disk is ~119 MiB.

### Run STS non-interactively

```bash
# rebuild assess if architecture changed (e.g. x86_64 → aarch64)
(cd research/third_party/sts-2_1_2/sts-2.1.2/sts-2.1.2 && make clean && make -j"$(nproc)")

./research/sts/run_nist_sts.sh research/results/rrann_sts_1e6x1000.bin 1000000 1000
```

Results land in:

- `research/third_party/sts-2_1_2/.../experiments/AlgorithmTesting/finalAnalysisReport.txt`
- `research/results/sts_results/finalAnalysisReport_1000000x1000_*.txt` (timestamped copy)
- `research/results/sts_results/assess_*.log`

**Pass criteria (α = 0.01):** for each test, proportion of sequences with
p-value ≥ α should be in the NIST interval for m=1000 streams, and the
uniformity (χ²) p-value on the p-value histogram should be ≥ 0.0001. Lines
marked with `*` failed.

---

## TestU01 Bbattery — yes, available outside OCaml

The [OCaml `testu01` package docs](https://ocaml.org/p/testu01/latest/doc/testu01.testu01/TestU01/Bbattery/index.html)
are just bindings. The **same batteries** ship as the original C library
**TestU01 1.2.3** (L’Ecuyer & Simard).

| Channel | Package / path |
|---------|----------------|
| Ubuntu/Debian (multiverse) | `testu01-bin`, `libtestu01-0-dev`, `testu01-data` |
| Upstream source | http://www.iro.umontreal.ca/~simardr/testu01/TestU01.zip |
| This machine (user install) | `~/.local/testu01` |
| Vendored source (optional) | `research/third_party/TestU01-1.2.3` |
| OCaml | opam `testu01` (bindings only) |

Batteries in `bbattery`:

| Battery | Role | Cost |
|---------|------|------|
| **SmallCrush** | 10 quick tests | seconds–minutes |
| **Crush** | 96 tests | long |
| **BigCrush** | 106 tests | very long (~hours–days; ~2³⁸ numbers) |
| **Rabbit** | bit-oriented suite | medium |
| **Alphabit** | hardware-style bit tests | medium |
| **PseudoDIEHARD** | DIEHARD-like (not very stringent) | medium |
| **FIPS-140-2** | old 4-test module | fast |

### Build & run harness here

```bash
./research/sts/build_testu01_rrann.sh

./research/sts/testu01_rrann smallcrush research/results/rrann_sts_1e6x1000.bin
./research/sts/testu01_rrann alphabit   research/results/rrann_sts_1e6x1000.bin 33554432
./research/sts/testu01_rrann rabbit     research/results/rrann_sts_1e6x1000.bin 33554432
./research/sts/testu01_rrann crush      research/results/rrann_sts_1e6x1000.bin   # long
./research/sts/testu01_rrann bigcrush   research/results/rrann_sts_1e6x1000.bin   # very long
```

**Caveat:** SmallCrush/Crush/BigCrush consume far more than 125 MiB of
32-bit words. The harness **rewinds** the file when it hits EOF so the
battery can finish, but that injects a short period and can cause extra
failures. Prefer Rabbit/Alphabit on the existing dump, or generate a much
larger continuous stream before Crush/BigCrush.

System packages (if you have sudo):

```bash
sudo apt-get install -y testu01-bin libtestu01-0-dev testu01-data
```

---

## Disk reality check

| Artifact | Size |
|----------|------|
| `research/results/rrann_sts_1e6x1000.bin` | 125 MB |
| STS experiments/ outputs | typically a few hundred MB for 1000 streams |
| TestU01 install | ~tens of MB |
| **Not** required | 100+ GB dumps |
