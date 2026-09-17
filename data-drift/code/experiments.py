"""Table 3 of Read (2018), reproduced on all four of its streams.

    Run:  python3 experiments.py              # the full table
          python3 experiments.py --quick      # 10k caps, RF-HT at 10 trees
          python3 experiments.py --trees 25   # override the ensemble size

Prequential evaluation: test on x_t with a model that has not seen it, then train.

WARMUP. Table 1: "In all experiments, accuracy is recorded over instances
tau_0, ..., T", with tau_0 = T/10; Table 5 confirms the same for the real data,
timing "the initial block (which is not evaluated in terms of accuracy)". So the
first tenth of every stream is training-only and is excluded from the accuracy,
which is what `warmup` implements. Reporting the whole stream instead would
charge every method for its cold start.

WHAT IS COMPARABLE TO THE PAPER:
    Electricity  yes  -- natively binary, full 45,312 instances
    Synthetic    yes  -- Table 1 parameters; Table 3's row is the Figure 6
                        (sustained) stream, per section 7's cross-reference
    RTG          yes  -- scikit-multiflow defaults, as Table 2 directs
    CoverType    NO   -- the paper classifies all 7 classes; data.py binarises
                        one-vs-rest, and we evaluate a subset. Reported so the
                        methods can be ranked on a second real stream, nothing more.
"""
import sys, time
import data, methods, synthetic as syn

PAPER = {                        # Table 3, for side-by-side reporting only
    ("Electricity", "SAMkNN"):  79.8, ("Electricity", "PBF-SGD"): 85.9,
    ("Electricity", "RF-HT"):   86.2,
    ("RTG",         "SAMkNN"):  78.8, ("RTG",         "PBF-SGD"): 81.8,
    ("RTG",         "RF-HT"):   77.9,
    ("CoverType",   "SAMkNN"):  93.3, ("CoverType",   "PBF-SGD"): 92.6,
    ("CoverType",   "RF-HT"):   93.9,
    ("Synthetic",   "SAMkNN"):  96.0, ("Synthetic",   "PBF-SGD"): 95.1,
    ("Synthetic",   "RF-HT"):   93.6,
}

COMPARABLE = {"Electricity", "RTG", "Synthetic"}     # CoverType is not; see docstring


def prequential(learner, rows, warmup):
    """Test-then-train. Accuracy is over rows[warmup:] only; timing is over all."""
    err, n, t0 = 0, 0, time.time()
    for i, (_, x, y, _, _) in enumerate(rows):
        if i >= warmup:
            # TEST first: the label is consumed only on the line below this one.
            err += 0 if (1 if learner.predict(x) > 0.5 else 0) == y else 1
            n += 1
        learner.update(x, y)
    return 100.0*(1 - err/n), time.time() - t0


def pbf_degree(d, budget=6000):
    """Highest polynomial degree whose expansion fits inside `budget` features.

    Table 2 specifies degree 3, and that is what runs for Electricity (d=8 -> 164
    monomials) and RTG (d=30 -> 5,455). CoverType is the one that does not fit:
    d=55 expands to 30,855 monomials, ~190x Electricity's cost per instance and
    not feasible in pure Python, so it falls back to degree 2 (1,595).

    This is Table 5's own point arriving early. The paper times PBF-SGD(2) and
    PBF-SGD(3) separately precisely because the basis expansion is where the cost
    goes, and C(d+k-1, k) grows in the ATTRIBUTE count, not the stream length. We
    drop to the highest affordable degree and print which one ran, rather than
    silently reporting a "degree 3" row that was really degree 2.
    """
    from itertools import combinations_with_replacement as cwr
    for deg in (3, 2, 1):
        n = sum(len(list(cwr(range(d), k))) for k in range(1, deg + 1))
        if n <= budget: return deg, n
    return 1, d


