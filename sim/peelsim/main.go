// peelsim: proof-diagnostic simulator for the Plain IBLT peeling critical window.
//
// One trial = one Plain mapping hypergraph (d edges, each a uniform k-subset of
// [M] with distinct cells; different edges may coincide).  On that single graph
// it records:
//
//   - the standardized measurement X_v = (dhat_v - d)/sqrt(2d(d-1)/(M-1)) for
//     several sign variants v (fixed negative ratios and iid random signs),
//     all sharing the same mapping (experiments A and B);
//   - unsigned initial-profile statistics: n0,n1,n2, S2c = sum_i (D_i - kd/M)^2,
//     Hc = sum_i D_i s_c^(D_i-1) (candidate critical influence functional),
//     and VsIID = Var_s(X | mapping) for iid signs, computed exactly from the
//     pair overlaps W_xy = H_xy - k^2/M;
//   - the ideal peeling outcome (failed iff nonempty 2-core), core size, and
//     the degree-one set size Q(t) after t removals at t = floor(j d / G),
//     j = 0..G, under uniformly random choice among degree-one cells
//     (-1 once the process has stopped before t);
//   - optionally (experiment C) the failure frequency of R re-pairings of the
//     same unsigned degree sequence, both as a raw configuration model
//     (within-edge repeats allowed) and conditioned on no within-edge repeats
//     (rejection; exactly the Plain law given the degree sequence).
//
// Records are fixed-size little-endian 4-byte fields; the layout is written
// to manifest.json.  Mapping, signs, peeling order and re-pairing use
// separate PCG streams derived from an explicit run seed.
package main

import (
	"bufio"
	"encoding/binary"
	"encoding/json"
	"flag"
	"fmt"
	"math"
	"math/big"
	"math/rand/v2"
	"os"
	"path/filepath"
	"runtime"
	"strconv"
	"strings"
	"sync"
	"sync/atomic"
	"time"
)

// Boundary-experiment options (all off by default; the record layout is then
// identical to round 1/2).
var (
	optConfig bool     // configuration model: k iid uniform endpoints per edge, repeats allowed
	optPlant  bool     // uniformly chosen edge labels share a mapping
	optScore  bool     // record the precritical score R_M, H_M and core duplicate pairs
	optEps    []string // score times t_- = t_* - eps: "m8" = M^-1/8, "m4" = M^-1/4, or a number
	optSrep   int      // random fixed-composition sign redraws per graph
	optSrepC  string   // composition token for the redraws (same syntax as -signs)
	optKeep   int      // >0: per chunk write the first optKeep trials plus every later failed trial
	optDupIdx bool     // with -score: record the edge indices of the first identical pair in the core
	optSumC   bool     // record exact integers S1_rand = sum_v C_v and S2_rand = sum_v C_v^2 of the rand variant
)

type spec struct {
	M, K, D, Trials int
}

type variant struct {
	Name     string  `json:"name"`
	NegRatio float64 `json:"neg_ratio"` // <0 means iid random signs
	NegCount int     `json:"neg_count"`
	RandSign bool    `json:"rand_sign,omitempty"` // random-sign encoding: coefficient s_e * eps_e, eps_e iid
	Rho      float64 `json:"rho"`                 // realized for fixed; NaN->0 reported for iid
}

type cfgMeta struct {
	Index    int       `json:"index"`
	M        int       `json:"M"`
	K        int       `json:"k"`
	D        int       `json:"d"`
	Load     float64   `json:"load"`
	Trials   int       `json:"trials"`
	Chunks   int       `json:"chunks"`
	Variants []variant `json:"variants"`
	SC       float64   `json:"s_c"`
	MuC      float64   `json:"mu_c"`
	XC       float64   `json:"x_c"`
	Failed   int64     `json:"failed"`
	Seconds  float64   `json:"seconds"`
}

type manifest struct {
	CodeVersion string    `json:"code_version"`
	RNGSeeding  string    `json:"rng_seeding"`
	PlantScheme string    `json:"plant_scheme"`
	RunSeed     uint64    `json:"run_seed"`
	Args        []string  `json:"args"`
	Fields      []string  `json:"fields"`
	FieldTypes  []string  `json:"field_types"`
	RecordBytes int       `json:"record_bytes"`
	QGrid       int       `json:"qgrid"`
	RSimple     int       `json:"r_simple"`
	RConfig     int       `json:"r_config"`
	Configs     []cfgMeta `json:"configs"`
	Started     string    `json:"started"`
	Finished    string    `json:"finished"`
	Resumes     int       `json:"resumes"`
	ChunksDone  int64     `json:"chunks_done"`
	ChunksTotal int       `json:"chunks_total"`
	Updated     string    `json:"updated"`
}

// critical point of the k-uniform 2-core: mu(x) = x/(1-e^{-x})^{k-1} minimized.
func critical(k int) (xc, muc, sc float64) {
	f := func(x float64) float64 { return x / math.Pow(1-math.Exp(-x), float64(k-1)) }
	a, b := 0.01, 20.0
	g := (math.Sqrt(5) - 1) / 2
	for i := 0; i < 200; i++ {
		c, d := b-g*(b-a), a+g*(b-a)
		if f(c) < f(d) {
			b = d
		} else {
			a = c
		}
	}
	xc = (a + b) / 2
	muc = f(xc)
	sc = 1 - xc/muc // s = 1 - q^{k-1}, x = mu q^{k-1}
	return
}

type worker struct {
	M, K, D  int
	vars     []variant
	qgrid    int
	rSimple  int
	rConfig  int
	pairs    bool
	sc       float64
	cells    []int32 // D*K
	deg      []int32
	deg0     []int32
	xor      []int32
	sumID    []int64
	cnt      []int64
	ones     []int32
	pos      []int32
	csrStart []int32
	csr      []int32
	mark     []int32
	touched  []int32
	stubs    []int32
	rcells   []int32
	stack    []int32
	tgrid    []int
	signs    []int8
	coef     []int8     // selftest only: coefficients of the last variant
	re       *rand.Rand // eps stream of the random-sign variants (separate, so rs is unchanged)
	powc     []float64

	plantI, plantJ int
	rplant         *rand.Rand

	// score
	nMinus  []int       // per eps, increasing removal counts (-1: not representable)
	fB      [][]float64 // per eps, f_j(b_-)
	scoreC  float64     // M m_M(t_*)
	scoreSc float64     // x_c sqrt(M)
	hCenter float64     // M E_Pois(mu_M) h_c
	hScale  float64     // mu_c sqrt(M)
	// sign redraws
	lx     []float64
	sarr   []int8
	srNeg  int
	srCoef [3]float64 // Var(Y|G) = c0 B + c1 A + c2 W^2
	srA2   float64
}

