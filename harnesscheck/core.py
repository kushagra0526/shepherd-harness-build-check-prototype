"""Verify a robot-assembled wire harness from the build log against the spec.
Synthetic data only. Stdlib only. Thresholds are illustrative; set them from a real spec."""
import random

TERMINAL = {22: "T22", 20: "T20", 18: "T18", 16: "T16", 14: "T14"}   # AWG -> terminal series
MIN_PULL_N = {22: 18, 20: 25, 18: 40, 16: 50, 14: 70}               # illustrative minimums
COLORS = ["red", "black", "white", "green", "blue", "yellow", "orange", "brown"]
STEP = 0.1                                                          # mm per force sample
SEAT_LO, SEAT_HI = 5.0, 7.0                                         # mm window where the click must happen


# ---------- generator ----------
def make_spec(rng, n, n_conn=3):
    cav, wires = {}, []
    conns = [f"J{i + 1}" for i in range(n_conn)]
    free = {c: list(range(1, 101)) for c in conns}
    for c in free:
        rng.shuffle(free[c])
    for i in range(n):
        a, b = rng.sample(conns, 2)
        awg = rng.choice(list(TERMINAL))
        wires.append(dict(id=f"W{i + 1:03d}", color=rng.choice(COLORS), awg=awg, len=rng.choice(range(150, 900, 10)),
                          a=(a, free[a].pop()), b=(b, free[b].pop())))
    return wires


def force_curve(rng, seated, noise, snag):
    f, peak = [], rng.uniform(4, 8)
    stop = rng.uniform(5.2, 6.4) if not seated else None    # a stuck terminal stops before the click
    for i in range(80):
        d = i * STEP
        v = 0.5 + 0.35 * d
        if snag and 2.0 < d < 2.4:
            v += 2.2 * (1 - abs(d - 2.2) / 0.2)               # early snag bump, not a click
        if seated:
            if 6.0 <= d < 6.3:
                v += peak * (1 - abs(d - 6.15) / 0.15)
            elif d >= 6.3:
                v = 0.4 * (0.5 + 0.35 * 6.0)
        elif d > stop:
            v = 0.5 + 0.35 * stop
        f.append(max(0.0, v + rng.gauss(0, noise)))
    return f


def build_log(spec, rng, defects=(), noise=0.2, snag=0.0):
    """Return (log, planted). Each log row is what the robot's cell recorded for one insertion."""
    rows, planted = {}, {}
    for w in spec:
        for end in ("a", "b"):
            conn, c = w[end]
            seated = True
            rows[(w["id"], end)] = dict(wire=w["id"], end=end, conn=conn, cav=c, terminal=TERMINAL[w["awg"]],
                                        color_seen=w["color"], len_mm=w["len"] + rng.randint(-3, 3), seated=seated)
    keys = list(rows)
    rng.shuffle(keys)
    for kind in defects:
        k = keys.pop()
        r = rows[k]
        w = next(x for x in spec if x["id"] == k[0])
        if kind == "WRONG_CAVITY":
            used = {(x["conn"], x["cav"]) for x in rows.values()}
            r["cav"] = next(c for c in range(1, 101) if (r["conn"], c) not in used)
        elif kind == "SWAPPED_PAIR":
            other = next((x for x in keys if rows[x]["conn"] == r["conn"]), None)
            if other is None:
                continue
            keys.remove(other)
            o = rows[other]
            r["cav"], o["cav"] = o["cav"], r["cav"]
            planted[other] = kind
        elif kind == "MISSING":
            del rows[k]
        elif kind == "WRONG_TERMINAL":
            r["terminal"] = TERMINAL[next(a for a in TERMINAL if a != w["awg"])]
        elif kind == "WRONG_COLOR":
            r["color_seen"] = next(c for c in COLORS if c != w["color"])
        elif kind == "LENGTH":
            r["len_mm"] = w["len"] + rng.choice((-1, 1)) * rng.randint(15, 40)
        elif kind == "PARTIAL_SEAT":
            r["seated"] = False
        elif kind == "WEAK_CRIMP":
            r["weak"] = True
        planted[k] = kind
    for k, r in rows.items():
        awg = next(x["awg"] for x in spec if x["id"] == k[0])
        r["curve"] = force_curve(rng, r.pop("seated"), noise, rng.random() < snag)
        weak = r.pop("weak", False)
        lo = MIN_PULL_N[awg]
        r["pull_n"] = rng.gauss(0.45 * lo, 0.1 * lo) if (weak or not has_click(r["curve"])) else rng.gauss(1.8 * lo, 0.12 * lo)
    return list(rows.values()), planted


# ---------- checker ----------
def has_click(curve):
    """A seat click = in the seat window, a rise of >= 2.5 N over the earlier level, then a drop of >= 30% soon after."""
    lo, hi = int(SEAT_LO / STEP), int(SEAT_HI / STEP)
    base = sorted(curve[lo - 10:lo])[5]
    j = max(range(lo, hi), key=lambda i: curve[i])
    peak = curve[j]
    if peak - base < 2.5:
        return False
    after = min(curve[j + 1:j + 11])
    return after <= 0.7 * peak


