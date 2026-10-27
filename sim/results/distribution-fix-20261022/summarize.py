"""Reproduce the corrected appendix table from full-CDF results."""
import csv, math
from pathlib import Path
p=Path(__file__).parent
rows=list(csv.DictReader(open(p/'limit_ks.tsv'),delimiter='\t'))
print('all analyzed rows:',len(rows))
for M in (256,1024,4096,16384):
    a=[r for r in rows if int(r['M'])==M and any(abs(float(r['c'])-c)<.02 for c in (1,2,4))]
    b=[r for r in rows if int(r['M'])==M and float(r['c'])>=8 and r['kind']=='direct']
    c=[r for r in a if abs(float(r['c'])-1)<.02]
    def span(rs,key): return f"{min(float(r[key]) for r in rs):.3f}--{max(float(r[key]) for r in rs):.3f}"
    dq=max(abs(float(r['dq0.01_gauss'])) for r in b)
    print(f"{M} & {span(a,'ks_cross')} & {span(c,'ks_tilde_gauss')} & {len(a)} & {span(b,'ks_gauss')} & {dq:.2f} & {len(b)}"+r'\\')
# Compare the independent audit on all 36 matching configurations.
old=list(csv.DictReader(open(p.parent/'distribution-audit-20261022/results.csv')))
for r in old:
    if not r['source'].startswith('exp6-'): continue
    v=next(x for x in rows if x['kind']==r['source'][5:] and all(x[k]==r[k] for k in ('k','M','d')))
    assert abs(float(v['ks_cross'])-float(r['KS_tilde_Gd']))<1e-12
print('PASS: all 36 independent audit distances reproduced.')
