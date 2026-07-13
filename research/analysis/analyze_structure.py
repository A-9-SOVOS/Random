#!/usr/bin/env python3
"""
Deep structure analysis for RRann residual harvest.

Suites:
  - Zipf's law on token ranks (bytes, n-grams, run lengths)
  - Compressibility proxies for Kolmogorov complexity (zlib/bz2/lzma + entropy bound)
  - N-gram / Markov chain (transition entropy, surprisal, chi-square vs iid)
  - Autocorrelation (bits, values, multi-lag, runs indicators)

Compares four streams under the same sample budget:
  indep_base, indep_out, chain_base, chain_out
"""

from __future__ import annotations

import argparse
import collections
import gzip
import io
import lzma
import math
import struct
import sys
import time
import zlib
import bz2
from pathlib import Path

import numpy as np

_REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO))
from RRann import generate, _RNGEngine as E  # noqa: E402


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------

def harvest_base(seed: float, prec_digits: int = 8) -> tuple[str, float, float]:
    sv = E._normalize_seed(seed)
    digits = E._error_digits(sv, count=prec_digits + 4)
    digits = digits[: prec_digits + 2].ljust(prec_digits + 2, "0")
    base = float("0." + digits)
    out = generate(sv)
    return digits, base, out


def bits_msb(x: float, nbits: int = 32) -> np.ndarray:
    w = int(x * (2**nbits)) & ((1 << nbits) - 1)
    return np.array([(w >> i) & 1 for i in range(nbits - 1, -1, -1)], dtype=np.uint8)


def pack_bits(bits: np.ndarray) -> bytes:
    """Pack MSB-first bit array to bytes (pad last byte with zeros)."""
    n = len(bits)
    pad = (-n) % 8
    if pad:
        bits = np.concatenate([bits, np.zeros(pad, dtype=np.uint8)])
    b = np.packbits(bits)  # packbits is MSB-first in each byte
    return b.tobytes()


def build_streams(n_samples: int, seed0: float = 2.4) -> dict[str, dict]:
    """Return dict name -> {values, bits, digits, bytes}."""
    streams: dict[str, dict] = {}

    def collect(mode: str, chained: bool):
        values = []
        bit_chunks = []
        digit_str = []
        seed = seed0
        for i in range(n_samples):
            if chained:
                s = seed
            else:
                s = seed0 + i * math.pi * 1e-3
            digits, base, out = harvest_base(s)
            v = base if mode == "base" else out
            values.append(v)
            bit_chunks.append(bits_msb(v))
            digit_str.append(digits)
            if chained:
                seed = out * 10.0 if out != 0.0 else 1.6180339887498948
        bits = np.concatenate(bit_chunks)
        vals = np.asarray(values, dtype=np.float64)
        dig = "".join(digit_str)
        return {
            "values": vals,
            "bits": bits,
            "digits": dig,
            "bytes": pack_bits(bits),
            "digit_bytes": dig.encode("ascii"),
        }

    for chained, cname in [(False, "indep"), (True, "chain")]:
        for mode in ("base", "out"):
            name = f"{cname}_{mode}"
            print(f"  generating {name} ({n_samples} samples)...", flush=True)
            t0 = time.perf_counter()
            streams[name] = collect(mode, chained)
            print(f"    done in {time.perf_counter()-t0:.1f}s  "
                  f"bits={len(streams[name]['bits']):,}", flush=True)
    return streams


def iid_control(n_bits: int, rng: np.random.Generator) -> dict:
    bits = rng.integers(0, 2, size=n_bits, dtype=np.uint8)
    # synthetic values from 32-bit chunks
    n = n_bits // 32
    vals = np.zeros(n, dtype=np.float64)
    for i in range(n):
        w = 0
        for b in bits[i * 32 : (i + 1) * 32]:
            w = (w << 1) | int(b)
        vals[i] = w / 2**32
    return {
        "values": vals,
        "bits": bits,
        "digits": "",  # N/A
        "bytes": pack_bits(bits),
        "digit_bytes": b"",
    }


# ---------------------------------------------------------------------------
# Zipf
# ---------------------------------------------------------------------------

