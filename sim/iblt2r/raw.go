package main

// Final sizing rule: raw-energy inversion of theory/extensions/random-sign-crossover-inversion.md §4–5.
// Same algorithm as sim/peelsim/e0extract/rawreplay.go, which matches the Decimal reference
// theory/scripts/random_sign_crossover.py on 4822 cases.

import (
	"math"
	"sort"
)

type poisTab struct {
	lo      int       // p[i], F[i] refer to the value lo+i
	p, F    []float64 // pmf and CDF (from lo) on the window
	lastUse uint64
}

// poisCache holds the Poisson tables of one (M, k), indexed by the candidate n. The tables do not
// depend on u, so engines with different risk levels can share one cache. When a new table would
// exceed maxTabEntries, the least recently used tables are evicted until half the capacity is free.
type poisCache struct {
	M, k    int
	tabs    map[int64]*poisTab
	entries int // float64 pairs held in tabs
	peak    int // largest entries reached
	clock   uint64
}

func newPoisCache(M, k int) *poisCache {
	return &poisCache{M: M, k: k, tabs: map[int64]*poisTab{}}
}

func (c *poisCache) evict(need int) {
	ts := make([]*poisTab, 0, len(c.tabs))
	ns := make(map[*poisTab]int64, len(c.tabs))
	for n, t := range c.tabs {
		ts = append(ts, t)
		ns[t] = n
	}
	sort.Slice(ts, func(i, j int) bool { return ts[i].lastUse < ts[j].lastUse })
	for _, t := range ts {
		if c.entries+need <= maxTabEntries/2 {
			break
		}
		delete(c.tabs, ns[t])
		c.entries -= len(t.p)
	}
}

type rawEngine struct {
	M, k    int
	u       float64
	lamStar float64 // normal approximation above this Poisson mean (math.Inf(1): exact everywhere)
	cache   *poisCache
	ucache  map[int64]int64 // nil: no reuse of finished upper bounds
}

// maxTabEntries bounds each Poisson-table cache (two float64 per entry, 16 bytes; 4M entries is about
// 64 MB). Set from -tabcap.
var maxTabEntries = 4_000_000

// rawLamStar is set from -lamstar; the default is the exact rule. The normal approximation is kept
// only as a timing option.
var rawLamStar = math.Inf(1)

// rawBernstein enables the §5.1 search cutoff (-bernstein=false restores the scan from (10), for timing).
var rawBernstein = true

// newRaw returns an engine with its own empty table cache.
func newRaw(M, k int, u float64, cacheU bool) *rawEngine {
	return newRawShared(newPoisCache(M, k), u, cacheU)
}

// newRawShared returns an engine that uses (and fills) the shared table cache c.
func newRawShared(c *poisCache, u float64, cacheU bool) *rawEngine {
	e := &rawEngine{M: c.M, k: c.k, u: u, lamStar: rawLamStar, cache: c}
	if cacheU {
		e.ucache = map[int64]int64{}
	}
	return e
}

func (e *rawEngine) lambda(n int64) float64 {
	return float64(e.k*e.k) * float64(n-2) * float64(n-3) / (4 * float64(e.M))
}

func (e *rawEngine) tab(n int64) *poisTab {
	c := e.cache
	c.clock++
	if t, ok := c.tabs[n]; ok {
		t.lastUse = c.clock
		return t
	}
	// Window [lo, hi] = lambda -/+ (14 sd + 40). The Poisson mass outside is below 1e-40 on each side,
	// smaller than the double-precision rounding of the CDF. The pmf is built by the recursion
	// p(i+1) = p(i) lambda/(i+1) outward from the mode and normalized over the window, which avoids
	// one Lgamma per entry.
	lam := e.lambda(n)
	w := 14*math.Sqrt(lam) + 40
	lo := int(math.Max(0, math.Floor(lam-w)))
	hi := int(lam + w)
	p := make([]float64, hi-lo+1)
	mode := int(lam)
	if mode < lo {
		mode = lo
	}
	p[mode-lo] = 1
	for i := mode; i < hi; i++ {
		p[i+1-lo] = p[i-lo] * lam / float64(i+1)
	}
	for i := mode; i > lo; i-- {
		p[i-1-lo] = p[i-lo] * float64(i) / lam
	}
	var z float64
	for _, v := range p {
		z += v
	}
	F := make([]float64, len(p))
	var s float64
	for i := range p {
		p[i] /= z
		s += p[i]
		F[i] = s
	}
	t := &poisTab{lo, p, F, c.clock}
	if c.entries+len(p) > maxTabEntries {
		c.evict(len(p))
	}
	c.tabs[n] = t
	c.entries += len(p)
	if c.entries > c.peak {
		c.peak = c.entries
	}
	return t
}