func newWorker(M, K, D int, vars []variant, qgrid, rs, rc int, pairs bool, sc float64) *worker {
	w := &worker{M: M, K: K, D: D, vars: vars, qgrid: qgrid, rSimple: rs, rConfig: rc, pairs: pairs, sc: sc}
	w.rplant = rand.New(rand.NewPCG(11, 12)) // selftest default; production sets a separate seeded stream
	w.cells = make([]int32, D*K)
	w.deg = make([]int32, M)
	w.deg0 = make([]int32, M)
	w.xor = make([]int32, M)
	w.sumID = make([]int64, M)
	w.cnt = make([]int64, M)
	w.ones = make([]int32, 0, M)
	w.pos = make([]int32, M)
	w.csrStart = make([]int32, M+1)
	w.csr = make([]int32, D*K)
	w.mark = make([]int32, D)
	w.touched = make([]int32, 0, 1024)
	w.stubs = make([]int32, D*K)
	w.rcells = make([]int32, D*K)
	w.stack = make([]int32, 0, M)
	w.signs = make([]int8, D)
	if qgrid > 0 {
		w.tgrid = make([]int, qgrid+1)
		for j := 0; j <= qgrid; j++ {
			w.tgrid[j] = j * D / qgrid
		}
	}
	if optScore {
		xc, muc, _ := critical(K)
		mf, kf, df := float64(M), float64(K), float64(D)
		qc := 1 - math.Exp(-xc)
		ac := math.Pow(qc, kf-1)
		muM := kf * df / mf
		tStar := df / mf * (1 - math.Pow(qc, kf))
		for _, tag := range optEps {
			eps := epsValue(tag, mf)
			n := int(math.Floor(mf * (tStar - eps)))
			if n < 0 {
				n = -1
			}
			tm := float64(n) / mf
			aM := math.Pow((muM-kf*tm)/muM, (kf-1)/kf)
			b := ac / aM
			f := make([]float64, 256)
			for j := 2; j < len(f); j++ {
				f[j] = float64(j) * b * (1 - math.Pow(1-b, float64(j-1)))
			}
			w.nMinus = append(w.nMinus, n)
			w.fB = append(w.fB, f)
		}
		w.scoreC = kf * df * math.Pow(qc, kf)
		w.scoreSc = xc * math.Sqrt(mf)
		w.hCenter = mf * muM * math.Exp(-muM*ac)
		w.hScale = muc * math.Sqrt(mf)
	}
	if optSrep > 0 {
		w.lx = make([]float64, D)
		w.sarr = make([]int8, D)
		w.srNeg = parseVariants(optSrepC, D)[0].NegCount
		w.srA2, w.srCoef = fixedCompCoef(D, D-2*w.srNeg)
	}
	w.powc = make([]float64, 4*D/M+64)
	for j := range w.powc {
		if j == 0 {
			w.powc[j] = 0
		} else {
			w.powc[j] = float64(j) * math.Pow(sc, float64(j-1))
		}
	}
	return w
}

// fixedCompCoef: for n uniform fixed-composition signs with sum S, a2 = E s_x s_y,
// and the exact coefficients of Var(Y|G) = c0 B + c1 A + c2 W^2 (theory/fixed-sign
// proof, eq. 9), computed in exact rational arithmetic.
func fixedCompCoef(n, S int) (float64, [3]float64) {
	N, S2 := big.NewRat(int64(n), 1), new(big.Rat).SetInt64(int64(S)*int64(S))
	one := big.NewRat(1, 1)
	r := func(v int64) *big.Rat { return big.NewRat(v, 1) }
	a2 := new(big.Rat).Sub(S2, N)
	a2.Quo(a2, new(big.Rat).Mul(N, r(int64(n-1))))
	S4 := new(big.Rat).Mul(S2, S2)
	num := new(big.Rat).Sub(S4, new(big.Rat).Mul(r(int64(6*n-8)), S2))
	num.Add(num, r(3*int64(n)*int64(n-2)))
	den := r(int64(n) * int64(n-1) * int64(n-2) * int64(n-3))
	a4 := new(big.Rat).Quo(num, den)
	c0 := new(big.Rat).Sub(one, new(big.Rat).Mul(r(2), a2))
	c0.Add(c0, a4)
	c1 := new(big.Rat).Sub(a2, a4)
	c2 := new(big.Rat).Sub(a4, new(big.Rat).Mul(a2, a2))
	f := func(x *big.Rat) float64 { v, _ := x.Float64(); return v }
	return f(a2), [3]float64{f(c0), f(c1), f(c2)}
}

func epsValue(tag string, mf float64) float64 {
	switch tag {
	case "m8":
		return math.Pow(mf, -0.125)
	case "m4":
		return math.Pow(mf, -0.25)
	}
	v, err := strconv.ParseFloat(tag, 64)
	if err != nil {
		panic(err)
	}
	return v
}

func (w *worker) hc(j int32) float64 {
	if int(j) < len(w.powc) {
		return w.powc[j]
	}
	return float64(j) * math.Pow(w.sc, float64(j-1))
}

func nFields(nv, qgrid, rs, rc int) int {
	n := nv + 1 + 5 + 3 + 0
	if qgrid > 0 {
		n += qgrid + 1
	}
	if rs > 0 {
		n += 3
	}
	if rc > 0 {
		n += 2
	}
	if optScore {
		n += 2 + 2*len(optEps)
		if optDupIdx {
			n += 2
		}
	}
	if optSrep > 0 {
		n += 4
	}
	if optSumC {
		n += 2
	}
	if optKeep > 0 {
		n++
	}
	return n
}

func fieldNames(vars []variant, qgrid, rs, rc int) ([]string, []string) {
	var f, t []string
	for _, v := range vars {
		f = append(f, "X_"+v.Name)
		t = append(t, "f32")
	}
	for _, s := range []string{"failed", "core_edges", "core_cells", "n0", "n1", "n2"} {
		f = append(f, s)
		t = append(t, "i32")
	}
	for _, s := range []string{"S2c", "Hc", "VsIID"} {
		f = append(f, s)
		t = append(t, "f32")
	}
	for j := 0; qgrid > 0 && j <= qgrid; j++ {
		f = append(f, fmt.Sprintf("Q%d", j))
		t = append(t, "i32")
	}
	if rs > 0 {
		f = append(f, "simple_fail_frac", "simple_core_mean", "simple_attempts")
		t = append(t, "f32", "f32", "i32")
	}
	if rc > 0 {
		f = append(f, "config_fail_frac", "config_core_mean")
		t = append(t, "f32", "f32")
	}
	if optScore {
		f = append(f, "Hs", "core_dup")
		t = append(t, "f32", "i32")
		for _, e := range optEps {
			f = append(f, "reached_"+e, "R_"+e)
			t = append(t, "i32", "f32")
		}
		if optDupIdx {
			f = append(f, "dup_a", "dup_b") // -1: no identical pair counted
			t = append(t, "i32", "i32")
		}
	}
	if optSrep > 0 {
		f = append(f, "SR_mean", "SR_var", "SR_exmean", "SR_exvar")
		t = append(t, "f32", "f32", "f32", "f32")
	}
	if optSumC {
		f = append(f, "S1_rand", "S2_rand")
		t = append(t, "i32", "i32")
	}
	if optKeep > 0 {
		f = append(f, "uncond") // 1: among the first optKeep trials of its chunk (unconditional sample)
		t = append(t, "i32")
	}
	return f, t
}

