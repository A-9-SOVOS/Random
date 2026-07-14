//! Licensed under the Arc-9 Open Royalty Agreement v1.4. See LICENSE in the repository root.
//!
//! RRann core (Rust) — portable helpers, residual harvest, C ABI, optional WASM.
//!
//! Native build: MPFR harvest (exact vs Python vectors). WASM: soft-harvest demo.

mod c_api;
pub mod harvest;

#[cfg(feature = "wasm")]
mod wasm_api;

pub use harvest::{
    extract_bits as harvest_extract_bits, extract_float as harvest_extract_float, harvest,
    HarvestResult, DEFAULT_CULL_HEAD, DEFAULT_DIGIT_COUNT,
};

/// Mix master seed + integer stream id into (0.5, 10) — mirrors Python `stream_seed`.
pub fn stream_seed_i64(master: f64, stream_id: i64) -> f64 {
    let master = if master.is_finite() && master > 0.0 {
        master
    } else {
        0.123456789
    };
    let tag = stream_id as u64;
    let x = master
        + ((tag % 1_000_003) as f64) * std::f64::consts::PI
        + (((tag >> 20) % 997) as f64) * 0.6180339887498949;
    let mut y = (x * 12.9898).sin().abs() * 43758.5453;
    y %= 1.0;
    if y < 0.0 {
        y += 1.0;
    }
    0.5 + y * 9.5
}

/// Approximate Python `float.__repr__` for common seeds.
pub fn python_float_repr(x: f64) -> String {
    let mut s = format!("{x}");
    if s == "inf" || s == "-inf" || s == "NaN" {
        return s;
    }
    if !s.contains('.') && !s.contains('e') && !s.contains('E') {
        s.push_str(".0");
    }
    s
}

/// SHA-256 hex commit matching Python `commit_seed` (empty extra).
pub fn commit_seed(seed: f64, game_id: &str, season: &str) -> String {
    use sha2::{Digest, Sha256};
    let mut payload = Vec::new();
    payload.extend_from_slice(b"rrann-commit-v1\0");
    payload.extend_from_slice(python_float_repr(seed).as_bytes());
    payload.push(0);
    payload.extend_from_slice(game_id.as_bytes());
    payload.push(0);
    payload.extend_from_slice(season.as_bytes());
    payload.push(0);
    let hash = Sha256::digest(&payload);
    hash.iter().map(|b| format!("{b:02x}")).collect()
}

pub fn verify_commit(commit: &str, seed: f64, game_id: &str, season: &str) -> bool {
    commit_seed(seed, game_id, season).eq_ignore_ascii_case(commit.trim())
}

/// Optional light mixer (splitmix64 finalizer) — not residual entropy.
pub fn splitmix64(mut x: u64) -> u64 {
    x = x.wrapping_add(0x9E3779B97F4A7C15);
    let mut z = x;
    z = (z ^ (z >> 30)).wrapping_mul(0xBF58476D1CE4E5B9);
    z = (z ^ (z >> 27)).wrapping_mul(0x94D049BB133111EB);
    z ^ (z >> 31)
}

/// Simple LCG-ish u64 from stream seed float for demo scatter (not harvest).
pub fn demo_u64(master: f64, stream_id: i64, n: u64) -> u64 {
    let s = stream_seed_i64(master, stream_id);
    let bits = s.to_bits();
    splitmix64(bits.wrapping_add(n.wrapping_mul(0x9E3779B97F4A7C15)))
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use std::path::PathBuf;

    #[test]
    fn stream_seed_differs_by_id() {
        let a = stream_seed_i64(2.4, 0);
        let b = stream_seed_i64(2.4, 1);
        assert!(a > 0.5 && a < 10.0);
        assert_ne!(a, b);
    }

    #[test]
    fn stream_seed_matches_python_vectors() {
        let a = stream_seed_i64(2.4, 0);
        let b = stream_seed_i64(2.4, 1);
        assert!((a - 8.098338869696818).abs() < 1e-12, "a={a}");
        assert!((b - 1.4671550965867937).abs() < 1e-12, "b={b}");
    }

    #[test]
    fn commit_matches_python_file_if_present() {
        let mut path = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
        path.push("../../tests/vectors_commit.json");
        let Ok(data) = fs::read_to_string(&path) else {
            return;
        };
        let v: serde_json::Value = serde_json::from_str(&data).unwrap();
        for c in v["cases"].as_array().unwrap() {
            let seed = c["seed"].as_f64().unwrap();
            let game_id = c["game_id"].as_str().unwrap();
            let season = c["season"].as_str().unwrap();
            let want = c["commit"].as_str().unwrap();
            let got = commit_seed(seed, game_id, season);
            assert_eq!(got, want, "seed={seed}");
            let ss0 = c["stream_seed_0"].as_f64().unwrap();
            assert!((stream_seed_i64(seed, 0) - ss0).abs() < 1e-12);
        }
    }

    #[test]
    fn commit_roundtrip() {
        let c = commit_seed(2.4, "demo", "s1");
        assert_eq!(c.len(), 64);
        assert!(verify_commit(&c, 2.4, "demo", "s1"));
        assert!(!verify_commit(&c, 2.4, "other", "s1"));
    }
}
