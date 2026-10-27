// iblt2r: end-to-end two-round set reconciliation with a real IBLT (experiment 3).
//
// Each cell holds count (int64), keySum and chkSum (uint64, additive mod 2^64). A key x is inserted
// with coefficient c in {+1,-1}: count += c, keySum += c*x, chkSum += c*chk(x). Two encodings share
// the same cell hash:
//
//	signed:   c = eps(x) for both parties (eps = shared sign hash), so after A - B the coefficient of
//	          x in A\B is eps(x) and of x in B\A is -eps(x);
//	standard: c = +1 (classic additive IBLT, coefficient = set direction).
//
// Decoding peels cells with count = +-1 whose chkSum matches chk(count*keySum) and whose key hashes to
// the cell; the direction is count*eps(x) (signed) or count (standard). Success = every field of every
// cell returns to zero. The measurement sum C, sum C^2 is taken from the difference table before peeling.
//
// Protocol per trial: round 1 with M1 cells; on failure compute the upper bound U of d from round-1
// counts with a rule, set M2 = max(ceil(U/(theta alpha_c)), mmin) (empty set: M2 = 4 M1), rebuild with a
// fresh cell-hash seed and decode again.
//
// usage: iblt2r -q qtable.json -spec FILE -trials N -out results.csv [-jobs J]
// spec lines: k M1 d common onesided(0/1)
package main

import (
	"bufio"
	"encoding/json"
	"flag"
	"fmt"
	"math"
	"math/rand/v2"
	"os"
	"runtime"
	"sort"
	"strconv"
	"strings"
	"sync"
	"time"
)

var alphaC = map[int]float64{3: 0.818469160761, 4: 0.772279839803, 5: 0.701780266485}

func mix64(z uint64) uint64 {
	z += 0x9E3779B97F4A7C15
	z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9
	z = (z ^ (z >> 27)) * 0x94D049BB133111EB
	return z ^ (z >> 31)
}

type hasher struct{ cellSeed, signSeed, chkSeed uint64 }

func (h hasher) eps(x uint64) int64 {
	if mix64(x^h.signSeed)&1 == 0 {
		return -1
	}
	return 1
}
func (h hasher) chk(x uint64) uint64 { return mix64(mix64(x ^ h.chkSeed)) }

// cells writes k distinct cells of x into dst.
func (h hasher) cells(x uint64, k, M int, dst []int) {
	n := 0
	for j := uint64(0); n < k; j++ {
		c := int(mix64(x^h.cellSeed^(j*0xD6E8FEB86659FD93)) % uint64(M))
		dup := false
		for i := 0; i < n; i++ {
			if dst[i] == c {
				dup = true
				break
			}
		}
		if !dup {
			dst[n] = c
			n++
		}
	}
}

type table struct {
	count  []int64
	keySum []uint64
	chkSum []uint64
	audit  func(int, uint64, int64) // optional experiment-only check at every accepted operation
}

func newTable(M int) *table {
	return &table{count: make([]int64, M), keySum: make([]uint64, M), chkSum: make([]uint64, M)}
}

func (t *table) add(x uint64, c int64, cs []int, ck uint64) {
	uc := uint64(c)
	for _, v := range cs {
		t.count[v] += c
		t.keySum[v] += uc * x
		t.chkSum[v] += uc * ck
	}
}

type decoded struct {
	ok     bool
	plus   map[uint64]bool // recovered A\B
	minus  map[uint64]bool // recovered B\A
	falsep int             // checksum-accepted keys that are not true differences (filled by caller)
	cnt    dcount
}

// dcount: work counters of one decoding (performance attribution).
type dcount struct {
	pops, cand, chkRej, memRej, sign, cellHash, chkHash int64
}

