package main

// Checks the production raw rule (windowed Poisson tables, Bernstein search cutoff) against the full-table
// implementation with the original cutoff (10), which matched the Decimal reference
// (theory/scripts/random_sign_crossover.py) on 4822 cases: the upper bound must be identical. A second
// test evaluates the exact CDF on every candidate skipped by the Bernstein cutoff.

import (
	"math"
	"math/rand/v2"
	"testing"
)

type fullEngine struct {
	M, k int
	u    float64
	tabs map[int64][2][]float64
}

func (e *fullEngine) lambda(n int64) float64 {
	return float64(e.k*e.k) * float64(n-2) * float64(n-3) / (4 * float64(e.M))
}

func (e *fullEngine) cdf(n, j int64) float64 {
	lam := e.lambda(n)
	if lam == 0 {
		if j >= 0 {
			return 1
		}
		return 0
	}
	t, ok := e.tabs[n]
	if !ok {
		imax := int(lam+14*math.Sqrt(lam)) + 40
		p := make([]float64, imax+1)
		F := make([]float64, imax+1)
		var s float64
		for i := 0; i <= imax; i++ {
			lg, _ := math.Lgamma(float64(i) + 1)
			p[i] = math.Exp(-lam + float64(i)*math.Log(lam) - lg)
			s += p[i]
			F[i] = s
		}
		t = [2][]float64{p, F}
		e.tabs[n] = t
	}
	p, F := t[0], t[1]
	var s float64
	L := int64(len(p))
	for m := int64(0); m < L; m++ {
		x := j + m
		if x < 0 {
			continue
		}
		if x >= L {
			s += p[m]
			continue
		}
		s += p[m] * F[x]
	}
	return s
}

func (e *fullEngine) upper(S2 int64) int64 {
	k := int64(e.k)
	if math.Exp(-9*float64(e.M)/80) >= e.u {
		return -1
	}
	stop := (4*S2 + 8*k + k - 1) / k
	if s := (int64(e.M) + 2*k - 1) / (2 * k); s > stop {
		stop = s
	}
	if stop < 4 {
		stop = 4
	}
	for n := stop - 1; n >= 2; n-- {
		jm := floorDiv2(S2 - k*n - 2*k)
		jp := floorDiv2(S2 - k*n + 2*k)
		if jp < 0 && chernoffUpper(e.lambda(n), jp) <= e.u*(1-1e-9) {
			continue
		}
		if (e.cdf(n, jm)+e.cdf(n, jp))/2 > e.u-1e-12 {
			return n
		}
	}
	return -1
}

func TestWindowedMatchesFull(t *testing.T) {
	rng := rand.New(rand.NewPCG(20261014, 1))
	cases, inf := 0, 0
	for _, M := range []int{16, 64, 256, 1024, 4096, 16384} {
		for _, k := range []int{3, 4, 5} {
			for _, u := range []float64{0.01, 0.05} {
				full := &fullEngine{M: M, k: k, u: u, tabs: map[int64][2][]float64{}}
				win := newRaw(M, k, u, false)
				// d up to about 3 alpha_c M (the largest load in the E5 grid), S2/k near n and spread around it
				dmax := 3 * M
				if testing.Short() || M == 16384 {
					dmax = M / 2
				}
				for i := 0; i < 60; i++ {
					d := 2 + rng.IntN(dmax)
					lam := float64(k*k) * float64(d) * float64(d) / (4 * float64(M))
					off := int64(math.Round(rng.NormFloat64() * 2 * math.Sqrt(2*lam+1) * float64(k)))
					for _, S2 := range []int64{int64(k*d) + off, int64(k*d) + off + 1, int64(k * d), int64(k*d) - 2*int64(k)} {
						if S2 < 0 {
							continue
						}
						a, b := full.upper(S2), win.upper(S2)
						cases++
						if a < 0 {
							inf++
						}
						if a != b {
							t.Fatalf("M=%d k=%d u=%g S2=%d: full %d windowed %d", M, k, u, S2, a, b)
						}
					}
				}
			}
		}
	}
	// small d and every S2 near the lattice atoms
	for _, M := range []int{16, 64, 256, 1024} {
		for _, k := range []int{3, 4, 5} {
			for _, u := range []float64{0.01, 0.05} {
				full := &fullEngine{M: M, k: k, u: u, tabs: map[int64][2][]float64{}}
				win := newRaw(M, k, u, false)
				for S2 := int64(0); S2 <= int64(k*14); S2++ {
					a, b := full.upper(S2), win.upper(S2)
					cases++
					if a < 0 {
						inf++
					}
					if a != b {
						t.Fatalf("M=%d k=%d u=%g S2=%d: full %d windowed %d", M, k, u, S2, a, b)
					}
				}
			}
		}
	}
	t.Logf("%d cases identical (%d +inf)", cases, inf)
}

