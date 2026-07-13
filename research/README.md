# Research lab (optional)

Statistical batteries, structure analysis, and large local artifacts that are
**not** required to use the RRann library.

Product code lives at the repo root (`rrann/`, `rust/`, `go/`, …). Empirical
summary for library design: [../docs/FINDINGS.md](../docs/FINDINGS.md) and
[../docs/RESEARCH_HEAD_BIAS.md](../docs/RESEARCH_HEAD_BIAS.md).

## Layout

```text
research/
  analysis/       Zipf / compress / Markov / ACF; legacy validate
  sts/            NIST STS + TestU01 export & runners
  results/        Binary dumps + timestamped reports (gitignored bulk)
  third_party/    NIST STS tree, TestU01 sources (gitignored)
  vendor/         Optional local .deb extracts for headers (gitignored)
```

## Quick commands (from repo root)

```bash
# Structure suite (needs numpy for full report)
python3 research/analysis/analyze_structure.py

# Export STS binary (~119 MiB for full 1e6×1000 profile)
python3 research/sts/export_sts_input.py \
  -o research/results/rrann_sts_1e6x1000.bin \
  --bits-per-stream 1000000 --streams 1000

# NIST STS (needs built assess under research/third_party/sts-2_1_2/…)
./research/sts/run_nist_sts.sh research/results/rrann_sts_1e6x1000.bin 1000000 1000

# TestU01
./research/sts/build_testu01_rrann.sh
./research/sts/testu01_rrann smallcrush research/results/rrann_sts_1e6x1000.bin
```

Full battery notes: [sts/STS_AND_TESTU01.md](sts/STS_AND_TESTU01.md).