func decode(t *table, h hasher, signed bool, k int) decoded {
	M := len(t.count)
	cs := make([]int, k)
	stack := make([]int, 0, M)
	for v := 0; v < M; v++ {
		if t.count[v] == 1 || t.count[v] == -1 {
			stack = append(stack, v)
		}
	}
	res := decoded{plus: map[uint64]bool{}, minus: map[uint64]bool{}}
	for len(stack) > 0 {
		v := stack[len(stack)-1]
		stack = stack[:len(stack)-1]
		res.cnt.pops++
		c := t.count[v]
		if c != 1 && c != -1 {
			continue
		}
		res.cnt.cand++
		x := uint64(c) * t.keySum[v]
		ck := h.chk(x)
		res.cnt.chkHash++
		if t.chkSum[v] != uint64(c)*ck {
			res.cnt.chkRej++
			continue
		}
		h.cells(x, k, M, cs)
		res.cnt.cellHash++
		in := false
		for _, u := range cs {
			if u == v {
				in = true
			}
		}
		if !in {
			res.cnt.memRej++
			continue
		}
		if t.audit != nil {
			t.audit(v, x, c)
		}
		dir := c
		if signed {
			dir *= h.eps(x)
			res.cnt.sign++
		}
		if dir > 0 {
			res.plus[x] = true
		} else {
			res.minus[x] = true
		}
		t.add(x, -c, cs, ck)
		for _, u := range cs {
			if t.count[u] == 1 || t.count[u] == -1 {
				stack = append(stack, u)
			}
		}
	}
	res.ok = true
	for v := 0; v < M; v++ {
		if t.count[v] != 0 || t.keySum[v] != 0 || t.chkSum[v] != 0 {
			res.ok = false
			break
		}
	}
	return res
}

// upper bound rules -------------------------------------------------------------------------------

func sOf(n int64, M int) float64 { return math.Sqrt(2 * float64(n) * float64(n-1) / float64(M-1)) }

// largest returns the largest accepted candidate n >= 2 (a failure needs at least two edges), or -1
// for the empty set.
func largest(acc func(int64) bool) int64 {
	if !acc(2) {
		return -1
	}
	lo, hi := int64(2), int64(4)
	for acc(hi) {
		lo, hi = hi, 2*hi
	}
	for hi-lo > 1 {
		m := (lo + hi) / 2
		if acc(m) {
			lo = m
		} else {
			hi = m
		}
	}
	return lo
}

func phi(x float64) float64 { return 0.5 * math.Erfc(-x/math.Sqrt2) }

func upperChi(dhat, q float64, M int) int64 {
	return largest(func(n int64) bool { return dhat-float64(n) >= q*sOf(n, M) })
}

func upperMix(dhat, u float64, M int) int64 {
	cdf := func(x, sd float64) float64 {
		if sd == 0 {
			if x >= 0 {
				return 1
			}
			return 0
		}
		return phi(x / sd)
	}
	return largest(func(n int64) bool {
		sd := sOf(n, M)
		return (cdf(dhat-float64(n)+2, sd)+cdf(dhat-float64(n)-2, sd))/2 >= u
	})
}

// experiment --------------------------------------------------------------------------------------

type spec struct{ k, M1, d, common, onesided int }

// arms: (encoding, rule). signed_rchi_b raises the rchi bound to |b| = ||A|-|B|| (set sizes, or one global
// direction counter). standard+chi is the naive rule on the classic encoding (no selection
// correction); the corrected standard rules (env, selchi) are compared on stored samples in E2.
// signed_raw_b is the final rule: raw-energy inversion raised to |b|. standard_chi_b gives the classic
// encoding the same set-size information (b = sum C / k there) and the same empty-set fallback.
type armT struct {
	name   string
	signed bool
	rule   string
}

var allArms = []armT{{"signed_rchi", true, "rchi"}, {"signed_mix", true, "mix"}, {"signed_oracle", true, "oracle"},
	{"standard_chi", false, "rchi"}, {"signed_rchi_b", true, "rchi_b"}, {"signed_raw_b", true, "raw_b"}, {"standard_chi_b", false, "rchi_b_std"},
	{"standard_vldb", false, "vldb"}, {"standard_vldb_b", false, "vldb_b_std"}, {"signed_vldb", true, "vldb"},
	{"signed_vldb_b", true, "vldb_b"}}

// vldbQ: the worst failed-only q_{0.01} per first-round tier, copied from the VLDB manuscript
// (not-a-waste-paper/vldb-en/sections/04-protocol.tex, tab:capacity-tiers, commit b2aec07). The VLDB rule
// sizes from dhat/q_{0.01}; it is calibrated for k = 3 and delta = 0.01 only. Here U = ceil(dhat/q) is fed
// into the common round-2 map, so the baseline differs from the VLDB protocol in the decoder margin
// (beta = 1.56 there, 1/(theta alpha_c) here), in d_rec (0 here) and in joint peeling (not used here).
var vldbQ = map[int]float64{64: 0.6308, 256: 0.8045, 512: 0.8598, 1024: 0.8997, 4096: 0.9482}