// genericPeel: 2-core by leaf removal on edges given as K consecutive cells in
// rc (multiplicities allowed).  Returns number of edges left in the core.
func (w *worker) genericPeel(rc []int32) int {
	M, K, D := w.M, w.K, w.D
	for i := 0; i < M; i++ {
		w.deg[i], w.sumID[i] = 0, 0
	}
	for e := 0; e < D; e++ {
		id := int64(e + 1)
		for j := 0; j < K; j++ {
			c := rc[e*K+j]
			w.deg[c]++
			w.sumID[c] += id
		}
	}
	st := w.stack[:0]
	for c := 0; c < M; c++ {
		if w.deg[c] == 1 {
			st = append(st, int32(c))
		}
	}
	removed := 0
	for len(st) > 0 {
		c := st[len(st)-1]
		st = st[:len(st)-1]
		if w.deg[c] != 1 {
			continue
		}
		id := w.sumID[c]
		e := int(id - 1)
		for j := 0; j < K; j++ {
			c2 := rc[e*K+j]
			w.deg[c2]--
			w.sumID[c2] -= id
			if w.deg[c2] == 1 {
				st = append(st, c2)
			}
		}
		removed++
	}
	w.stack = st
	return D - removed
}

// uniformPair samples each unordered label pair with probability 1/C(d,2).
func uniformPair(r *rand.Rand, d int) (int, int) {
	if d < 2 {
		panic("planted sampling requires d >= 2")
	}
	i, j := r.IntN(d), r.IntN(d-1)
	if j >= i {
		j++
	}
	if i > j {
		i, j = j, i
	}
	return i, j
}

func savedPlantScheme(m manifest) string {
	if m.PlantScheme != "" {
		return m.PlantScheme
	}
	for _, arg := range m.Args {
		if arg == "-plant-dup" || arg == "--plant-dup" || arg == "-plant-dup=true" || arg == "--plant-dup=true" {
			return "fixed-last-pair-v0"
		}
	}
	return "none"
}

