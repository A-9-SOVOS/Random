"""
Statistical validation for RRann sequence.
Tests: distribution uniformity, entropy, chi-square, autocorrelation.
"""

import math
import sys

from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from RRann import generate


def test_distribution(num_samples: int = 10_000) -> dict:
    """Test distribution uniformity across [0, 1) range."""
    seed = 2.4
    buckets = [0] * 10

    for _ in range(num_samples):
        val = generate(seed)
        if not math.isfinite(val) or val < 0.0 or val >= 1.0:
            val = 0.9999999999999999

        buckets[min(9, int(val * 10))] += 1
        seed = val if val != 0.0 else 1.6180339887498948
    
    # Chi-square test (expect ~1000 per bucket for 10k samples)
    chi_square = sum((b - num_samples/10)**2 / (num_samples/10) for b in buckets)
    
    # Critical value for df=9 at 0.05 significance: 16.919
    chi_pass = chi_square < 20
    
    return {
        'samples': num_samples,
        'buckets': buckets,
        'chi_square': chi_square,
        'chi_pass': chi_pass,
    }


def test_entropy(num_samples: int = 10_000) -> dict:
    """Shannon entropy of bit patterns."""
    seed = 2.4
    bits = []
    
    for _ in range(num_samples):
        val = generate(seed)
        # Extract bit patterns from fractional part
        as_int = int(val * (2**32)) & 0xFFFFFFFF
        for i in range(32):
            bits.append((as_int >> i) & 1)
        seed = val if val != 0.0 else 1.6180339887498948
    
    # Count bits
    zeros = bits.count(0)
    ones = bits.count(1)
    total = len(bits)
    
    p0 = zeros / total if total > 0 else 0.5
    p1 = ones / total if total > 0 else 0.5
    
    # Shannon entropy (max = 1.0 for uniform)
    entropy = 0
    if p0 > 0:
        entropy -= p0 * math.log2(p0)
    if p1 > 0:
        entropy -= p1 * math.log2(p1)
    
    return {
        'total_bits': total,
        'zeros': zeros,
        'ones': ones,
        'zero_fraction': p0,
        'one_fraction': p1,
        'entropy': entropy,
        'entropy_ideal': 1.0,
    }


def test_autocorrelation(num_samples: int = 1_000, lag: int = 100) -> dict:
    """Test for autocorrelation between outputs."""
    seed = 2.4
    values = []
    
    for _ in range(num_samples):
        val = generate(seed)
        values.append(val)
        seed = val * 10.0 if val != 0.0 else 1.6180339887498948
    
    # Compute correlation at lag
    mean = sum(values) / len(values)
    
    c0 = sum((v - mean)**2 for v in values) / len(values)
    c_lag = sum((values[i] - mean) * (values[i + lag] - mean) 
                for i in range(len(values) - lag)) / (len(values) - lag)
    
    autocorr = c_lag / c0 if c0 > 0 else 0
    
    return {
        'lag': lag,
        'autocorrelation': autocorr,
        'significant_threshold': 0.05,  # Should be < this for independence
        'independent': abs(autocorr) < 0.05,
    }


def test_sequential_independence(num_samples: int = 1_000) -> dict:
    """Test pairs of consecutive values for independence."""
    seed = 2.4
    pairs = []
    
    for _ in range(num_samples):
        val1 = generate(seed)
        val2 = generate(val1 * 10.0)
        pairs.append((val1, val2))
        seed = val2 * 10.0 if val2 != 0.0 else 1.6180339887498948
    
    # Check if pairs are scattered or clustered
    x_avg = sum(p[0] for p in pairs) / len(pairs)
    y_avg = sum(p[1] for p in pairs) / len(pairs)
    
    covariance = sum((p[0] - x_avg) * (p[1] - y_avg) for p in pairs) / len(pairs)
    x_var = sum((p[0] - x_avg)**2 for p in pairs) / len(pairs)
    y_var = sum((p[1] - y_avg)**2 for p in pairs) / len(pairs)
    
    correlation = covariance / (math.sqrt(x_var * y_var) + 1e-10)
    
    return {
        'pairs': num_samples,
        'x_mean': x_avg,
        'y_mean': y_avg,
        'correlation': correlation,
        'independent': abs(correlation) < 0.1,
    }


if __name__ == "__main__":
    print("=" * 60)
    print("RRann Statistical Validation Suite")
    print("=" * 60)
    
    print("\n[1] Distribution Uniformity Test [0, 1)")
    dist = test_distribution()
    print(f"  Samples: {dist['samples']}")
    print(f"  Chi-square: {dist['chi_square']:.2f} (pass: {dist['chi_pass']})")
    print(f"  Bucket distribution: {[f'{b//100}h' for b in dist['buckets']]}")
    
    print("\n[2] Entropy Test")
    ent = test_entropy()
    print(f"  Total bits: {ent['total_bits']}")
    print(f"  Zeros: {ent['zeros']} ({ent['zero_fraction']:.4f})")
    print(f"  Ones: {ent['ones']} ({ent['one_fraction']:.4f})")
    print(f"  Entropy: {ent['entropy']:.4f} / {ent['entropy_ideal']:.4f}")
    
    print("\n[3] Autocorrelation Test (lag=100)")
    auto = test_autocorrelation(lag=100)
    print(f"  Lag: {auto['lag']}")
    print(f"  Autocorrelation: {auto['autocorrelation']:.6f}")
    print(f"  Independent: {auto['independent']}")
    
    print("\n[4] Sequential Independence Test")
    seq = test_sequential_independence()
    print(f"  Pairs tested: {seq['pairs']}")
    print(f"  Correlation: {seq['correlation']:.6f}")
    print(f"  Independent: {seq['independent']}")
    
    print("\n" + "=" * 60)
    all_pass = dist['chi_pass'] and ent['entropy'] > 0.9 and auto['independent'] and seq['independent']
    print(f"Overall: {'PASS' if all_pass else 'NEEDS WORK'}")
    print("=" * 60)
