"""Read-only protocol stopping audit: python scripts/check_protocol_stopping.py RESULTS_DIR.

RESULTS_DIR contains pilot.tsv, protocol.tsv and historical pilot/ and p/ task folders.
"""
import collections
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sim/exp6"))
import collect
import make_tasks


def read_rows(path, delimiter=","):
    with path.open() as stream:
        return list(csv.DictReader(stream, delimiter=delimiter))


def main():
    results = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / "sim/results/exp6-20261016"
    frozen = json.loads((ROOT / "sim/exp6/frozen/main.json").read_text())
    regenerated = json.loads(subprocess.check_output([
        sys.executable, str(ROOT / "sim/exp6/freeze_main.py"), str(results / "pilot.tsv")
    ]))
    assert regenerated == frozen, "freeze regeneration differs"
    tasks = {collect.task_name(t): t for t in frozen["tasks"] if t["stage"] == "p"}
    assert set(tasks) == {p.name for p in (results / "p").iterdir() if not p.name.startswith(".")}
    aggregate = collections.defaultdict(collections.Counter)
    paired = {}
    counts = ("trials", "f1", "f1_miss", "f2", "fail", "wrong", "falsepos")
    for name, task in tasks.items():
        folder = results / "p" / name
        records = [line.split("\t") for line in (folder / ".record").read_text().splitlines()]
        record = {line[0]: line[1] for line in records}
        assert record["rc"] == "0", name
        assert record["task"] == name, name
        binary = next(line[1] for line in records if line[0] == "bin" and line[1].startswith("iblt2r-"))
        body = make_tasks.protocol_task({"iblt2r": binary}, "p", task, task["block"], task["trials"], task["u"])
        assert hashlib.sha256(body.encode()).hexdigest() == record["task_sha256"], name
        assert list(map(int, (folder / "spec").read_text().split())) == [
            int(task[key]) for key in ("k", "M", "d", "common", "onesided")
        ], name
        rows = read_rows(folder / "proto.csv")
        assert len(rows) == len({row["arm"] for row in rows}), name
        for row in rows:
            assert int(row["trials"]) == task["trials"], name
            for key in ("k", "M1", "d", "common", "onesided"):
                assert int(row[key]) == int(task["M" if key == "M1" else key]), name
            aggregate[task["id"], str(task["u"]), row["arm"]].update({key: int(row[key]) for key in counts})
        paired[task["id"], task["block"], str(task["u"])] = sorted(
            (row["arm"], row["trials"], row["f1"]) for row in rows
            if row["arm"] in ("signed_raw_b", "signed_rchi_b", "signed_oracle")
        )
    for task in tasks.values():
        assert paired[task["id"], task["block"], "0.01"] == paired[task["id"], task["block"], "0.05"]

    pilot = {}
    for row in read_rows(results / "pilot.tsv", "\t"):
        if row["item"] not in ("pu01", "pu05"):
            continue
        raw = read_rows(results / "pilot" / f"pilot-{row['item']}-{row['id']}-b000" / "proto.csv")[0]
        assert int(raw["trials"]) == int(row["trials"])
        assert int(raw["f1"]) == round(float(row["pF"]) * int(row["trials"]))
        pilot[row["item"], row["id"]] = raw
    for cid in {key[1] for key in pilot}:
        assert pilot["pu01", cid]["f1"] == pilot["pu05", cid]["f1"], cid

    rows = read_rows(results / "protocol.tsv", "\t")
    assert len(rows) == len(aggregate)
    assert len(rows) == len({(row["id"], row["u"], row["arm"]) for row in rows})
    for row in rows:
        acc = aggregate[row["id"], row["u"], row["arm"]]
        assert int(row["trials"]) == acc["trials"] and int(row["f1"]) == acc["f1"]
        for column, key in (("pF1", "f1"), ("final_fail", "fail"), ("joint_miss", "f1_miss")):
            assert row[column] == f"{acc[key] / acc['trials']:.4g}", (row["id"], column)
        assert row["cond_miss"] == (f"{acc['f1_miss'] / acc['f1']:.4g}" if acc["f1"] else "nan")
        assert int(row["wrong"]) == acc["wrong"] == 0
        assert acc["falsepos"] == 0
    configurations = [row for row in rows if row["u"] == "0.01" and row["arm"] == "signed_raw_b"]
    summary = {
        "freeze_regenerated_exactly": True,
        "blocks_checked_including_task_hashes": len(tasks),
        "protocol_rows_checked": len(rows),
        "configurations": len(configurations),
        "trials_per_u": {u: sum(int(row["trials"]) for row in rows if row["u"] == u and row["arm"] == "signed_raw_b")
                         for u in ("0.01", "0.05")},
        "first_round_failure_range": [min(int(row["f1"]) for row in configurations), max(int(row["f1"]) for row in configurations)],
        "configurations_below_19000_failures": sum(int(row["f1"]) < 19000 for row in configurations),
        "configurations_with_zero_failures": sum(int(row["f1"]) == 0 for row in configurations),
        "capped_configurations": [row["id"] for row in configurations if int(row["trials"]) == 3000000],
        "pilot_zero_configurations": [dict(id=row["id"], trials=int(row["trials"]), f1=int(row["f1"]))
                                      for row in configurations if int(pilot["pu01", row["id"]]["f1"]) == 0],
        "local_trial_csv_files": len(list((results / "p").glob("*/trials.csv"))),
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
