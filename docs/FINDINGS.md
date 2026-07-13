# Empirical findings (STS / structure suite)

Summary of the investigation that motivated `drop=2` remainder extraction.
Not a formal paper — lab notes.

## Mechanism

RRann is a **dual-precision residual harvester**:

1. Evaluate `seed ** seed` in IEEE-754 binary64 and in high-precision `Decimal`.
2. Find the first decimal digit where they disagree (typically index ~15–17).
3. Read subsequent Decimal digits as the residual (“error”) string.
4. Historically: form `0.digits` and mix with `sin(seed * 1e6)`.

This is **deterministic algorithmic** material (digits of a real map), not physical TRNG noise. SHA-256 fallback applies when float/Decimal never diverge.

## What passed / failed

| Battery | Result |
|---------|--------|
| Shannon \(H_1\), small n-gram H | Near ideal — “can't tell” |
| Compressibility (zlib/lzma on bits) | Incompressible |
| NIST STS 1e6×1000 | **Runs** hard fail (911/1000); BlockFrequency uniformity; two NonOverlappingTemplate margins |
| TestU01 SmallCrush / Alphabit / Rabbit | Failures on gap / MaxOft / walks / periods / autocorr |
| Bit ACF / geometric run GOF on **raw residual→bits** | **Too many short runs** (anti-persistence) |
| Same on **full `generate()`** (sin mix) | Mostly repaired on aggregate blobs |

## Bullseye: sequential runs vs remainder

| Material | Runs z (approx) |
|----------|-----------------|
| Residual digits pos 0–1 only | **FAIL** (~+6.5) |
| Full residual → 32 bits | **FAIL** (~+6–10) |
| Digits pos **2–9** (remainder) | **ok** (~0) |
| Digits pos 4–9 (deep) | **ok** |
| Full out + von Neumann | **ok** (~¼ rate) |

Leading residual digits after the diverge cut are **position-biased** (non-uniform first/second digit). Deeper digits look Shannon-flat and pass run geometry.

## Library consequence

Default extraction (`cull_head=2`; `drop=` is a compat alias):

```text
harvest → cull residual head (2 digits) → map remainder to bits/float
```

API: `extract_float` / `extract_bits` / `Rng` / `roll` / `health_check` / receipts.
Legacy `generate()` / `mode="legacy"` kept for demos only.
For adversarial secrecy, pipe bits into a standard DRBG — do not claim CSPRNG.

## Artifacts

Lab tools live under **`research/`** (not required to use the library):

- `research/analysis/analyze_structure.py` — Zipf, compressibility, Markov, ACF
- `research/sts/export_sts_input.py` / `run_nist_sts.sh` — NIST STS harness
- `research/results/sts_results/` — local reports (gitignored by default)
- Overview: [research/README.md](../research/README.md)
