"""Compute the encoding diagram's counts and energy from its bundled mapping."""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    data = json.loads((ROOT / 'sim/results/analytic/structure-mapping.json').read_text())
    edges, signs, M = data['edges'], data['signs'], data['M']
    assert len(edges) == len(signs) and all(len(set(e)) == data['k'] for e in edges)
    std = [sum(v in e for e in edges) for v in range(1, M+1)]
    rs = [sum(s for e, s in zip(edges, signs) if v in e) for v in range(1, M+1)]
    values = dict(standardEnergy=sum(c*c for c in std), signedEnergy=sum(c*c for c in rs),
                  standardCounts=','.join(map(str, std)), signedCounts=','.join(map(str, rs)),
                  mappingSigns=','.join(map(str, signs)),
                  mappingSignLabels=','.join('+/sgnpos' if s == 1 else '-/sgnneg' for s in signs),
                  mappingEdges=','.join(str(i)+'/{'+','.join(map(str, e))+'}' for i, e in enumerate(edges, 1)))
    out = ROOT / 'outputs/figures'; out.mkdir(parents=True, exist_ok=True)
    (out / 'structure-values.tex').write_text(''.join('\\def\\'+k+'{'+str(v)+'}\n' for k, v in values.items()))
    with (out / 'fig-structure.tsv').open('w') as f:
        w = csv.writer(f, delimiter='\t', lineterminator='\n'); w.writerow(['cell', 'standard_count', 'signed_count'])
        w.writerows(zip(range(1, M+1), std, rs))
    print('fig:structure: counts and energies regenerated')


if __name__ == '__main__': main()
