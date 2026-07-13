//go:build !cgo

package rrann

// Pure-Go soft residual harvest (no cgo / no MPFR).
// Approximate x^x via math/big.Float ln/exp — same role as Rust soft-harvest
// (WASM demos). Not bit-identical to CPython Decimal or native MPFR.
// For economy / parity, use cgo + librann_core (native MPFR) or Python.

import (
	"crypto/sha256"
	"fmt"
	"math"
	"math/big"
	"strconv"
	"strings"
)

const (
	defaultCullHead    = 2
	defaultDigitCount  = 12
	softFloatPrecBits  = 256 // soft high-path precision
)

// ExtractFloat returns culled residual float via pure-Go soft harvest.
// cullHead < 0 uses default (2).
func ExtractFloat(seed float64, cullHead int) float64 {
	if cullHead < 0 {
		cullHead = defaultCullHead
	}
	h := softHarvest(seed, defaultDigitCount)
	body := remainder(h.digits, cullHead)
	if body == "" {
		body = h.digits
	}
	for len(body) < 16 {
		body += "0"
	}
	s := "0." + body[:16]
	x, err := strconv.ParseFloat(s, 64)
	if err != nil {
		return 0.5
	}
	if x < 0 {
		return 0
	}
	if x >= 1 {
		return 0.9999999999999999
	}
	return x
}

// ExtractU64 packs up to 64 residual bits (MSB-first).
func ExtractU64(seed float64, nbits uint32, cullHead int) uint64 {
	if cullHead < 0 {
		cullHead = defaultCullHead
	}
	if nbits == 0 {
		return 0
	}
	if nbits > 64 {
		nbits = 64
	}
	bits := softExtractBits(seed, int(nbits), cullHead)
	var v uint64
	for _, b := range bits {
		v = (v << 1) | uint64(b&1)
	}
	return v
}

// HarvestDigits returns residual digit string (soft).
func HarvestDigits(seed float64, count uint32) string {
	if count == 0 {
		count = defaultDigitCount
	}
	return softHarvest(seed, int(count)).digits
}

// DivergenceIndex returns diverge index or -1 (soft).
func DivergenceIndex(seed float64) int {
	h := softHarvest(seed, defaultDigitCount)
	if h.divIndex < 0 {
		return -1
	}
	return h.divIndex
}

// HarvestBackend reports which implementation is linked.
func HarvestBackend() string { return "soft-bigfloat" }

type softResult struct {
	digits    string
	divIndex  int
	fallback  bool
}

func softHarvest(seed float64, count int) softResult {
	seed = normalizeSeed(seed)
	if count <= 0 {
		count = defaultDigitCount
	}
	floatResult := math.Pow(seed, seed)
	if math.IsInf(floatResult, 0) || math.IsNaN(floatResult) {
		return softResult{digits: fallbackDigits(seed, count), divIndex: -1, fallback: true}
	}
	hd, ok := highDigitStringSoft(seed, count+32)
	if !ok {
		return softResult{digits: fallbackDigits(seed, count), divIndex: -1, fallback: true}
	}
	fd := float64DigitString(floatResult, count+32)
	div := -1
	n := len(fd)
	if len(hd) < n {
		n = len(hd)
	}
	for i := 0; i < n; i++ {
		if fd[i] != hd[i] {
			div = i
			break
		}
	}
	if div < 0 {
		return softResult{digits: fallbackDigits(seed, count), divIndex: -1, fallback: true}
	}
	end := div + count
	if end > len(hd) {
		end = len(hd)
	}
	slice := hd[div:end]
	if len(slice) < count || allZero(slice) {
		return softResult{digits: fallbackDigits(seed, count), divIndex: div, fallback: true}
	}
	for len(slice) < count {
		slice += "0"
	}
	return softResult{digits: slice[:count], divIndex: div, fallback: false}
}

