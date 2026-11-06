"""python evaluate.py dev|heldout"""
import json
import os
import sys
from harnesscheck.core import evaluate, KINDS

name = sys.argv[1] if len(sys.argv) > 1 else "dev"
# (harnesses, seed, wires range, force noise N, share of insertions with an early snag bump)
cfg = {"dev": (200, 1, (20, 60), 0.2, 0.0), "heldout": (400, 9001, (40, 120), 0.5, 0.3)}[name]
r = evaluate(*cfg)
os.makedirs("results", exist_ok=True)
json.dump(r, open(f"results/{name}.json", "w"), indent=1)
print(f"{name}: {cfg[0]} harnesses ({r['clean_harnesses']} clean), {r['planted']} planted defects, noise {cfg[3]}, snags {cfg[4]}")
print(f"{'method':11} {'found':>6} {'extra flags':>11} {'clean flagged':>13}")
for m, v in r["res"].items():
    print(f"{m:11} {v['found']:6d} {v['false']:11d} {v['clean_flagged']:13d}")
print("recall by defect (check / continuity):")
for k in KINDS:
    a, b = r["per"]["check"][k], r["per"]["continuity"][k]
    print(f"  {k:15} {a[0]:3d}/{a[1]:<3d}   {b[0]:3d}/{b[1]:<3d}")
