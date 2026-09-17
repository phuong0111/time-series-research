"""The three worked figures the notes cite, regenerated from synthetic.py.

    python3 demos.py chain      -> 01-core-argument.md, the concept-chain counts
    python3 demos.py rotation   -> 02-taxonomy.md, the A_0.01 trace
    python3 demos.py scale      -> NOTATION.md, theta vs theta_hat scale-invariance
    python3 demos.py            -> all three

Every number quoted in the notes comes from here, so the notes stay checkable.
"""
import math, random, sys
import methods, synthetic as syn


def chain():
    """Lemma 1 made countable: P(C_t) != P(C_t | C_{t-1}) on a 20-step stream.

    The paper's proof turns on P(C_t = 0) != P(C_t = 0 | C_{t-1} = 1) -- after the
    drift you no longer expect instances from the first concept. With tau = 10 over
    20 steps that is 9/20 against 0/10, and the second probability is exactly zero
    because a sudden drift is irreversible: once C has flipped it never flips back.
    """
    T, tau = 20, 10
    dr = syn.SuddenDrift(2, random.Random(0), tau1=tau)
    C = [dr.concept(t) for t in range(1, T+1)]
    p0 = sum(1 for c in C if c == 0) / T
    # Conditional: over the pairs (C_{t-1}, C_t), how often is C_t = 0 given C_{t-1} = 1?
    pairs = [(C[i-1], C[i]) for i in range(1, T)]
    given1 = [b for a, b in pairs if a == 1]
    p0g1 = (sum(1 for b in given1 if b == 0) / len(given1)) if given1 else float("nan")
    print("Lemma 1, counted on a %d-step stream with tau = %d" % (T, tau))
    print("  C_t            = %s" % "".join(str(c) for c in C))
    print("  P(C_t = 0)             = %d/%d = %.3f" % (sum(1 for c in C if c == 0), T, p0))
    print("  P(C_t = 0 | C_{t-1}=1) = %d/%d = %.3f"
          % (sum(1 for b in given1 if b == 0), len(given1), p0g1))
    print("  -> the two differ, so C_t is NOT independent of C_{t-1}.")


def rotation(n=5, th0=(0.7, -0.3)):
    """Eq. (4) as the paper realises it: theta_t = A^T_0.01 theta_{t-1}.

    The invariant worth seeing is the third column: a rotation preserves ||theta||
    exactly, so the concept moves without changing magnitude. Delta_t theta is
    therefore a pure change of DIRECTION -- which is what makes the trajectory
    trackable by a fixed-step method at all.
    """
    A = syn.rotation(syn.ANGLE, d=2)
    th = list(th0)
    print("Eq. (4): theta_t = A^T_%s theta_{t-1}, theta_0 = %s\n" % (syn.ANGLE, list(th0)))
    print("  %-3s %-24s %-9s %-12s %s" % ("t", "theta_t", "||theta||", "angle", "Delta_t theta"))
    prev = None
    for t in range(n+1):
        norm = math.hypot(*th)
        ang  = math.degrees(math.atan2(th[1], th[0]))
        dlt  = "-" if prev is None else "[%+.5f, %+.5f]" % (th[0]-prev[0], th[1]-prev[1])
        print("  %-3d [%+.5f, %+.5f]   %-9.4f %-12.4f %s" % (t, th[0], th[1], norm, ang, dlt))
        prev = list(th)
        th = syn.apply_T(A, th)


def scale(T=10000, d=2, seed=0, at=2000):
    """theta_hat never needs to EQUAL theta: the boundary theta^T x = 0 is scale-free.

    Two vectors that differ by a positive scalar define the same hyperplane and so
    make identical predictions. This prints how far apart theta and theta_hat are
    in magnitude at step `at`, and how often they nevertheless agree -- which is
    why the tracking metric in these notes is an ANGLE and never a distance.
    """
    dr   = syn.scenarios(d=d, seed=seed)["sustained"]
    st   = syn.Stream(dr, d=d, seed=seed)
    rows = st.take(T)
    l = methods.HingeSGD(d, lam=0.5)          # lam large enough to actually track
    th_true = th_hat = None
    for i, (t, x, y, th, c) in enumerate(rows, start=1):
        l.update(x, y)
        if t == at:
            th_true, th_hat = list(th), l.theta_hat()
            break
    na, nb = math.hypot(*th_true), math.hypot(*th_hat)
    cos = sum(a*b for a, b in zip(th_true, th_hat))/(na*nb)
    ang = math.degrees(math.acos(max(-1.0, min(1.0, cos))))
    # Agreement is measured on FRESH random inputs, not on the training stream.
    rng = random.Random(999)
    agree = 0
    for _ in range(10000):
        xx = [rng.gauss(0, 1) for _ in range(d)]
        s1 = 1 if sum(a*b for a, b in zip(th_true, xx)) > 0 else 0
        s2 = 1 if sum(a*b for a, b in zip(th_hat,  xx)) > 0 else 0
        agree += (s1 == s2)
    print("At t = %d on the sustained stream (d = %d, lambda = 0.5):" % (at, d))
    print("  theta      = [%s]  ||.|| = %.4f" % (", ".join("%+.4f" % v for v in th_true), na))
    print("  theta_hat  = [%s]  ||.|| = %.4f" % (", ".join("%+.4f" % v for v in th_hat), nb))
    print("  magnitude ratio = %.1fx,  angle = %.2f deg" % (nb/na, ang))
    print("  yet they agree on %.1f%% of 10,000 fresh random inputs." % (100*agree/10000))


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    for name, fn in (("chain", chain), ("rotation", rotation), ("scale", scale)):
        if which in (name, "all"):
            fn(); print()
