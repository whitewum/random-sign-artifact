"""Regenerate every numerical CN paper table from bundled summaries.

Generation never reads audit/table-reference.json or the manuscript. Values retain
source precision; check_tables.py applies each manuscript cell's printed precision.
"""
import csv
import importlib.util
import json
import math
from pathlib import Path
import statistics as st
import sys

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / 'sim/results'
EXP = RESULTS / 'exp6-20261016'
sys.path.insert(0, str(ROOT / 'sim/exp6'))
from grid import ALPHA  # noqa: E402


def read(path):
    with path.open() as f:
        return list(csv.DictReader(f, delimiter='\t' if path.suffix == '.tsv' else ','))


def load(path):
    return json.loads(path.read_text())


def configuration(cid):
    return tuple(int(s[1:]) for s in cid.split('-')[:3])


def pair(a, b):
    return f'{a} ; {b}'


def write(label, header, rows):
    out = ROOT / 'outputs/tables'
    out.mkdir(parents=True, exist_ok=True)
    with (out / (label.replace(':', '-') + '.tsv')).open('w') as f:
        writer = csv.writer(f, delimiter='\t', lineterminator='\n')
        writer.writerow(header.split())
        writer.writerows([[format(v, '.12f').rstrip('0').rstrip('.') if isinstance(v, float) else v for v in row] for row in rows])
    print(f'{label}: {len(rows)} rows')


