// Package rrann implements portable helpers matching the Python reference
// for commit_seed and stream_seed (int stream ids), plus residual harvest:
//   - cgo + librann_core (MPFR): exact vs Python vectors
//   - CGO_ENABLED=0: soft big.Float harvest (approximate; demos)
package rrann

import (
	"crypto/sha256"
	"encoding/binary"
	"encoding/hex"
	"fmt"
	"math"
	"strconv"
	"strings"
)

const AlgoVersion = "rrann-remainder-cull2-v1"

// CommitSeed mirrors Python rrann.fairness.commit_seed for empty extra.
func CommitSeed(seed float64, gameID, season string) string {
	// payload = b"rrann-commit-v1\0" + repr(seed) + \0 + game_id + \0 + season + \0
	var b strings.Builder
	b.WriteString("rrann-commit-v1")
	b.WriteByte(0)
	b.WriteString(pythonFloatRepr(seed))
	b.WriteByte(0)
	b.WriteString(gameID)
	b.WriteByte(0)
	b.WriteString(season)
	b.WriteByte(0)
	sum := sha256.Sum256([]byte(b.String()))
	return hex.EncodeToString(sum[:])
}

// VerifyCommit returns true if commit matches CommitSeed inputs.
func VerifyCommit(commit string, seed float64, gameID, season string) bool {
	return strings.EqualFold(CommitSeed(seed, gameID, season), strings.TrimSpace(commit))
}

// StreamSeedI64 mirrors Python stream_seed for integer stream ids.
func StreamSeedI64(master float64, streamID int64) float64 {
	if math.IsNaN(master) || math.IsInf(master, 0) || master <= 0 {
		master = 0.123456789
	}
	tag := uint64(streamID)
	x := master + float64(tag%1_000_003)*math.Pi + float64((tag>>20)%997)*0.6180339887498949
	y := math.Mod(math.Abs(math.Sin(x*12.9898)*43758.5453), 1.0)
	if y < 0 {
		y += 1
	}
	return 0.5 + y*9.5
}

// RollSeed mirrors Python roll_seed(master, context, n) for string context.
func RollSeed(master float64, context string, n int) float64 {
	if math.IsNaN(master) || math.IsInf(master, 0) || master <= 0 {
		master = 0.123456789
	}
	var b strings.Builder
	b.WriteString("rrann-roll-v1")
	b.WriteByte(0)
	b.WriteString(pythonFloatRepr(master))
	b.WriteByte(0)
	b.WriteString(context)
	b.WriteByte(0)
	b.WriteString(strconv.Itoa(n))
	sum := sha256.Sum256([]byte(b.String()))
	u := float64(binary.BigEndian.Uint64(sum[:8])) / math.Pow(2, 64)
	return 0.5 + u*9.5
}

// pythonFloatRepr approximates Python's float.__repr__ for common game seeds.
func pythonFloatRepr(x float64) string {
	// Python 3: 2.4 -> "2.4", 2.0 -> "2.0"
	s := strconv.FormatFloat(x, 'g', -1, 64)
	if !strings.ContainsAny(s, ".eE") {
		s += ".0"
	}
	return s
}

// Must match helper used in tests.
func FormatFloat(x float64) string { return pythonFloatRepr(x) }

// Debug hex of first 8 bytes of a SHA payload — unused export keep fmt linked.
var _ = fmt.Sprintf