def zipf_analysis(tokens: list, title: str, top: int = 30) -> dict:
    """Rank-frequency; fit log f ~ -s log r on top ranks."""
    ctr = collections.Counter(tokens)
    if not ctr:
        return {"title": title, "empty": True}
    ranks = sorted(ctr.values(), reverse=True)
    total = sum(ranks)
    # Fit s on first min(200, n) ranks with count>0
    k = min(200, len(ranks))
    r = np.arange(1, k + 1, dtype=np.float64)
    f = np.asarray(ranks[:k], dtype=np.float64)
    # avoid log0
    mask = f > 0
    log_r = np.log(r[mask])
    log_f = np.log(f[mask])
    if len(log_r) >= 2:
        # least squares slope
        s, intercept = np.polyfit(log_r, log_f, 1)
        s = -s  # Zipf: f ∝ r^{-s}
        # R^2
        pred = intercept - s * log_r
        ss_res = np.sum((log_f - pred) ** 2)
        ss_tot = np.sum((log_f - log_f.mean()) ** 2)
        r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
    else:
        s, r2 = float("nan"), float("nan")

    # normalized entropy of token dist
    h = 0.0
    for c in ranks:
        p = c / total
        h -= p * math.log2(p)
    h_max = math.log2(len(ranks)) if len(ranks) > 1 else 0.0

    return {
        "title": title,
        "empty": False,
        "vocab": len(ranks),
        "total": total,
        "top": [(i + 1, ranks[i], ranks[i] / total) for i in range(min(top, len(ranks)))],
        "zipf_s": s,
        "zipf_r2": r2,
        "H": h,
        "H_max": h_max,
        "H_ratio": h / h_max if h_max else 0.0,
        "head_mass": sum(ranks[:10]) / total if ranks else 0.0,
    }


def print_zipf(z: dict) -> None:
    if z.get("empty"):
        print(f"  [{z['title']}] empty")
        return
    print(f"  [{z['title']}] vocab={z['vocab']:,}  N={z['total']:,}  "
          f"Zipf s≈{z['zipf_s']:.4f} (R²={z['zipf_r2']:.4f})  "
          f"H/Hmax={z['H_ratio']:.4f}  top10_mass={z['head_mass']:.4f}")
    print("    rank  count    frac")
    for rank, cnt, frac in z["top"][:12]:
        bar = "█" * int(frac * 80)
        print(f"    {rank:4d}  {cnt:7d}  {frac:.6f}  {bar}")


# ---------------------------------------------------------------------------
# Compressibility / Kolmogorov proxies
# ---------------------------------------------------------------------------

def compress_ratio(data: bytes) -> dict:
    if not data:
        return {}
    n = len(data)
    # Shannon bit entropy of bytes as upper-ish bound on compression
    ctr = collections.Counter(data)
    h = 0.0
    for c in ctr.values():
        p = c / n
        h -= p * math.log2(p)
    shannon_bound = h / 8.0  # bytes of entropy per byte

    out = {"n": n, "H_byte": h, "shannon_ratio": shannon_bound}
    for name, fn in [
        ("zlib", lambda d: zlib.compress(d, 9)),
        ("bz2", lambda d: bz2.compress(d, 9)),
        ("lzma", lambda d: lzma.compress(d, preset=6)),
        ("gzip", lambda d: gzip.compress(d, compresslevel=9)),
    ]:
        c = fn(data)
        out[name] = len(c)
        out[f"{name}_ratio"] = len(c) / n
    return out


def print_compress(label: str, r: dict) -> None:
    if not r:
        print(f"  [{label}] empty")
        return
    print(f"  [{label}] n={r['n']:,} B  H_byte={r['H_byte']:.4f}/8  "
          f"shannon_floor≈{r['shannon_ratio']:.4f}")
    for name in ("zlib", "bz2", "lzma", "gzip"):
        print(f"    {name:5s}  {r[name]:8d} B  ratio={r[f'{name}_ratio']:.4f}  "
              f"({'incompressible' if r[f'{name}_ratio']>0.98 else 'some structure' if r[f'{name}_ratio']<0.95 else 'near-random'})")


# ---------------------------------------------------------------------------
# N-gram / Markov
# ---------------------------------------------------------------------------

def ngram_counts(bits: np.ndarray, n: int) -> collections.Counter:
    ctr = collections.Counter()
    # pack n-bit windows non-overlapping for clean alphabet, and overlapping for Markov
    x = bits.astype(np.int64)
    for i in range(len(x) - n + 1):
        v = 0
        for j in range(n):
            v = (v << 1) | int(x[i + j])
        ctr[v] += 1
    return ctr