def check(spec, log):
    """Return {(wire, end): code}. Codes: MISSING, WRONG_CAVITY, SWAPPED_PAIR, WRONG_TERMINAL, WRONG_COLOR,
    LENGTH, NOT_SEATED, WEAK_PULL."""
    by = {(r["wire"], r["end"]): r for r in log}
    out = {}
    for w in spec:
        for end in ("a", "b"):
            r = by.get((w["id"], end))
            if r is None:
                out[(w["id"], end)] = "MISSING"
                continue
            if (r["conn"], r["cav"]) != w[end]:
                out[(w["id"], end)] = "WRONG_CAVITY"
            elif r["terminal"] != TERMINAL[w["awg"]]:
                out[(w["id"], end)] = "WRONG_TERMINAL"
            elif r["color_seen"] != w["color"]:
                out[(w["id"], end)] = "WRONG_COLOR"
            elif abs(r["len_mm"] - w["len"]) > 10:
                out[(w["id"], end)] = "LENGTH"
            elif not has_click(r["curve"]):
                out[(w["id"], end)] = "NOT_SEATED"
            elif r["pull_n"] < MIN_PULL_N[w["awg"]]:
                out[(w["id"], end)] = "WEAK_PULL"
    # two wrong-cavity rows that sit in each other's spec cavity are one swap, one rework action
    spec_cav = {(w["id"], e): w[e] for w in spec for e in ("a", "b")}
    wrong = [k for k, v in out.items() if v == "WRONG_CAVITY"]
    for k in wrong:
        for k2 in wrong:
            if k < k2 and (by[k]["conn"], by[k]["cav"]) == spec_cav[k2] and (by[k2]["conn"], by[k2]["cav"]) == spec_cav[k]:
                out[k] = out[k2] = "SWAPPED_PAIR"
    return out


# ---------- baselines ----------
def count_check(spec, log):
    return {} if len(log) == 2 * len(spec) else {("*", "*"): "COUNT"}


def continuity_only(spec, log, rng):
    """Cavity wiring test. Sees wrong cavity, swap, missing. A half-seated terminal still conducts most
    of the time (assumed 80%); wrong terminal / colour / length / weak crimp pass."""
    by = {(r["wire"], r["end"]): r for r in log}
    out = {}
    for w in spec:
        for e in ("a", "b"):
            r = by.get((w["id"], e))
            if r is None:
                out[(w["id"], e)] = "MISSING"
            elif (r["conn"], r["cav"]) != w[e]:
                out[(w["id"], e)] = "WRONG_CAVITY"
            elif not has_click(r["curve"]) and rng.random() < 0.2:
                out[(w["id"], e)] = "OPEN"
    return out


KINDS = ["WRONG_CAVITY", "SWAPPED_PAIR", "MISSING", "WRONG_TERMINAL", "WRONG_COLOR", "LENGTH", "PARTIAL_SEAT", "WEAK_CRIMP"]
OK_CODES = {"WRONG_CAVITY": {"WRONG_CAVITY", "SWAPPED_PAIR"}, "SWAPPED_PAIR": {"SWAPPED_PAIR", "WRONG_CAVITY"},
            "MISSING": {"MISSING"}, "WRONG_TERMINAL": {"WRONG_TERMINAL"}, "WRONG_COLOR": {"WRONG_COLOR"},
            "LENGTH": {"LENGTH"}, "PARTIAL_SEAT": {"NOT_SEATED", "OPEN", "WEAK_PULL"}, "WEAK_CRIMP": {"WEAK_PULL"}}


def evaluate(n_harness, seed, size, noise, snag):
    rng = random.Random(seed)
    res = {m: dict(found=0, false=0, clean_flagged=0) for m in ("check", "continuity", "count")}
    per = {m: {k: [0, 0] for k in KINDS} for m in res}
    planted_total = clean = 0
    for h in range(n_harness):
        spec = make_spec(rng, rng.randint(*size))
        defects = [] if h % 4 == 0 else [rng.choice(KINDS) for _ in range(rng.randint(1, 4))]
        log, planted = build_log(spec, rng, defects, noise, snag)
        clean += not planted
        planted_total += len(planted)
        outs = {"check": check(spec, log), "continuity": continuity_only(spec, log, rng), "count": count_check(spec, log)}
        for m, o in outs.items():
            for k, kind in planted.items():
                per[m][kind][1] += 1
                if k in o and o[k] in OK_CODES[kind]:
                    res[m]["found"] += 1
                    per[m][kind][0] += 1
            res[m]["false"] += sum(1 for k in o if k not in planted and k != ("*", "*"))
            if not planted and o:
                res[m]["clean_flagged"] += 1
    return dict(planted=planted_total, clean_harnesses=clean, res=res, per=per)
