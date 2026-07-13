//! Residual harvest (OPEN_SEQUENCE step 1 / execution order 3rd).
//!
//! - **native-harvest** (default): MPFR via `rug` — matches CPython residual on tested seeds.
//! - **soft-harvest** (wasm): `rust_decimal` ln/exp — approximate; demos only.

pub const DEFAULT_CULL_HEAD: usize = 2;
pub const DEFAULT_DIGIT_COUNT: usize = 12;

#[derive(Debug, Clone)]
pub struct HarvestResult {
    pub seed: f64,
    pub digits: String,
    pub divergence_index: Option<usize>,
    pub used_fallback: bool,
}

impl HarvestResult {
    pub fn head(&self) -> &str {
        let n = self.digits.len().min(2);
        &self.digits[..n]
    }

    pub fn remainder(&self, cull_head: usize) -> &str {
        if cull_head >= self.digits.len() {
            return "";
        }
        &self.digits[cull_head..]
    }
}

fn normalize_seed(seed: f64) -> f64 {
    if seed.is_finite() && seed > 0.0 {
        seed
    } else if seed.is_finite() && seed < 0.0 {
        let a = seed.abs();
        if a > 0.0 {
            a
        } else {
            0.123456789
        }
    } else {
        0.123456789
    }
}

fn significant_digits_from_float_str(s: &str, count: usize) -> String {
    let mut digits: String = s.chars().filter(|c| c.is_ascii_digit()).collect();
    let first = digits.find(|c| c != '0').unwrap_or(0);
    if first > 0 {
        digits = digits[first..].to_string();
    }
    if digits.is_empty() {
        return "0".repeat(count);
    }
    if digits.len() >= count {
        digits[..count].to_string()
    } else {
        format!("{:0<width$}", digits, width = count)
    }
}

fn float64_digit_string(x: f64, count: usize) -> String {
    let s = format!("{:.50}", x.abs());
    significant_digits_from_float_str(&s, count)
}

/// Match Python `_fallback_digits`: SHA-256 of `f"{seed:.18g}"`, then decimal digits of the int.
fn fallback_digits(seed: f64, count: usize) -> String {
    use sha2::{Digest, Sha256};
    let msg = python_g18(seed);
    let hash = Sha256::digest(msg.as_bytes());
    let hex: String = hash.iter().map(|b| format!("{b:02x}")).collect();
    hex_digest_to_decimal_digits(&hex, count)
}

/// Approximate Python 3 `format(x, '.18g')` for positive game seeds.
fn python_g18(seed: f64) -> String {
    if !seed.is_finite() {
        return format!("{seed}");
    }
    // Integers in a safe range: Python prints without trailing `.0` ("2", "10").
    if seed.fract() == 0.0 && seed.abs() < 1e15 {
        return format!("{}", seed as i64);
    }
    // 18 significant digits, fixed form when magnitude is moderate (matches common seeds).
    let ax = seed.abs();
    if ax >= 1e-4 && ax < 1e16 {
        // Trim like Python g: no trailing zeros, no trailing dot.
        let mut s = format!("{seed:.17}");
        if let Some(dot) = s.find('.') {
            while s.ends_with('0') && s.len() > dot + 1 {
                s.pop();
            }
            if s.ends_with('.') {
                s.pop();
            }
        }
        return s;
    }
    format!("{seed:.17e}")
}

fn hex_digest_to_decimal_digits(hex: &str, count: usize) -> String {
    // Convert full SHA-256 hex to decimal string without external bigint crate.
    // Process nibble-by-nibble into a base-10 digit vector.
    let mut dec: Vec<u8> = vec![0]; // little-endian digits
    for ch in hex.chars() {
        let v = ch.to_digit(16).unwrap_or(0) as u8;
        // dec = dec * 16 + v
        let mut carry = v as u32;
        for d in dec.iter_mut() {
            let t = (*d as u32) * 16 + carry;
            *d = (t % 10) as u8;
            carry = t / 10;
        }
        while carry > 0 {
            dec.push((carry % 10) as u8);
            carry /= 10;
        }
    }
    // big-endian decimal string
    let mut s: String = dec.iter().rev().map(|d| char::from(b'0' + d)).collect();
    if s.is_empty() {
        s.push('0');
    }
    while s.len() < count {
        s.push('0');
    }
    s[..count].to_string()
}

