"""Reproductions of Read (2018)'s claims, on the same base model per mechanism.

Run:  python3 experiments.py
Every number quoted in ../04-experiments.md comes from here.
"""
import math, random
import drift, learners
from drift import dot

T, SEEDS, SIGMA = 4000, range(5), 0.10   # sigma=0.30 leaves label noise
                                          # swamping every mechanism


def angle_gap(a, b):
    if a is None or b is None: return None
    na, nb = math.sqrt(dot(a, a)), math.sqrt(dot(b, b))
    if na == 0 or nb == 0: return None
    return math.degrees(math.acos(max(-1, min(1, dot(a, b)/(na*nb)))))


def scenarios():
    c1, c2 = [0.9, -0.4], [-0.5, 0.8]
    return {
        "stationary":       lambda r: drift.NoDrift(c1),
        "sudden":           lambda r: drift.SuddenDrift(c1, c2, T//2),
        "incremental":      lambda r: drift.IncrementalDrift(c1, 0.01, T//4, 3*T//4),
        "gradual":          lambda r: drift.GradualDrift(c1, c2, T//4, 3*T//4,
                                                          rng=random.Random(r)),
        "sustained (Fig 6)":lambda r: drift.IncrementalDrift(c1, 0.01, 0, 10**9),
        "reoccurring":      lambda r: drift.ReoccurringDrift([c1, c2], 500),
    }


def make_learners():
    return [learners.ContinuousSGD(2, lam=0.5),
            learners.DetectResetLearner(2, lam=0.5),
            learners.BufferLearner(2, w=100, k=10)]


def run(drift_fn, seed, ls=None):
    """Prequential: test then train. Returns per-learner (err_rate, mean angle gap)."""
    ls = ls or make_learners()
    stream = drift.Stream(drift_fn(seed), sigma=SIGMA, seed=seed)
    errs = [0]*len(ls); gaps = [[] for _ in ls]
    for t, x, y, th, c in stream.take(T):
        for i, l in enumerate(ls):
            errs[i] += 0 if (1 if l.predict(x) > 0.5 else 0) == y else 1
            g = angle_gap(th, l.theta_hat())
            if g is not None: gaps[i].append(g)
            l.update(x, y)
    return ls, [(e/T, (sum(g)/len(g) if g else None)) for e, g in zip(errs, gaps)]


_RESULTS = {}

def all_results():
    """Run every scenario x seed ONCE; tables 1 and 2 both read from here."""
    if _RESULTS: return _RESULTS
    for name, fn in scenarios().items():
        acc = [[] for _ in range(3)]; gaps = [[] for _ in range(3)]; resets = []
        for s in SEEDS:
            ls, res = run(fn, s)
            for i, (e, a) in enumerate(res):
                acc[i].append(e)
                if a is not None: gaps[i].append(a)
            resets.append(ls[1].resets)
        _RESULTS[name] = (
            [sum(a)/len(a) for a in acc],
            [(sum(g)/len(g) if g else None) for g in gaps],
            sum(resets)/len(resets),
        )
    return _RESULTS


def table1():
    print("="*74)
    print("1. THREE MECHANISMS x SIX SCENARIOS   (error rate, mean over 5 seeds)")
    print("   lower is better;  T =", T, " same base linear model for 1 and 2")
    print("="*74)
    print(f"{'scenario':<20}{'continuous':>13}{'detect-reset':>15}{'buffer-kNN':>13}"
          f"{'resets':>9}")
    for name, (m, _, resets) in all_results().items():
        print(f"{name:<20}{m[0]:>13.3f}{m[1]:>15.3f}{m[2]:>13.3f}{resets:>9.1f}")


def table2():
    print()
    print("="*74)
    print("2. TRACKING: mean angle(theta_t, theta_hat_t) in degrees")
    print("   buffer-kNN has no theta_hat at all -- that absence is the point")
    print("="*74)
    print(f"{'scenario':<20}{'continuous':>13}{'detect-reset':>15}{'buffer-kNN':>13}")
    for name, (_, row, _) in all_results().items():
        cells = "".join(f"{v:>13.1f}" if v is not None else f"{'--':>13}"
                        for v in row[:1]) + \
                "".join(f"{v:>15.1f}" if v is not None else f"{'--':>15}"
                        for v in row[1:2]) + \
                "".join(f"{v:>13.1f}" if v is not None else f"{'n/a':>13}"
                        for v in row[2:])
        print(f"{name:<20}{cells}")


def table3():
    print()
    print("="*74)
    print("3. THE LAMBDA CONDITION (Section 5): decaying the learning rate")
    print("   'this would cause SGD to react more and more slowly to concept")
    print("    drift until eventually becoming stuck in one concept'")
    print("="*74)
    print(f"{'scenario':<20}{'constant lam':>14}{'decayed lam':>14}{'penalty':>10}")
    for name in ("stationary", "sustained (Fig 6)", "sudden"):
        fn = scenarios()[name]
        con, dec = [], []
        for s in SEEDS:
            for decay, out in ((False, con), (True, dec)):
                l = learners.ContinuousSGD(2, lam=0.5, decay=decay)
                _, res = run(fn, s, ls=[l])
                out.append(res[0][0])
        c, d = sum(con)/len(con), sum(dec)/len(dec)
        print(f"{name:<20}{c:>14.3f}{d:>14.3f}{d-c:>+10.3f}")


def table4():
    print()
    print("="*74)
    print("4. COST OF DESTRUCTIVE ADAPTATION under sustained drift")
    print("   how often the detector fires, and what each reset costs in accuracy")
    print("="*74)
    fn = scenarios()["sustained (Fig 6)"]
    for delta in (0.25, 0.15, 0.08):
        errs, rs = [], []
        for s in SEEDS:
            ls = [learners.DetectResetLearner(2, lam=0.5, delta=delta)]
            _, res = run(fn, s, ls=ls)
            errs.append(res[0][0]); rs.append(ls[0].resets)
        print(f"  detector sensitivity delta={delta:<5}  resets={sum(rs)/len(rs):>5.1f}"
              f"   err={sum(errs)/len(errs):.3f}")
    errs = []
    for s in SEEDS:
        _, res = run(fn, s, ls=[learners.ContinuousSGD(2, lam=0.5)])
        errs.append(res[0][0])
    print(f"  continuous adaptation (no detector)  resets=  0.0   "
          f"err={sum(errs)/len(errs):.3f}")


def table5():
    print()
    print("="*74)
    print("5. MOMENTUM as the forecasting term gestured at in Fig. 4")
    print("   the paper argues for FORECASTING theta but ships reactive tracking")
    print("="*74)
    print("   lambda scaled by (1-beta) so effective step size is held constant")
    print(f"{'scenario':<20}{'beta=0.0':>11}{'beta=0.5':>11}{'beta=0.9':>11}")
    for name in ("sustained (Fig 6)", "incremental", "sudden"):
        fn = scenarios()[name]
        row = []
        for beta in (0.0, 0.5, 0.9):
            e = []
            for s in SEEDS:
                # compensate: a momentum chain multiplies the effective step by
                # 1/(1-beta), so scale lambda to isolate DIRECTION from step size
                l = learners.ContinuousSGD(2, lam=0.5*(1-beta), momentum=beta)
                _, res = run(fn, s, ls=[l])
                e.append(res[0][0])
            row.append(sum(e)/len(e))
        print(f"{name:<20}" + "".join(f"{v:>11.3f}" for v in row))


def table6():
    print()
    print("="*74)
    print("6. THE LAMBDA TRADEOFF: responsiveness vs variance")
    print("   Section 5 says 'do not decay lambda' but never quantifies the cost")
    print("="*74)
    print(f"{'lambda':>8}{'stationary':>13}{'sustained':>12}{'sudden':>10}"
          f"{'mean angle gap':>17}")
    for lam in (0.05, 0.1, 0.3, 0.5, 1.0):
        row, gaps = [], []
        for name in ("stationary", "sustained (Fig 6)", "sudden"):
            fn = scenarios()[name]; e = []
            for s in SEEDS:
                l = learners.ContinuousSGD(2, lam=lam)
                _, res = run(fn, s, ls=[l])
                e.append(res[0][0])
                if res[0][1] is not None: gaps.append(res[0][1])
            row.append(sum(e)/len(e))
        print(f"{lam:>8.2f}{row[0]:>13.3f}{row[1]:>12.3f}{row[2]:>10.3f}"
              f"{sum(gaps)/len(gaps):>17.1f}")


if __name__ == "__main__":
    table1(); table2(); table3(); table4(); table5(); table6()