func (w *worker) trial(rm, rs, rp, rr *rand.Rand, rec []uint32) {
	M, K, D := w.M, w.K, w.D
	mf, kf, df := float64(M), float64(K), float64(D)
	gamma := kf * (1 - kf/mf)
	sdd := math.Sqrt(2 * df * (df - 1) / (mf - 1))
	for i := 0; i < M; i++ {
		w.deg0[i] = 0
	}
	// Select labels independently of mapping, signs, and peeling streams.
	if optPlant {
		w.plantI, w.plantJ = uniformPair(w.rplant, D)
	}
	// mapping
	for e := 0; e < D; e++ {
		base := e * K
	pick:
		for n := 0; n < K; {
			c := int32(rm.IntN(M))
			for j := 0; j < n && !optConfig; j++ {
				if w.cells[base+j] == c {
					continue pick
				}
			}
			w.cells[base+n] = c
			n++
		}
		if optPlant && e == w.plantJ {
			// draw as usual (keeps the mapping stream aligned with the unplanted run), then copy
			copy(w.cells[base:base+K], w.cells[w.plantI*K:(w.plantI+1)*K])
		}
		for j := 0; j < K; j++ {
			w.deg0[w.cells[base+j]]++
		}
	}
	f := 0
	// sign variants
	for _, v := range w.vars {
		for i := 0; i < M; i++ {
			w.cnt[i] = 0
		}
		for e := 0; e < D; e++ {
			var s int64 = 1
			if v.NegRatio < 0 {
				if rs.IntN(2) == 0 {
					s = -1
				}
			} else if e < v.NegCount {
				s = -1
			}
			if v.RandSign && w.re.IntN(2) == 0 {
				s = -s
			}
			if w.coef != nil {
				w.coef[e] = int8(s)
			}
			for j := 0; j < K; j++ {
				w.cnt[w.cells[e*K+j]] += s
			}
		}
		var s1, s2 float64
		for i := 0; i < M; i++ {
			c := float64(w.cnt[i])
			s1 += c
			s2 += c * c
		}
		dhat := (s2 - s1*s1/mf) / gamma
		rec[f] = math.Float32bits(float32((dhat - df) / sdd))
		f++
		if optSumC && v.NegRatio < 0 {
			if s2 > math.MaxInt32 {
				panic("S2_rand overflows int32")
			}
			o := len(rec) - 2
			if optKeep > 0 {
				o--
			}
			rec[o] = uint32(int32(s1))
			rec[o+1] = uint32(int32(s2))
		}
	}
	// profile stats
	var n0, n1, n2 int32
	var s2c, hcs float64
	mu := kf * df / mf
	for i := 0; i < M; i++ {
		dg := w.deg0[i]
		switch dg {
		case 0:
			n0++
		case 1:
			n1++
		case 2:
			n2++
		}
		x := float64(dg) - mu
		s2c += x * x
		hcs += w.hc(dg)
	}
	// exact Var_s(X|mapping) for iid signs
	vs := math.NaN()
	for x := range w.lx {
		w.lx[x] = 0
	}
	if w.pairs {
		w.csrStart[0] = 0
		for i := 0; i < M; i++ {
			w.csrStart[i+1] = w.csrStart[i] + w.deg0[i]
		}
		fill := w.pos // reuse as cursor
		for i := 0; i < M; i++ {
			fill[i] = w.csrStart[i]
		}
		for e := 0; e < D; e++ {
			for j := 0; j < K; j++ {
				c := w.cells[e*K+j]
				w.csr[fill[c]] = int32(e)
				fill[c]++
			}
		}
		var sumH, sumH2 float64
		for x := 0; x < D; x++ {
			w.touched = w.touched[:0]
			for j := 0; j < K; j++ {
				c := w.cells[x*K+j]
				for p := w.csrStart[c]; p < w.csrStart[c+1]; p++ {
					y := w.csr[p]
					if int(y) > x {
						if w.mark[y] == 0 {
							w.touched = append(w.touched, y)
						}
						w.mark[y]++
					}
				}
			}
			for _, y := range w.touched {
				h := float64(w.mark[y])
				sumH += h
				sumH2 += h * h
				if w.lx != nil {
					w.lx[x] += h
					w.lx[y] += h
				}
				w.mark[y] = 0
			}
		}
		if optSrep > 0 {
			w.signRedraws(rs, rec, sumH, sumH2)
		}
		a := kf * kf / mf
		npairs := df * (df - 1) / 2
		sumW2 := sumH2 - 2*a*sumH + npairs*a*a
		vs = 4 * sumW2 / (gamma * gamma) / (sdd * sdd)
	}
	// peeling with uniform choice among degree-one cells
	for i := 0; i < M; i++ {
		w.deg[i] = w.deg0[i]
		w.sumID[i] = 0
		w.pos[i] = -1
	}
	for e := 0; e < D; e++ {
		id := int64(e + 1)
		for j := 0; j < K; j++ {
			w.sumID[w.cells[e*K+j]] += id
		}
	}
	ones := w.ones[:0]
	add := func(c int32) {
		w.pos[c] = int32(len(ones))
		ones = append(ones, c)
	}
	del := func(c int32) {
		p := w.pos[c]
		last := ones[len(ones)-1]
		ones[p] = last
		w.pos[last] = p
		ones = ones[:len(ones)-1]
		w.pos[c] = -1
	}
	for c := 0; c < M; c++ {
		if w.deg[c] == 1 {
			add(int32(c))
		}
	}
	qstart := f + 1 + 5 + 3
	nextj := 0
	removed := 0
	ne := len(w.nMinus)
	var reached [16]int32
	var score [16]float64
	for i := 0; i < ne; i++ {
		score[i] = math.NaN()
	}
	for len(ones) > 0 {
		for w.qgrid > 0 && nextj <= w.qgrid && w.tgrid[nextj] == removed {
			rec[qstart+nextj] = uint32(int32(len(ones)))
			nextj++
		}
		for i := 0; i < ne; i++ {
			if removed == w.nMinus[i] {
				reached[i] = 1
				score[i] = (w.scoreC - w.heavyNow(i)) / w.scoreSc
			}
		}
		c := ones[rp.IntN(len(ones))]
		id := w.sumID[c]
		e := int(id - 1)
		for j := 0; j < K; j++ {
			c2 := w.cells[e*K+j]
			w.deg[c2]--
			w.sumID[c2] -= id
			switch w.deg[c2] {
			case 1:
				add(c2)
			case 0:
				del(c2)
			}
		}
		removed++
	}
	for w.qgrid > 0 && nextj <= w.qgrid {
		if w.tgrid[nextj] == removed {
			rec[qstart+nextj] = 0
		} else {
			rec[qstart+nextj] = 0xFFFFFFFF // -1: stopped before t
		}
		nextj++
	}
	w.ones = ones
	var coreCells int32
	for i := 0; i < M; i++ {
		if w.deg[i] > 0 {
			coreCells++
		}
	}
	failed := int32(0)
	if removed != D {
		failed = 1
	}
	rec[f] = uint32(failed)
	rec[f+1] = uint32(int32(D - removed))
	rec[f+2] = uint32(coreCells)
	rec[f+3] = uint32(n0)
	rec[f+4] = uint32(n1)
	rec[f+5] = uint32(n2)
	rec[f+6] = math.Float32bits(float32(s2c))
	rec[f+7] = math.Float32bits(float32(hcs))
	rec[f+8] = math.Float32bits(float32(vs))
	g := qstart
	if w.qgrid > 0 {
		g += w.qgrid + 1
	}
	sc := g
	if w.rSimple > 0 {
		sc += 3
	}
	if w.rConfig > 0 {
		sc += 2
	}
	if optScore {
		rec[sc] = math.Float32bits(float32((hcs - w.hCenter) / w.hScale))
		ndup, da, db := w.coreDup(int32(D-removed), failed)
		rec[sc+1] = uint32(ndup)
		for i := 0; i < ne; i++ {
			if removed == w.nMinus[i] && reached[i] == 0 { // stopped exactly at n_-
				reached[i] = 1
				score[i] = (w.scoreC - w.heavyNow(i)) / w.scoreSc
			}
			rec[sc+2+2*i] = uint32(reached[i])
			rec[sc+3+2*i] = math.Float32bits(float32(score[i]))
		}
		if optDupIdx {
			rec[sc+2+2*ne] = uint32(da)
			rec[sc+3+2*ne] = uint32(db)
		}
	}
	// re-pairings of the same unsigned degree sequence
	if w.rSimple > 0 || w.rConfig > 0 {
		n := 0
		for i := 0; i < M; i++ {
			for j := int32(0); j < w.deg0[i]; j++ {
				w.stubs[n] = int32(i)
				n++
			}
		}
		if w.rSimple > 0 {
			fails, core, attempts := 0, 0, 0
			for r := 0; r < w.rSimple; r++ {
				for {
					attempts++
					ok := true
					// incremental Fisher-Yates; reject at first within-edge repeat
					for p := 0; p < n && ok; p++ {
						q := p + rr.IntN(n-p)
						w.stubs[p], w.stubs[q] = w.stubs[q], w.stubs[p]
						e0 := (p / K) * K
						for j := e0; j < p; j++ {
							if w.stubs[j] == w.stubs[p] {
								ok = false
								break
							}
						}
					}
					if ok {
						break
					}
				}
				copy(w.rcells, w.stubs[:n])
				cc := w.genericPeel(w.rcells)
				core += cc
				if cc > 0 {
					fails++
				}
			}
			rec[g] = math.Float32bits(float32(float64(fails) / float64(w.rSimple)))
			rec[g+1] = math.Float32bits(float32(float64(core) / float64(w.rSimple)))
			rec[g+2] = uint32(int32(attempts))
			g += 3
		}
		if w.rConfig > 0 {
			fails, core := 0, 0
			for r := 0; r < w.rConfig; r++ {
				for p := n - 1; p > 0; p-- {
					q := rr.IntN(p + 1)
					w.stubs[p], w.stubs[q] = w.stubs[q], w.stubs[p]
				}
				copy(w.rcells, w.stubs[:n])
				cc := w.genericPeel(w.rcells)
				core += cc
				if cc > 0 {
					fails++
				}
			}
			rec[g] = math.Float32bits(float32(float64(fails) / float64(w.rConfig)))
			rec[g+1] = math.Float32bits(float32(float64(core) / float64(w.rConfig)))
		}
	}
}

// heavyNow: sum over cells of f_{deg}(b_-) for score time i.
func (w *worker) heavyNow(e int) float64 {
	fb := w.fB[e]
	var heavy float64
	for i := 0; i < w.M; i++ {
		if dg := w.deg[i]; dg >= 2 {
			if int(dg) < len(fb) {
				heavy += fb[dg]
			} else {
				heavy += float64(dg)
			}
		}
	}
	return heavy
}

// coreDup: for a failed graph with a core of at most 200 edges, the number of
// pairs of identical edges inside the core; -1 for a larger core, 0 if no failure.
// Also returns the edge indices a<b of the first identical pair found (-1, -1 if none).
func (w *worker) coreDup(coreEdges, failed int32) (int32, int32, int32) {
	if failed == 0 {
		return 0, -1, -1
	}
	if coreEdges > 200 {
		return -1, -1, -1
	}
	K := w.K
	alive := func(e int) bool {
		for j := 0; j < K; j++ {
			if w.deg[w.cells[e*K+j]] == 0 {
				return false
			}
		}
		return true
	}
	// core edges are exactly the unremoved ones: every cell of a core edge has deg>0,
	// and a removed edge was removed through a cell that then dropped to deg 0.
	var ce []int
	for e := 0; e < w.D && len(ce) <= int(coreEdges); e++ {
		if alive(e) {
			ce = append(ce, e)
		}
	}
	key := func(e int) [8]int32 {
		var k [8]int32
		for j := 0; j < K && j < 8; j++ {
			k[j] = w.cells[e*K+j]
		}
		s := k[:K]
		for a := 1; a < len(s); a++ {
			for b := a; b > 0 && s[b] < s[b-1]; b-- {
				s[b], s[b-1] = s[b-1], s[b]
			}
		}
		return k
	}
	var dup int32
	da, db := int32(-1), int32(-1)
	for a := 0; a < len(ce); a++ {
		ka := key(ce[a])
		for b := a + 1; b < len(ce); b++ {
			if key(ce[b]) == ka {
				if dup == 0 {
					da, db = int32(ce[a]), int32(ce[b])
				}
				dup++
			}
		}
	}
	return dup, da, db
}

