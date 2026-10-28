"""Compare generated table cells with a numeric-only CN reference snapshot.

The reference stores printed numeric tokens, source lines and source hashes, not
CN prose. --cn PATH checks the current read-only CN tree instead of the snapshot.
Generation is independent of both oracles. A mismatch makes this command fail.
"""
import argparse
import csv
from decimal import Decimal
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
NUMBER = re.compile(r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?')


def tokens(cell, exact=False):
    cell = cell.replace('{,}', ',')
    if not exact:
        cell = re.sub(r'(?<=\d),(?=\d{3}(?:\D|$))', '', cell)
    elif not cell.strip().startswith('('):
        cell = re.sub(r'(?<=\d),(?=\d{3}(?:\D|$))', '', cell)
    cell = cell.replace('\\pm', ';').replace('--', ';')
    if exact and re.fullmatch(r'\s*\$?\d+/\d+\$?\\*\s*', cell):
        return [cell.strip().strip('\\').strip().strip('$')]
    return NUMBER.findall(cell)


def extract(cn):
    tables = {}
    for path in sorted(cn.rglob('*.tex')):
        text = path.read_text()
        for match in re.finditer(r'\\begin\{table\}.*?\\end\{table\}', text, re.S):
            lab = re.search(r'\\label\{([^}]+)', match[0])
            if not lab or lab[1] == 'tab:sizing-options': continue
            rows = []; body = False
            start = text[:match.start()].count('\n') + 1
            for i, line in enumerate(match[0].splitlines()):
                if '\\midrule' in line: body = True; continue
                if '\\bottomrule' in line: body = False
                if body and '&' in line:
                    rows.append(dict(line=start+i, cells=[tokens(c, lab[1]=='tab:exact') for c in line.split('&')]))
            tables[lab[1]] = dict(source='manuscript/random-sign/CN/'+str(path.relative_to(cn)),
                                 source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(), rows=rows)
    return tables


def equal(actual, expected):
    if '/' in expected:
        return Fraction(actual) == Fraction(expected)
    a = Decimal(actual) if '/' not in actual else Decimal(Fraction(actual).numerator) / Decimal(Fraction(actual).denominator)
    e = Decimal(expected)
    quantum = Decimal(1).scaleb(e.as_tuple().exponent)
    # Accept either conventional tie rule at exactly half a printed unit.
    # The epsilon only absorbs floating arithmetic, not sampling uncertainty.
    return abs(a - e) <= quantum / 2 + Decimal('1e-12')


def check(tables):
    report = {}; mismatches = []
    for label, ref in tables.items():
        path = ROOT / 'outputs/tables' / (label.replace(':', '-')+'.tsv')
        if not path.exists():
            report[label] = dict(status='missing', errors=['Run make tables first'])
            mismatches.append(dict(label=label, reason='missing generated table'))
            print(f'{label}: FAIL (missing generated table)')
            continue
        with path.open() as f:
            rows = list(csv.reader(f, delimiter='\t'))[1:]
        errors = []
        if len(rows) != len(ref['rows']): errors.append(dict(reason='row count', expected=len(ref['rows']), actual=len(rows)))
        count = 0
        for i, (row, rr) in enumerate(zip(rows, ref['rows']), 1):
            if len(row) != len(rr['cells']): errors.append(dict(row=i, reason='column count', actual=len(row), expected=len(rr['cells'])))
            for col, (cell, expected) in enumerate(zip(row, rr['cells']), 1):
                if not expected: continue
                actual = tokens(cell, label == 'tab:exact')
                count += len(expected)
                if len(actual) != len(expected) or not all(equal(a, e) for a, e in zip(actual, expected)):
                    errors.append(dict(row=i, column=col, source=ref['source'], line=rr['line'], expected=expected, actual=actual))
        report[label] = dict(status='mismatch' if errors else 'match', numeric_tokens=count, errors=errors)
        mismatches.extend(dict(label=label, **e) for e in errors)
        print(f"{label}: {'FAIL' if errors else 'PASS'} ({count} numeric tokens, {len(errors)} differing cells)")
    out = ROOT / 'outputs/tables/check.json'
    out.write_text(json.dumps(report, indent=2)+'\n')
    for error in mismatches: print(json.dumps(error))
    return bool(mismatches)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cn', type=Path, help='Read a current CN source tree; never modified')
    parser.add_argument('--snapshot', action='store_true', help='Refresh the numeric-only comparison oracle (requires --cn)')
    args = parser.parse_args()
    tables = extract(args.cn) if args.cn else json.loads((ROOT / 'audit/table-reference.json').read_text())['tables']
    if args.snapshot:
        if not args.cn: parser.error('--snapshot requires --cn')
        (ROOT / 'audit/table-reference.json').write_text(json.dumps(dict(purpose='Numeric comparison oracle extracted automatically from CN; never a generation input.', tables=tables), indent=2)+'\n')
    raise SystemExit(check(tables))


if __name__ == '__main__': main()
