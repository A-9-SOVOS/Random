/**
 * Thin JS façade over WASM (preferred) with pure-JS fallback for commit/stream.
 * Full residual harvest still Python until OPEN_SEQUENCE step 1 (3rd).
 */

let wasm = null;

export async function init(wasmModuleUrl) {
  if (wasm) return wasm;
  try {
    // Built by: npm run build:wasm
    const mod = await import("../pkg/rrann_core.js");
    await mod.default(wasmModuleUrl);
    wasm = mod;
    return wasm;
  } catch (e) {
    console.warn("rrann WASM not loaded; using JS fallback for commit/stream", e);
    wasm = null;
    return null;
  }
}

export function streamSeed(master, streamId) {
  if (wasm?.wasm_stream_seed) return wasm.wasm_stream_seed(master, streamId);
  return streamSeedJs(master, streamId);
}

export function commitSeed(seed, gameId = "", season = "") {
  if (wasm?.wasm_commit_seed) return wasm.wasm_commit_seed(seed, gameId, season);
  return commitSeedJs(seed, gameId, season);
}

export async function commitSeedAsync(seed, gameId = "", season = "") {
  if (wasm?.wasm_commit_seed) return wasm.wasm_commit_seed(seed, gameId, season);
  return commitSeedJsAsync(seed, gameId, season);
}

export function demoUnit(master, streamId, n) {
  if (wasm?.wasm_demo_unit) return wasm.wasm_demo_unit(master, streamId, n);
  // JS fallback: hash-ish
  let x = Math.sin((master + streamId * 12.9898 + n * 78.233) * 43758.5453);
  return x - Math.floor(x);
}

/** Culled residual float (requires WASM harvest). */
export function extractFloat(seed, cullHead = 2) {
  if (!wasm?.wasm_extract_float) {
    throw new Error("extractFloat requires WASM (npm run build:wasm)");
  }
  return wasm.wasm_extract_float(seed, cullHead);
}

export function extractBitsU32(seed, nbits = 32, cullHead = 2) {
  if (!wasm?.wasm_extract_bits_u32) {
    throw new Error("extractBitsU32 requires WASM");
  }
  return wasm.wasm_extract_bits_u32(seed, nbits, cullHead);
}

export function harvestDigits(seed, count = 12) {
  if (!wasm?.wasm_harvest_digits) {
    throw new Error("harvestDigits requires WASM");
  }
  return wasm.wasm_harvest_digits(seed, count);
}

export function divergenceIndex(seed) {
  if (!wasm?.wasm_divergence_index) {
    throw new Error("divergenceIndex requires WASM");
  }
  return wasm.wasm_divergence_index(seed);
}

/** Pure JS stream mix (matches Python/Rust for integer ids when f64 agrees). */
export function streamSeedJs(master, streamId) {
  if (!Number.isFinite(master) || master <= 0) master = 0.123456789;
  const tag = BigInt(streamId >>> 0) | (BigInt(Math.floor(streamId / 0x100000000)) << 32n);
  // Use Number for mix — same as f64 path for small ids
  const t = Number(BigInt.asUintN(64, BigInt(streamId)));
  const x =
    master +
    (t % 1000003) * Math.PI +
    (Math.floor(t / 2 ** 20) % 997) * 0.6180339887498949;
  let y = Math.abs(Math.sin(x * 12.9898) * 43758.5453) % 1.0;
  if (y < 0) y += 1;
  return 0.5 + y * 9.5;
}

function pythonFloatRepr(x) {
  let s = String(x);
  if (!s.includes(".") && !s.toLowerCase().includes("e")) s += ".0";
  return s;
}

/** Sync commit only available via WASM; async uses Web Crypto. */
export function commitSeedJs() {
  throw new Error("Use commitSeedAsync in pure JS (Web Crypto is async)");
}

export async function commitSeedJsAsync(seed, gameId = "", season = "") {
  const enc = new TextEncoder();
  const parts = [
    enc.encode("rrann-commit-v1\0"),
    enc.encode(pythonFloatRepr(seed) + "\0"),
    enc.encode(gameId + "\0"),
    enc.encode(season + "\0"),
  ];
  const total = parts.reduce((n, p) => n + p.length, 0);
  const out = new Uint8Array(total);
  let o = 0;
  for (const p of parts) {
    out.set(p, o);
    o += p.length;
  }
  const buf = await crypto.subtle.digest("SHA-256", out);
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
}
