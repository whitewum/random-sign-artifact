// Read-only check of the PROTO per-trial records against the per-block aggregates.
// usage: go run main.go <campaign>/out/p > trialcheck.json  (reads each block's trials.csv and proto.csv)
package main

import (
	"bufio"
	"encoding/csv"
	"encoding/json"
	"fmt"
	"math"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
)

var alphaC = map[int]float64{3: 0.818469160761, 4: 0.772279839803, 5: 0.701780266485}

type row struct {
	U   int64
	M2  int
	ok2 int
}

type block struct {
	k, M1, d, onesided, trials int
	arms                       map[string]map[int]row // arm -> trial -> row
	agg                        map[string]map[string]string
}

var problems []string

func bad(f string, a ...any) {
	if len(problems) < 200 {
		problems = append(problems, fmt.Sprintf(f, a...))
	}
}

func atoi(s string) int { v, err := strconv.Atoi(s); if err != nil { panic(s) }; return v }

func load(dir string) *block {
	b := &block{arms: map[string]map[int]row{}, agg: map[string]map[string]string{}}
	f, _ := os.Open(filepath.Join(dir, "proto.csv"))
	recs, err := csv.NewReader(f).ReadAll()
	f.Close()
	if err != nil {
		panic(err)
	}
	for _, r := range recs[1:] {
		m := map[string]string{}
		for i, h := range recs[0] {
			m[h] = r[i]
		}
		b.agg[m["arm"]] = m
		b.k, b.M1, b.d, b.onesided, b.trials = atoi(m["k"]), atoi(m["M1"]), atoi(m["d"]), atoi(m["onesided"]), atoi(m["trials"])
	}
	tf, err := os.Open(filepath.Join(dir, "trials.csv"))
	if err != nil {
		bad("%s: no trials.csv", dir)
		return b
	}
	sc := bufio.NewScanner(tf)
	sc.Buffer(make([]byte, 1<<20), 1<<20)
	sc.Scan() // header
	for sc.Scan() {
		p := strings.Split(sc.Text(), ",")
		if len(p) != 6 || p[0] != "0" {
			bad("%s: malformed line %q", dir, sc.Text())
			continue
		}
		t, arm := atoi(p[1]), p[2]
		U, _ := strconv.ParseInt(p[3], 10, 64)
		if b.arms[arm] == nil {
			b.arms[arm] = map[int]row{}
		}
		if _, dup := b.arms[arm][t]; dup {
			bad("%s: duplicate trial %d arm %s", dir, t, arm)
		}
		b.arms[arm][t] = row{U, atoi(p[4]), atoi(p[5])}
	}
	tf.Close()
	return b
}

func keys(m map[int]row) []int {
	out := make([]int, 0, len(m))
	for t := range m {
		out = append(out, t)
	}
	sort.Ints(out)
	return out
}

func sameKeys(a, b map[int]row) bool {
	if len(a) != len(b) {
		return false
	}
	for t := range a {
		if _, ok := b[t]; !ok {
			return false
		}
	}
	return true
}

func main() {
	root := os.Args[1]
	dirs, _ := filepath.Glob(filepath.Join(root, "p-u0*-b*"))
	sort.Strings(dirs)
	blocks := map[string]*block{}
	var lines, f1total int
	m2mismatch, belowB, oracleNotD := 0, 0, 0
	for _, dir := range dirs {
		b := load(dir)
		name := filepath.Base(dir)
		blocks[name] = b
		for arm, ag := range b.agg {
			rs := b.arms[arm]
			var f1, empty, miss, f2, ok1 int
			var m2sum float64
			for t, r := range rs {
				if t < 0 || t >= b.trials {
					bad("%s %s: trial %d out of range", name, arm, t)
				}
				f1++
				lines++
				m2sum += float64(r.M2)
				want := 4 * b.M1
				if r.U < 0 {
					empty++
				} else {
					if r.U < int64(b.d) {
						miss++
					}
					want = int(math.Ceil(float64(r.U) / (0.8 * alphaC[b.k])))
					if want < 64 {
						want = 64
					}
				}
				if r.M2 != want {
					m2mismatch++
				}
				if r.ok2 == 0 {
					f2++
				} else {
					ok1++
				}
				if strings.HasSuffix(arm, "_b") && r.U >= 0 {
					bb := 0
					if b.onesided == 1 {
						bb = b.d
					} else {
						bb = b.d%2
					}
					if r.U < int64(bb) {
						belowB++
					}
				}
				if arm == "signed_oracle" && r.U != int64(b.d) {
					oracleNotD++
				}
			}
			f1total += f1
			for _, c := range [][2]any{{"f1", f1}, {"f1_empty", empty}, {"f1_miss", miss}, {"f2", f2}} {
				if atoi(ag[c[0].(string)]) != c[1].(int) {
					bad("%s %s: %s agg %s trials.csv %d", name, arm, c[0], ag[c[0].(string)], c[1])
				}
			}
			if f1 > 0 {
				mean, _ := strconv.ParseFloat(ag["mean_M2"], 64)
				if math.Abs(m2sum/float64(f1)-mean) > 0.006 {
					bad("%s %s: mean_M2 agg %s trials.csv %.3f", name, arm, ag["mean_M2"], m2sum/float64(f1))
				}
			}
		}
		for arm := range b.arms {
			if _, ok := b.agg[arm]; !ok {
				bad("%s: arm %s in trials.csv but not proto.csv", name, arm)
			}
		}
		// round-1 failures are the same trials for every arm (Prop. decode: both encodings recover the same keys)
		ref := b.arms["signed_raw_b"]
		for arm, rs := range b.arms {
			if !sameKeys(ref, rs) {
				bad("%s: failing trial set of %s differs from signed_raw_b", name, arm)
			}
		}
	}
	// pairing across u: same block, same seed -> same failing trials and identical oracle rows
	pairs, oracleRowsCompared, oracleRowDiff := 0, 0, 0
	for name, b1 := range blocks {
		if !strings.HasPrefix(name, "p-u01-") {
			continue
		}
		b5, ok := blocks["p-u05-"+strings.TrimPrefix(name, "p-u01-")]
		if !ok {
			bad("%s: no u05 partner", name)
			continue
		}
		pairs++
		if b1.trials != b5.trials {
			bad("%s: trials differ across u", name)
		}
		for _, arm := range []string{"signed_raw_b", "signed_rchi_b", "signed_oracle"} {
			if !sameKeys(b1.arms[arm], b5.arms[arm]) {
				bad("%s %s: failing trial set differs across u", name, arm)
			}
		}
		o1, o5 := b1.arms["signed_oracle"], b5.arms["signed_oracle"]
		for _, t := range keys(o1) {
			oracleRowsCompared++
			if o1[t] != o5[t] {
				oracleRowDiff++
			}
		}
	}
	out := map[string]any{
		"blocks": len(dirs), "u_pairs": pairs, "trial_lines": lines, "round1_failure_lines": f1total,
		"m2_formula_mismatch": m2mismatch, "ub_below_abs_b": belowB, "oracle_U_not_d": oracleNotD,
		"oracle_rows_compared_across_u": oracleRowsCompared, "oracle_rows_differing_across_u": oracleRowDiff,
		"problems": problems,
	}
	enc := json.NewEncoder(os.Stdout)
	enc.SetIndent("", " ")
	enc.Encode(out)
}