#[cfg(feature = "native-harvest")]
fn high_digit_string(seed: f64, count: usize) -> Option<String> {
    use rug::{ops::PowAssign, Float};
    const HIGH_PREC_BITS: u32 = 640;
    if !(seed.is_finite() && seed > 0.0) {
        return None;
    }
    let x = Float::with_val(HIGH_PREC_BITS, seed);
    let mut y = x.clone();
    y.pow_assign(&x);
    if !y.is_finite() {
        return None;
    }
    let s = format!("{y:.prec$}", prec = count + 48);
    Some(significant_digits_from_float_str(&s, count))
}

#[cfg(all(feature = "soft-harvest", not(feature = "native-harvest")))]
fn high_digit_string(seed: f64, count: usize) -> Option<String> {
    use rust_decimal::MathematicalOps;
    use rust_decimal::Decimal;
    use std::str::FromStr;
    if !(seed.is_finite() && seed > 0.0) {
        return None;
    }
    let d_seed = Decimal::from_str(&format!("{:.17}", seed)).ok()?;
    if d_seed <= Decimal::ZERO {
        return None;
    }
    let d_result = (d_seed.ln() * d_seed).exp();
    let s = d_result.abs().normalize().to_string();
    Some(significant_digits_from_float_str(&s, count))
}

#[cfg(not(any(feature = "native-harvest", feature = "soft-harvest")))]
fn high_digit_string(_seed: f64, _count: usize) -> Option<String> {
    None
}

/// Dual-precision residual harvest.
pub fn harvest(seed: f64, count: usize) -> HarvestResult {
    let seed = normalize_seed(seed);
    let float_result = seed.powf(seed);
    if !float_result.is_finite() {
        return HarvestResult {
            seed,
            digits: fallback_digits(seed, count),
            divergence_index: None,
            used_fallback: true,
        };
    }

    let Some(hd) = high_digit_string(seed, count + 32) else {
        return HarvestResult {
            seed,
            digits: fallback_digits(seed, count),
            divergence_index: None,
            used_fallback: true,
        };
    };

    let fd = float64_digit_string(float_result, count + 32);

    let mut divergence_index = None;
    for i in 0..fd.len().min(hd.len()) {
        if fd.as_bytes()[i] != hd.as_bytes()[i] {
            divergence_index = Some(i);
            break;
        }
    }

    let (digits, used_fallback) = match divergence_index {
        None => (fallback_digits(seed, count), true),
        Some(i) => {
            let end = (i + count).min(hd.len());
            let mut slice = hd[i..end].to_string();
            if slice.len() < count || slice.chars().all(|c| c == '0') {
                (fallback_digits(seed, count), true)
            } else {
                while slice.len() < count {
                    slice.push('0');
                }
                (slice[..count].to_string(), false)
            }
        }
    };

    HarvestResult {
        seed,
        digits,
        divergence_index,
        used_fallback,
    }
}

pub fn extract_float(seed: f64, cull_head: usize) -> f64 {
    let h = harvest(seed, DEFAULT_DIGIT_COUNT);
    let mut body = h.remainder(cull_head).to_string();
    if body.is_empty() {
        body = h.digits.clone();
    }
    while body.len() < 16 {
        body.push('0');
    }
    let s = format!("0.{}", &body[..16]);
    s.parse::<f64>()
        .unwrap_or(0.5)
        .clamp(0.0, 0.9999999999999999)
}

