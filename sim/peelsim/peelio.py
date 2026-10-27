"""Reader for peelsim output: load(outdir, cfg_index) -> dict of numpy arrays."""
import glob
import json
import os

import numpy as np


def manifest(outdir):
    with open(os.path.join(outdir, "manifest.json")) as f:
        return json.load(f)


def load(outdir, ci, fields=None, man=None):
    man = man or manifest(outdir)
    names, types = man["fields"], man["field_types"]
    dt = np.dtype([(n, "<f4" if t == "f32" else "<i4") for n, t in zip(names, types)])
    files = sorted(glob.glob(os.path.join(outdir, f"cfg_{ci:03d}", "chunk_*.bin")))
    arr = np.concatenate([np.fromfile(p, dtype=dt) for p in files])
    want = fields or names
    return {n: arr[n] for n in want}
