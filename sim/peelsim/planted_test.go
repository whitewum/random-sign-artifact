package main

import (
	"math"
	"math/rand/v2"
	"testing"
)

func TestPlantedBalancedLabels(t *testing.T) {
	old := optPlant
	optPlant = true
	defer func() { optPlant = old }()
	const M, K, D, N = 64, 3, 6, 30000
	w := newWorker(M, K, D, parseVariants("0.5,rand", D), 0, 0, 0, false, 0.5)
	rm := rand.New(rand.NewPCG(1, 2))
	rs := rand.New(rand.NewPCG(3, 4))
	rp := rand.New(rand.NewPCG(5, 6))
	rr := rand.New(rand.NewPCG(7, 8))
	w.rplant = rand.New(rand.NewPCG(9, 10))
	rec := make([]uint32, nFields(2, 0, 0, 0))
	counts := map[[2]int]int{}
	var balanced, iid float64
	sd := math.Sqrt(2.0 * D * (D - 1) / (M - 1))
	for n := 0; n < N; n++ {
		w.trial(rm, rs, rp, rr, rec)
		if rec[2] != 1 {
			t.Fatal("planted mapping must fail")
		}
		counts[[2]int{w.plantI, w.plantJ}]++
		for j := 0; j < K; j++ {
			if w.cells[w.plantI*K+j] != w.cells[w.plantJ*K+j] {
				t.Fatal("pair mappings differ")
			}
		}
		balanced += float64(math.Float32frombits(rec[0])) * sd
		iid += float64(math.Float32frombits(rec[1])) * sd
	}
	if len(counts) != 15 {
		t.Fatalf("observed %d label pairs", len(counts))
	}
	for pair, n := range counts {
		if math.Abs(float64(n)-N/15) > 200 {
			t.Fatalf("pair %v count %d", pair, n)
		}
	}
	if math.Abs(balanced/N+0.4) > 0.06 {
		t.Fatalf("balanced mean bias = %g", balanced/N)
	}
	if math.Abs(iid/N) > 0.06 {
		t.Fatalf("iid mean bias = %g", iid/N)
	}
	t.Logf("balanced mean bias %.6f (expected -0.4), iid %.6f (expected 0)", balanced/N, iid/N)
}

func TestSavedPlantScheme(t *testing.T) {
	for _, tc := range []struct {
		m    manifest
		want string
	}{
		{manifest{Args: []string{"-plant-dup"}}, "fixed-last-pair-v0"},
		{manifest{Args: []string{"-plant-dup=true"}}, "fixed-last-pair-v0"},
		{manifest{}, "none"},
		{manifest{PlantScheme: "uniform-pair-v1"}, "uniform-pair-v1"},
	} {
		if got := savedPlantScheme(tc.m); got != tc.want {
			t.Fatalf("got %q, want %q", got, tc.want)
		}
	}
}
