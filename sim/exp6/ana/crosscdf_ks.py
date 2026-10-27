"""Exact-record replacement for the former truncated-histogram diagnostic.

Usage: python crosscdf_ks.py ROOT OUTDIR --figure-root OLD_ROOT
Delegates to limit_ks.py; historical raw_dev_hist was truncated and is unsuitable for CDF validation.
"""
import runpy
from pathlib import Path
if __name__ == '__main__':
    runpy.run_path(str(Path(__file__).with_name('limit_ks.py')), run_name='__main__')