func upperVldb(dhat float64, M int) int64 {
	q, ok := vldbQ[M]
	if !ok {
		panic(fmt.Sprintf("vldb rule undefined for M1=%d", M))
	}
	if dhat <= 0 {
		return 0
	}
	return int64(math.Ceil(dhat / q))
}

var arms = allArms[:5]

type acc struct {
	trials, f1, f1miss, f1empty, f2, fail, falsep, wrong int64
	m2sum, bytesSum                                      float64
	m2s                                                  []float64
	encNs, decNs, sizeNs                                 float64
	encKeys, decKeys                                     float64
	sizeColdNs, sizeWarmNs                               float64
	coldN                                                int
	protoNs                                              float64 // round 1 + sizing + round 2, per trial
	tabPeak                                              int     // largest Poisson-table cache over workers (entries)
	coldPeak                                             int     // largest table set built by one first-session call
	dc                                                   dcount
}

const cellBytes = 20 // count int32 on the wire + keySum + chkSum (uint64 each)

func main() {
	qpath := flag.String("q", "qtable.json", "quantile table keyed by M")
	specPath := flag.String("spec", "", "spec file")
	trials := flag.Int("trials", 1000, "trials per spec line")
	out := flag.String("out", "iblt2r.csv", "output csv")
	jobs := flag.Int("jobs", runtime.NumCPU(), "workers")
	seed := flag.Uint64("seed", 1, "run seed")
	u := flag.Float64("u", 0.01, "risk level for the sizing rule")
	theta := flag.Float64("theta", 0.8, "round-2 target load as a fraction of alpha_c")
	mmin := flag.Int("mmin", 64, "minimum round-2 table size")
	flag.Float64Var(&rawLamStar, "lamstar", math.Inf(1), "Poisson mean above which the raw rule uses the normal approximation (default: exact)")
	flag.IntVar(&maxTabEntries, "tabcap", 4_000_000, "Poisson-table cache entries per raw engine")
	flag.BoolVar(&rawBernstein, "bernstein", true, "use the Bernstein search cutoff of the raw rule (false: cutoff (10) only)")
	armList := flag.String("arms", "", "comma-separated arm names (default: the first five)")
	trialOut := flag.String("trialout", "", "optional csv with one line per (trial, arm) that fails round 1: spec,trial,arm,U,M2,ok2 (U=-1: empty set)")
	flag.Parse()
	if *stressMode {
		runDecodeStress(*out, *jobs, *seed)
		return
	}
	if *rejectMode {
		runDecodeReject(*out, *jobs, *seed)
		return
	}
	if *armList != "" {
		arms = nil
		for _, nm := range strings.Split(*armList, ",") {
			found := false
			for _, a := range allArms {
				if a.name == nm {
					arms, found = append(arms, a), true
				}
			}
			if !found {
				panic("unknown arm " + nm)
			}
		}
	}
	for _, a := range arms {
		if strings.Contains(a.rule, "vldb") && *u != 0.01 {
			panic("the vldb arms are calibrated for u = 0.01 only")
		}
	}
	var tw *bufio.Writer
	var twMu sync.Mutex
	if *trialOut != "" {
		tf, err := os.Create(*trialOut)
		must(err)
		defer tf.Close()
		tw = bufio.NewWriterSize(tf, 1<<20)
		defer tw.Flush()
		fmt.Fprintln(tw, "spec,trial,arm,U,M2,ok2")
	}
	emit := func(si, t int, arm string, U int64, M2 int, ok2 bool) {
		if tw == nil {
			return
		}
		o := 0
		if ok2 {
			o = 1
		}
		twMu.Lock()
		fmt.Fprintf(tw, "%d,%d,%s,%d,%d,%d\n", si, t, arm, U, M2, o)
		twMu.Unlock()
	}
	var qtab map[string]map[string]float64
	b, err := os.ReadFile(*qpath)
	must(err)
	must(json.Unmarshal(b, &qtab))
	qkey := "rchi01"
	if *u == 0.05 {
		qkey = "rchi05"
	} else if *u != 0.01 {
		panic("u must be 0.01 or 0.05")
	}
	var specs []spec
	sb, err := os.ReadFile(*specPath)
	must(err)
	for _, ln := range strings.Split(string(sb), "\n") {
		f := strings.Fields(ln)
		if len(f) != 5 || strings.HasPrefix(ln, "#") {
			continue
		}
		v := make([]int, 5)
		for i := range f {
			v[i], err = strconv.Atoi(f[i])
			must(err)
		}
		specs = append(specs, spec{v[0], v[1], v[2], v[3], v[4]})
	}
	fo, err := os.Create(*out)
	must(err)
	w := bufio.NewWriter(fo)
	fmt.Fprintln(w, "k,M1,d,common,onesided,arm,trials,f1,f1_miss,f1_empty,f2,fail,falsepos,wrong,mean_M2,median_M2,mean_bytes,enc_ns_per_key,dec_ns_per_key,size_ns,agree_signed_standard,size_ns_cold,dec_pops,dec_cand,dec_chkrej,dec_memrej,dec_sign,dec_cellhash,dec_chkhash,size_ns_warm,proto_ns_per_trial,tab_mb_peak,cold_mb_peak,dec_ns_per_trial")
	for si, sp := range specs {
		q, ok := qtab[fmt.Sprint(sp.M1)]
		if !ok {
			panic(fmt.Sprintf("no quantile for M=%d", sp.M1))
		}
		accs := make([]acc, len(arms))
		var agree, total int64
		var mu sync.Mutex
		var wg sync.WaitGroup
		next := make(chan int)
		for j := 0; j < *jobs; j++ {
			wg.Add(1)
			go func() {
				defer wg.Done()
				local := make([]acc, len(arms))
				var la, lt int64
				// Consecutive sessions of one receiver: (M, k) fixed, the Poisson tables persist across trials
				// (LRU eviction at -tabcap), the observed S2 changes and the upper bound is recomputed.
				tcache := newPoisCache(sp.M1, sp.k)
				warm := newRawShared(tcache, *u, false)
				for t := range next {
					rng := rand.New(rand.NewPCG(*seed^uint64(si)<<40, uint64(t)))
					dplus := sp.d / 2
					if sp.onesided == 1 {
						dplus = sp.d
					}
					seen := map[uint64]bool{}
					draw := func(n int) []uint64 {
						r := make([]uint64, 0, n)
						for len(r) < n {
							x := rng.Uint64()
							if x != 0 && !seen[x] {
								seen[x] = true
								r = append(r, x)
							}
						}
						return r
					}
					common, onlyA, onlyB := draw(sp.common), draw(dplus), draw(sp.d-dplus)
					A := append(append([]uint64{}, common...), onlyA...)
					B := append(append([]uint64{}, common...), onlyB...)
					truthP, truthM := map[uint64]bool{}, map[uint64]bool{}
					for _, x := range onlyA {
						truthP[x] = true
					}
					for _, x := range onlyB {
						truthM[x] = true
					}
					h1 := hasher{rng.Uint64(), rng.Uint64(), rng.Uint64()}
					h2 := hasher{rng.Uint64(), h1.signSeed, h1.chkSeed}
					var r1ok [2]bool
					var r1done [2]bool
					for ai, arm := range arms {
						a := &local[ai]
						a.trials++
						ei := 0
						if !arm.signed {
							ei = 1
						}
						ts := time.Now()
						t1 := encodeSets(h1, arm.signed, sp.k, sp.M1, A, B)
						a.encNs += float64(time.Since(ts).Nanoseconds())
						a.protoNs += float64(time.Since(ts).Nanoseconds())
						a.encKeys += float64(len(A) + len(B))
						var s1, s2 int64
						for _, c := range t1.count {
							s1 += c
							s2 += c * c
						}
						ts = time.Now()
						d1 := decode(t1, h1, arm.signed, sp.k)
						a.decNs += float64(time.Since(ts).Nanoseconds())
						a.protoNs += float64(time.Since(ts).Nanoseconds())
						a.dc.pops += d1.cnt.pops
						a.dc.cand += d1.cnt.cand
						a.dc.chkRej += d1.cnt.chkRej
						a.dc.memRej += d1.cnt.memRej
						a.dc.sign += d1.cnt.sign
						a.dc.cellHash += d1.cnt.cellHash
						a.dc.chkHash += d1.cnt.chkHash
						a.decKeys += float64(len(d1.plus) + len(d1.minus))
						if !r1done[ei] {
							r1ok[ei], r1done[ei] = d1.ok, true
						}
						bytes := float64(sp.M1 * cellBytes)
						if arm.rule == "rchi_b" || arm.rule == "raw_b" || arm.rule == "vldb_b" {
							bytes += 8 // global direction counter (or exchanged set sizes)
						}
						if d1.ok {
							a.falsep += countWrong(d1, truthP, truthM)
							if !sameAs(d1, truthP, truthM) {
								a.wrong++
							}
							a.bytesSum += bytes
							continue
						}
						a.f1++
						ts = time.Now()
						M := sp.M1
						gamma := float64(sp.k) * (1 - float64(sp.k)/float64(M))
						dhat := (float64(s2) - float64(s1)*float64(s1)/float64(M)) / gamma
						var U int64
						switch arm.rule {
						case "rchi":
							U = upperChi(dhat, q[qkey], M)
						case "mix":
							U = upperMix(dhat, *u, M)
						case "oracle":
							U = int64(sp.d)
						case "rchi_b":
							// b = d+ - d- = |A| - |B| from the exchanged set sizes; d >= |b| always
							U = upperChi(dhat, q[qkey], M)
							b := int64(len(A) - len(B))
							if b < 0 {
								b = -b
							}
							if U >= 0 && U < b {
								U = b
							}
						case "raw_b":
							U = warm.upper(s2)
							b := int64(len(A) - len(B))
							if b < 0 {
								b = -b
							}
							if U >= 0 && U < b {
								U = b
							}
						case "vldb":
							U = upperVldb(dhat, M)
						case "vldb_b":
							U = upperVldb(dhat, M)
							b := int64(len(A) - len(B))
							if b < 0 {
								b = -b
							}
							if U < b {
								U = b
							}
						case "vldb_b_std":
							U = upperVldb(dhat, M)
							b := s1 / int64(sp.k)
							if b < 0 {
								b = -b
							}
							if U < b {
								U = b
							}
						case "rchi_b_std":
							// classic encoding: sum C = k (d+ - d-), so |b| is read from the same counts
							U = upperChi(dhat, q[qkey], M)
							b := s1 / int64(sp.k)
							if b < 0 {
								b = -b
							}
							if U >= 0 && U < b {
								U = b
							}
						}
						a.sizeNs += float64(time.Since(ts).Nanoseconds())
						a.protoNs += float64(time.Since(ts).Nanoseconds())
						if arm.rule == "raw_b" && t%16 == 0 { // cold and warm timing on a subsample of trials
							a.coldN++
							ts = time.Now()
							ce := newRaw(sp.M1, sp.k, *u, false)
							ce.upper(s2) // first session: empty tables
							a.sizeColdNs += float64(time.Since(ts).Nanoseconds())
							if ce.cache.peak > a.coldPeak {
								a.coldPeak = ce.cache.peak
							}
							ts = time.Now()
							warm.upper(s2) // same observation again: every table it needs is cached
							a.sizeWarmNs += float64(time.Since(ts).Nanoseconds())
						}
						var M2 int
						if U < 0 {
							a.f1empty++
							M2 = 4 * sp.M1
						} else {
							if U < int64(sp.d) {
								a.f1miss++
							}
							M2 = int(math.Ceil(float64(U) / (*theta * alphaC[sp.k])))
							if M2 < *mmin {
								M2 = *mmin
							}
						}
						a.m2sum += float64(M2)
						a.m2s = append(a.m2s, float64(M2))
						bytes += float64(M2 * cellBytes)
						if arm.rule == "rchi_b" || arm.rule == "raw_b" || arm.rule == "vldb_b" {
							bytes += 8
						}
						a.bytesSum += bytes
						ts = time.Now()
						t2 := encodeSets(h2, arm.signed, sp.k, M2, A, B)
						d2 := decode(t2, h2, arm.signed, sp.k)
						a.protoNs += float64(time.Since(ts).Nanoseconds())
						if !d2.ok {
							a.f2++
							a.fail++
							emit(si, t, arm.name, U, M2, false)
							continue
						}
						a.falsep += countWrong(d2, truthP, truthM)
						same := sameAs(d2, truthP, truthM)
						if !same {
							a.wrong++
						}
						emit(si, t, arm.name, U, M2, same)
					}
					lt++
					if r1ok[0] == r1ok[1] {
						la++
					}
				}
				mu.Lock()
				for i := range accs {
					m := &accs[i]
					l := local[i]
					m.trials += l.trials
					m.f1 += l.f1
					m.f1miss += l.f1miss
					m.f1empty += l.f1empty
					m.f2 += l.f2
					m.fail += l.fail
					m.falsep += l.falsep
					m.wrong += l.wrong
					m.m2sum += l.m2sum
					m.bytesSum += l.bytesSum
					m.m2s = append(m.m2s, l.m2s...)
					m.encNs += l.encNs
					m.decNs += l.decNs
					m.sizeNs += l.sizeNs
					m.encKeys += l.encKeys
					m.sizeColdNs += l.sizeColdNs
					m.coldN += l.coldN
					m.sizeWarmNs += l.sizeWarmNs
					m.protoNs += l.protoNs
					if l.coldPeak > m.coldPeak {
						m.coldPeak = l.coldPeak
					}
					if arms[i].rule == "raw_b" && tcache.peak > m.tabPeak {
						m.tabPeak = tcache.peak
					}
					m.dc.pops += l.dc.pops
					m.dc.cand += l.dc.cand
					m.dc.chkRej += l.dc.chkRej
					m.dc.memRej += l.dc.memRej
					m.dc.sign += l.dc.sign
					m.dc.cellHash += l.dc.cellHash
					m.dc.chkHash += l.dc.chkHash
					m.decKeys += l.decKeys
				}
				agree += la
				total += lt
				mu.Unlock()
			}()
		}
		for t := 0; t < *trials; t++ {
			next <- t
		}
		close(next)
		wg.Wait()
		for i, arm := range arms {
			a := accs[i]
			med := math.NaN()
			if len(a.m2s) > 0 {
				sort.Float64s(a.m2s)
				med = a.m2s[len(a.m2s)/2]
			}
			meanM2, sizeNs := math.NaN(), math.NaN()
			if a.f1 > 0 {
				meanM2 = a.m2sum / float64(a.f1)
				sizeNs = a.sizeNs / float64(a.f1)
			}
			sizeCold, sizeWarm, tabMB, coldMB := math.NaN(), math.NaN(), math.NaN(), math.NaN()
			if a.coldN > 0 {
				sizeCold = a.sizeColdNs / float64(a.coldN)
				sizeWarm = a.sizeWarmNs / float64(a.coldN)
				tabMB = float64(a.tabPeak) * 16 / 1e6
				coldMB = float64(a.coldPeak) * 16 / 1e6
			}
			dk := math.Max(a.decKeys, 1)
			fmt.Fprintf(w, "%d,%d,%d,%d,%d,%s,%d,%d,%d,%d,%d,%d,%d,%d,%.2f,%.0f,%.1f,%.2f,%.2f,%.0f,%d/%d,%.0f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.0f,%.0f,%.1f,%.1f,%.0f\n",
				sp.k, sp.M1, sp.d, sp.common, sp.onesided, arm.name, a.trials, a.f1, a.f1miss, a.f1empty, a.f2, a.fail,
				a.falsep, a.wrong, meanM2, med, a.bytesSum/float64(a.trials), a.encNs/a.encKeys, a.decNs/dk, sizeNs, agree, total,
				sizeCold, float64(a.dc.pops)/dk, float64(a.dc.cand)/dk, float64(a.dc.chkRej)/dk, float64(a.dc.memRej)/dk,
				float64(a.dc.sign)/dk, float64(a.dc.cellHash)/dk, float64(a.dc.chkHash)/dk,
				sizeWarm, a.protoNs/float64(a.trials), tabMB, coldMB, a.decNs/float64(a.trials))
		}
		w.Flush()
		fmt.Fprintf(os.Stderr, "spec %d/%d done: k=%d M1=%d d=%d onesided=%d\n", si+1, len(specs), sp.k, sp.M1, sp.d, sp.onesided)
	}
	w.Flush()
	fo.Close()
}

func encodeSets(h hasher, signed bool, k, M int, A, B []uint64) *table {
	t := newTable(M)
	cs := make([]int, k)
	for _, x := range A {
		c := int64(1)
		if signed {
			c = h.eps(x)
		}
		h.cells(x, k, M, cs)
		t.add(x, c, cs, h.chk(x))
	}
	for _, x := range B {
		c := int64(-1)
		if signed {
			c = -h.eps(x)
		}
		h.cells(x, k, M, cs)
		t.add(x, c, cs, h.chk(x))
	}
	return t
}

func countWrong(r decoded, P, N map[uint64]bool) int64 {
	var n int64
	for x := range r.plus {
		if !P[x] {
			n++
		}
	}
	for x := range r.minus {
		if !N[x] {
			n++
		}
	}
	return n
}

func sameAs(r decoded, P, N map[uint64]bool) bool {
	if len(r.plus) != len(P) || len(r.minus) != len(N) {
		return false
	}
	return countWrong(r, P, N) == 0
}

func must(err error) {
	if err != nil {
		panic(err)
	}
}
