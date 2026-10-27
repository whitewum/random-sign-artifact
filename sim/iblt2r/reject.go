package main

// Per-encoding count of the +-1 candidates that the decoder rejects, across sign compositions.
// Each trial is the audited paired decoding of stress.go; standard and random-sign are reported separately.
import (
	"bufio"
	"encoding/json"
	"flag"
	"fmt"
	"math"
	"os"
	"sync"
	"time"
)

var rejectMode = flag.Bool("decode-reject", false, "run per-encoding rejected-candidate experiment over sign compositions")
var rejectTrials = flag.Int("reject-trials", 20000, "trials per configuration")

// Minus fractions d_-/d; Plus = d - round(d * minus).
var rejectMinus = []float64{0, 0.125, 0.25, 0.375, 0.5, 0.625, 0.75, 0.875, 1}

func rejectConfigs() []stressConfig {
	var out []stressConfig
	m := 16384
	for _, k := range []int{3, 4, 5, 6, 10} {
		a := peelingAlpha(k)
		for _, load := range []float64{0.5, 0.95, 1} {
			d := int(math.Round(a * float64(m) * load))
			for _, minus := range rejectMinus {
				plus := d - int(math.Round(float64(d)*minus))
				out = append(out, stressConfig{len(out), k, m, d, plus, min(1000, m), *rejectTrials, load, minus, a})
			}
		}
	}
	return out
}

// encCount sums over trials; *2 fields are sums of squares for standard errors.
type encCount struct {
	Cand, Rej, MemRej, Fake, Accepted int64
	Rej2, Fake2                       float64
}
type rejectRow struct {
	Task     int          `json:"task"`
	Config   stressConfig `json:"config"` // Fraction holds d_-/d
	Start    int          `json:"start"`
	Trials   int          `json:"trials"`
	Success  int          `json:"success"`
	Standard encCount     `json:"standard"`
	Signed   encCount     `json:"signed"`
	Seconds  float64      `json:"seconds"`
	Seed     uint64       `json:"seed"`
}

func (e *encCount) add(r decoded, n int64, f int) {
	rej := r.cnt.chkRej + r.cnt.memRej
	e.Cand += r.cnt.cand
	e.Rej += rej
	e.MemRej += r.cnt.memRej
	e.Fake += int64(f)
	e.Accepted += n
	e.Rej2 += float64(rej) * float64(rej)
	e.Fake2 += float64(f) * float64(f)
}

func runDecodeReject(path string, jobs int, seed uint64) {
	if *stressShards < 1 || *stressShard < 0 || *stressShard >= *stressShards || *stressChunk < 1 || jobs < 1 {
		panic("invalid partition or worker count")
	}
	configs := rejectConfigs()
	done := map[int]bool{}
	if f, e := os.Open(path); e == nil {
		sc := bufio.NewScanner(f)
		for sc.Scan() {
			var r rejectRow
			must(json.Unmarshal(sc.Bytes(), &r))
			if r.Seed != seed || r.Config != configs[r.Config.ID] {
				panic("resume seed or configuration mismatch")
			}
			done[r.Task] = true
		}
		must(sc.Err())
		f.Close()
	} else if !os.IsNotExist(e) {
		must(e)
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
	results := make(chan rejectRow, jobs)
	var wg sync.WaitGroup
	for w := 0; w < jobs; w++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for t := range tasks {
				row := rejectRow{Task: t.id, Config: t.c, Start: t.start, Trials: t.n, Seed: seed}
				start := time.Now()
				for j := 0; j < t.n; j++ {
					r0, r1, n0, n1, f0, f1 := stressPair(t.c, t.start+j, seed)
					if r0.ok {
						row.Success++
					}
					row.Standard.add(r0, n0, f0)
					row.Signed.add(r1, n1, f1)
				}
				row.Seconds = time.Since(start).Seconds()
				results <- row
			}
		}()
	}
	go func() {
		id := 0
		for start := 0; start < *rejectTrials; start += *stressChunk {
			for _, c := range configs {
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
	for r := range results {
		must(enc.Encode(r))
		must(f.Sync())
		fmt.Fprintf(os.Stderr, "task=%d k=%d load=%g minus=%g trials=%d seconds=%.1f\n", r.Task, r.Config.K, r.Config.Load, r.Config.Fraction, r.Trials, r.Seconds)
	}
}