func softExtractBits(seed float64, nbits, cullHead int) []uint8 {
	h := softHarvest(seed, defaultDigitCount)
	body := remainder(h.digits, cullHead)
	if body == "" {
		body = h.digits
	}
	num := new(big.Int)
	num.SetString(body, 10)
	den := new(big.Int).Exp(big.NewInt(10), big.NewInt(int64(len(body))), nil)
	// word = (num << nbits) / den
	word := new(big.Int).Lsh(num, uint(nbits))
	word.Div(word, den)
	bits := make([]uint8, nbits)
	for i := 0; i < nbits; i++ {
		shift := nbits - 1 - i
		bits[i] = uint8(word.Bit(shift))
	}
	return bits
}

func normalizeSeed(seed float64) float64 {
	if math.IsNaN(seed) || math.IsInf(seed, 0) || seed <= 0 {
		a := math.Abs(seed)
		if math.IsNaN(a) || math.IsInf(a, 0) || a <= 0 {
			return 0.123456789
		}
		return a
	}
	return seed
}

func remainder(digits string, cull int) string {
	if cull <= 0 {
		return digits
	}
	if cull >= len(digits) {
		return ""
	}
	return digits[cull:]
}

func allZero(s string) bool {
	for _, c := range s {
		if c != '0' {
			return false
		}
	}
	return true
}

func fallbackDigits(seed float64, count int) string {
	// Match Python: sha256(f"{seed:.18g}")
	msg := pythonG18(seed)
	sum := sha256.Sum256([]byte(msg))
	n := new(big.Int).SetBytes(sum[:])
	s := n.String()
	for len(s) < count {
		s += "0"
	}
	return s[:count]
}

func pythonG18(seed float64) string {
	if math.IsNaN(seed) || math.IsInf(seed, 0) {
		return fmt.Sprint(seed)
	}
	if seed == math.Trunc(seed) && math.Abs(seed) < 1e15 {
		return strconv.FormatInt(int64(seed), 10)
	}
	// General: 18 significant digits (close enough for soft fallback path)
	return strconv.FormatFloat(seed, 'g', 18, 64)
}

func significantDigitsFromFloatStr(s string, count int) string {
	var b strings.Builder
	for _, c := range s {
		if c >= '0' && c <= '9' {
			b.WriteRune(c)
		}
	}
	digits := b.String()
	// strip leading zeros (keep fractional significance start)
	i := 0
	for i < len(digits) && digits[i] == '0' {
		i++
	}
	if i > 0 {
		digits = digits[i:]
	}
	if digits == "" {
		return strings.Repeat("0", count)
	}
	if len(digits) >= count {
		return digits[:count]
	}
	return digits + strings.Repeat("0", count-len(digits))
}

func float64DigitString(x float64, count int) string {
	s := strconv.FormatFloat(math.Abs(x), 'f', 50, 64)
	return significantDigitsFromFloatStr(s, count)
}

// highDigitStringSoft: seed^seed via exp(seed * ln(seed)) at softFloatPrecBits.
func highDigitStringSoft(seed float64, count int) (string, bool) {
	if !(seed > 0 && !math.IsNaN(seed) && !math.IsInf(seed, 0)) {
		return "", false
	}
	x := new(big.Float).SetPrec(softFloatPrecBits).SetFloat64(seed)
	// ln(x)
	ln, ok := bigLog(x)
	if !ok {
		return "", false
	}
	// x * ln(x)
	prod := new(big.Float).SetPrec(softFloatPrecBits).Mul(x, ln)
	// exp(prod)
	y, ok := bigExp(prod)
	if !ok {
		return "", false
	}
	// Text form with enough digits
	s := y.Text('f', count+48)
	if strings.HasPrefix(s, "-") {
		s = s[1:]
	}
	return significantDigitsFromFloatStr(s, count), true
}

