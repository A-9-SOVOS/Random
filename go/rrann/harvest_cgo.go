//go:build cgo

package rrann

/*
#cgo LDFLAGS: ${SRCDIR}/../../rust/rrann-core/target/release/librrann_core.a -ldl -lm -lpthread -lgmp -lmpfr
#cgo CFLAGS: -I${SRCDIR}/../../cpp
#include "rrann.h"
*/
import "C"
import "unsafe"

// ExtractFloat returns culled residual float via Rust harvest (MPFR).
// cullHead < 0 uses default (2).
func ExtractFloat(seed float64, cullHead int) float64 {
	return float64(C.rrann_extract_float(C.double(seed), C.int(cullHead)))
}

// ExtractU64 packs up to 64 residual bits (MSB-first).
func ExtractU64(seed float64, nbits uint32, cullHead int) uint64 {
	return uint64(C.rrann_extract_u64(C.double(seed), C.uint(nbits), C.int(cullHead)))
}

// HarvestDigits returns residual digit string.
func HarvestDigits(seed float64, count uint32) string {
	buf := make([]byte, 256)
	n := C.rrann_harvest_digits(
		C.double(seed),
		C.uint(count),
		(*C.char)(unsafe.Pointer(&buf[0])),
		C.size_t(len(buf)),
	)
	if n < 0 {
		return ""
	}
	return C.GoStringN((*C.char)(unsafe.Pointer(&buf[0])), n)
}

// DivergenceIndex returns diverge index or -1.
func DivergenceIndex(seed float64) int {
	return int(C.rrann_divergence_index(C.double(seed)))
}

// HarvestBackend reports which implementation is linked.
func HarvestBackend() string { return "cgo-mpfr" }
