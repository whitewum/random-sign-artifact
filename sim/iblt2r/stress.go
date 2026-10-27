package main

// First-round experiments use the production hasher, encoder and decoder.
// An independent unsigned incidence graph checks every accepted operation,
// including operations on trials whose decoding ultimately fails.
import (
	"bufio"
	"encoding/json"
	"flag"
	"fmt"
	"math"
	"math/rand/v2"
	"os"
	"strings"
	"sync"
	"time"
)

var stressResume = flag.String("stress-resume", "", "comma-separated immutable checkpoint baselines to skip")
var stressMode = flag.Bool("decode-stress", false, "run audited first-round paired decoding experiment")
var stressShard = flag.Int("stress-shard", 0, "task partition index")
var stressShards = flag.Int("stress-shards", 1, "number of task partitions")
var stressPilot = flag.Int("stress-pilot", 0, "override trials per configuration for pilot")
var stressChunk = flag.Int("stress-chunk", 10000, "trials per durable checkpoint")

type stressConfig struct {
	ID, K, M, D, Plus, Common, Trials int
	Load, Fraction, Alpha             float64
}
type stressRow struct {
	Task             int          `json:"task"`
	Config           stressConfig `json:"config"`
	Start            int          `json:"start"`
	Trials           int          `json:"trials"`
	Success          int          `json:"success"`
	Failure          int          `json:"failure"`
	Accepted         int64        `json:"accepted"`
	Candidates       int64        `json:"candidates"`
	ChecksumRejected int64        `json:"checksum_rejected"`
	Seconds          float64      `json:"seconds"`
	Seed             uint64       `json:"seed"`
}

func peelingAlpha(k int) float64 {
	lo, hi := 0.000001, 30.0
	// Positive solution exp(x)=1+(k-1)x, above its positive minimum.
	lo = math.Log(float64(k - 1))
	for j := 0; j < 100; j++ {
		x := (lo + hi) / 2
		if math.Expm1(x) > float64(k-1)*x {
			hi = x
		} else {
			lo = x
		}
	}
	x := (lo + hi) / 2
	return x / (float64(k) * math.Pow(-math.Expm1(-x), float64(k-1)))
}
func stressConfigs() []stressConfig {
	var out []stressConfig
	for _, k := range []int{3, 4, 5, 6, 10} {
		a := peelingAlpha(k)
		for mi, m := range []int{64, 1024, 16384} {
			for _, load := range []float64{0.5, 0.95, 1, 1.05, 3} {
				d := int(math.Round(a * float64(m) * load))
				for _, fraction := range []float64{0, 0.25, 0.5, 0.75, 1} {
					n := []int{3000000, 900000, 100000}[mi]
					if *stressPilot > 0 {
						n = *stressPilot
					}
					out = append(out, stressConfig{len(out), k, m, d, int(math.Round(float64(d) * fraction)), min(1000, m), n, load, fraction, a})
				}
			}
		}
	}
	return out
}

// Mapping is constructed directly from the true difference, independently of aggregate fields.
type stressGraph struct {
	edges, head, next, edgeID, degree, xor []int
	core                                   []bool
}