def markov_analysis(bits: np.ndarray, order: int = 1) -> dict:
    """order-k Markov on bits: transition matrix entropy, chi2 vs independent."""
    x = bits.astype(np.int64)
    # state = previous `order` bits as int
    n_states = 1 << order
    trans = np.zeros((n_states, 2), dtype=np.float64)
    for i in range(order, len(x)):
        state = 0
        for j in range(order):
            state = (state << 1) | int(x[i - order + j])
        trans[state, int(x[i])] += 1

    # row-normalize; conditional entropy H(X_t | state)
    h_cond = 0.0
    total = trans.sum()
    state_p = trans.sum(axis=1) / total
    for s in range(n_states):
        row = trans[s]
        rs = row.sum()
        if rs == 0:
            continue
        h_row = 0.0
        for c in row:
            if c > 0:
                p = c / rs
                h_row -= p * math.log2(p)
        h_cond += state_p[s] * h_row

    # marginal H
    ones = float(x.sum())
    n = float(len(x))
    p1 = ones / n
    p0 = 1 - p1
    h_marg = 0.0
    for p in (p0, p1):
        if p > 0:
            h_marg -= p * math.log2(p)

    mutual = h_marg - h_cond  # I(X_t; state) approx info from past

    # chi-square: observed bigrams vs product of margins (order=1 style on consecutive)
    # general: for each state, expect next bit ~ marginal
    chi2 = 0.0
    dof = 0
    for s in range(n_states):
        rs = trans[s].sum()
        if rs < 5:
            continue
        for b in (0, 1):
            expected = rs * (p0 if b == 0 else p1)
            if expected < 1:
                continue
            obs = trans[s, b]
            chi2 += (obs - expected) ** 2 / expected
            dof += 1
    dof = max(0, dof - 1)  # rough

    return {
        "order": order,
        "H_marginal": h_marg,
        "H_cond": h_cond,
        "I_past": mutual,
        "chi2": chi2,
        "dof_approx": dof,
        "trans_01": float(trans[0, 1] / trans[0].sum()) if order == 1 and trans[0].sum() else None,
        "trans_10": float(trans[1, 0] / trans[1].sum()) if order == 1 and trans[1].sum() else None,
        "trans_00": float(trans[0, 0] / trans[0].sum()) if order == 1 and trans[0].sum() else None,
        "trans_11": float(trans[1, 1] / trans[1].sum()) if order == 1 and trans[1].sum() else None,
    }


def ngram_entropy(bits: np.ndarray, n: int) -> tuple[float, float, int]:
    ctr = ngram_counts(bits, n)
    total = sum(ctr.values())
    h = 0.0
    for c in ctr.values():
        p = c / total
        h -= p * math.log2(p)
    return h, h / n, len(ctr)


def print_markov(label: str, bits: np.ndarray) -> None:
    print(f"  [{label}]")
    for n in (1, 2, 3, 4, 8):
        h, hn, vocab = ngram_entropy(bits, n)
        print(f"    {n}-gram H={h:8.4f}/{n}  per-bit={hn:.6f}  seen={vocab}/{1<<n}")
    for order in (1, 2, 4, 8):
        m = markov_analysis(bits, order=order)
        extra = ""
        if order == 1 and m["trans_01"] is not None:
            extra = (f"  P(1|0)={m['trans_01']:.4f} P(0|1)={m['trans_10']:.4f} "
                     f"P(0|0)={m['trans_00']:.4f} P(1|1)={m['trans_11']:.4f}")
        print(f"    Markov order={order}: H(X)={m['H_marginal']:.6f}  "
              f"H(X|past)={m['H_cond']:.6f}  I(X;past)={m['I_past']:.6e}  "
              f"χ²≈{m['chi2']:.2f}{extra}")


# ---------------------------------------------------------------------------
# Autocorrelation
# ---------------------------------------------------------------------------

def autocorr_values(vals: np.ndarray, max_lag: int) -> np.ndarray:
    x = vals - vals.mean()
    var = np.dot(x, x) / len(x)
    if var <= 0:
        return np.zeros(max_lag + 1)
    ac = np.empty(max_lag + 1)
    ac[0] = 1.0
    for lag in range(1, max_lag + 1):
        ac[lag] = np.dot(x[:-lag], x[lag:]) / ((len(x) - lag) * var)
    return ac