// signRedraws: optSrep uniform fixed-composition sign vectors on this graph;
// records the sample mean/variance of X over the redraws and the exact
// graph-conditional mean and variance (Plain: self-energy k per edge).
func (w *worker) signRedraws(rs *rand.Rand, rec []uint32, W, B float64) {
	M, K, D := w.M, w.K, w.D
	mf, kf, df := float64(M), float64(K), float64(D)
	gamma := kf * (1 - kf/mf)
	sdd := math.Sqrt(2 * df * (df - 1) / (mf - 1))
	for x := 0; x < D; x++ {
		w.sarr[x] = 1
		if x < w.srNeg {
			w.sarr[x] = -1
		}
	}
	var m1, m2 float64
	for r := 0; r < optSrep; r++ {
		for x := D - 1; x > 0; x-- {
			y := rs.IntN(x + 1)
			w.sarr[x], w.sarr[y] = w.sarr[y], w.sarr[x]
		}
		for i := 0; i < M; i++ {
			w.cnt[i] = 0
		}
		for e := 0; e < D; e++ {
			s := int64(w.sarr[e])
			for j := 0; j < K; j++ {
				w.cnt[w.cells[e*K+j]] += s
			}
		}
		var s1, s2 float64
		for i := 0; i < M; i++ {
			c := float64(w.cnt[i])
			s1 += c
			s2 += c * c
		}
		x := ((s2-s1*s1/mf)/gamma - df) / sdd
		m1 += x
		m2 += x * x
	}
	R := float64(optSrep)
	mean := m1 / R
	v := (m2 - R*mean*mean) / (R - 1)
	var A float64
	for _, l := range w.lx {
		A += l * l
	}
	S := df - 2*float64(w.srNeg)
	exMean := ((kf*df+2*w.srA2*W-kf*kf*S*S/mf)/gamma - df) / sdd
	varY := w.srCoef[0]*B + w.srCoef[1]*A + w.srCoef[2]*W*W
	exVar := 4 * varY / (gamma * gamma * sdd * sdd)
	o := len(rec) - 4
	if optKeep > 0 {
		o--
	}
	if optSumC {
		o -= 2
	}
	rec[o] = math.Float32bits(float32(mean))
	rec[o+1] = math.Float32bits(float32(v))
	rec[o+2] = math.Float32bits(float32(exMean))
	rec[o+3] = math.Float32bits(float32(exVar))
}

func parseSpecs(path string) ([]spec, error) {
	b, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var out []spec
	for _, line := range strings.Split(string(b), "\n") {
		line = strings.TrimSpace(line)
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		fs := strings.Fields(line)
		if len(fs) != 4 {
			return nil, fmt.Errorf("bad spec line %q (want: M k d trials)", line)
		}
		var v [4]int
		for i := range fs {
			if v[i], err = strconv.Atoi(fs[i]); err != nil {
				return nil, err
			}
		}
		out = append(out, spec{v[0], v[1], v[2], v[3]})
	}
	return out, nil
}

func parseVariants(text string, D int) []variant {
	var out []variant
	for _, t := range strings.Split(text, ",") {
		t = strings.TrimSpace(t)
		if t == "" {
			continue
		}
		if t == "rand" {
			out = append(out, variant{Name: "rand", NegRatio: -1, NegCount: -1, Rho: 0})
			continue
		}
		// "rs<token>": random-sign encoding over the fixed composition <token>
		rsign := strings.HasPrefix(t, "rs")
		if rsign {
			t = t[2:]
		}
		var nc int
		var r float64
		switch {
		case t == "sqrt": // floor(sqrt d) negatives
			nc = int(math.Floor(math.Sqrt(float64(D))))
		case t == "zp": // d = L^2, sum = L: a = (d rho^2 - 1)/(d-1) = 0 exactly
			L := int(math.Round(math.Sqrt(float64(D))))
			if L*L != D {
				panic(fmt.Sprintf("sign variant zp needs d a perfect square, got %d", D))
			}
			nc = (D - L) / 2
		case strings.HasPrefix(t, "n"): // exact negative count
			v, err := strconv.Atoi(t[1:])
			if err != nil {
				panic(err)
			}
			nc = v
		default:
			v, err := strconv.ParseFloat(t, 64)
			if err != nil {
				panic(err)
			}
			nc = int(v*float64(D) + 0.5)
		}
		r = float64(nc) / float64(D)
		if rsign {
			out = append(out, variant{Name: "rs" + t, NegRatio: r, NegCount: nc, RandSign: true, Rho: 0})
			continue
		}
		if strings.HasPrefix(t, "n") || t == "sqrt" || t == "zp" {
			out = append(out, variant{Name: t, NegRatio: r, NegCount: nc, Rho: float64(D-2*nc) / float64(D)})
			continue
		}
		out = append(out, variant{Name: "neg" + t, NegRatio: r, NegCount: nc, Rho: float64(D-2*nc) / float64(D)})
	}
	return out
}