def exact():
    spec = importlib.util.spec_from_file_location('encoding', ROOT / 'theory/scripts/check_random_sign_encoding.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    cases = load(ROOT / 'theory/diagnostics/random-sign-encoding-exact.json')['cases']
    rows = []
    for c in cases:
        r = mod.check_configuration(c['M'], c['k'], c['d'])
        assert json.loads(json.dumps(r)) == c, 'Exact enumeration differs from the archived diagnostic'
        rows.append([f"({r['M']},{r['k']},{r['d']})", r['effective_sign_states_checked'],
                     r['failure_probability'], r['unconditional_variance'], r['failure_conditional_mean'],
                     r['failure_conditional_variance'], r['failure_conditional_third_central_moment'],
                     r['failure_conditional_zero_probability']])
    write('tab:exact', 'M_k_d states pF var mean_F var_F third_F zero_F', rows)


def decoding():
    groups = {}
    for p in sorted((RESULTS / 'decode-threshold-20261021').glob('*.jsonl')):
        for line in p.read_text().splitlines():
            r = json.loads(line); c = r['config']
            key = c['K'], c['M'], c['Load']
            g = groups.setdefault(key, [0, 0, c['Alpha']])
            g[0] += r['trials']; g[1] += r['trials'] - r['success']
    rows = []
    for k in (3, 4, 5, 6, 10):
        rows.append([k, groups[k, 1024, 1][2]] +
                    [groups[k, M, L][1] / groups[k, M, L][0]
                     for M in (1024, 16384, 65536) for L in (0.98, 1, 1.02)])
    write('tab:decode', 'k alpha M1024_L098 M1024_L1 M1024_L102 M16384_L098 M16384_L1 M16384_L102 M65536_L098 M65536_L1 M65536_L102', rows)
    summary = load(RESULTS / 'decode-stress-20261015/final-summary.json')['by_k']
    write('tab:decode-paired', 'k trials success failure',
          [[k] + [summary[str(k)][field] for field in ('trials', 'success', 'failure')] for k in (3, 4, 5, 6, 10)])


def composition():
    calib = read(RESULTS / 'tail/calib.csv')
    rows = []
    for k, name, index in ((3, 'k3', 0), (4, 'k4', 0), (5, 'k56', 0), (6, 'k56', 1)):
        cols = {c['name']: c['mean_F'] for c in load(RESULTS / f'rs-columns-20261018/{name}.json')[index]['cols']}
        d = min(int(r['d']) for r in calib if int(r['k']) == k and r['M'] == '16384'
                and r['var'] == 'neg0' and r['run'] in ('round1_AB', 'round2_k56'))
        for prefix in ('neg', 'rs'):
            rows.append(([k, d] if prefix == 'neg' else ['', '']) + [prefix] +
                        [cols[f'X_{prefix}{r}'] for r in ('0', '0.1', '0.25', '0.4', '0.5')])
    write('tab:mean-by-k', 'k d encoding rho0 rho01 rho025 rho04 rho05', rows)


def planted(cov):
    ks = {r['id']: r for r in read(EXP / 'ana/fullks.tsv')}
    low = []
    for folder, name in (('v2', 'v2'), ('v3', 'v3a'), ('v3', 'v3bc')):
        low.extend(r for r in read(EXP / f'ana/{folder}/{name}.tsv') if r['u'] == '0.05')
    low.sort(key=lambda r: configuration(r['id']))
    counts = {(r['id'], r['kind'], r['u']): r for r in read(EXP / 'ana/low-load-counts.tsv')}
    rows = []
    for r in low:
        k, M, d = configuration(r['id']); f = ks[r['id']]
        dr, pl = (counts[r['id'], kind, r['u']] for kind in ('direct', 'plant'))
        nd, np = int(dr['n_fail']), int(pl['n_fail'])
        assert nd == int(r['n_direct']) and np == int(r['n_plant'])
        pd, pp = int(dr['miss']) / nd, int(pl['miss']) / np
        u = float(r['u'])
        diff = (pd - pp) / u
        halfwidth = 1.96 * math.sqrt(pd * (1 - pd) / nd + pp * (1 - pp) / np) / u
        rows.append([k, M, d, d / math.sqrt(M), d / (ALPHA[k] * M), nd, f['pair_direct'],
                     pair(pd / u, pp / u), pair(diff - halfwidth, diff + halfwidth), f['ks_full']])
    write('tab:v-low', 'k M d c load n_direct pair_direct miss_u_direct_plant diff_interval KS', rows)
    ids = sorted({r['id'] for r in cov if r['stage'] == 'v'}, key=lambda cid: (configuration(cid)[1], configuration(cid)[0], configuration(cid)[2]))
    rows = []
    for cid in ids:
        k, M, d = configuration(cid)
        g = {(r['kind'], r['u']): r for r in cov if r['stage'] == 'v' and r['rule'] == 'Skellam' and r['id'] == cid}
        rows.append([k, M, float(g['direct', '0.01']['load']), ks[cid]['pair_direct']])
        for u in ('0.01', '0.05'):
            dr, pl = g['direct', u], g['plant', u]
            p1, p2 = float(dr['miss']) / int(dr['n_fail']), float(pl['miss']) / int(pl['n_fail'])
            se = math.sqrt(p1*(1-p1)/int(dr['n_fail']) + p2*(1-p2)/int(pl['n_fail'])) / float(u)
            rows[-1] += [pair(p1/float(u), p2/float(u)), pair((p1-p2)/float(u), 1.96*se)]
        rows[-1].append(ks[cid]['ks_full'])
    write('tab:v', 'k M load pair_direct miss_u01 diff01_halfwidth miss_u05 diff05_halfwidth KS', rows)


def limits():
    data = read(RESULTS / 'distribution-fix-20261022/limit_ks.tsv')
    def span(rs, key):
        return pair(min(float(r[key]) for r in rs), max(float(r[key]) for r in rs))
    rows = []
    for M in (256, 1024, 4096, 16384):
        a = [r for r in data if int(r['M']) == M and any(abs(float(r['c'])-c)<.02 for c in (1, 2, 4))]
        b = [r for r in data if int(r['M']) == M and float(r['c']) >= 8 and r['kind'] == 'direct']
        c = [r for r in a if abs(float(r['c'])-1)<.02]
        rows.append([M, span(a, 'ks_cross'), span(c, 'ks_tilde_gauss'), len(a), span(b, 'ks_gauss'),
                     max(abs(float(r['dq0.01_gauss'])) for r in b), len(b)])
    write('tab:limit-ks', 'M cross_KS tilde_gauss_KS_c1 n_cross gauss_KS max_q01_error n_gauss', rows)


def coverage(cov):
    stat = [r for r in cov if r['stage'] in ('c1', 'c1x')]
    rows = []
    for M in (256, 1024, 4096, 16384):
        g = [r for r in stat if int(r['M']) == M and float(r['c']) >= 8 and r['u'] == '0.01']
        sk = [r for r in g if r['rule'] == 'Skellam']; ga = [r for r in g if r['rule'] == 'Gaussian']
        rows.append([M, 100*st.median(float(r['w50_rel']) for r in sk),
                     100*max(float(r['w90_rel']) for r in sk), 100*st.median(float(r['w50_rel']) for r in ga)])
    for c in (1, 2, 4):
        g = [r for r in stat if float(r['c']) == c and r['u'] == '0.01']
        rows.append([c] + [st.median(float(r['w50_rel'])*int(r['d']) for r in g if r['rule'] == rule)
                           for rule in ('Skellam', 'Gaussian')])
    write('tab:extra', 'M_or_c Skellam_median_pct_or_count Skellam_p90_pct_or_Gaussian_count Gaussian_median_pct', rows)
    rows = []
    for c in (0.5, 1, 2, 4, 8, 16):
        rows.append([c] + [float(next(r for r in stat if r['M'] == '16384' and float(r['c']) == c and
                     int(r['k']) == k and r['u'] == u and r['rule'] == 'Gaussian')['miss_u'])
                     for u in ('0.01', '0.05') for k in (3, 4, 5)])
    write('tab:gauss-c', 'c u01_k3 u01_k4 u01_k5 u05_k3 u05_k4 u05_k5', rows)


def confirm():
    from scipy.stats import beta
    data = [r for r in read(EXP / 'c2.tsv') if r['rule'] == 'Skellam']
    ids = sorted({r['id'] for r in data}, key=lambda cid: (round(configuration(cid)[2] / (ALPHA[configuration(cid)[0]] * configuration(cid)[1]), 2), configuration(cid)[0], configuration(cid)[2] / (ALPHA[configuration(cid)[0]] * configuration(cid)[1])))
    rows = []
    for cid in ids:
        k, M, d = configuration(cid); g = {r['u']: r for r in data if r['id'] == cid}
        row = [f'k={k}, M={M}, d={d}', d / (ALPHA[k]*M), g['0.01']['n_fail']]
        for u in ('0.01', '0.05'):
            n, m = int(g[u]['n_fail']), int(g[u]['miss'])
            row.append(pair(m/n/float(u), beta.ppf(1-0.05/24, m+1, n-m)/float(u)))
        rows.append(row)
    write('tab:confirm', 'configuration load n_fail u01_estimate_ucb u05_estimate_ucb', rows)


def protocol():
    data = read(EXP / 'protocol.tsv'); idx = {(r['id'], r['u'], r['arm']): r for r in data}
    rows = []
    for u in ('0.01', '0.05'):
        for M in (256, 1024, 4096, 16384):
            for arm in ('signed_raw_b', 'signed_rchi_b', 'signed_oracle'):
                if u == '0.05' and arm == 'signed_oracle': continue
                g = [r for r in data if r['u'] == u and int(r['M1']) == M and r['arm'] == arm]
                mu = [float(r['cond_miss'])/float(u) for r in g if r['onesided'] == '0' and int(r['f1']) >= 1000]
                m2, byte = [], []
                for r in g:
                    o = idx[r['id'], u, 'signed_oracle']
                    if int(r['f1']) > 0 and float(o['mean_M2_f1']) > 0:
                        m2.append(100*(float(r['mean_M2_f1'])/float(o['mean_M2_f1'])-1))
                    byte.append(100*(float(r['mean_bytes'])/float(o['mean_bytes'])-1))
                rows.append([pair(M, u) if arm == 'signed_raw_b' else '', arm,
                             '--' if arm == 'signed_oracle' else pair(st.median(mu), max(mu)),
                             100*max(float(r['final_fail']) for r in g), st.median(m2), st.median(byte)])
    write('tab:e2e', 'M_u arm miss_u final_fail_pct M2_extra_pct bytes_extra_pct', rows)
    rows = []
    for M in (256, 1024, 4096):
        for arm in ('standard_vldb', 'standard_vldb_b', 'signed_vldb', 'signed_raw_b'):
            g = [r for r in data if r['k'] == '3' and int(r['M1']) == M and r['u'] == '0.01' and r['arm'] == arm]
            eligible = [r for r in g if int(r['f1']) >= 1000]
            mu = [float(r['cond_miss'])/.01 for r in eligible if r['onesided'] == '0']
            one = [float(r['cond_miss'])/.01 for r in eligible if r['onesided'] == '1']
            byte = [100*(float(r['mean_bytes'])/float(idx[r['id'], '0.01', 'signed_oracle']['mean_bytes'])-1) for r in g]
            rows.append([M if arm == 'standard_vldb' else '', arm, pair(st.median(mu), max(mu)),
                         0 if max(one) == 0 else pair(min(one), max(one)),
                         100*max(float(r['final_fail']) for r in g), st.median(byte)])
    write('tab:vldb', 'M arm balanced_miss_u onesided_miss_u final_fail_pct bytes_extra_pct', rows)


def timing():
    # The second timing run adds the per-trial first-round decoding measurement.
    groups = {}
    for path in sorted((EXP / 'T').glob('proto2-*.csv')):
        for r in read(path):
            k, d, one = int(r['k']), int(r['d']), int(r['onesided'])
            target = min((1, 1.05, 1.5, 3), key=lambda L: abs(d/(ALPHA[k]*int(r['M1']))-L))
            key = k, target, one, r['arm']
            groups.setdefault(key, []).append(r)
    rows = []
    for L in (1, 1.05, 1.5, 3):
        rows.append([L] + [st.median(float(r['proto_ns_per_trial']) for r in groups[k, L, 1, arm])/1e6
                          for arm in ('signed_raw_b', 'signed_rchi_b') for k in (3, 4, 5)])
    write('tab:proto', 'load Skellam_k3 Skellam_k4 Skellam_k5 Gaussian_k3 Gaussian_k4 Gaussian_k5', rows)
    rows = []
    for L, one in ((1, 1), (1.05, 1), (1.5, 1), (3, 1), (1.05, 0), (3, 0)):
        rows.append([L, 'onesided' if one else 'balanced'] +
                    [st.median(float(r['dec_ns_per_trial']) for r in groups[k, L, one, 'signed_raw_b']) /
                     st.median(float(r['dec_ns_per_trial']) for r in groups[k, L, one, 'standard_chi_b']) for k in (3, 4, 5)])
    write('tab:dec-ratio', 'load composition k3 k4 k5', rows)


def main():
    cov = read(EXP / 'coverage.tsv')
    decoding(); composition(); planted(cov); limits(); coverage(cov); confirm(); protocol(); timing(); exact()


if __name__ == '__main__':
    main()