def table(name, rows, d, n_trees):
    deg, nfeat = pbf_degree(d)
    warmup = len(rows)//10                      # tau_0 = T/10, per Table 1
    print("\n%s  (n = %d, d = %d, warmup = %d, PBF degree %d -> %d features%s)" % (
        name, len(rows), d, warmup, deg, nfeat,
        ", RF-HT at %d trees" % n_trees if n_trees != 100 else ""))
    print("  %-9s %8s %8s %9s   %s" % ("method", "acc", "paper", "sec", "delta"))
    built = [
        ("kNN",     lambda: methods.KNN(d, w=100, k=10)),
        ("SGD",     lambda: methods.HingeSGD(d, lam=0.01)),
        ("HT",      lambda: methods.HoeffdingTree(d, delta=1e-7, tau=0.05)),
        ("SAMkNN",  lambda: methods.SAMkNN(d, k=5)),
        ("PBF-SGD", lambda: methods.PBFSGD(d, degree=deg, lam=0.01)),
        ("RF-HT",   lambda: methods.AdaptiveRandomForest(d, n_trees=n_trees,
                                                         lam=6.0, n_min=50)),
    ]
    for mname, mk in built:
        acc, secs = prequential(mk(), rows, warmup)
        ref = PAPER.get((name.split()[0], mname))
        delta = ""
        if ref is not None:
            delta = ("%+.1f" % (acc - ref)) if name.split()[0] in COMPARABLE \
                    else "not comparable"
        print("  %-9s %8.1f %8s %9.1f   %s" %
              (mname, acc, ("%.1f" % ref) if ref else "-", secs, delta))
        sys.stdout.flush()


if __name__ == "__main__":
    quick = "--quick" in sys.argv
    trees = 10 if quick else 100
    if "--trees" in sys.argv:
        trees = int(sys.argv[sys.argv.index("--trees") + 1])
    cap = 10000 if quick else None

    # --- Electricity: full 45,312 unless --quick
    elec = data.electricity(max_rows=cap)
    table("Electricity", list(elec), elec.d, trees)

    # --- RTG: scikit-multiflow defaults, T as per Table 1
    rtg = syn.RandomTreeGenerator(seed=0)
    table("RTG", rtg.take(syn.T_DEFAULT), rtg.d, trees)

    # --- CoverType: 10k subset, binarised -- NOT comparable, see docstring
    cov = data.covertype(max_rows=10000)
    table("CoverType", list(cov), cov.d, trees)

    # --- Synthetic: Table 3's row is Figure 6, i.e. the SUSTAINED drift stream
    #
    # d = 20 is OURS, not the paper's: section 6 never states the synthetic input
    # dimension. It matters more than any other unstated choice here, because our
    # A_0.01 is a Givens rotation in one coordinate plane, so it disturbs 2 of d
    # components -- the larger d is, the more of theta survives each step and the
    # better any tracker does. Measured, at Table 1 parameters (SGD / PBF-SGD / HT):
    #
    #     d=2    57.7  76.3  50.7        paper's Synthetic row:
    #     d=5    74.5  82.4  71.8          SAMkNN 96.0
    #     d=10   83.1  83.4  80.9          PBF-SGD 95.1
    #     d=20   92.2  88.5  88.0          RF-HT 93.6
    #
    # So the paper's numbers are reachable only at the high end and are nowhere
    # near the d=2 that Figure 4 plots. Two readings could explain it and we
    # cannot distinguish them from the text: either the synthetic stream had many
    # more attributes than the figure, or "a rotational matrix of angle 0.01"
    # means a full random rotation rather than a Givens one, in which case the
    # d-dependence above largely disappears. Flagged, not resolved.
    D_SYNTH = 20
    dr = syn.scenarios(d=D_SYNTH, seed=0)["sustained"]
    st = syn.Stream(dr, d=D_SYNTH, seed=0)
    table("Synthetic", st.take(syn.T_DEFAULT), D_SYNTH, trees)