func selftest() {
	// dhat from counts must equal d + (2/gamma) sum_{x<y} s_x s_y W_xy exactly;
	// mean of VsIID must equal 1 in expectation.
	M, K, D := 40, 3, 30
	vars := parseVariants("0,0.3,0.5,rand", D)
	w := newWorker(M, K, D, vars, 8, 2, 2, true, 0.5)
	rm := rand.New(rand.NewPCG(1, 2))
	rs := rand.New(rand.NewPCG(3, 4))
	rp := rand.New(rand.NewPCG(5, 6))
	rr := rand.New(rand.NewPCG(7, 8))
	nf := nFields(len(vars), 8, 2, 2)
	rec := make([]uint32, nf)
	var vsum float64
	maxErr := 0.0
	nt := 20000
	for t := 0; t < nt; t++ {
		w.trial(rm, rs, rp, rr, rec)
		vsum += float64(math.Float32frombits(rec[len(vars)+1+5+2]))
		// brute force for the fixed variants
		mf, kf, df := float64(M), float64(K), float64(D)
		gamma := kf * (1 - kf/mf)
		sdd := math.Sqrt(2 * df * (df - 1) / (mf - 1))
		for vi, v := range vars {
			if v.NegRatio < 0 {
				continue
			}
			sg := func(e int) float64 {
				if e < v.NegCount {
					return -1
				}
				return 1
			}
			var cross float64
			for x := 0; x < D; x++ {
				for y := x + 1; y < D; y++ {
					h := 0
					for a := 0; a < K; a++ {
						for b := 0; b < K; b++ {
							if w.cells[x*K+a] == w.cells[y*K+b] {
								h++
							}
						}
					}
					cross += sg(x) * sg(y) * (float64(h) - kf*kf/mf)
				}
			}
			want := (2 * cross / gamma) / sdd
			got := float64(math.Float32frombits(rec[vi]))
			if e := math.Abs(want - got); e > maxErr {
				maxErr = e
			}
		}
	}
	fmt.Printf("selftest: max |X_counts - X_pairs| = %.3g (float32 storage)\n", maxErr)

	// random-sign variants: brute force with the stored coefficients of the last variant,
	// and composition-free moments (mean 0, variance close to 1 at this tiny size)
	{
		vr := parseVariants("rs0,rs0.5,rs0.3", D)
		w2 := newWorker(M, K, D, vr, 0, 0, 0, false, 0.5)
		w2.coef = make([]int8, D)
		w2.re = rand.New(rand.NewPCG(9, 10))
		rec2 := make([]uint32, nFields(len(vr), 0, 0, 0))
		mf, kf, df := float64(M), float64(K), float64(D)
		gamma := kf * (1 - kf/mf)
		sdd := math.Sqrt(2 * df * (df - 1) / (mf - 1))
		var e2 float64
		var m1, m2 [3]float64
		for t := 0; t < nt; t++ {
			w2.trial(rm, rs, rp, rr, rec2)
			for vi := range vr {
				x := float64(math.Float32frombits(rec2[vi]))
				m1[vi] += x
				m2[vi] += x * x
			}
			if t%20 != 0 {
				continue
			}
			var cross float64
			for x := 0; x < D; x++ {
				for y := x + 1; y < D; y++ {
					h := 0
					for a := 0; a < K; a++ {
						for b := 0; b < K; b++ {
							if w2.cells[x*K+a] == w2.cells[y*K+b] {
								h++
							}
						}
					}
					cross += float64(w2.coef[x]) * float64(w2.coef[y]) * (float64(h) - kf*kf/mf)
				}
			}
			if e := math.Abs(2*cross/gamma/sdd - float64(math.Float32frombits(rec2[len(vr)-1]))); e > e2 {
				e2 = e
			}
		}
		fmt.Printf("selftest rs: max |X_counts - X_pairs| = %.3g\n", e2)
		for vi, v := range vr {
			mu := m1[vi] / float64(nt)
			fmt.Printf("selftest rs %-6s: mean %.4f (se %.4f), var %.4f\n", v.Name, mu,
				math.Sqrt((m2[vi]/float64(nt)-mu*mu)/float64(nt)), m2[vi]/float64(nt)-mu*mu)
		}
	}
	fmt.Printf("selftest: mean VsIID over %d graphs = %.4f (expect 1)\n", nt, vsum/float64(nt))

	// fixed-composition redraws: sample moments vs exact eq.(9), several compositions
	for _, comp := range []string{"n0", "n1", "n7", "n15", "zp"} {
		M2, K2, D2 := 60, 3, 36
		if comp != "zp" {
			D2 = 30
		}
		optSrep, optSrepC = 400000, comp
		w2 := newWorker(M2, K2, D2, parseVariants("0", D2), 0, 0, 0, true, 0.5)
		rec2 := make([]uint32, nFields(1, 0, 0, 0))
		w2.trial(rm, rs, rp, rr, rec2)
		o := len(rec2) - 4
		g := func(i int) float64 { return float64(math.Float32frombits(rec2[o+i])) }
		fmt.Printf("selftest srep %-4s: mean %.5f exact %.5f (se %.5f) | var %.5f exact %.5f\n",
			comp, g(0), g(2), math.Sqrt(g(1)/4e5), g(1), g(3))
		optSrep = 0
	}
	// planted duplicate: always fails; config model runs
	optPlant = true
	for _, cfgm := range []bool{false, true} {
		optConfig, optScore, optEps = cfgm, true, []string{"m8"}
		w3 := newWorker(400, 3, 300, parseVariants("0", 300), 0, 0, 0, false, 0.5)
		rec3 := make([]uint32, nFields(1, 0, 0, 0))
		nf, dupc := 0, 0
		for t := 0; t < 2000; t++ {
			w3.trial(rm, rs, rp, rr, rec3)
			nf += int(rec3[1])
			if int32(rec3[len(rec3)-3]) > 0 {
				dupc++
			}
		}
		fmt.Printf("selftest plant (config=%v): failed %d/2000, core has duplicate pair %d/2000\n", cfgm, nf, dupc)
	}
	// dup-idx: the sampled planted pair is recorded whenever the core is that pair alone
	optConfig, optScore, optEps, optDupIdx = false, true, []string{"m8"}, true
	w4 := newWorker(400, 3, 300, parseVariants("0", 300), 0, 0, 0, false, 0.5)
	rec4 := make([]uint32, nFields(1, 0, 0, 0))
	pureN, hit := 0, 0
	for t := 0; t < 2000; t++ {
		w4.trial(rm, rs, rp, rr, rec4)
		n := len(rec4)
		if int32(rec4[2]) == 2 && int32(rec4[n-5]) == 1 {
			pureN++
			if int32(rec4[n-2]) == int32(w4.plantI) && int32(rec4[n-1]) == int32(w4.plantJ) {
				hit++
			}
		}
	}
	fmt.Printf("selftest dup-idx: planted pair recorded in %d/%d pure-pair failures (expect all)\n", hit, pureN)
	optDupIdx = false
	optPlant, optConfig, optScore = false, false, false
}

// rngSeeding is recorded with each run. legacy-v1 reproduces frozen streams.
var rngSeeding = "splitmix64-v1"

func seedMix64(x uint64) uint64 {
	x += 0x9E3779B97F4A7C15
	x = (x ^ (x >> 30)) * 0xBF58476D1CE4E5B9
	x = (x ^ (x >> 27)) * 0x94D049BB133111EB
	return x ^ (x >> 31)
}

func seededPCG(seed1, seed2 uint64) *rand.PCG {
	if rngSeeding == "legacy-v1" {
		return rand.NewPCG(seed1, seed2)
	}
	return rand.NewPCG(seedMix64(seed1^seedMix64(seed2)),
		seedMix64(seed2^0x9E3779B97F4A7C15^seedMix64(^seed1)))
}

func validateSeedScheme() {
	if rngSeeding != "splitmix64-v1" && rngSeeding != "legacy-v1" {
		panic("rng-seeding must be splitmix64-v1 or legacy-v1")
	}
}