func TestBernsteinSkipsOnlyRejected(t *testing.T) {
	rng := rand.New(rand.NewPCG(20261014, 2))
	checked, maxGap := 0, 0.0
	for _, M := range []int{64, 256, 1024, 4096, 16384} {
		for _, k := range []int{3, 4, 5} {
			for _, u := range []float64{0.01, 0.05} {
				full := &fullEngine{M: M, k: k, u: u, tabs: map[int64][2][]float64{}}
				win := newRaw(M, k, u, false)
				for i := 0; i < 40; i++ {
					d := 2 + rng.IntN(M/2)
					S2 := int64(k*d) + int64(math.Round(rng.NormFloat64()*float64(k)*math.Sqrt(float64(k*k*d*d)/(2*float64(M))+1)))
					if S2 < 0 {
						S2 = 0
					}
					c := win.bernsteinCut(S2)
					kk := int64(k)
					for n := c; n < c+200; n++ { // the candidates nearest the cutoff are the hardest to reject
						jm := floorDiv2(S2 - kk*n - 2*kk)
						jp := floorDiv2(S2 - kk*n + 2*kk)
						cdf := (full.cdf(n, jm) + full.cdf(n, jp)) / 2
						if cdf > u-1e-12 {
							t.Fatalf("M=%d k=%d u=%g S2=%d: skipped candidate %d accepted (CDF %g)", M, k, u, S2, n, cdf)
						}
						if r := cdf / u; r > maxGap {
							maxGap = r
						}
						checked++
					}
				}
			}
		}
	}
	t.Logf("%d skipped candidates rejected; largest CDF/u among them %.3g", checked, maxGap)
}

// TestEvictionKeepsResults runs consecutive sessions through one shared cache with a capacity far below
// the working set, so tables are evicted constantly, and compares each bound with a fresh engine.
func TestEvictionKeepsResults(t *testing.T) {
	saved := maxTabEntries
	maxTabEntries = 20000
	defer func() { maxTabEntries = saved }()
	rng := rand.New(rand.NewPCG(20261014, 3))
	c := newPoisCache(4096, 3)
	shared01, shared05 := newRawShared(c, 0.01, false), newRawShared(c, 0.05, false)
	for i := 0; i < 300; i++ {
		S2 := int64(3*(2+rng.IntN(9000))) + int64(rng.IntN(200)) - 100
		if S2 < 0 {
			S2 = 0
		}
		for _, p := range []struct {
			e *rawEngine
			u float64
		}{{shared01, 0.01}, {shared05, 0.05}} {
			if a, b := p.e.upper(S2), newRaw(4096, 3, p.u, false).upper(S2); a != b {
				t.Fatalf("S2=%d u=%g: shared %d fresh %d", S2, p.u, a, b)
			}
		}
	}
	if c.peak > maxTabEntries {
		t.Fatalf("cache peak %d above capacity %d", c.peak, maxTabEntries)
	}
	t.Logf("600 bounds identical; cache peak %d entries", c.peak)
}
