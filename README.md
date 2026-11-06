# shepherd-harness-build-check-prototype

**Problem.** Shepherd's launch coverage describes robots that route wires and insert terminals in electrical assembly, with humans handling exceptions ([article](https://fondo.com/blog/shepherd-robotics-takes-on-the-wiring-work-behind-ai-infrastructure)). A robot cell then has to prove, per terminal, that the right wire went into the right cavity and seated. "N insertions were logged" does not prove that, and a continuity test misses a wrong terminal, a wrong colour, a wrong length or a weak crimp. I do not know their actual log format; everything below is synthetic.

**What I built.** A stdlib-only checker that compares a harness spec (wire, colour, gauge, length, connector + cavity at both ends) with the cell's assembly log (cavity, terminal series, colour read by vision, cut length, an insertion-force curve and a pull-test value) and returns one rework item per problem: `MISSING`, `WRONG_CAVITY`, `SWAPPED_PAIR` (two rows, one fix), `WRONG_TERMINAL`, `WRONG_COLOR`, `LENGTH`, `NOT_SEATED` (no click in the seat window: a rise of at least 2.5 N followed by a drop of at least 30%), `WEAK_PULL`.

```
python -m unittest discover -s tests -t .   # 5 tests
python evaluate.py dev                       # 200 harnesses
python evaluate.py heldout                   # 400 harnesses, noisier
```

**Results.** The held-out config (seed 9001, 40-120 wires, force noise 0.5 N, 30% of insertions with an early snag bump) was committed before its first run; nothing changed after (`results/`).

| method | planted defects found (of 868) | extra flags | clean harnesses flagged (of 100) |
|---|---|---|---|
| spec check (this repo) | 868 | 30 | 5 |
| continuity test only | 410 | 3 | 0 |
| count of insertions | 0 | 0 | 0 |

Continuity finds wrong/swapped/missing cavities (387 of 387) but 0 of the wrong terminals, colours, lengths and weak crimps, and only 23 of 88 half-seated terminals (I assumed a half-seated terminal still conducts 80% of the time).

**Limits.** Near-circular: I wrote the generator and the checker, so a high find rate mainly shows the rules are coherent. The honest weak point is the click detector under noise: the 30 extra flags and 5 flagged clean harnesses come from it, and I left it as is. Pull-test minimums are illustrative, not from a standard. Real force curves will look different.

Unofficial prototype by Kushagra Pratap Singh. Not affiliated with Shepherd Robotics.