func makeStressGraph(keys []uint64, h hasher, k, m int) stressGraph {
	g := stressGraph{edges: make([]int, len(keys)*k), head: make([]int, m), next: make([]int, len(keys)*k), edgeID: make([]int, len(keys)*k), degree: make([]int, m), xor: make([]int, m), core: make([]bool, len(keys))}
	for v := range g.head {
		g.head[v] = -1
	}
	for i, x := range keys {
		h.cells(x, k, m, g.edges[i*k:(i+1)*k])
		g.core[i] = true
		for j, v := range g.edges[i*k : (i+1)*k] {
			p := i*k + j
			g.next[p] = g.head[v]
			g.head[v] = p
			g.edgeID[p] = i
			g.degree[v]++
			g.xor[v] ^= i
		}
	}
	deg := append([]int(nil), g.degree...)
	var queue []int
	for v, n := range deg {
		if n == 1 {
			queue = append(queue, v)
		}
	}
	for qi := 0; qi < len(queue); qi++ {
		v := queue[qi]
		if deg[v] != 1 {
			continue
		}
		i := -1
		for p := g.head[v]; p >= 0; p = g.next[p] {
			if g.core[g.edgeID[p]] {
				i = g.edgeID[p]
				break
			}
		}
		if i < 0 {
			panic("unsigned reference: missing degree-one edge")
		}
		g.core[i] = false
		for _, u := range g.edges[i*k : (i+1)*k] {
			deg[u]--
			if deg[u] == 1 {
				queue = append(queue, u)
			}
		}
	}
	return g
}
func auditedDecode(t *table, h hasher, signed bool, k int, keys []uint64, plus int, index map[uint64]int, g stressGraph) (decoded, int64) {
	active := make([]bool, len(keys))
	for i := range active {
		active[i] = true
	}
	deg := append([]int(nil), g.degree...)
	xx := append([]int(nil), g.xor...)
	var accepted int64
	t.audit = func(v int, x uint64, c int64) {
		i, ok := index[x]
		if !ok || !active[i] || deg[v] != 1 || xx[v] != i {
			panic(fmt.Sprintf("non-pure or false acceptance: cell=%d key=%d degree=%d", v, x, deg[v]))
		}
		direction := int64(-1)
		if i < plus {
			direction = 1
		}
		coeff := direction
		if signed {
			coeff *= h.eps(x)
		}
		if c != coeff {
			panic("wrong accepted direction")
		}
		active[i] = false
		accepted++
		for _, u := range g.edges[i*k : (i+1)*k] {
			deg[u]--
			xx[u] ^= i
		}
	}
	r := decode(t, h, signed, k)
	expected := newTable(len(t.count))
	for i, x := range keys {
		if active[i] != g.core[i] {
			panic("recovered set differs from unsigned residual core")
		}
		_, p := r.plus[x]
		_, n := r.minus[x]
		if active[i] {
			if p || n {
				panic("core key reported recovered")
			}
		} else if (i < plus && (!p || n)) || (i >= plus && (!n || p)) {
			panic("recovered key direction mismatch")
		}
		if active[i] {
			c := int64(-1)
			if i < plus {
				c = 1
			}
			if signed {
				c *= h.eps(x)
			}
			expected.add(x, c, g.edges[i*k:(i+1)*k], h.chk(x))
		}
	}
	coreN := 0
	for _, b := range g.core {
		if b {
			coreN++
		}
	}
	if r.ok != (coreN == 0) {
		panic("zero-field termination differs from true success")
	}
	for v := range t.count {
		if t.count[v] != expected.count[v] || t.keySum[v] != expected.keySum[v] || t.chkSum[v] != expected.chkSum[v] {
			panic("residual fields differ from true residual encoding")
		}
	}
	if int64(len(r.plus)+len(r.minus)) != accepted {
		panic("duplicate or extra recovery")
	}
	return r, accepted
}
func stressTrial(c stressConfig, trial int, seed uint64) (bool, int64, int64, int64) {
	r0, r1, n0, n1, _, _ := stressPair(c, trial, seed)
	return r0.ok, n0 + n1, r0.cnt.cand + r1.cnt.cand, r0.cnt.chkRej + r1.cnt.chkRej
}

