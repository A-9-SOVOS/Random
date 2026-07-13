//! WASM bindings for browser / three.js.

use wasm_bindgen::prelude::*;

use crate::harvest::{extract_bits, extract_float, harvest, DEFAULT_CULL_HEAD};
use crate::{commit_seed, demo_u64, splitmix64, stream_seed_i64, verify_commit};

#[wasm_bindgen]
pub fn wasm_stream_seed(master: f64, stream_id: i32) -> f64 {
    stream_seed_i64(master, stream_id as i64)
}

#[wasm_bindgen]
pub fn wasm_commit_seed(seed: f64, game_id: &str, season: &str) -> String {
    commit_seed(seed, game_id, season)
}

#[wasm_bindgen]
pub fn wasm_verify_commit(commit: &str, seed: f64, game_id: &str, season: &str) -> bool {
    verify_commit(commit, seed, game_id, season)
}

#[wasm_bindgen]
pub fn wasm_splitmix64(x: f64) -> f64 {
    // JS loses u64 precision; pass as f64 bit pattern via trunc
    let u = x as u64;
    splitmix64(u) as f64
}

/// Deterministic [0,1) float for scatter demos from master+stream+n.
#[wasm_bindgen]
pub fn wasm_demo_unit(master: f64, stream_id: i32, n: u32) -> f64 {
    let u = demo_u64(master, stream_id as i64, n as u64);
    (u as f64) / (u64::MAX as f64)
}

/// Culled residual float (Rust harvest prototype; not CPython-bit-identical).
#[wasm_bindgen]
pub fn wasm_extract_float(seed: f64, cull_head: i32) -> f64 {
    let cull = if cull_head < 0 {
        DEFAULT_CULL_HEAD
    } else {
        cull_head as usize
    };
    extract_float(seed, cull)
}

/// Up to 32 residual bits as a JS number (integer 0..2^n-1).
#[wasm_bindgen]
pub fn wasm_extract_bits_u32(seed: f64, nbits: u32, cull_head: i32) -> u32 {
    let cull = if cull_head < 0 {
        DEFAULT_CULL_HEAD
    } else {
        cull_head as usize
    };
    let n = nbits.clamp(0, 32) as usize;
    if n == 0 {
        return 0;
    }
    let bits = extract_bits(seed, n, cull);
    let mut v: u32 = 0;
    for b in bits {
        v = (v << 1) | (b as u32);
    }
    v
}

/// Residual digit string from harvest (for debug / demos).
#[wasm_bindgen]
pub fn wasm_harvest_digits(seed: f64, count: u32) -> String {
    let n = if count == 0 { 12 } else { count as usize };
    harvest(seed, n).digits
}

#[wasm_bindgen]
pub fn wasm_divergence_index(seed: f64) -> i32 {
    match harvest(seed, 12).divergence_index {
        Some(i) => i as i32,
        None => -1,
    }
}
