//go:build ignore

// r22replay: replay stored peelsim records (-sumc) under the final raw-energy inversion and rchi,
// for R22 (d >> sqrt(M) and overload, sim/runs/make_r22_specs.py). The raw engine below is a verbatim
// copy of sim/iblt2r/raw.go (windowed exact Poisson tables, Bernstein search cutoff, exact CDF
// everywhere); rchi is copied from rawreplay.go (candidates from 2). Configurations are processed in
// parallel (-jobs). Timing: for each configuration, the first -tn failed records are sized again
// without reuse of finished bounds, (a) cold: a fresh table cache per record, (b) session: one table
// cache shared over the records of the configuration; single goroutine per configuration.
//
// usage: go run r22replay.go -q qtable.json -out r22.json -jobs 64 -tn 0 RUNDIR [RUNDIR...]   (coverage)
//
//	go run r22replay.go -q qtable.json -out r22t.json -jobs 1 -timeonly RUNDIR [...]    (timing)
package main

import (
	"bufio"
	"encoding/binary"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"math"
	"os"
	"path/filepath"
	"sort"
	"sync"
	"time"
)

// ---- raw engine: verbatim copy of sim/iblt2r/raw.go -------------------------------------------

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

// ---- rchi (copied from rawreplay.go) ------------------------------------------------------------

