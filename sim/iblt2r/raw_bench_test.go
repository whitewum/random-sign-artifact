package main

import "testing"

func benchBoth(b *testing.B, d int64, warm bool) {
	for _, on := range []bool{false, true} {
		name := "cut10"
		if on {
			name = "bernstein"
		}
		b.Run(name, func(b *testing.B) {
			rawBernstein = on
			defer func() { rawBernstein = true }()
			e := newRaw(16384, 3, 0.01, false)
			e.upper(3 * d)
			b.ResetTimer()
			for i := 0; i < b.N; i++ {
				if !warm {
					e = newRaw(16384, 3, 0.01, false)
				}
				e.upper(3 * d)
			}
		})
	}
}

func BenchmarkCold105(b *testing.B) { benchBoth(b, 14080, false) }
func BenchmarkWarm105(b *testing.B) { benchBoth(b, 14080, true) }
func BenchmarkCold3(b *testing.B)   { benchBoth(b, 40229, false) }
func BenchmarkWarm3(b *testing.B)   { benchBoth(b, 40229, true) }

// BenchmarkUpperLoad3 times one raw upper bound at M=16384, k=3, d=40229 (load 3), S2 = k d, cold engine.
func BenchmarkUpperLoad3(b *testing.B) {
	for i := 0; i < b.N; i++ {
		newRaw(16384, 3, 0.01, false).upper(3 * 40229)
	}
}

// BenchmarkUpperLoad105 is the same at d=14080 (load 1.05), the timing configuration.
func BenchmarkUpperLoad105(b *testing.B) {
	for i := 0; i < b.N; i++ {
		newRaw(16384, 3, 0.01, false).upper(3 * 14080)
	}
}
