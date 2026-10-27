// fullks: full-range two-sample KS distance of X, direct against planted (run on the server).
//
// usage: fullks SPEC > fullks.tsv
//
// SPEC has one line per configuration: "group<TAB>id<TAB>direct dirs<TAB>planted dirs", where the dir
// lists are space-separated run directories (each holding s/manifest.json and s/cfg_000/chunk_*.bin).
// Failed records are pooled per sample. X = (dhat - d) / s(d) as in v_tail.py, with
// dhat = (S2 - S1^2/M) / (k (1 - k/M)) and s(d) = sqrt(2 d (d-1) / (M-1)).
//
// Output per configuration: failures of each sample, pure-pair share (core_edges == 2) of each sample,
// the full-range KS distance sup_x |F_direct(x) - F_plant(x)|, the asymptotic 95% two-sample critical
// value 1.358 sqrt(1/n1 + 1/n2), the asymptotic p-value (conservative for a discrete X), and the
// largest gap on the pooled 0.2-15 % range for comparison with v_tail.py.
package main

import (
	"bufio"
	"encoding/binary"
	"encoding/json"
	"fmt"
	"math"
	"os"
	"path/filepath"
	"sort"
	"strings"
)

type manifest struct {
	Fields      []string `json:"fields"`
	RecordBytes int      `json:"record_bytes"`
	Configs     []struct {
		M, K, D int
	} `json:"configs"`
}

func read(run string) (xs []float64, pairs int) {
	raw, err := os.ReadFile(filepath.Join(run, "s", "manifest.json"))
	check(err)
	var m manifest
	check(json.Unmarshal(raw, &m))
	idx := map[string]int{}
	for i, f := range m.Fields {
		idx[f] = i
	}
	c := m.Configs[0]
	M, k, d := float64(c.M), float64(c.K), float64(c.D)
	sd := math.Sqrt(2 * d * (d - 1) / (M - 1))
	nf := m.RecordBytes / 4
	chunks, _ := filepath.Glob(filepath.Join(run, "s", "cfg_000", "chunk_*.bin"))
	sort.Strings(chunks)
	for _, p := range chunks {
		b, err := os.ReadFile(p)
		check(err)
		col := func(r int, name string) int64 {
			o := (r*nf + idx[name]) * 4
			return int64(int32(binary.LittleEndian.Uint32(b[o:])))
		}
		for r := 0; r < len(b)/(nf*4); r++ {
			if col(r, "failed") != 1 {
				continue
			}
			S1, S2 := float64(col(r, "S1_rand")), float64(col(r, "S2_rand"))
			dhat := (S2 - S1*S1/M) / (k * (1 - k/M))
			xs = append(xs, (dhat-d)/sd)
			if col(r, "core_edges") == 2 {
				pairs++
			}
		}
	}
	return
}

func pool(dirs string) ([]float64, int) {
	var all []float64
	pairs := 0
	for _, r := range strings.Fields(dirs) {
		x, p := read(r)
		all = append(all, x...)
		pairs += p
	}
	sort.Float64s(all)
	return all, pairs
}

// cdf returns the fraction of sorted a that is <= x.
func cdf(a []float64, x float64) float64 {
	return float64(sort.Search(len(a), func(i int) bool { return a[i] > x })) / float64(len(a))
}

// quantile follows numpy's default linear interpolation.
func quantile(a []float64, q float64) float64 {
	h := q * float64(len(a)-1)
	i := int(math.Floor(h))
	if i+1 >= len(a) {
		return a[len(a)-1]
	}
	return a[i] + (h-float64(i))*(a[i+1]-a[i])
}

// kolmogorov is the asymptotic survival function of the Kolmogorov distribution.
func kolmogorov(l float64) float64 {
	if l < 0.2 {
		return 1
	}
	s := 0.0
	for j := 1; j <= 100; j++ {
		t := 2 * math.Exp(-2*float64(j*j)*l*l)
		if j%2 == 0 {
			t = -t
		}
		s += t
	}
	return math.Min(1, math.Max(0, s))
}

func main() {
	f, err := os.Open(os.Args[1])
	check(err)
	sc := bufio.NewScanner(f)
	sc.Buffer(make([]byte, 1<<20), 1<<26)
	fmt.Println("group\tid\tn_direct\tn_plant\tpair_direct\tpair_plant\tks_full\tks_crit95\tks_p\ttail_gap")
	for sc.Scan() {
		t := strings.Split(sc.Text(), "\t")
		if len(t) != 4 {
			continue
		}
		A, pa := pool(t[2])
		B, pb := pool(t[3])
		pooled := append(append([]float64{}, A...), B...)
		sort.Float64s(pooled)
		lo, hi := quantile(pooled, 0.002), quantile(pooled, 0.15)
		ks, tail := 0.0, 0.0
		for i, x := range pooled {
			if i+1 < len(pooled) && pooled[i+1] == x {
				continue
			}
			g := math.Abs(cdf(A, x) - cdf(B, x))
			ks = math.Max(ks, g)
			if x >= lo && x <= hi {
				tail = math.Max(tail, g)
			}
		}
		n1, n2 := float64(len(A)), float64(len(B))
		ne := n1 * n2 / (n1 + n2)
		p := kolmogorov((math.Sqrt(ne) + 0.12 + 0.11/math.Sqrt(ne)) * ks)
		fmt.Printf("%s\t%s\t%d\t%d\t%.4f\t%.4f\t%.4f\t%.4f\t%.3f\t%.4f\n", t[0], t[1], len(A), len(B),
			float64(pa)/n1, float64(pb)/n2, ks, 1.358*math.Sqrt(1/n1+1/n2), p, tail)
	}
	check(sc.Err())
}

func check(err error) {
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
