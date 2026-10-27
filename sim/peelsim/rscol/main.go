// rscol summarises the random-sign columns of the table tab:mean-by-k rerun
// (sim/results/rs-columns-20261018/). For each config of a peelsim output dir it
// prints, for every X_* field, the failure-conditional mean and its standard error.
// With -ref OLDDIR it first checks, trial by trial, that every field the two runs
// share (X_neg*, X_rand, failed) is bit-identical, i.e. the rerun used the same
// mappings and the same sign draws for the old variants.
//
// usage: rscol [-ref OLDDIR] -out summary.json NEWDIR
package main

import (
	"encoding/binary"
	"encoding/json"
	"flag"
	"fmt"
	"math"
	"os"
	"path/filepath"
	"strings"
)

type cfg struct {
	Index  int `json:"index"`
	M      int `json:"M"`
	K      int `json:"k"`
	D      int `json:"d"`
	Trials int `json:"trials"`
	Chunks int `json:"chunks"`
}

type manifest struct {
	Fields      []string `json:"fields"`
	RecordBytes int      `json:"record_bytes"`
	Configs     []cfg    `json:"configs"`
}

type col struct {
	Name   string  `json:"name"`
	MeanF  float64 `json:"mean_F"`
	SeF    float64 `json:"se_F"`
	MeanA  float64 `json:"mean_all"`
	VarF   float64 `json:"var_F"`
	Within int     `json:"within_2se"` // 1 if |mean_F| <= 2 se_F
}

type out struct {
	Index    int     `json:"index"`
	M, K, D  int     `json:"-"`
	Trials   int64   `json:"trials"`
	Failed   int64   `json:"failed"`
	PF       float64 `json:"p_F"`
	RefTrial int64   `json:"ref_trials_compared"`
	RefDiff  int64   `json:"ref_field_mismatches"`
	Cols     []col   `json:"cols"`
}

func readMan(dir string) manifest {
	b, err := os.ReadFile(filepath.Join(dir, "manifest.json"))
	if err != nil {
		panic(err)
	}
	var m manifest
	if err := json.Unmarshal(b, &m); err != nil {
		panic(err)
	}
	return m
}

func idx(fs []string, n string) int {
	for i, f := range fs {
		if f == n {
			return i
		}
	}
	return -1
}

func main() {
	ref := flag.String("ref", "", "old run dir to compare shared fields against")
	outPath := flag.String("out", "", "summary json")
	flag.Parse()
	dir := flag.Arg(0)
	m := readMan(dir)
	var rm manifest
	if *ref != "" {
		rm = readMan(*ref)
	}
	fi := idx(m.Fields, "failed")
	var xs []int
	for i, f := range m.Fields {
		if strings.HasPrefix(f, "X_") {
			xs = append(xs, i)
		}
	}
	// shared fields: X_* and failed present in both layouts
	type pair struct{ a, b int }
	var shared []pair
	if *ref != "" {
		for i, f := range m.Fields {
			if strings.HasPrefix(f, "X_") || f == "failed" {
				if j := idx(rm.Fields, f); j >= 0 {
					shared = append(shared, pair{i, j})
				}
			}
		}
	}
	var res []out
	for _, c := range m.Configs {
		d := filepath.Join(dir, fmt.Sprintf("cfg_%03d", c.Index))
		if _, err := os.Stat(filepath.Join(d, "chunk_00000.bin")); err != nil {
			continue
		}
		o := out{Index: c.Index, M: c.M, K: c.K, D: c.D}
		s1F := make([]float64, len(xs))
		s2F := make([]float64, len(xs))
		s1A := make([]float64, len(xs))
		for ch := 0; ch < c.Chunks; ch++ {
			name := fmt.Sprintf("chunk_%05d.bin", ch)
			b, err := os.ReadFile(filepath.Join(d, name))
			if err != nil {
				panic(fmt.Sprintf("cfg %d: missing %s", c.Index, name))
			}
			var rb []byte
			if *ref != "" {
				if rb, err = os.ReadFile(filepath.Join(*ref, fmt.Sprintf("cfg_%03d", c.Index), name)); err != nil {
					panic(err)
				}
			}
			n := len(b) / m.RecordBytes
			for t := 0; t < n; t++ {
				r := b[t*m.RecordBytes:]
				failed := binary.LittleEndian.Uint32(r[4*fi:]) == 1
				o.Trials++
				if failed {
					o.Failed++
				}
				for q, i := range xs {
					x := float64(math.Float32frombits(binary.LittleEndian.Uint32(r[4*i:])))
					s1A[q] += x
					if failed {
						s1F[q] += x
						s2F[q] += x * x
					}
				}
				if rb != nil {
					o.RefTrial++
					rr := rb[t*rm.RecordBytes:]
					for _, p := range shared {
						if binary.LittleEndian.Uint32(r[4*p.a:]) != binary.LittleEndian.Uint32(rr[4*p.b:]) {
							o.RefDiff++
						}
					}
				}
			}
		}
		o.PF = float64(o.Failed) / float64(o.Trials)
		nf := float64(o.Failed)
		for q, i := range xs {
			mu := s1F[q] / nf
			v := (s2F[q] - nf*mu*mu) / (nf - 1)
			cl := col{Name: m.Fields[i], MeanF: mu, SeF: math.Sqrt(v / nf), MeanA: s1A[q] / float64(o.Trials), VarF: v}
			if math.Abs(mu) <= 2*cl.SeF {
				cl.Within = 1
			}
			o.Cols = append(o.Cols, cl)
		}
		res = append(res, o)
		fmt.Printf("cfg %d M=%d k=%d d=%d trials=%d pF=%.4f ref_compared=%d mismatches=%d\n",
			c.Index, c.M, c.K, c.D, o.Trials, o.PF, o.RefTrial, o.RefDiff)
		for _, cl := range o.Cols {
			fmt.Printf("  %-12s E[X|F]=%+.4f se=%.4f var=%.4f\n", cl.Name, cl.MeanF, cl.SeF, cl.VarF)
		}
	}
	if *outPath != "" {
		b, _ := json.MarshalIndent(res, "", "  ")
		if err := os.WriteFile(*outPath, b, 0o644); err != nil {
			panic(err)
		}
	}
}