func floorDiv2(x int64) int64 {
	if x >= 0 {
		return x / 2
	}
	return -((-x + 1) / 2)
}

func (e *rawEngine) skellamCDF(n, j int64) float64 {
	lam := e.lambda(n)
	if lam == 0 {
		if j >= 0 {
			return 1
		}
		return 0
	}
	if lam > e.lamStar {
		return 0.5 * math.Erfc(-(float64(j)+0.5)/math.Sqrt(2*lam)/math.Sqrt2)
	}
	t := e.tab(n)
	var s float64
	L := int64(len(t.p))
	for m := int64(0); m < L; m++ { // P2 = lo+m, need P1 <= j+lo+m
		x := j + m // index of j+lo+m in the window
		if x < 0 {
			continue
		}
		if x >= L {
			s += t.p[m]
			continue
		}
		s += t.p[m] * t.F[x]
	}
	return s
}

func chernoffUpper(lam float64, j int64) float64 {
	if lam == 0 {
		return 0
	}
	t := float64(-j)
	r := t / (2 * lam)
	return math.Exp(-(t*math.Asinh(r) - 2*lam*(math.Sqrt(1+r*r)-1)))
}

func (e *rawEngine) accepts(n, S2 int64) bool {
	k := int64(e.k)
	jm := floorDiv2(S2 - k*n - 2*k)
	jp := floorDiv2(S2 - k*n + 2*k)
	if jp < 0 && chernoffUpper(e.lambda(n), jp) <= e.u*(1-1e-9) {
		return false
	}
	return (e.skellamCDF(n, jm)+e.skellamCDF(n, jp))/2 > e.u-1e-12
}

// bernsteinCut returns an integer c such that every candidate n >= c is rejected, by the Bernstein
// bound of random-sign-crossover-inversion.md §5.1 (11); math.MaxInt64 when M <= 4 log(1/u). The bound
// is evaluated at a risk u(1-1e-9) below the acceptance level u-1e-12 used in accepts, and the ceiling
// gets one extra candidate, so floating-point rounding cannot skip a candidate the scan would accept.
func (e *rawEngine) bernsteinCut(S2 int64) int64 {
	if !rawBernstein {
		return math.MaxInt64
	}
	L := math.Log(1 / (e.u * (1 - 1e-9)))
	if float64(e.M) <= 4*L {
		return math.MaxInt64
	}
	k := float64(e.k)
	x := (float64(S2)/k + 2 + 4*L/(3*k)) / (1 - 2*math.Sqrt(L/float64(e.M)))
	return int64(math.Ceil(x)) + 1
}

// upper returns U or -1 for +inf.
func (e *rawEngine) upper(S2 int64) int64 {
	if e.ucache != nil {
		if u, ok := e.ucache[S2]; ok {
			return u
		}
	}
	k := int64(e.k)
	var U int64 = -1
	if math.Exp(-9*float64(e.M)/80) < e.u {
		stop := (4*S2 + 8*k + k - 1) / k
		if s := (int64(e.M) + 2*k - 1) / (2 * k); s > stop {
			stop = s
		}
		if stop < 4 {
			stop = 4
		}
		if c := e.bernsteinCut(S2); c < stop {
			stop = c
		}
		for n := stop - 1; n >= 2; n-- {
			if e.accepts(n, S2) {
				U = n
				break
			}
		}
	}
	if e.ucache != nil {
		e.ucache[S2] = U
	}
	return U
}
