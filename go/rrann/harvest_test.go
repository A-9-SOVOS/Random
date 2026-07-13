package rrann

import (
	"encoding/json"
	"os"
	"path/filepath"
	"runtime"
	"testing"
)

func repoRoot(t *testing.T) string {
	t.Helper()
	_, file, _, ok := runtime.Caller(0)
	if !ok {
		t.Fatal("no caller")
	}
	// go/rrann -> repo root
	return filepath.Clean(filepath.Join(filepath.Dir(file), "..", ".."))
}

func TestExtractFloatRange(t *testing.T) {
	x := ExtractFloat(2.4, 2)
	if x < 0 || x >= 1 {
		t.Fatalf("out of range %v", x)
	}
	if HarvestBackend() == "cgo-mpfr" {
		if abs(x-0.5744833867) > 1e-12 {
			t.Fatalf("got %v want ~0.5744833867", x)
		}
	} else {
		// soft: only range + determinism
		if ExtractFloat(2.4, 2) != x {
			t.Fatal("not deterministic")
		}
	}
}

func TestHarvestDigitsMatchPythonCGO(t *testing.T) {
	if HarvestBackend() != "cgo-mpfr" {
		t.Skip("native MPFR only")
	}
	d := HarvestDigits(2.4, 12)
	if d != "525744833867" {
		t.Fatalf("digits %q", d)
	}
	if DivergenceIndex(2.4) != 16 {
		t.Fatalf("diverge %d", DivergenceIndex(2.4))
	}
}

func TestVectorsJSONNative(t *testing.T) {
	if HarvestBackend() != "cgo-mpfr" {
		t.Skip("native MPFR only — soft harvest is approximate")
	}
	path := filepath.Join(repoRoot(t), "tests", "vectors.json")
	raw, err := os.ReadFile(path)
	if err != nil {
		t.Skip("no vectors.json")
	}
	var doc struct {
		Cases []struct {
			Seed               float64 `json:"seed"`
			Digits             string  `json:"digits"`
			DivergenceIndex    *int    `json:"divergence_index"`
			UsedFallback       bool    `json:"used_fallback"`
			ExtractFloatCull2  float64 `json:"extract_float_cull2"`
			ExtractBits32Cull2 []int   `json:"extract_bits32_cull2"`
		} `json:"cases"`
	}
	if err := json.Unmarshal(raw, &doc); err != nil {
		t.Fatal(err)
	}
	if len(doc.Cases) < 20 {
		t.Fatalf("want ≥20 cases, got %d", len(doc.Cases))
	}
	for _, c := range doc.Cases {
		d := HarvestDigits(c.Seed, 12)
		if d != c.Digits {
			t.Fatalf("seed=%v digits got %q want %q", c.Seed, d, c.Digits)
		}
		f := ExtractFloat(c.Seed, 2)
		if abs(f-c.ExtractFloatCull2) > 1e-12 {
			t.Fatalf("seed=%v float got %v want %v", c.Seed, f, c.ExtractFloatCull2)
		}
		div := DivergenceIndex(c.Seed)
		if c.DivergenceIndex == nil {
			if div != -1 {
				t.Fatalf("seed=%v div got %d want -1", c.Seed, div)
			}
		} else if div != *c.DivergenceIndex {
			t.Fatalf("seed=%v div got %d want %d", c.Seed, div, *c.DivergenceIndex)
		}
	}
}

func TestSoftHarvestSmoke(t *testing.T) {
	// Always valid path: soft or cgo both implement API
	d := HarvestDigits(2.4, 12)
	if len(d) != 12 {
		t.Fatalf("len %d digits %q", len(d), d)
	}
	for _, ch := range d {
		if ch < '0' || ch > '9' {
			t.Fatalf("non-digit %q", d)
		}
	}
	x := ExtractFloat(1.5, 2)
	if x < 0 || x >= 1 {
		t.Fatalf("range %v", x)
	}
	_ = ExtractU64(1.5, 32, 2)
	_ = DivergenceIndex(1.5)
	t.Logf("backend=%s digits(2.4)=%s float(1.5)=%v", HarvestBackend(), d, x)
}

func abs(x float64) float64 {
	if x < 0 {
		return -x
	}
	return x
}
