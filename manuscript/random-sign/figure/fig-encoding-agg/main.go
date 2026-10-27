// Summarize per-run fig-encoding CSVs (R,F,X_0,X_1,X_rand) into the figures' inputs:
// histogram counts on 40 bins over [-4,4] for all and failed runs, per-column statistics over failed runs,
// the joint statistics of (X_1, R) used by the STD figures, and every 1000th run as a scatter sample.
//
// fig-encoding-agg HIST.csv STATS.csv JOINT.csv SAMPLE.csv s1.csv s2.csv ...
package main

import (
	"bufio"
	"fmt"
	"math"
	"os"
	"sort"
	"strconv"
	"strings"
)

var cols = []string{"X_0", "X_1", "X_rand"}

const nbin, lo, hi = 40, -4.0, 4.0

func main() {
	var fail []bool
	var r []float64
	xs := make([][]float64, len(cols))
	for _, path := range os.Args[5:] {
		f, err := os.Open(path)
		check(err)
		sc := bufio.NewScanner(f)
		sc.Scan()
		if sc.Text() != "R,F,X_0,X_1,X_rand" {
			panic(path + ": unexpected header")
		}
		for sc.Scan() {
			p := strings.Split(sc.Text(), ",")
			fail = append(fail, p[1] == "1")
			v, err := strconv.ParseFloat(p[0], 64)
			check(err)
			r = append(r, v)
			for j := range cols {
				v, err := strconv.ParseFloat(p[2+j], 64)
				check(err)
				xs[j] = append(xs[j], v)
			}
		}
		check(sc.Err())
		f.Close()
	}
	h, err := os.Create(os.Args[1])
	check(err)
	fmt.Fprintln(h, "col,bin_lo,bin_hi,n_all,n_fail")
	s, err := os.Create(os.Args[2])
	check(err)
	fmt.Fprintln(s, "col,runs,n_fail,mean_fail,se_fail,var_fail,ks_fail_all")
	for j, c := range cols {
		var all, fl [nbin]int
		var xf []float64
		for i, v := range xs[j] {
			if fail[i] {
				xf = append(xf, v)
			}
			if v < lo || v > hi {
				continue
			}
			// as numpy.histogram: bin b is [edge b, edge b+1), the last bin is closed
			b := sort.Search(nbin+1, func(i int) bool { return edge(i) > v }) - 1
			if b == nbin {
				b--
			}
			all[b]++
			if fail[i] {
				fl[b]++
			}
		}
		for b := 0; b < nbin; b++ {
			fmt.Fprintf(h, "%s,%.1f,%.1f,%d,%d\n", c, edge(b), edge(b+1), all[b], fl[b])
		}
		m, v := meanVar(xf)
		fmt.Fprintf(s, "%s,%d,%d,%.6f,%.6f,%.6f,%.6f\n", c, len(xs[j]), len(xf), m, math.Sqrt(v/float64(len(xf))), v, ks(xf, xs[j]))
	}
	check(h.Close())
	check(s.Close())
	writeJoint(os.Args[3], xs[1], r, fail)
	writeSample(os.Args[4], xs[1], r, fail)
}

// writeJoint writes the sample covariance (numpy.cov, ddof=1) of (X_1, R) and the agreement of {R <= 0} with failure.
func writeJoint(path string, x, r []float64, fail []bool) {
	mx, _ := meanVar(x)
	mr, _ := meanVar(r)
	var sxx, srr, sxr float64
	agree := 0
	for i := range x {
		sxx += (x[i] - mx) * (x[i] - mx)
		srr += (r[i] - mr) * (r[i] - mr)
		sxr += (x[i] - mx) * (r[i] - mr)
		if (r[i] <= 0) == fail[i] {
			agree++
		}
	}
	n := float64(len(x))
	f, err := os.Create(path)
	check(err)
	fmt.Fprintln(f, "runs,var_x1,var_r,cov_x1_r,agree_r_le0_fail")
	fmt.Fprintf(f, "%d,%.6f,%.6f,%.6f,%.6f\n", len(x), sxx/(n-1), srr/(n-1), sxr/(n-1), float64(agree)/n)
	check(f.Close())
}

// writeSample writes every 1000th run (R, F, X_1) for the scatter panel.
func writeSample(path string, x, r []float64, fail []bool) {
	f, err := os.Create(path)
	check(err)
	w := bufio.NewWriter(f)
	fmt.Fprintln(w, "R,F,X_1")
	for i := 0; i < len(x); i += 1000 {
		b := 0
		if fail[i] {
			b = 1
		}
		fmt.Fprintf(w, "%.5f,%d,%.5f\n", r[i], b, x[i])
	}
	check(w.Flush())
	check(f.Close())
}

// edge is numpy.linspace(lo, hi, nbin+1)[i].
func edge(i int) float64 {
	if i == nbin {
		return hi
	}
	return lo + float64(i)*((hi-lo)/nbin)
}

// meanVar returns the mean and the population variance (numpy ddof=0).
func meanVar(x []float64) (float64, float64) {
	var m, q float64
	for _, v := range x {
		m += v
	}
	m /= float64(len(x))
	for _, v := range x {
		q += (v - m) * (v - m)
	}
	return m, q / float64(len(x))
}

// ks is the two-sample Kolmogorov-Smirnov distance sup |F_a - F_b|.
func ks(a, b []float64) float64 {
	a, b = sorted(a), sorted(b)
	var d float64
	i, j := 0, 0
	for i < len(a) && j < len(b) {
		t := math.Min(a[i], b[j])
		for i < len(a) && a[i] <= t {
			i++
		}
		for j < len(b) && b[j] <= t {
			j++
		}
		d = math.Max(d, math.Abs(float64(i)/float64(len(a))-float64(j)/float64(len(b))))
	}
	return d
}

func sorted(x []float64) []float64 {
	y := append([]float64(nil), x...)
	sort.Float64s(y)
	return y
}

func check(err error) {
	if err != nil {
		panic(err)
	}
}
