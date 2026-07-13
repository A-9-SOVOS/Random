/* RRann C API for engines (Unity/Godot/native).
 *
 * Link against librann_core (Rust static/shared) OR implement the same
 * symbols yourself. See docs/OPEN_SEQUENCE.md step 3.
 */
#ifndef RRANN_H
#define RRANN_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/** Independent stream seed in (0.5, 10). */
double rrann_stream_seed(double master, long long stream_id);

/** splitmix64 finalizer (mixer, not harvest). */
uint64_t rrann_splitmix64(uint64_t x);

/** Demo u64 for scatter (not residual harvest). */
uint64_t rrann_demo_u64(double master, long long stream_id, uint64_t n);

/**
 * Write 64-char hex commit + NUL into out (out_len >= 65).
 * Returns 0 on success, -1 on error.
 */
int rrann_commit_seed(double seed, const char *game_id, const char *season,
                      char *out, size_t out_len);

/** 1 match, 0 mismatch, -1 error. */
int rrann_verify_commit(const char *commit, double seed, const char *game_id,
                        const char *season);

/**
 * Culled residual float in [0,1).
 * cull_head < 0 uses default (2). Rust harvest prototype — not CPython-identical.
 */
double rrann_extract_float(double seed, int cull_head);

/** Pack up to 64 residual bits into a u64 (MSB-first). nbits clamped 0..64. */
uint64_t rrann_extract_u64(double seed, uint32_t nbits, int cull_head);

/**
 * Write residual digit string + NUL. Returns length or -1.
 * count==0 → 12 digits. out_len must include room for NUL.
 */
int rrann_harvest_digits(double seed, uint32_t count, char *out, size_t out_len);

/** Diverge index, or -1 if fallback/none. */
int rrann_divergence_index(double seed);

#ifdef __cplusplus
}
#endif

#endif /* RRANN_H */
