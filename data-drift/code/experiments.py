"""Reproductions of Read (2018)'s claims, on the same base model per mechanism.

Run:  python3 experiments.py
Every number quoted in ../04-experiments.md comes from here.
"""
import math, random
import drift, learners
from drift import dot

T, SEEDS, SIGMA = 4000, range(5), 0.10   # sigma=0.30 leaves label noise
                                          # swamping every mechanism
# T      = stream length per run; long enough for the detector's 150-wide window
# SEEDS  = 5 repeats; each reseeds the drift generator AND the stream RNG
# SIGMA  = std of eps_t. The label-noise floor is (1/pi)*arctan(4*sigma/||theta||),
#          so sigma=0.10 -> ~12.6% irreducible error, sigma=0.30 -> ~29.4%.


def angle_gap(a, b):
    """Angle between two vectors in degrees -- the tracking metric of table 2.

    Scale-invariant on purpose: what matters is whether theta_hat points the same
    way as theta (same decision boundary), not whether it has the same magnitude.
    """
    if a is None or b is None: return None      # buffer-kNN has no theta_hat at all
    na, nb = math.sqrt(dot(a, a)), math.sqrt(dot(b, b))   # ||a||, ||b||
    if na == 0 or nb == 0: return None          # theta_hat=0 at t=1: angle undefined
    # clamp to [-1,1] before acos: floating-point error can push cos just outside
    return math.degrees(math.acos(max(-1, min(1, dot(a, b)/(na*nb)))))


