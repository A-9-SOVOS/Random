package rrann

import (
	"encoding/json"
	"os"
	"path/filepath"
	"runtime"
	"testing"
)

func TestStreamSeedDiffers(t *testing.T) {
	a := StreamSeedI64(2.4, 0)
	b := StreamSeedI64(2.4, 1)
	if a == b {
		t.Fatalf("expected different streams")
	}
	if a <= 0.5 || a >= 10 {
		t.Fatalf("out of band %v", a)
	}
}

func TestCommitStable(t *testing.T) {
	c1 := CommitSeed(2.4, "demo", "s1")
	c2 := CommitSeed(2.4, "demo", "s1")
	if c1 != c2 || len(c1) != 64 {
		t.Fatalf("commit unstable %s", c1)
	}
	if !VerifyCommit(c1, 2.4, "demo", "s1") {
		t.Fatal("verify failed")
	}
	if VerifyCommit(c1, 2.4, "other", "s1") {
		t.Fatal("expected mismatch")
	}
}

func TestCommitMatchesPythonVectorsIfPresent(t *testing.T) {
	// Load optional golden commits generated next to module
	_, file, _, _ := runtime.Caller(0)
	root := filepath.Clean(filepath.Join(filepath.Dir(file), "..", ".."))
	path := filepath.Join(root, "tests", "vectors_commit.json")
	data, err := os.ReadFile(path)
	if err != nil {
		t.Skip("no vectors_commit.json")
	}
	var v struct {
		Cases []struct {
			Seed   float64 `json:"seed"`
			GameID string  `json:"game_id"`
			Season string  `json:"season"`
			Commit string  `json:"commit"`
		} `json:"cases"`
	}
	if err := json.Unmarshal(data, &v); err != nil {
		t.Fatal(err)
	}
	for _, c := range v.Cases {
		got := CommitSeed(c.Seed, c.GameID, c.Season)
		if got != c.Commit {
			t.Fatalf("seed=%v got %s want %s", c.Seed, got, c.Commit)
		}
	}
}
