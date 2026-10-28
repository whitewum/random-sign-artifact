"""Validate and summarize durable first-round stress checkpoints.
Usage: python3 sim/iblt2r/stress_report.py node1_full.jsonl node2_full.jsonl
"""
import collections
import json
import sys

complete = "--complete" in sys.argv
rows = []
for path in [arg for arg in sys.argv[1:] if arg != "--complete"]:
    with open(path) as f:
        rows.extend(json.loads(line) for line in f if line.strip())
seen = set()
grouped = collections.defaultdict(lambda: collections.Counter())
for row in rows:
    task = row['task']
    assert task not in seen, f'duplicate task {task}'
    seen.add(task)
    assert row['seed'] == 2026101501
    assert row['success'] + row['failure'] == row['trials']
    assert row['candidates'] >= row['accepted']
    c = row['config']
    g = grouped[c['K']]
    for key in ['trials', 'success', 'failure', 'accepted', 'candidates', 'checksum_rejected']:
        g[key] += row[key]
    g['worker_seconds'] += row['seconds']
if complete:
    configs = {}
    starts = collections.defaultdict(list)
    for row in rows:
        c = row['config']
        i = c['ID']
        assert i not in configs or configs[i] == c
        configs[i] = c
        starts[i].append(row['start'])
    assert set(configs) == set(range(375))
    expected = {}
    task = 0
    for start in range(0, 3000000, 10000):
        for i in range(375):
            c = configs[i]
            if start < c['Trials']:
                expected[task] = (i, start, min(10000, c['Trials'] - start))
                task += 1
    assert len(rows) == len(expected) == 50000
    for row in rows:
        assert (row['config']['ID'], row['start'], row['trials']) == expected[row['task']]
    for i, c in configs.items():
        assert c['Trials'] == {64: 3000000, 1024: 900000, 16384: 100000}[c['M']]
        assert sorted(starts[i]) == list(range(0, c['Trials'], 10000))
    assert set(grouped) == {3, 4, 5, 6, 10}
    assert all(g['trials'] == 100000000 for g in grouped.values())
print(json.dumps({'completed_checkpoints': len(rows), 'completed_trials': sum(r['trials'] for r in rows),
                  'target_trials': 500000000, 'by_k': grouped,
                  'status': 'COMPLETE' if complete else 'SNAPSHOT',
                  'checkpoint_coverage_verified': complete, 'trial_range_coverage_verified': complete}, indent=2))
