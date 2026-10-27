"""Full CDF distances from exact integer records.

python limit_ks.py CAMPAIGN_ROOT OUTDIR [--figure-root OLD_CAMPAIGN_ROOT]
ks_cross and cross quantiles use tilde d against the manuscript G_d.
ks_gauss and Gaussian quantiles use hat d, the CLT statistic.
All failure records are pooled over c1/c1x blocks; no midpoint sampling or histogram rounding.
"""
import argparse
import csv
import json
import math
import re
import sys
from pathlib import Path
import numpy as np
from scipy.stats import norm
sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'peelsim'))
from distribution import gd_lattice, discrete_ks, continuous_ks, quantile


def read(path, index=0):
    man = json.load(open(path/'manifest.json'))
    names, nf = man['fields'], man['record_bytes']//4
    for part in sorted((path/f'cfg_{index:03d}').glob('chunk_*.bin')):
        a = np.fromfile(part, dtype='<i4').reshape(-1, nf)
        a = a[a[:, names.index('failed')] == 1]
        yield a[:, names.index('S1_rand')].astype(np.int64), a[:, names.index('S2_rand')].astype(np.int64)


def hist(paths, k, M, d):
    raw, hat = {}, {}
    for path, index in paths:
        for s1, s2 in read(path, index):
            if np.any((s2-k*d) % 2):
                raise ValueError('S2 parity inconsistent with k*d')
            for target, vals in ((raw, (s2-k*d)//2), (hat, M*(s2-k*d)-s1*s1+d*k*k)):
                x, n = np.unique(vals, return_counts=True)
                for v, count in zip(x, n):
                    target[int(v)] = target.get(int(v), 0)+int(count)
    def unpack(h):
        x = np.array(sorted(h), dtype=np.int64)
        n = np.array([h[int(v)] for v in x], dtype=np.int64)
        return x, n
    return (*unpack(raw), *unpack(hat))


def main(root, out, figure_root=None):
    out.mkdir(parents=True, exist_ok=True)
    runs = {}
    for stage in ('c1', 'c1x'):
        for r in sorted((root/'out'/stage).glob('*')):
            m = re.search(r'-(direct|plant)-k(\d+)-M(\d+)-d(\d+)-b\d+$', r.name)
            if m and not r.name.startswith('.'):
                runs.setdefault((m[1], *map(int, m.groups()[1:])), []).append((r/'s', 0))
    fields = ['kind','k','M','d','c','load_d_over_M','n','ks_gauss','ks_cross','ks_tilde_gauss',
              'dq0.01_gauss','dq0.05_gauss','dq0.01_cross','dq0.05_cross']
    with open(out/'limit_ks.tsv', 'w') as f:
        w = csv.DictWriter(f, fields, delimiter='\t'); w.writeheader()
        for (kind,k,M,d), paths in sorted(runs.items()):
            x,n,h,hn = hist(paths,k,M,d)
            if n.sum() < 1000: continue
            p,hp = n/n.sum(), hn/hn.sum()
            s = math.sqrt(2*d*(d-1)/(M-1)); hx = h/(k*(M-k))
            row = dict(kind=kind,k=k,M=M,d=d,c=d/math.sqrt(M),load_d_over_M=d/M,n=int(n.sum()),
                       ks_gauss=continuous_ks(hx,hp,lambda v: norm.cdf(v/s)),
                       ks_tilde_gauss=continuous_ks(x*2/k,p,lambda v: norm.cdf(v/s)))
            for u in (0.01,0.05): row[f'dq{u:g}_gauss'] = (quantile(hx,hp,u)-s*norm.ppf(u))/s
            if math.comb(max(d-2,0),2)*k*k/M <= 3000:
                y,q = gd_lattice(k,M,d)
                row['ks_cross'] = discrete_ks(x,p,y,q)
                for u in (0.01,0.05): row[f'dq{u:g}_cross'] = (quantile(x,p,u)-quantile(y,q,u))*2/k/s
            w.writerow(row); f.flush()
    if figure_root:
        rows=[]
        for run, ds in (('confirm_plant',(32,64,1024)), ('conv_plant',(128,256,512))):
            path=figure_root/run; man=json.load(open(path/'manifest.json'))
            for m in man['configs']:
                k,M,d=m['k'],m['M'],m['d']
                if k!=3 or M!=16384 or d not in ds: continue
                x,n,_,_=hist([(path,m['index'])],k,M,d)
                rows.append(dict(k=k,M=M,d=d,n=int(n.sum()),lattice=x.tolist(),counts=n.tolist(),
                                 source=run,index=m['index'],code_version=man['code_version'],seed=man['run_seed']))
        if len(rows)!=6: raise ValueError('Expected all six figure configurations')
        (out/'crossover_hist.json').write_text(json.dumps(sorted(rows,key=lambda r:r['d']),indent=2)+'\n')

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('root',type=Path); ap.add_argument('out',type=Path)
    ap.add_argument('--figure-root',type=Path)
    a=ap.parse_args(); main(a.root,a.out,a.figure_root)
