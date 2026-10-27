"""KS distance and 1%/5% quantile error (in units of s(d)) between failed samples and the compound Poisson
law of theorem cross, on rand-cross2 conv_* runs, for d̂-d (dhat_dev_hist) and d̃-d (raw_dev_hist).

usage: uv run --with numpy,scipy,pandas python crosscdf_ks.py

raw_dev_hist only keeps |S2 - k d| <= 8k (|d̃-d| <= 8), so its rows are truncated and not usable for the
lower tail at c >= 2; the figure fig:crossover-cdf therefore stays on X = (d̂-d)/s(d).
"""
import json, math, os, sys
import numpy as np
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
sys.path.insert(0, ROOT+"/sim/peelsim")
from exp4_report import cp_law, ks, quant
s=json.load(open(ROOT+"/sim/results/rand-cross2/data/exp4_summary.json"))
def emp(h):
    xs=np.array(sorted(int(a) for a in h))/1000.0
    ps=np.array([h[str(int(round(x*1000)))] for x in xs],float); return xs, ps/ps.sum()
for run in ("conv_plant","conv_direct"):
  for c in s["runs"][run]:
    m=c["meta"]; k,M,d=int(m["k"]),int(m["M"]),int(m["d"]); g=c["groups"]["failed"]
    if g["n"]<200: continue
    sd=math.sqrt(2*d*(d-1)/(M-1))
    for key,scl in (("raw_dev_hist",False),("dhat_dev_hist",True)):
        xe,pe=emp(g[key]); xc,pc=cp_law(k,M,d)
        if not scl: xc=xc*(1-k/M)
        Fc=np.cumsum(pc)
        cdf=lambda x: np.where(np.searchsorted(xc,np.atleast_1d(x),side="right")>0, Fc[np.maximum(np.searchsorted(xc,np.atleast_1d(x),side="right")-1,0)],0.0)
        step=2/k/(1-k/M) if scl else 2/k
        K=ks(xe,pe,cdf,step)
        q=[(quant(xe,pe,u)-quant(xc,pc,u))/sd for u in (0.01,0.05)]
        print(run,k,M,d,round(d/math.sqrt(M),2),g["n"],key[:4],f"ks={K:.4f}",f"dq01={q[0]:+.3f} dq05={q[1]:+.3f}")
