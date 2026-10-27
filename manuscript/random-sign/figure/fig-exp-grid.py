"""Actual C1/C1x configurations; run with python3 fig-exp-grid.py."""
from pathlib import Path
import sys
import pandas as pd
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / 'manuscript/STD/figure'))
from figstyle import plt

df = pd.read_csv(ROOT / 'sim/results/exp6-20261016/coverage.tsv', sep='\t')
df = df[df.stage.isin(['c1', 'c1x']) & (df.M >= 256)].drop_duplicates('id')
assert len(df) == 189
assert df.kind.value_counts().to_dict() == {'plant': 105, 'direct': 84}
fig, axs = plt.subplots(1, 3, figsize=(6.6, 2.65), sharex=True, sharey=True)
for ax, k in zip(axs, [3, 4, 5]):
    ax.axhspan(.95, 1.05, color='0.8', alpha=.7, zorder=0)
    ax.axhline(1, color='0.4', lw=.6, zorder=0)
    for c in [1, 8]:
        ax.axvline(c, color='0.65', ls=':', lw=.7, zorder=0)
    for kind, marker, color, label in [('direct','o','#0072B2','Direct'),('plant','^','#D55E00','Planted')]:
        g = df[(df.k == k) & (df.kind == kind)]
        ax.scatter(g.c, g.load, s=13, marker=marker, color=color, linewidths=.3, edgecolors='white', label=label)
    ax.set(xscale='log', yscale='log', xlim=(.01,450), ylim=(.0001,4.5), xlabel=r'$c=d/\sqrt{M}$', title=f'$k={k}$')
axs[0].set_ylabel(r'Load $d/(\alpha_c M)$')
h, l = axs[0].get_legend_handles_labels()
fig.legend(h, l, loc='lower center', ncol=2, bbox_to_anchor=(.5, -.02))
fig.tight_layout(rect=(0,.08,1,1), w_pad=.6)
for ext in ['pdf','png']:
    fig.savefig(HERE / f'fig-exp-grid.{ext}', bbox_inches='tight', dpi=220)
print(df.groupby(['k','kind']).size().to_string())