def scenarios():
    """The six streams. Each value is seed -> Drift, so every seed gets a fresh one."""
    c1, c2 = [0.9, -0.4], [-0.5, 0.8]   # two concepts ~90 deg apart, both norm ~1
    return {
        # theta never moves: the i.i.d. baseline, and the floor for every other row
        "stationary":       lambda r: drift.NoDrift(c1),
        # one jump c1 -> c2 at the midpoint, so 2000 instances either side
        "sudden":           lambda r: drift.SuddenDrift(c1, c2, T//2),
        # rotate 0.01 rad/step over the middle half: 2000 steps = 1 rad = 57 deg
        "incremental":      lambda r: drift.IncrementalDrift(c1, 0.01, T//4, 3*T//4),
        # alpha_t ramps over the middle half; rng seeded per-seed for the Bernoulli
        "gradual":          lambda r: drift.GradualDrift(c1, c2, T//4, 3*T//4,
                                                          rng=random.Random(r)),
        # tau2=1e9 means the rotation NEVER stops -- Fig 6's never-ending drift
        "sustained (Fig 6)":lambda r: drift.IncrementalDrift(c1, 0.01, 0, 10**9),
        # c1,c2,c1,c2,... every 500 instances: 8 switches over T=4000
        "reoccurring":      lambda r: drift.ReoccurringDrift([c1, c2], 500),
    }


def make_learners():
    """One learner per mechanism, all at lambda=0.5 so only the RESPONSE differs."""
    return [learners.ContinuousSGD(2, lam=0.5),           # mechanism 3
            learners.DetectResetLearner(2, lam=0.5),      # mechanism 2
            learners.BufferLearner(2, w=100, k=10)]       # mechanism 1


def run(drift_fn, seed, ls=None):
    """Prequential: test then train. Returns per-learner (err_rate, mean angle gap)."""
    ls = ls or make_learners()                    # default: all three mechanisms
    stream = drift.Stream(drift_fn(seed), sigma=SIGMA, seed=seed)   # same seed both
    errs = [0]*len(ls); gaps = [[] for _ in ls]   # cumulative E_t, and angle history
    for t, x, y, th, c in stream.take(T):         # th is the GROUND-TRUTH theta_t
        for i, l in enumerate(ls):                # every learner sees the SAME stream
            # TEST first, on a model that has never seen (x_t, y_t). The inner
            # parenthesis thresholds the probability to a 0/1 label BEFORE the
            # comparison, so this is 0/1 loss, not a residual.
            errs[i] += 0 if (1 if l.predict(x) > 0.5 else 0) == y else 1
            g = angle_gap(th, l.theta_hat())      # how far theta_hat lags theta_t
            if g is not None: gaps[i].append(g)   # skipped for kNN and for theta_hat=0
            l.update(x, y)                        # THEN train: the label is consumed
    # err_rate = (1/T) sum E_t;  angle = mean over the steps where it was defined
    return ls, [(e/T, (sum(g)/len(g) if g else None)) for e, g in zip(errs, gaps)]


_RESULTS = {}   # memo, so tables 1 and 2 report the SAME runs rather than re-rolling

def all_results():
    """Run every scenario x seed ONCE; tables 1 and 2 both read from here."""
    if _RESULTS: return _RESULTS                  # already computed: reuse verbatim
    for name, fn in scenarios().items():
        acc = [[] for _ in range(3)]              # per-learner ERROR rates (misnomer)
        gaps = [[] for _ in range(3)]             # per-learner mean angle gaps
        resets = []                               # detector firings, mechanism 2 only
        for s in SEEDS:
            ls, res = run(fn, s)                  # one full prequential pass
            for i, (e, a) in enumerate(res):
                acc[i].append(e)                  # collect this seed's error rate
                if a is not None: gaps[i].append(a)
            resets.append(ls[1].resets)           # ls[1] is the DetectResetLearner
        _RESULTS[name] = (
            [sum(a)/len(a) for a in acc],                    # mean error over seeds
            [(sum(g)/len(g) if g else None) for g in gaps],  # mean angle over seeds
            sum(resets)/len(resets),                         # mean resets over seeds
        )
    return _RESULTS


def table1():
    """B1: do the three mechanisms differ, once the base model is held fixed?"""
    print("="*74)
    print("1. THREE MECHANISMS x SIX SCENARIOS   (error rate, mean over 5 seeds)")
    print("   lower is better;  T =", T, " same base linear model for 1 and 2")
    print("="*74)
    print(f"{'scenario':<20}{'continuous':>13}{'detect-reset':>15}{'buffer-kNN':>13}"
          f"{'resets':>9}")
    for name, (m, _, resets) in all_results().items():
        # m[0]=continuous, m[1]=detect-reset, m[2]=kNN -- the make_learners() order
        print(f"{name:<20}{m[0]:>13.3f}{m[1]:>15.3f}{m[2]:>13.3f}{resets:>9.1f}")


def table2():
    """B2: how well does theta_hat actually TRACK theta? Free -- reuses table 1's runs."""
    print()
    print("="*74)
    print("2. TRACKING: mean angle(theta_t, theta_hat_t) in degrees")
    print("   buffer-kNN has no theta_hat at all -- that absence is the point")
    print("="*74)
    print(f"{'scenario':<20}{'continuous':>13}{'detect-reset':>15}{'buffer-kNN':>13}")
    for name, (_, row, _) in all_results().items():
        # Three slices only because the middle column is 15 wide, not 13; the kNN
        # column prints 'n/a' where the other two print '--' (they never hit None).
        cells = "".join(f"{v:>13.1f}" if v is not None else f"{'--':>13}"
                        for v in row[:1]) + \
                "".join(f"{v:>15.1f}" if v is not None else f"{'--':>15}"
                        for v in row[1:2]) + \
                "".join(f"{v:>13.1f}" if v is not None else f"{'n/a':>13}"
                        for v in row[2:])
        print(f"{name:<20}{cells}")


def table3():
    """B3: the paper's one prescription -- never let lambda decay to zero."""
    print()
    print("="*74)
    print("3. THE LAMBDA CONDITION (Section 5): decaying the learning rate")
    print("   'this would cause SGD to react more and more slowly to concept")
    print("    drift until eventually becoming stuck in one concept'")
    print("="*74)
    print(f"{'scenario':<20}{'constant lam':>14}{'decayed lam':>14}{'penalty':>10}")
    # Three scenarios only: stationary (where decay SHOULD help) plus the two
    # where being stuck in one concept is fatal.
    for name in ("stationary", "sustained (Fig 6)", "sudden"):
        fn = scenarios()[name]
        con, dec = [], []                         # constant-lambda vs decayed-lambda
        for s in SEEDS:
            for decay, out in ((False, con), (True, dec)):
                # A fresh learner per (seed, variant); same seed -> same stream, so
                # the two variants are compared on IDENTICAL data.
                l = learners.ContinuousSGD(2, lam=0.5, decay=decay)
                _, res = run(fn, s, ls=[l])       # ls=[l] -> one learner, no kNN cost
                out.append(res[0][0])             # res[0] = (err, angle) for that learner
        c, d = sum(con)/len(con), sum(dec)/len(dec)
        print(f"{name:<20}{c:>14.3f}{d:>14.3f}{d-c:>+10.3f}")   # penalty = decayed - constant


def table4():
    """B4: does firing the detector more often ever pay for itself?"""
    print()
    print("="*74)
    print("4. COST OF DESTRUCTIVE ADAPTATION under sustained drift")
    print("   how often the detector fires, and what each reset costs in accuracy")
    print("="*74)
    fn = scenarios()["sustained (Fig 6)"]         # the hardest case for a frozen model
    for delta in (0.25, 0.15, 0.08):              # delta DOWN = detector more sensitive
        errs, rs = [], []
        for s in SEEDS:
            ls = [learners.DetectResetLearner(2, lam=0.5, delta=delta)]
            _, res = run(fn, s, ls=ls)
            errs.append(res[0][0]); rs.append(ls[0].resets)   # error AND firing count
        print(f"  detector sensitivity delta={delta:<5}  resets={sum(rs)/len(rs):>5.1f}"
              f"   err={sum(errs)/len(errs):.3f}")
    # The control row: the identical base model with the detector removed entirely.
    errs = []
    for s in SEEDS:
        _, res = run(fn, s, ls=[learners.ContinuousSGD(2, lam=0.5)])
        errs.append(res[0][0])
    print(f"  continuous adaptation (no detector)  resets=  0.0   "
          f"err={sum(errs)/len(errs):.3f}")


def table5():
    """B5: does momentum deliver the FORECASTING the paper argues for? (No.)"""
    print()
    print("="*74)
    print("5. MOMENTUM as the forecasting term gestured at in Fig. 4")
    print("   the paper argues for FORECASTING theta but ships reactive tracking")
    print("="*74)
    print("   lambda scaled by (1-beta) so effective step size is held constant")
    print(f"{'scenario':<20}{'beta=0.0':>11}{'beta=0.5':>11}{'beta=0.9':>11}")
    for name in ("sustained (Fig 6)", "incremental", "sudden"):   # the drifts with a DIRECTION
        fn = scenarios()[name]
        row = []
        for beta in (0.0, 0.5, 0.9):              # no / moderate / heavy velocity
            e = []
            for s in SEEDS:
                # compensate: a momentum chain multiplies the effective step by
                # 1/(1-beta), so scale lambda to isolate DIRECTION from step size
                l = learners.ContinuousSGD(2, lam=0.5*(1-beta), momentum=beta)
                _, res = run(fn, s, ls=[l])
                e.append(res[0][0])
            row.append(sum(e)/len(e))             # mean error at this beta
        print(f"{name:<20}" + "".join(f"{v:>11.3f}" for v in row))


def table6():
    """B6: price out the lambda dial the paper leaves unquantified."""
    print()
    print("="*74)
    print("6. THE LAMBDA TRADEOFF: responsiveness vs variance")
    print("   Section 5 says 'do not decay lambda' but never quantifies the cost")
    print("="*74)
    print(f"{'lambda':>8}{'stationary':>13}{'sustained':>12}{'sudden':>10}"
          f"{'mean angle gap':>17}")
    for lam in (0.05, 0.1, 0.3, 0.5, 1.0):        # two orders of magnitude of step size
        row, gaps = [], []
        for name in ("stationary", "sustained (Fig 6)", "sudden"):
            fn = scenarios()[name]; e = []
            for s in SEEDS:
                l = learners.ContinuousSGD(2, lam=lam)
                _, res = run(fn, s, ls=[l])
                e.append(res[0][0])
                # NOTE gaps pools across all three scenarios, so the last column is
                # one number per lambda, not per scenario.
                if res[0][1] is not None: gaps.append(res[0][1])
            row.append(sum(e)/len(e))
        print(f"{lam:>8.2f}{row[0]:>13.3f}{row[1]:>12.3f}{row[2]:>10.3f}"
              f"{sum(gaps)/len(gaps):>17.1f}")


if __name__ == "__main__":
    # Order matters only for table 2, which is free because table 1 filled _RESULTS.
    table1(); table2(); table3(); table4(); table5(); table6()
