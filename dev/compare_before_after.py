"""Compare the encounter rate grid between two sets of harness runs.

Usage (from the inner workflow env):
    pixi run --frozen python ../dev/compare_before_after.py <before_results_root> <after_results_root> <case> [<case> ...]

Each root holds one directory per case as `dev/run-test-cases.sh` leaves them
(`<root>/<case>/<hash>_encounter_rate_map.html` + `result.json`). For every case and every
dashboard view, the polygon layer's table (Parquet bytes) is decoded from the lonboard widget state
embedded in the HTML and every column present on BOTH sides is compared row by row (the
grid is sorted by rate upstream, so row order is stable). A column that is numeric on one
side and a fixed-decimal string on the other (the tooltip formatting) compares after
rounding to that many decimals. View keys are compared after `--map-key old=new`
substitutions (the Patrol Type key changed from the slug to the display name).
Exit code 1 on any difference.
"""

import argparse
import base64
import json
import re
import sys
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

TOL = 1e-9


def layer_tables(html: str) -> list[pa.Table]:
    m = re.search(r'<script type="application/vnd.jupyter.widget-state\+json">\s*(\{.*?\})\s*</script>', html, re.S)
    if not m:
        return []
    state = json.loads(m.group(1))["state"]
    tables = []
    for model in state.values():
        for buf in model.get("buffers", []):
            if buf.get("path", [None])[0] == "table":
                raw = base64.b64decode(buf["data"])
                tables.append(pq.read_table(pa.BufferReader(raw)))
    return tables


def views(root: Path, case: str) -> dict[str, list[pa.Table]]:
    result = json.loads((root / case / "result.json").read_text())
    out = {}
    for key, widgets in result["result"]["views"].items():
        for w in widgets:
            if w["widget_type"] != "map":
                continue
            if not w.get("data"):
                out[key] = []  # widget rendered without data (e.g. the events branch skipped)
                continue
            html = (root / case / Path(w["data"]).name).read_text()
            out[key] = layer_tables(html)
    return out


def column_values(table: pa.Table, name: str) -> list:
    col = table.column(name)
    if pa.types.is_struct(col.type) or pa.types.is_list(col.type) or "geometry" in name:
        return [str(v) for v in col.to_pylist()]
    return col.to_pylist()


def same(a, b) -> bool:
    if a is None or b is None:
        return a is None and b is None
    if isinstance(a, str) and not isinstance(b, str):
        a, b = b, a
    if isinstance(b, str) and isinstance(a, (int, float)):
        dec = len(b.split(".")[1]) if "." in b else 0
        return abs(round(float(a), dec) - float(b)) <= TOL
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(a - b) <= TOL
    return a == b


def compare_case(before: Path, after: Path, case: str, key_map: dict[str, str]) -> list[str]:
    b, a = views(before, case), views(after, case)
    for old_key, new_key in key_map.items():
        b = {k.replace(old_key, new_key): v for k, v in b.items()}
    diffs = []
    if set(b) != set(a):
        diffs.append(f"{case}: view keys differ: before {sorted(b)} after {sorted(a)}")
    for key in sorted(set(b) & set(a)):
        tb, ta = b[key], a[key]
        if len(tb) != len(ta):
            diffs.append(f"{case} {key}: layer count {len(tb)} -> {len(ta)}")
            continue
        for i, (x, y) in enumerate(zip(tb, ta)):
            shared = [c for c in x.column_names if c in y.column_names]
            if x.num_rows != y.num_rows:
                diffs.append(f"{case} {key} layer {i}: rows {x.num_rows} -> {y.num_rows}")
                continue
            for c in shared:
                vx, vy = column_values(x, c), column_values(y, c)
                bad = [r for r, (p, q) in enumerate(zip(vx, vy)) if not same(p, q)]
                if bad:
                    r = bad[0]
                    diffs.append(f"{case} {key} layer {i} column {c!r}: {len(bad)} rows differ, first row {r}: {vx[r]!r} -> {vy[r]!r}")
    return diffs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("before", type=Path)
    ap.add_argument("after", type=Path)
    ap.add_argument("cases", nargs="+")
    ap.add_argument("--map-key", action="append", default=[], help="old=new substring substitution applied to the before side's view keys")
    args = ap.parse_args()
    key_map = dict(kv.split("=", 1) for kv in args.map_key)
    rc = 0
    for case in args.cases:
        diffs = compare_case(args.before, args.after, case, key_map)
        print(f"{case}: {'same' if not diffs else 'DIFF'}")
        for d in diffs:
            print("  " + d)
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
