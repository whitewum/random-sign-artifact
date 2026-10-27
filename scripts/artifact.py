"""Portable build, smoke experiment, and paper-figure entry points."""
import csv
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
os.environ.setdefault('GOCACHE', str(ROOT / '.cache/go-build'))
os.environ.setdefault('MPLCONFIGDIR', str(ROOT / '.cache/matplotlib'))
os.environ.setdefault('XDG_CACHE_HOME', str(ROOT / '.cache'))

def run(*args, cwd=ROOT):
    subprocess.run([str(a) for a in args], cwd=cwd, check=True)

def build():
    (ROOT / 'bin').mkdir(exist_ok=True)
    for name, folder, source in [('peelsim','sim/peelsim','.'), ('iblt2r','sim/iblt2r','.'),
                                 ('r22replay','sim/peelsim/e0extract','r22replay.go'),
                                 ('rscol','sim/peelsim/rscol','main.go')]:
        run('go','build','-trimpath','-o',ROOT/'bin'/name,source,cwd=ROOT/folder)
    (ROOT/'bin/qtable.json').write_bytes((ROOT/'sim/peelsim/e0extract/qtable.json').read_bytes())
    (ROOT/'bin/bins.json').write_text(json.dumps({n:n for n in ['peelsim','iblt2r','r22replay']})+'\n')

def smoke():
    import tempfile
    parent=ROOT/'outputs/smoke';parent.mkdir(parents=True,exist_ok=True)
    out=Path(tempfile.mkdtemp(prefix='run-',dir=parent))
    for mode,d in [('direct',300),('planted',16)]:
        spec=out/(mode+'.spec');spec.write_text(f'256 3 {d} 200\n')
        args=['bin/peelsim','-spec',spec,'-seed','20261021','-signs','0,0.5,rand',
              '-pairs=false','-qgrid','0','-sumc','-chunk','200','-jobs','1','-out',out/mode,
              '-code-version','artifact-0.1.0-dev']
        if mode=='planted': args += ['-plant-dup']
        run(*args)
        run('bin/r22replay','-q','bin/qtable.json','-tn','0','-jobs','1','-out',out/(mode+'-replay.json'),out/mode)
        replay=json.loads((out/(mode+'-replay.json')).read_text())
        groups=next(iter(replay['runs'].values()))[0]['groups']
        assert groups['failed']['n']>0, 'Smoke experiment produced no failures'
        if mode=='planted': assert groups['failed']['n']==200
    spec=out/'protocol.spec';spec.write_text('3 256 300 20 0\n3 256 300 20 1\n')
    run('bin/iblt2r','-q','bin/qtable.json','-spec',spec,'-trials','100','-seed','20261021',
        '-jobs','1','-arms','signed_raw_b,signed_rchi_b,signed_oracle',
        '-out',out/'protocol.csv','-trialout',out/'trials.csv')
    rows=list(csv.DictReader((out/'protocol.csv').open()))
    assert len(rows)==6, f'Expected six protocol rows; got {len(rows)}'
    for row in rows:
        assert int(row['wrong']) == 0 and int(row['falsepos']) == 0, row
        assert row['agree_signed_standard'] == '100/100', row
        assert int(row['trials']) == 100, row
    print('Smoke experiment passed:',out.relative_to(ROOT))

def figures():
    for name in ['encoding','composition','crossover-cdf','coverage','confirm','protocol','scale',
                 'sizing','planted','exp-grid','aux']:
        run(sys.executable,ROOT/'manuscript/random-sign/figure'/f'fig-{name}.py')
    print('Generated eleven paper figures.')

if __name__=='__main__':
    if len(sys.argv)!=2 or sys.argv[1] not in ('build','smoke','figures'):
        raise SystemExit('Usage: python scripts/artifact.py {build|smoke|figures}')
    globals()[sys.argv[1]]()
