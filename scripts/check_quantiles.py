"""Check the frozen finite-size comparator quantiles against their definition."""
import json
import math
from pathlib import Path
from scipy.stats import chi2, norm
root=Path(__file__).resolve().parents[1]
table=json.loads((root/'sim/peelsim/e0extract/qtable.json').read_text())
errors=[]
for size, row in table.items():
    nu=int(size)-1
    for tag,u in [('01',0.01),('05',0.05)]:
        expected=(chi2.ppf(u,nu)-nu)/math.sqrt(2*nu)
        errors.append(abs(expected-row['rchi'+tag]))
        errors.append(abs(norm.ppf(u)-row['rnorm'+tag]))
assert max(errors)<1e-10, max(errors)
print(f'PASS: frozen quantiles match definitions; maximum absolute error {max(errors):.3g}')
