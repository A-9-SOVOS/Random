# Research: residual head bias (OPEN_SEQUENCE step 4)

**Status:** Product path is green (WASM, C ABI, full harvest ports). These notes
are the science backlog — **do not block shipping** on deeper models. Default
library behavior remains: **cull head (`cull_head=2`), use remainder**.

Primary empirical write-up: [FINDINGS.md](FINDINGS.md).

---

## What we already know

1. **Diverge cut.** Dual-precision residual of \(x^x\) (IEEE-754 binary64 vs
   high-precision Decimal / MPFR) first disagrees near decimal index **15–17**
   for normal game seeds in \((0, 20]\).

2. **Head non-uniformity.** Positions **0–1** of the residual string (first
   digits *after* the cut) are **position-biased** — not uniform over digits.

3. **Runs failure.** Packing bits from the **full residual** (no cull) fails
   run-length geometry: **too many short runs** (anti-persistence). On NIST STS
   scale (e.g. 1e6×1000), **Runs** hard-fails while monobit-ish structure can
   still look fine.

4. **Cull fixes the product path.** Discarding the first **two** residual digits
   restores run geometry on remainder material (digits 2–9, etc.) for STS-scale
   remainder tests. Library default: `cull_head=2`.

5. **Shannon is not the right alarm.** \(H_1\) of residual digits is near max —
   the defect is **positional / sequential**, not “empty entropy.” Compressors
   also see little structure on raw residual *blobs*; geometric run GOF does.

6. **Deeper digits look ordinary.** Positions 2+ (and 4–9 “deep”) pass run
   checks in the lab suite; Shannon-flat and usable as the default signal.

### Bullseye table (lab)

| Material | Runs (approx) |
|----------|----------------|
| Residual digits pos 0–1 only | **FAIL** (~z +6.5) |
| Full residual → 32 bits | **FAIL** (~z +6–10) |
| Digits pos **2–9** (remainder) | **ok** (~z ≈ 0) |
| Digits pos 4–9 (deep) | **ok** |
| Full residual + von Neumann | **ok** (~¼ rate) |

Artifacts: `research/analysis/analyze_structure.py`,
`research/sts/` (NIST STS + TestU01 harness),
`research/results/` (local dumps/reports, typically gitignored).
TestU01 SmallCrush / Alphabit / Rabbit showed gap / MaxOft / walk-style
failures on raw-ish material.

---

## Working hypothesis

The residual **head is not unstructured noise**. It is the **first symbol of
disagreement** between two representations of the same real \(x^x\):

- binary64 expansion (rounded), and  
- high-precision decimal (or MPFR) expansion.

That first differing digit is a **conditioned** random variable — conditioned on
“this is where the two expansions split.” Conditioned first digits often carry
Benford-like or positional structure. Packing them into bits injects short-run
geometry.

Deeper residual digits behave more like ordinary samples from the fractional
expansion of a smooth map past the split — hence usable remainder after cull.

This is a **hypothesis**, not a theorem. It motivates `cull_head=2` as an
engineering fix with empirical support, not a claim of cryptographic mixing.

---

## Open questions (optional)

- [ ] Analytic model: distribution of first residual digit as a function of
      fractional part / mantissa state at the diverge index
- [ ] Is the bias Benford-like, or specific to “first differing digit of two
      expansions”?
- [ ] Interaction of legacy `sin` mix vs cull (secondary; legacy is demo-only)
- [ ] Does `cull_head=4` buy Serial / FFT / ApEn margin worth the bit loss?
- [ ] Formal link between diverge index (~15–17) and binary64 decimal print
      precision (~15–17 significant digits)

---

## Library consequence (locked)

```text
harvest → cull residual head (default 2) → remainder → bits / float
```

- API: `extract_float`, `extract_bits`, `Rng`, `roll`, receipts, `health_check`
- `drop=` remains a compat alias for `cull_head=`
- Legacy `generate()` / `mode="legacy"`: sin-mix demos only
- Not a CSPRNG; for adversarial secrecy, use OS seed + standard DRBG

---

## When to push further

Revisit only if:

1. A new battery fails **on remainder** (not raw residual) at product-relevant scale, or  
2. You need a paper-grade model of the diverge digit for research, or  
3. You are choosing between `cull_head=2` vs `4` under a specific soft-fail suite.

Until then: **cull head, use remainder, ship.**
