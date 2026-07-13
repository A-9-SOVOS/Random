//! C ABI for engines (Unity/Godot/native plugins).

use std::ffi::{CStr, CString};
use std::os::raw::{c_char, c_double, c_longlong};

use crate::harvest::{extract_bits, extract_float, harvest, DEFAULT_CULL_HEAD};
use crate::{commit_seed, demo_u64, splitmix64, stream_seed_i64, verify_commit};

/// Independent stream seed in (0.5, 10).
#[no_mangle]
pub extern "C" fn rrann_stream_seed(master: c_double, stream_id: c_longlong) -> c_double {
    stream_seed_i64(master as f64, stream_id as i64) as c_double
}

/// splitmix64 mixer.
#[no_mangle]
pub extern "C" fn rrann_splitmix64(x: u64) -> u64 {
    splitmix64(x)
}

/// Demo u64 from master + stream + counter (scatter / not harvest).
#[no_mangle]
pub extern "C" fn rrann_demo_u64(master: c_double, stream_id: c_longlong, n: u64) -> u64 {
    demo_u64(master as f64, stream_id as i64, n)
}

/// Write SHA-256 hex commit into *out* (must be ≥65 bytes including NUL).
/// Returns 0 on success, -1 on error.
#[no_mangle]
pub unsafe extern "C" fn rrann_commit_seed(
    seed: c_double,
    game_id: *const c_char,
    season: *const c_char,
    out: *mut c_char,
    out_len: usize,
) -> i32 {
    if out.is_null() || out_len < 65 {
        return -1;
    }
    let gid = if game_id.is_null() {
        ""
    } else {
        match CStr::from_ptr(game_id).to_str() {
            Ok(s) => s,
            Err(_) => return -1,
        }
    };
    let sea = if season.is_null() {
        ""
    } else {
        match CStr::from_ptr(season).to_str() {
            Ok(s) => s,
            Err(_) => return -1,
        }
    };
    let hex = commit_seed(seed as f64, gid, sea);
    let c = match CString::new(hex) {
        Ok(c) => c,
        Err(_) => return -1,
    };
    let bytes = c.as_bytes_with_nul();
    if bytes.len() > out_len {
        return -1;
    }
    std::ptr::copy_nonoverlapping(bytes.as_ptr(), out as *mut u8, bytes.len());
    0
}

/// Returns 1 if commit matches, 0 otherwise, -1 on error.
#[no_mangle]
pub unsafe extern "C" fn rrann_verify_commit(
    commit: *const c_char,
    seed: c_double,
    game_id: *const c_char,
    season: *const c_char,
) -> i32 {
    if commit.is_null() {
        return -1;
    }
    let cstr = match CStr::from_ptr(commit).to_str() {
        Ok(s) => s,
        Err(_) => return -1,
    };
    let gid = if game_id.is_null() {
        ""
    } else {
        match CStr::from_ptr(game_id).to_str() {
            Ok(s) => s,
            Err(_) => return -1,
        }
    };
    let sea = if season.is_null() {
        ""
    } else {
        match CStr::from_ptr(season).to_str() {
            Ok(s) => s,
            Err(_) => return -1,
        }
    };
    if verify_commit(cstr, seed as f64, gid, sea) {
        1
    } else {
        0
    }
}

/// Culled residual float in [0, 1). `cull_head < 0` → default (2).
#[no_mangle]
pub extern "C" fn rrann_extract_float(seed: c_double, cull_head: i32) -> c_double {
    let cull = if cull_head < 0 {
        DEFAULT_CULL_HEAD
    } else {
        cull_head as usize
    };
    extract_float(seed as f64, cull) as c_double
}

/// Pack up to 64 culled residual bits into a u64 (MSB-first in the high bits of the word).
/// Returns 0 on nbits==0; nbits is clamped to 1..64.
#[no_mangle]
pub extern "C" fn rrann_extract_u64(seed: c_double, nbits: u32, cull_head: i32) -> u64 {
    let cull = if cull_head < 0 {
        DEFAULT_CULL_HEAD
    } else {
        cull_head as usize
    };
    let n = nbits.clamp(0, 64) as usize;
    if n == 0 {
        return 0;
    }
    let bits = extract_bits(seed as f64, n, cull);
    let mut v: u64 = 0;
    for b in bits {
        v = (v << 1) | (b as u64);
    }
    v
}

/// Write residual digit string (NUL-terminated) into *out*.
/// Returns digit count on success, -1 on error. out_len must be > count.
#[no_mangle]
pub unsafe extern "C" fn rrann_harvest_digits(
    seed: c_double,
    count: u32,
    out: *mut c_char,
    out_len: usize,
) -> i32 {
    if out.is_null() || out_len == 0 {
        return -1;
    }
    let n = if count == 0 { 12 } else { count as usize };
    let h = harvest(seed as f64, n);
    let c = match CString::new(h.digits) {
        Ok(c) => c,
        Err(_) => return -1,
    };
    let bytes = c.as_bytes_with_nul();
    if bytes.len() > out_len {
        return -1;
    }
    std::ptr::copy_nonoverlapping(bytes.as_ptr(), out as *mut u8, bytes.len());
    (bytes.len() - 1) as i32
}

/// Divergence index, or -1 if fallback / none.
#[no_mangle]
pub extern "C" fn rrann_divergence_index(seed: c_double) -> i32 {
    let h = harvest(seed as f64, 12);
    match h.divergence_index {
        Some(i) => i as i32,
        None => -1,
    }
}
