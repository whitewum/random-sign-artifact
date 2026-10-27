package main

import (
	"math"
	"os"
	"testing"
)

func TestStressThresholdsAndBudget(t *testing.T) {
	for k, want := range map[int]float64{3: 0.818469160761, 4: 0.772279839803, 5: 0.701780266485} {
		if math.Abs(peelingAlpha(k)-want) > 1e-11 {
			t.Fatalf("k=%d alpha=%g", k, peelingAlpha(k))
		}
	}
	total := 0
	for _, c := range stressConfigs() {
		total += c.Trials
	}
	if total != 500000000 {
		t.Fatalf("trial budget %d", total)
	}
}
func TestStressPairedProductionDecoder(t *testing.T) {
	for _, c := range stressConfigs() {
		for trial := 0; trial < 2; trial++ {
			stressTrial(c, trial, 2026101501)
		}
	}
}
func TestStressDetectsAcceptedNonPureCell(t *testing.T) {
	// Forge aggregate fields so that a degree-two cell passes the actual decoder.
	// The experiment hook must detect the false acceptance before deletion.
	h := hasher{1, 2, 3}
	keys := []uint64{17, 30}
	k, m := 3, 8
	g := makeStressGraph(keys, h, k, m)
	v := g.edges[0]
	g.degree[v] = 2
	tab := newTable(m)
	tab.count[v] = 1
	tab.keySum[v] = 17
	tab.chkSum[v] = h.chk(17)
	defer func() {
		if recover() == nil {
			t.Fatal("accepted non-pure cell was not detected")
		}
	}()
	auditedDecode(tab, h, false, k, keys, 2, map[uint64]int{17: 0, 30: 1}, g)
}
func TestStressDetectsZeroFieldNonemptyCore(t *testing.T) {
	h := hasher{1, 2, 3}
	keys := []uint64{17, 30}
	k, m := 3, 8
	g := makeStressGraph(keys, h, k, m)
	for i := range g.core {
		g.core[i] = true
	}
	defer func() {
		if recover() == nil {
			t.Fatal("false zero-field success was not detected")
		}
	}()
	auditedDecode(newTable(m), h, false, k, keys, 2, map[uint64]int{17: 0, 30: 1}, g)
}

func TestStressResumeAcrossRepartition(t *testing.T) {
	oldPilot, oldChunk, oldShard, oldShards, oldResume := *stressPilot, *stressChunk, *stressShard, *stressShards, *stressResume
	defer func() {
		*stressPilot = oldPilot
		*stressChunk = oldChunk
		*stressShard = oldShard
		*stressShards = oldShards
		*stressResume = oldResume
	}()
	*stressPilot = 1
	*stressChunk = 10000
	*stressShard = 0
	*stressShards = 1
	baseline := t.TempDir() + "/baseline.jsonl"
	runDecodeStress(baseline, 2, 2026101501)
	*stressResume = baseline
	*stressShards = 3
	for shard := 0; shard < 3; shard++ {
		*stressShard = shard
		out := t.TempDir() + "/new.jsonl"
		runDecodeStress(out, 2, 2026101501)
		st, err := os.Stat(out)
		if err != nil {
			t.Fatal(err)
		}
		if st.Size() != 0 {
			t.Fatal("repartition duplicated a completed trial")
		}
	}
}