def autocorr_bits_fft(bits: np.ndarray, max_lag: int) -> np.ndarray:
    """Autocorr of ±1 mapped bits via FFT (Wiener–Khinchin)."""
    x = bits.astype(np.float64) * 2.0 - 1.0
    x = x - x.mean()
    n = len(x)
    # next pow2
    nfft = 1 << (n * 2 - 1).bit_length()
    fx = np.fft.rfft(x, n=nfft)
    acf = np.fft.irfft(fx * np.conjugate(fx), n=nfft)[:n]
    acf /= acf[0]
    return acf[: max_lag + 1]


def run_lengths(bits: np.ndarray) -> list[int]:
    if len(bits) == 0:
        return []
    runs = []
    cur = int(bits[0])
    length = 1
    for b in bits[1:]:
        b = int(b)
        if b == cur:
            length += 1
        else:
            runs.append(length)
            cur = b
            length = 1
    runs.append(length)
    return runs


def print_autocorr(label: str, vals: np.ndarray, bits: np.ndarray) -> None:
    print(f"  [{label}]")
    # value autocorr
    lags_v = [1, 2, 3, 5, 10, 20, 50, 100]
    max_lv = min(max(lags_v), len(vals) - 2)
    ac_v = autocorr_values(vals, max_lv)
    # 95% white-noise band ≈ 1.96/sqrt(N)
    band = 1.96 / math.sqrt(len(vals))
    print(f"    value ACF  ±1.96/√N band ≈ ±{band:.5f}  N={len(vals)}")
    for lag in lags_v:
        if lag <= max_lv:
            flag = " *" if abs(ac_v[lag]) > band else ""
            print(f"      lag={lag:4d}  r={ac_v[lag]:+.6f}{flag}")

    # bit autocorr (sample of lags including 32 for word boundary)
    max_lb = min(256, len(bits) - 2)
    ac_b = autocorr_bits_fft(bits, max_lb)
    band_b = 1.96 / math.sqrt(len(bits))
    print(f"    bit ACF (±1 map)  band ≈ ±{band_b:.6f}  Nbits={len(bits):,}")
    for lag in [1, 2, 4, 8, 16, 31, 32, 33, 64, 128, 256]:
        if lag <= max_lb:
            flag = " *" if abs(ac_b[lag]) > band_b else ""
            print(f"      lag={lag:4d}  r={ac_b[lag]:+.6f}{flag}")

    # run length stats vs geometric
    runs = run_lengths(bits)
    runs_a = np.asarray(runs, dtype=np.float64)
    p1 = bits.mean()
    # For fair coin, mean run length = 2
    print(f"    runs: count={len(runs):,}  mean_len={runs_a.mean():.4f}  "
          f"max={runs_a.max():.0f}  "
          f"p(bit=1)={p1:.4f}  (fair mean run len≈2)")
    # histogram first 16
    hist = collections.Counter(int(x) for x in runs)
    print("    run-len hist (len:count):",
          " ".join(f"{k}:{hist[k]}" for k in range(1, 17) if hist[k]))


# ---------------------------------------------------------------------------
# Digit-level Zipf / n-gram extras
# ---------------------------------------------------------------------------