func upperRchi(dhat, q float64, M int) int64 {
	s := func(n int64) float64 { return math.Sqrt(2 * float64(n) * float64(n-1) / float64(M-1)) }
	acc := func(n int64) bool { return dhat-float64(n) >= q*s(n) }
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

// ---- replay -------------------------------------------------------------------------------------

var rules = []string{"raw01", "raw05", "rchi01", "rchi05"}

type group struct {
	N     int64                       `json:"n"`
	Miss  map[string]int64            `json:"miss"`
	Empty map[string]int64            `json:"empty"`
	Width map[string]map[string]int64 `json:"width"` // rule -> U-d -> count ("inf" for +inf)
}

func newGroup() *group {
	g := &group{Miss: map[string]int64{}, Empty: map[string]int64{}, Width: map[string]map[string]int64{}}
	for _, r := range rules {
		g.Width[r] = map[string]int64{}
	}
	return g
}

func (g *group) add(us map[string]int64, d int64) {
	g.N++
	for _, r := range rules {
		u := us[r]
		if u < 0 {
			g.Empty[r]++
			g.Width[r]["inf"]++
			continue
		}
		if u < d {
			g.Miss[r]++
		}
		g.Width[r][fmt.Sprint(u-d)]++
	}
}

type manifest struct {
	Fields      []string         `json:"fields"`
	RecordBytes int              `json:"record_bytes"`
	Configs     []map[string]any `json:"configs"`
}

var timeOnly bool
var timeReps = 1

func runCfg(dir string, man *manifest, c map[string]any, qtab map[string]map[string]float64, tn int) map[string]any {
	idx := map[string]int{}
	for i, f := range man.Fields {
		idx[f] = i
	}
	_, hasUn := idx["uncond"]
	ci := int(c["index"].(float64))
	M, k, d := int(c["M"].(float64)), int(c["k"].(float64)), int64(c["d"].(float64))
	q := qtab[fmt.Sprint(M)]
	gamma := float64(k) * (1 - float64(k)/float64(M))
	pc := newPoisCache(M, k)
	eng := map[string]*rawEngine{"raw01": newRawShared(pc, 0.01, true), "raw05": newRawShared(pc, 0.05, true)}
	gs := map[string]*group{"uncond": newGroup(), "failed": newGroup(), "failed_pair": newGroup(), "failed_other": newGroup()}
	var timeS2 []int64
	var timeDhat []float64
	files, _ := filepath.Glob(filepath.Join(dir, fmt.Sprintf("cfg_%03d", ci), "chunk_*.bin"))
	sort.Strings(files)
	buf := make([]byte, man.RecordBytes)
	var nrec int64
	for _, p := range files {
		if timeOnly && len(timeS2) >= tn {
			break
		}
		f, err := os.Open(p)
		must(err)
		r := bufio.NewReaderSize(f, 1<<22)
		for {
			if _, err := io.ReadFull(r, buf); err == io.EOF {
				break
			} else if err != nil {
				panic(fmt.Sprintf("%s: %v", p, err))
			}
			nrec++
			i32 := func(n string) int64 { return int64(int32(binary.LittleEndian.Uint32(buf[4*idx[n]:]))) }
			var sel []*group
			if !hasUn || i32("uncond") != 0 {
				sel = append(sel, gs["uncond"])
			}
			failed := i32("failed") != 0
			if failed {
				sel = append(sel, gs["failed"])
				if i32("core_edges") == 2 {
					sel = append(sel, gs["failed_pair"])
				} else {
					sel = append(sel, gs["failed_other"])
				}
			}
			if len(sel) == 0 {
				continue
			}
			S1, S2 := i32("S1_rand"), i32("S2_rand")
			dhat := (float64(S2) - float64(S1)*float64(S1)/float64(M)) / gamma
			if failed && len(timeS2) < tn {
				timeS2 = append(timeS2, S2)
				timeDhat = append(timeDhat, dhat)
			}
			if timeOnly {
				if len(timeS2) >= tn {
					break
				}
				continue
			}
			us := map[string]int64{"raw01": eng["raw01"].upper(S2), "raw05": eng["raw05"].upper(S2),
				"rchi01": upperRchi(dhat, q["rchi01"], M), "rchi05": upperRchi(dhat, q["rchi05"], M)}
			for _, g := range sel {
				g.add(us, d)
			}
		}
		f.Close()
	}
	// timing at u = 0.01 on the first tn failed records, repeated timeReps times. Modes: cold (a fresh
	// table cache per record), session (one cache over the records, starting empty), warm (the same
	// record sized twice in a row, the second call timed), gauss (the Gaussian rule). The order of the
	// four modes rotates with the repetition.
	tim := map[string]any{"n": len(timeS2), "tabcap_entries": maxTabEntries}
	if len(timeS2) > 0 {
		var reps []map[string]any
		coldPeak, sessPeak := 0, 0
		for r := 0; r < timeReps; r++ {
			res := map[string]any{}
			modes := []string{"cold", "session", "warm", "gauss"}
			for m := 0; m < 4; m++ {
				switch modes[(m+r)%4] {
				case "cold":
					x := make([]float64, len(timeS2))
					for i, s := range timeS2 {
						t0 := time.Now()
						e := newRaw(M, k, 0.01, false)
						e.upper(s)
						x[i] = time.Since(t0).Seconds()
						if e.cache.peak > coldPeak {
							coldPeak = e.cache.peak
						}
					}
					res["raw_cold"] = summ(x)
				case "session":
					x := make([]float64, len(timeS2))
					se := newRaw(M, k, 0.01, false)
					for i, s := range timeS2 {
						t0 := time.Now()
						se.upper(s)
						x[i] = time.Since(t0).Seconds()
					}
					if se.cache.peak > sessPeak {
						sessPeak = se.cache.peak
					}
					res["raw_session"] = summ(x)
				case "warm":
					x := make([]float64, len(timeS2))
					we := newRaw(M, k, 0.01, false)
					for i, s := range timeS2 {
						we.upper(s)
						t0 := time.Now()
						we.upper(s)
						x[i] = time.Since(t0).Seconds()
					}
					res["raw_warm"] = summ(x)
				case "gauss":
					x := make([]float64, len(timeDhat))
					for i, v := range timeDhat {
						t0 := time.Now()
						upperRchi(v, q["rchi01"], M)
						x[i] = time.Since(t0).Seconds()
					}
					res["gauss"] = summ(x)
				}
			}
			reps = append(reps, res)
		}
		tim["reps"] = reps
		tim["cold_peak_entries"] = coldPeak
		tim["session_peak_entries"] = sessPeak
	}
	meta := map[string]any{}
	for _, key := range []string{"index", "k", "M", "d", "trials", "failed"} {
		meta[key] = c[key]
	}
	meta["records"] = nrec
	meta["distinct_S2"] = len(eng["raw01"].ucache)
	fmt.Fprintf(os.Stderr, "%s cfg %d M=%d k=%d d=%d records=%d failed=%d distinctS2=%d\n", filepath.Base(dir), ci, M, k, d, nrec, gs["failed"].N, len(eng["raw01"].ucache))
	return map[string]any{"meta": meta, "groups": gs, "timing": tim}
}

func summ(x []float64) map[string]float64 {
	y := append([]float64(nil), x...)
	sort.Float64s(y)
	var s float64
	for _, v := range y {
		s += v
	}
	at := func(p float64) float64 { return y[int(p*float64(len(y)-1))] }
	return map[string]float64{"mean": s / float64(len(y)), "p25": at(0.25), "p50": at(0.5), "p75": at(0.75), "p90": at(0.9), "max": y[len(y)-1]}
}

func main() {
	qpath := flag.String("q", "qtable.json", "quantile table keyed by M (rchi)")
	out := flag.String("out", "r22.json", "output json")
	jobs := flag.Int("jobs", 8, "configurations processed in parallel")
	tn := flag.Int("tn", 300, "failed records per configuration used for timing")
	flag.BoolVar(&timeOnly, "timeonly", false, "only the timing pass (stop reading after tn failed records)")
	flag.IntVar(&timeReps, "reps", 1, "repetitions of the timing pass")
	flag.IntVar(&maxTabEntries, "tabcap", 4_000_000, "Poisson-table cache entries (16 bytes each)")
	flag.Parse()
	var qtab map[string]map[string]float64
	must(readJSON(*qpath, &qtab))
	runs := map[string]any{}
	for _, dir := range flag.Args() {
		var man manifest
		must(readJSON(filepath.Join(dir, "manifest.json"), &man))
		outs := make([]map[string]any, len(man.Configs))
		sem := make(chan struct{}, *jobs)
		var wg sync.WaitGroup
		for i, c := range man.Configs {
			wg.Add(1)
			sem <- struct{}{}
			go func(i int, c map[string]any) {
				defer wg.Done()
				outs[i] = runCfg(dir, &man, c, qtab, *tn)
				<-sem
			}(i, c)
		}
		wg.Wait()
		runs[runKey(dir)] = outs
		f, err := os.Create(*out)
		must(err)
		must(json.NewEncoder(f).Encode(map[string]any{"runs": runs}))
		f.Close()
	}
}

func readJSON(p string, v any) error {
	b, err := os.ReadFile(p)
	if err != nil {
		return err
	}
	return json.Unmarshal(b, v)
}

func must(err error) {
	if err != nil {
		panic(err)
	}
}

// runKey names a run in the output: the directory's base name, prefixed by its parent's base name
// when the base is the generic "s" of a queue task (exp6), so that several task runs stay distinct.
func runKey(dir string) string {
	d := filepath.Clean(dir)
	if filepath.Base(d) == "s" {
		return filepath.Base(filepath.Dir(d)) + "/s"
	}
	return filepath.Base(d)
}