// bigLog natural log via agm/atanh series for x > 0.
func bigLog(x *big.Float) (*big.Float, bool) {
	prec := x.Prec()
	if x.Sign() <= 0 {
		return nil, false
	}
	// Reduce: write x = m * 2^e with m in [0.5, 1)
	mant := new(big.Float).SetPrec(prec)
	exp := x.MantExp(mant)
	// ln(x) = ln(mant) + exp*ln(2)
	// For mant in [0.5,1): use artanh series on (mant-1)/(mant+1)
	lnMant := logNearOne(mant, prec)
	if lnMant == nil {
		return nil, false
	}
	ln2 := ln2Const(prec)
	e := new(big.Float).SetPrec(prec).SetInt64(int64(exp))
	out := new(big.Float).SetPrec(prec).Mul(e, ln2)
	out.Add(out, lnMant)
	return out, true
}

// logNearOne: ln(m) for m in (0, 2) using artanh: ln(m) = 2*(z + z^3/3 + ...) where z=(m-1)/(m+1)
func logNearOne(m *big.Float, prec uint) *big.Float {
	one := new(big.Float).SetPrec(prec).SetFloat64(1)
	num := new(big.Float).SetPrec(prec).Sub(m, one)
	den := new(big.Float).SetPrec(prec).Add(m, one)
	if den.Sign() == 0 {
		return nil
	}
	z := new(big.Float).SetPrec(prec).Quo(num, den)
	// series: 2 * sum_{k=0..} z^{2k+1}/(2k+1)
	z2 := new(big.Float).SetPrec(prec).Mul(z, z)
	term := new(big.Float).SetPrec(prec).Set(z)
	sum := new(big.Float).SetPrec(prec).Set(z)
	for k := 1; k < 200; k++ {
		term.Mul(term, z2)
		denK := new(big.Float).SetPrec(prec).SetInt64(int64(2*k + 1))
		inc := new(big.Float).SetPrec(prec).Quo(term, denK)
		sum.Add(sum, inc)
		af, _ := new(big.Float).SetPrec(prec).Abs(inc).Float64()
		if af < 1e-40 {
			break
		}
	}
	two := new(big.Float).SetPrec(prec).SetFloat64(2)
	return sum.Mul(sum, two)
}

func ln2Const(prec uint) *big.Float {
	// ln(2) ≈ series on logNearOne(2) but 2 is outside (0,2) for stability — use known digits
	// Or logNearOne on sqrt(2)*sqrt(2)... simpler: hardcode high-prec ln2
	ln2, _, err := big.ParseFloat(
		"0.693147180559945309417232121458176568075500134360255254120680009493393",
		10, prec, big.ToNearestEven,
	)
	if err != nil {
		return new(big.Float).SetPrec(prec).SetFloat64(math.Ln2)
	}
	return ln2
}

// bigExp exp via range reduction + Taylor.
func bigExp(x *big.Float) (*big.Float, bool) {
	prec := x.Prec()
	xf, _ := x.Float64()
	if math.IsInf(xf, 0) || math.IsNaN(xf) {
		return nil, false
	}
	// exp(x) = 2^{x/ln2} = 2^{n+f} = 2^n * exp(f*ln2) with f in [0,1)
	ln2 := ln2Const(prec)
	quot := new(big.Float).SetPrec(prec).Quo(x, ln2)
	// n = floor(quot)
	nInt, _ := quot.Int(nil)
	n := new(big.Float).SetPrec(prec).SetInt(nInt)
	frac := new(big.Float).SetPrec(prec).Sub(quot, n)
	// arg = frac * ln2  in ~[0, ln2]
	arg := new(big.Float).SetPrec(prec).Mul(frac, ln2)
	// Taylor exp(arg)
	one := new(big.Float).SetPrec(prec).SetFloat64(1)
	sum := new(big.Float).SetPrec(prec).Set(one)
	term := new(big.Float).SetPrec(prec).Set(one)
	for k := 1; k < 120; k++ {
		term.Mul(term, arg)
		term.Quo(term, new(big.Float).SetPrec(prec).SetInt64(int64(k)))
		sum.Add(sum, term)
		af, _ := new(big.Float).SetPrec(prec).Abs(term).Float64()
		if af < 1e-45 {
			break
		}
	}
	// scale by 2^n
	ni := nInt.Int64()
	out := new(big.Float).SetPrec(prec).SetMantExp(sum, int(ni))
	return out, true
}