def analyze_digits(label: str, dig: str) -> None:
    if not dig:
        print(f"  [{label}] no digits")
        return
    print(f"  [{label}] n_digits={len(dig):,}")
    z1 = zipf_analysis(list(dig), "digit unigrams", top=10)
    print_zipf(z1)
    digraphs = [dig[i : i + 2] for i in range(len(dig) - 1)]
    z2 = zipf_analysis(digraphs, "digit digraphs", top=10)
    print_zipf(z2)
    # 4-gram
    g4 = [dig[i : i + 4] for i in range(0, len(dig) - 3)]
    z4 = zipf_analysis(g4, "digit 4-grams", top=8)
    print_zipf(z4)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description="RRann structure analysis suite")
    ap.add_argument("-n", "--samples", type=int, default=20_000,
                    help="samples per stream (default 20000)")
    ap.add_argument("--seed", type=float, default=2.4)
    ap.add_argument("-o", "--output", type=str, default="",
                    help="optional path to write full text report")
    args = ap.parse_args()

    buf = io.StringIO()

    class Tee:
        def write(self, s):
            sys.__stdout__.write(s)
            buf.write(s)
        def flush(self):
            sys.__stdout__.flush()

    sys.stdout = Tee()  # type: ignore

    print("=" * 72)
    print("RRann structure suite: Zipf | Compressibility | N-gram/Markov | ACF")
    print(f"samples/stream = {args.samples}  seed0 = {args.seed}")
    print("=" * 72)

    print("\n[0] Building streams")
    streams = build_streams(args.samples, args.seed)
    n_bits = len(next(iter(streams.values()))["bits"])
    rng = np.random.default_rng(0)
    streams["iid_control"] = iid_control(n_bits, rng)
    print(f"  + iid_control ({n_bits:,} bits)")

    # ---- Zipf ----
    print("\n" + "=" * 72)
    print("[1] ZIPF'S LAW (rank–frequency)")
    print("=" * 72)
    for name, st in streams.items():
        print(f"\n-- {name} --")
        # byte tokens
        z_b = zipf_analysis(list(st["bytes"]), "packed-bit bytes", top=10)
        print_zipf(z_b)
        # 8-bit non-overlapping from bit stream
        bits = st["bits"]
        bytes_from_bits = []
        for i in range(len(bits) // 8):
            v = 0
            for j in range(8):
                v = (v << 1) | int(bits[i * 8 + j])
            bytes_from_bits.append(v)
        z8 = zipf_analysis(bytes_from_bits, "bit-stream as bytes", top=10)
        print_zipf(z8)
        # 4-bit nibbles
        nib = []
        for i in range(len(bits) // 4):
            v = 0
            for j in range(4):
                v = (v << 1) | int(bits[i * 4 + j])
            nib.append(v)
        zn = zipf_analysis(nib, "nibbles (4-bit)", top=10)
        print_zipf(zn)
        # run lengths as "words"
        runs = run_lengths(bits)
        zr = zipf_analysis(runs, "run lengths as tokens", top=15)
        print_zipf(zr)
        if st["digits"]:
            analyze_digits(name + " digits", st["digits"])

    # ---- Compressibility ----
    print("\n" + "=" * 72)
    print("[2] KOLMOGOROV / COMPRESSIBILITY PROXIES")
    print("    (ratio→1 => incompressible ≈ high complexity; <<1 => structure)")
    print("=" * 72)
    for name, st in streams.items():
        print(f"\n-- {name} --")
        print_compress("packed bits", compress_ratio(st["bytes"]))
        if st["digit_bytes"]:
            print_compress("ASCII digits", compress_ratio(st["digit_bytes"]))
        # also values as float64 raw
        raw = st["values"].astype("<f8").tobytes()
        print_compress("float64 values", compress_ratio(raw))

    # ---- N-gram / Markov ----
    print("\n" + "=" * 72)
    print("[3] N-GRAM & MARKOV CHAIN ANALYSIS")
    print("=" * 72)
    for name, st in streams.items():
        print(f"\n-- {name} --")
        print_markov(name, st["bits"])

    # ---- Autocorrelation ----
    print("\n" + "=" * 72)
    print("[4] AUTOCORRELATION ANALYSIS")
    print("    (*) marks |r| above white-noise 95% band")
    print("=" * 72)
    for name, st in streams.items():
        print(f"\n-- {name} --")
        print_autocorr(name, st["values"], st["bits"])

    # ---- Summary board ----
    print("\n" + "=" * 72)
    print("[5] ONE-LINE SCOREBOARD")
    print("=" * 72)
    print(f"{'stream':<14} {'zlib':>8} {'I(X;past1)':>12} {'ACF_v(1)':>10} "
          f"{'ACF_b(1)':>10} {'ACF_b(32)':>10} {'mean_run':>10}")
    for name, st in streams.items():
        cr = compress_ratio(st["bytes"])
        m = markov_analysis(st["bits"], 1)
        ac_v = autocorr_values(st["values"], 1)
        ac_b = autocorr_bits_fft(st["bits"], 32)
        runs = run_lengths(st["bits"])
        mean_run = float(np.mean(runs)) if runs else 0.0
        print(f"{name:<14} {cr.get('zlib_ratio',0):8.4f} {m['I_past']:12.3e} "
              f"{ac_v[1]:10.5f} {ac_b[1]:10.5f} {ac_b[32]:10.5f} {mean_run:10.4f}")

    print("\nDone.")
    sys.stdout = sys.__stdout__
    if args.output:
        Path(args.output).write_text(buf.getvalue(), encoding="utf-8")
        print(f"Wrote report → {args.output}")


if __name__ == "__main__":
    main()