func main() {
	flag.StringVar(&rngSeeding, "rng-seeding", "splitmix64-v1", "PCG seeding: splitmix64-v1 or legacy-v1 (frozen reproduction)")
	specPath := flag.String("spec", "", "spec file: lines 'M k d trials'")
	signText := flag.String("signs", "0,0.1,0.25,0.4,0.5,rand", "sign variants: fixed negative ratios and/or rand")
	qgrid := flag.Int("qgrid", 64, "record degree-one set size at t=floor(j d/G), j=0..G (0 disables)")
	rSimple := flag.Int("r-simple", 0, "re-pairings per graph conditioned on no within-edge repeat (exp C)")
	rConfig := flag.Int("r-config", 0, "raw configuration-model re-pairings per graph (exp C)")
	pairs := flag.Bool("pairs", true, "compute exact iid-sign Var_s(X|mapping)")
	runSeed := flag.Uint64("seed", 0, "explicit run seed (required, nonzero)")
	jobs := flag.Int("jobs", runtime.NumCPU(), "worker goroutines")
	chunk := flag.Int("chunk", 20000, "trials per chunk (unit of parallelism and output file)")
	outDir := flag.String("out", "", "output directory")
	codeVersion := flag.String("code-version", "", "code version tag recorded in manifest")
	st := flag.Bool("selftest", false, "run self test and exit")
	resume := flag.Bool("resume", false, "skip chunks already completed in -out (same spec and seed required)")
	model := flag.String("model", "plain", "plain (distinct cells per edge) or config (iid endpoints, repeats allowed)")
	flag.BoolVar(&optPlant, "plant-dup", false, "uniformly choose two edge labels and give them the same mapping")
	flag.BoolVar(&optScore, "score", false, "record precritical score R_M (t_- = t_* - M^-1/8), H_M, core duplicate pairs")
	flag.IntVar(&optSrep, "srep", 0, "random fixed-composition sign redraws per graph (records mean/var and exact values)")
	flag.StringVar(&optSrepC, "srep-comp", "zp", "composition for -srep (sign-variant token)")
	flag.BoolVar(&optDupIdx, "dup-idx", false, "with -score: record edge indices dup_a<dup_b of the first identical pair in the core")
	flag.BoolVar(&optSumC, "sumc", false, "record exact S1_rand = sum_v C_v and S2_rand = sum_v C_v^2 of the rand variant")
	onlyText := flag.String("only", "", "comma-separated config indices to run (others keep their index, so seeds match the full run)")
	flag.IntVar(&optKeep, "keep", 0, "if >0, per chunk store the first N trials (field uncond=1) and afterwards only failed trials")
	epsText := flag.String("score-eps", "m8,0.2,0.1,0.05,m4,0", "score times t_* - eps (m8=M^-1/8, m4=M^-1/4)")
	flag.Parse()
	validateSeedScheme()
	if optScore {
		optEps = strings.Split(*epsText, ",")
		if len(optEps) > 16 {
			panic("at most 16 score times")
		}
	}
	switch *model {
	case "plain":
	case "config":
		optConfig = true
	default:
		panic("bad -model")
	}
	if optSrep == 1 || (optSrep > 0 && (!*pairs || optConfig)) {
		panic("-srep needs >=2 redraws, -pairs and the plain model")
	}
	if *st {
		selftest()
		return
	}
	if *runSeed == 0 || *specPath == "" || *outDir == "" {
		fmt.Fprintln(os.Stderr, "need -seed, -spec, -out")
		os.Exit(2)
	}
	specs, err := parseSpecs(*specPath)
	if err != nil {
		panic(err)
	}
	if err := os.MkdirAll(*outDir, 0o755); err != nil {
		panic(err)
	}
	man := manifest{RNGSeeding: rngSeeding, CodeVersion: *codeVersion, RunSeed: *runSeed, Args: os.Args, QGrid: *qgrid,
		RSimple: *rSimple, RConfig: *rConfig, Started: time.Now().Format(time.RFC3339)}
	type job struct{ ci, chunk, n int }
	var jobsList []job
	only := map[int]bool{}
	for _, t := range strings.Split(*onlyText, ",") {
		if t = strings.TrimSpace(t); t != "" {
			i, err := strconv.Atoi(t)
			if err != nil || i < 0 || i >= len(specs) {
				panic("bad -only index " + t)
			}
			only[i] = true
		}
	}
	for ci, s := range specs {
		k := s.K
		xc, muc, sc := critical(k)
		vars := parseVariants(*signText, s.D)
		nch := (s.Trials + *chunk - 1) / *chunk
		man.Configs = append(man.Configs, cfgMeta{Index: ci, M: s.M, K: k, D: s.D, Load: float64(s.D) / float64(s.M),
			Trials: s.Trials, Chunks: nch, Variants: vars, SC: sc, MuC: muc, XC: xc})
		if err := os.MkdirAll(filepath.Join(*outDir, fmt.Sprintf("cfg_%03d", ci)), 0o755); err != nil {
			panic(err)
		}
		for c := 0; c < nch && (len(only) == 0 || only[ci]); c++ {
			n := *chunk
			if (c+1)**chunk > s.Trials {
				n = s.Trials - c**chunk
			}
			jobsList = append(jobsList, job{ci, c, n})
		}
	}
	vars0 := man.Configs[0].Variants
	man.PlantScheme = "none"
	if optPlant {
		man.PlantScheme = "uniform-pair-v1"
	}
	man.Fields, man.FieldTypes = fieldNames(vars0, *qgrid, *rSimple, *rConfig)
	man.RecordBytes = 4 * len(man.Fields)
	man.ChunksTotal = len(jobsList)
	manPath := filepath.Join(*outDir, "manifest.json")
	var mu sync.Mutex
	writeManifest := func() { // caller holds mu (or is single-threaded)
		man.Updated = time.Now().Format(time.RFC3339)
		b, _ := json.MarshalIndent(man, "", "  ")
		os.WriteFile(manPath+".tmp", b, 0o644)
		os.Rename(manPath+".tmp", manPath)
	}

	failed := make([]int64, len(specs))
	secs := make([]int64, len(specs)) // nanoseconds
	left := make([]int64, len(specs)) // chunks remaining per config
	for _, j := range jobsList {
		left[j.ci]++
	}
	var next, done int64
	var wg sync.WaitGroup
	failedIdx := len(vars0) // field index of "failed"

	// resume: verify spec/seed identity, then skip complete chunk files
	if *resume {
		if b, err := os.ReadFile(manPath); err == nil {
			var old manifest
			if err := json.Unmarshal(b, &old); err != nil {
				panic(err)
			}
			if savedPlantScheme(old) != man.PlantScheme {
				panic("resume: planted sampling scheme differs; use a new output directory")
			}
			oldScheme := old.RNGSeeding
			if oldScheme == "" {
				oldScheme = "legacy-v1"
			}
			if oldScheme != rngSeeding {
				panic("resume: RNG seeding differs; use a new output directory or explicitly reproduce with -rng-seeding legacy-v1")
			}
			if old.RunSeed != *runSeed || len(old.Configs) != len(man.Configs) || old.RecordBytes != man.RecordBytes {
				panic("resume: manifest seed/configs/record layout differ from this invocation")
			}
			for i := range old.Configs {
				o, c := old.Configs[i], man.Configs[i]
				if o.M != c.M || o.K != c.K || o.D != c.D || o.Trials != c.Trials {
					panic(fmt.Sprintf("resume: config %d differs", i))
				}
			}
			man.Started = old.Started
			man.Resumes = old.Resumes + 1
		} else {
			panic("resume: readable manifest required to verify RNG seeding")
		}
		var keep []job
		for _, j := range jobsList {
			path := filepath.Join(*outDir, fmt.Sprintf("cfg_%03d", j.ci), fmt.Sprintf("chunk_%05d.bin", j.chunk))
			os.Remove(path + ".tmp")
			b, err := os.ReadFile(path)
			// with -keep the file length varies; the final name is only created by an atomic rename
			if err == nil && (len(b) == j.n*man.RecordBytes || (optKeep > 0 && len(b)%man.RecordBytes == 0)) {
				var nf int64
				if optKeep > 0 {
					nf = chunkFails(filepath.Join(*outDir, "progress.tsv"), j.ci, j.chunk)
				} else {
					for t := 0; t < j.n; t++ {
						if binary.LittleEndian.Uint32(b[t*man.RecordBytes+4*failedIdx:]) == 1 {
							nf++
						}
					}
				}
				failed[j.ci] += nf
				left[j.ci]--
				done++
				continue
			}
			keep = append(keep, j)
		}
		fmt.Fprintf(os.Stderr, "resume: %d chunks already complete, %d to run\n", done, len(keep))
		jobsList = keep
	}
	man.ChunksDone = done
	writeManifest()

	// per-chunk progress log: survives crashes, gives interim p_F and failed-conditional moments
	plog, err := os.OpenFile(filepath.Join(*outDir, "progress.tsv"), os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0o644)
	if err != nil {
		panic(err)
	}
	if st, _ := plog.Stat(); st.Size() == 0 {
		fmt.Fprintln(plog, "time\tcfg\tchunk\tn\tnfail\tsumX0_F\tsumX0sq_F\tsumX0_all\tsumX0sq_all\tseconds")
	}
	lastMan := time.Now()
	total := int64(man.ChunksTotal)
	t0 := time.Now()
	startDone := done
	for g := 0; g < *jobs; g++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for {
				i := atomic.AddInt64(&next, 1) - 1
				if int(i) >= len(jobsList) {
					return
				}
				j := jobsList[i]
				s := specs[j.ci]
				meta := man.Configs[j.ci]
				w := newWorker(s.M, s.K, s.D, meta.Variants, *qgrid, *rSimple, *rConfig, *pairs, meta.SC)
				s2 := uint64(j.ci)<<32 | uint64(j.chunk)
				rm := rand.New(seededPCG(*runSeed^0x9E3779B97F4A7C15, s2))
				rs := rand.New(seededPCG(*runSeed^0xC2B2AE3D27D4EB4F, s2))
				rp := rand.New(seededPCG(*runSeed^0x165667B19E3779F9, s2))
				rr := rand.New(seededPCG(*runSeed^0xD6E8FEB86659FD93, s2))
				w.re = rand.New(seededPCG(*runSeed^0x27D4EB2F165667C5, s2))
				w.rplant = rand.New(seededPCG(*runSeed^0xA24BAED4963EE407, s2))
				nf := nFields(len(meta.Variants), *qgrid, *rSimple, *rConfig)
				rec := make([]uint32, nf)
				path := filepath.Join(*outDir, fmt.Sprintf("cfg_%03d", j.ci), fmt.Sprintf("chunk_%05d.bin", j.chunk))
				fh, err := os.Create(path + ".tmp")
				if err != nil {
					panic(err)
				}
				bw := bufio.NewWriterSize(fh, 1<<20)
				buf := make([]byte, 4*nf)
				ts := time.Now()
				var nfail int64
				var sF, s2F, sA, s2A float64
				for t := 0; t < j.n; t++ {
					w.trial(rm, rs, rp, rr, rec)
					x0 := float64(math.Float32frombits(rec[0]))
					sA += x0
					s2A += x0 * x0
					if rec[len(meta.Variants)] == 1 {
						nfail++
						sF += x0
						s2F += x0 * x0
					}
					if optKeep > 0 {
						u := uint32(0)
						if t < optKeep {
							u = 1
						}
						rec[nf-1] = u
						if u == 0 && rec[len(meta.Variants)] != 1 {
							continue
						}
					}
					for q, v := range rec {
						binary.LittleEndian.PutUint32(buf[4*q:], v)
					}
					bw.Write(buf)
				}
				if err := bw.Flush(); err != nil {
					panic(err)
				}
				if err := fh.Close(); err != nil {
					panic(err)
				}
				if err := os.Rename(path+".tmp", path); err != nil {
					panic(err)
				}
				el := time.Since(ts)
				atomic.AddInt64(&failed[j.ci], nfail)
				atomic.AddInt64(&secs[j.ci], int64(el))
				mu.Lock()
				done++
				d := done
				fmt.Fprintf(plog, "%s\t%d\t%d\t%d\t%d\t%.6g\t%.6g\t%.6g\t%.6g\t%.1f\n", time.Now().Format(time.RFC3339),
					j.ci, j.chunk, j.n, nfail, sF, s2F, sA, s2A, el.Seconds())
				left[j.ci]--
				if left[j.ci] == 0 {
					c := man.Configs[j.ci]
					fmt.Fprintf(os.Stderr, "[%s] config %d complete: M=%d k=%d d=%d trials=%d pF=%.4f\n",
						time.Now().Format("15:04:05"), j.ci, c.M, c.K, c.D, c.Trials, float64(failed[j.ci])/float64(c.Trials))
				}
				if d%20 == 0 || d == total || time.Since(lastMan) > 5*time.Minute {
					es := time.Since(t0).Seconds()
					fmt.Fprintf(os.Stderr, "[%s] %d/%d chunks, %.0fs elapsed, eta %.0fs\n", time.Now().Format("15:04:05"),
						d, total, es, es/float64(d-startDone)*float64(total-d))
					for i := range man.Configs {
						man.Configs[i].Failed = failed[i]
						man.Configs[i].Seconds = float64(secs[i]) / 1e9
					}
					man.ChunksDone = d
					writeManifest()
					lastMan = time.Now()
				}
				mu.Unlock()
			}
		}()
	}
	wg.Wait()
	for i := range man.Configs {
		man.Configs[i].Failed = failed[i]
		man.Configs[i].Seconds = float64(secs[i]) / 1e9
	}
	man.Finished = time.Now().Format(time.RFC3339)
	man.ChunksDone = done
	writeManifest()
	plog.Close()
	for _, c := range man.Configs {
		fmt.Printf("cfg %3d M=%d k=%d d=%d load=%.5f trials=%d pF=%.4f cpu=%.0fs\n", c.Index, c.M, c.K, c.D, c.Load,
			c.Trials, float64(c.Failed)/float64(c.Trials), c.Seconds)
	}
}

// chunkFails: failure count of a completed chunk from progress.tsv (used on resume with -keep,
// where the chunk file no longer holds every trial); 0 if the line is missing.  The file is
// parsed once and cached.
var chunkFailCache map[[2]int]int64

func chunkFails(path string, ci, chunk int) int64 {
	if chunkFailCache == nil {
		chunkFailCache = map[[2]int]int64{}
		b, _ := os.ReadFile(path)
		for _, line := range strings.Split(string(b), "\n") {
			fs := strings.Split(line, "\t")
			if len(fs) < 5 {
				continue
			}
			c, e1 := strconv.Atoi(fs[1])
			h, e2 := strconv.Atoi(fs[2])
			v, e3 := strconv.ParseInt(fs[4], 10, 64)
			if e1 == nil && e2 == nil && e3 == nil {
				chunkFailCache[[2]int{c, h}] = v
			}
		}
	}
	return chunkFailCache[[2]int{ci, chunk}]
}