pub fn extract_bits(seed: f64, nbits: usize, cull_head: usize) -> Vec<u8> {
    if nbits == 0 {
        return vec![];
    }
    // Match Python extract_bits: harvest DEFAULT_DIGIT_COUNT (12) residual digits.
    let h = harvest(seed, DEFAULT_DIGIT_COUNT);
    let mut body = h.remainder(cull_head).to_string();
    if body.is_empty() {
        body = h.digits.clone();
    }
    // floor(int(body) / 10^len(body) * 2^nbits) — use u128 for ≤38-digit bodies.
    let num: u128 = body.parse().unwrap_or(0);
    let den = 10u128.pow(body.len().min(38) as u32);
    let nb = nbits.min(64);
    let word = if den == 0 {
        0u128
    } else {
        // (num << nb) / den  — shift carefully if num is large
        if num.leading_zeros() as usize >= nb {
            (num << nb) / den
        } else {
            // num * 2^nb / den without overflowing intermediate when possible
            ((num as u128) * (1u128 << nb)) / den
        }
    };
    let mut bits = Vec::with_capacity(nbits);
    for i in 0..nbits {
        let shift = nbits - 1 - i;
        bits.push(((word >> shift) & 1) as u8);
    }
    bits
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use std::path::PathBuf;

    #[test]
    fn harvest_produces_digits() {
        let h = harvest(2.4, 12);
        assert_eq!(h.digits.len(), 12);
        assert!(h.digits.chars().all(|c| c.is_ascii_digit()));
    }

    #[test]
    fn extract_float_in_unit_interval() {
        let x = extract_float(2.4, 2);
        assert!(x >= 0.0 && x < 1.0);
        assert_eq!(extract_float(2.4, 2), extract_float(2.4, 2));
    }

    #[test]
    fn extract_bits_len() {
        let b = extract_bits(2.4, 32, 2);
        assert_eq!(b.len(), 32);
        assert!(b.iter().all(|&x| x <= 1));
    }

    #[cfg(feature = "native-harvest")]
    #[test]
    fn harvest_matches_python_2_4() {
        let h = harvest(2.4, 12);
        assert_eq!(h.digits, "525744833867");
        assert_eq!(h.divergence_index, Some(16));
        assert!((extract_float(2.4, 2) - 0.5744833867).abs() < 1e-12);
    }

    #[cfg(feature = "native-harvest")]
    #[test]
    fn harvest_matches_vectors_json() {
        let mut path = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
        path.push("../../tests/vectors.json");
        let data = fs::read_to_string(&path).expect("tests/vectors.json");
        let v: serde_json::Value = serde_json::from_str(&data).unwrap();
        let mut n = 0;
        for c in v["cases"].as_array().unwrap() {
            let seed = c["seed"].as_f64().unwrap();
            let want_digits = c["digits"].as_str().unwrap();
            let want_div = c["divergence_index"].as_i64();
            let want_fb = c["used_fallback"].as_bool().unwrap();
            let want_f = c["extract_float_cull2"].as_f64().unwrap();
            let h = harvest(seed, 12);
            assert_eq!(h.digits, want_digits, "digits seed={seed}");
            assert_eq!(h.used_fallback, want_fb, "fallback seed={seed}");
            match want_div {
                Some(i) if i >= 0 => assert_eq!(h.divergence_index, Some(i as usize), "div seed={seed}"),
                _ => assert_eq!(h.divergence_index, None, "div seed={seed}"),
            }
            let got_f = extract_float(seed, 2);
            assert!(
                (got_f - want_f).abs() < 1e-12,
                "float seed={seed} got={got_f} want={want_f}"
            );
            if let Some(bits) = c["extract_bits32_cull2"].as_array() {
                let got_bits = extract_bits(seed, 32, 2);
                let want_bits: Vec<u8> = bits
                    .iter()
                    .map(|b| b.as_u64().unwrap() as u8)
                    .collect();
                assert_eq!(got_bits, want_bits, "bits seed={seed}");
            }
            n += 1;
        }
        assert!(n >= 20, "expected ≥20 vectors, got {n}");
    }

    #[test]
    fn fallback_digits_match_python_style() {
        // Integer seeds that take SHA fallback in residual harvest
        let d = fallback_digits(2.0, 12);
        assert_eq!(d.len(), 12);
        assert!(d.chars().all(|c| c.is_ascii_digit()));
    }
}