// stressPair runs the audited paired decoding and also returns, per encoding, the number of
// cells whose initial count is +-1 although their degree is at least two.
func stressPair(c stressConfig, trial int, seed uint64) (decoded, decoded, int64, int64, int, int) {
	// Each (seed,configuration,trial) has its own reproducible PCG stream.
	rng := rand.New(rand.NewPCG(seed^uint64(c.ID)<<32, uint64(trial)))
	seen := make(map[uint64]bool, c.D+c.Common)
	draw := func(n int) []uint64 {
		xs := make([]uint64, 0, n)
		for len(xs) < n {
			x := rng.Uint64()
			if x != 0 && !seen[x] {
				seen[x] = true
				xs = append(xs, x)
			}
		}
		return xs
	}
	common, keys := draw(c.Common), draw(c.D)
	a := append(append([]uint64{}, common...), keys[:c.Plus]...)
	b := append(append([]uint64{}, common...), keys[c.Plus:]...)
	h := hasher{rng.Uint64(), rng.Uint64(), rng.Uint64()}
	index := make(map[uint64]int, len(keys))
	for i, x := range keys {
		index[x] = i
	}
	g := makeStressGraph(keys, h, c.K, c.M)
	standard := encodeSets(h, false, c.K, c.M, a, b)
	signed := encodeSets(h, true, c.K, c.M, a, b)
	// Explicitly verify common-element cancellation in all three fields.
	for _, sgn := range []bool{false, true} {
		t := standard
		if sgn {
			t = signed
		}
		direct := newTable(c.M)
		for i, x := range keys {
			coef := int64(-1)
			if i < c.Plus {
				coef = 1
			}
			if sgn {
				coef *= h.eps(x)
			}
			direct.add(x, coef, g.edges[i*c.K:(i+1)*c.K], h.chk(x))
		}
		for v := range t.count {
			if t.count[v] != direct.count[v] || t.keySum[v] != direct.keySum[v] || t.chkSum[v] != direct.chkSum[v] {
				panic("common cancellation mismatch")
			}
		}
	}
	fake := func(t *table) int {
		n := 0
		for v, x := range t.count {
			if (x == 1 || x == -1) && g.degree[v] >= 2 {
				n++
			}
		}
		return n
	}
	f0, f1 := fake(standard), fake(signed)
	r0, n0 := auditedDecode(standard, h, false, c.K, keys, c.Plus, index, g)
	r1, n1 := auditedDecode(signed, h, true, c.K, keys, c.Plus, index, g)
	if r0.ok != r1.ok {
		panic("paired first-round outcomes differ")
	}
	return r0, r1, n0, n1, f0, f1
}
func runDecodeStress(path string, jobs int, seed uint64) {
	if *stressShards < 1 || *stressShard < 0 || *stressShard >= *stressShards || *stressChunk < 1 || jobs < 1 {
		panic("invalid stress partition or worker count")
	}
	configs := stressConfigs()
	done := map[int]bool{}
	for _, resumePath := range append(strings.FieldsFunc(*stressResume, func(r rune) bool { return r == ',' }), path) {
		f, e := os.Open(resumePath)
		if e != nil {
			if resumePath == path && os.IsNotExist(e) {
				continue
			}
			must(e)
		}
		sc := bufio.NewScanner(f)
		for sc.Scan() {
			var r stressRow
			must(json.Unmarshal(sc.Bytes(), &r))
			if r.Seed != seed {
				panic("resume seed mismatch")
			}
			if r.Config != configs[r.Config.ID] {
				panic("resume configuration mismatch")
			}
			done[r.Task] = true
		}
		must(sc.Err())
		f.Close()
	}
	f, e := os.OpenFile(path, os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0644)
	must(e)
	defer f.Close()
	enc := json.NewEncoder(f)
	type task struct {
		id, start, n int
		c            stressConfig
	}
	tasks := make(chan task)
	results := make(chan stressRow, jobs)
	var wg sync.WaitGroup
	for w := 0; w < jobs; w++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for t := range tasks {
				row := stressRow{Task: t.id, Config: t.c, Start: t.start, Trials: t.n, Seed: seed}
				start := time.Now()
				for j := 0; j < t.n; j++ {
					func() {
						defer func() {
							if r := recover(); r != nil {
								panic(fmt.Sprintf("seed=%d config=%+v trial=%d: %v", seed, t.c, t.start+j, r))
							}
						}()
						ok, a, c, r := stressTrial(t.c, t.start+j, seed)
						if ok {
							row.Success++
						} else {
							row.Failure++
						}
						row.Accepted += a
						row.Candidates += c
						row.ChecksumRejected += r
					}()
				}
				row.Seconds = time.Since(start).Seconds()
				results <- row
			}
		}()
	}
	go func() {
		id := 0
		maxTrials := 0
		for _, c := range configs {
			maxTrials = max(maxTrials, c.Trials)
		}
		for start := 0; start < maxTrials; start += *stressChunk {
			for _, c := range configs {
				if start >= c.Trials {
					continue
				}
				if id%*stressShards == *stressShard && !done[id] {
					tasks <- task{id, start, min(*stressChunk, c.Trials-start), c}
				}
				id++
			}
		}
		close(tasks)
		wg.Wait()
		close(results)
	}()
	var total int64
	for r := range results {
		must(enc.Encode(r))
		must(f.Sync())
		total += int64(r.Trials)
		fmt.Fprintf(os.Stderr, "task=%d k=%d M=%d trials=%d success=%d failure=%d seconds=%.3f new_total=%d\n", r.Task, r.Config.K, r.Config.M, r.Trials, r.Success, r.Failure, r.Seconds, total)
	}
}
