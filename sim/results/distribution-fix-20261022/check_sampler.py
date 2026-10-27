"""CLI regression: direct stream preservation, worker determinism, resume scheme isolation."""
import json, subprocess, tempfile
from pathlib import Path
with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp); spec=root/'spec'; spec.write_text('64 3 6 2000\n')
    base=['-spec',str(spec),'-seed','2026102201','-signs','0.5,rand','-pairs=false','-qgrid','0','-sumc','-chunk','500']
    def run(binary,name,jobs=1,plant=False,resume=False,ok=True):
        args=[binary,*base,'-out',str(root/name),'-jobs',str(jobs)]
        if plant: args+=['-plant-dup']
        if resume: args+=['-resume']
        p=subprocess.run(args,capture_output=True,text=True)
        if ok: assert p.returncode==0,p.stderr
        else: assert p.returncode!=0 and 'planted sampling scheme differs' in p.stderr,p.stderr
    def chunks(name): return [p.read_bytes() for p in sorted((root/name).glob('cfg_*/chunk_*.bin'))]
    run('/tmp/peelsim-before','old-direct'); run('/tmp/peelsim-fixed','new-direct')
    assert chunks('old-direct')==chunks('new-direct')
    run('/tmp/peelsim-fixed','plant1',plant=True); run('/tmp/peelsim-fixed','plant2',jobs=2,plant=True)
    assert chunks('plant1')==chunks('plant2')
    before=chunks('plant1'); run('/tmp/peelsim-fixed','plant1',plant=True,resume=True)
    assert chunks('plant1')==before
    run('/tmp/peelsim-before','old-plant',plant=True)
    run('/tmp/peelsim-fixed','old-plant',plant=True,resume=True,ok=False)
    print('PASS: direct chunks byte-identical to pre-fix sampler; planted chunks independent of worker count; new resume preserved; legacy planted resume rejected.')
