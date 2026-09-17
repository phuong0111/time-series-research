"""Figure 5 of Read (2018): the vanilla three across the synthetic drift types.

Figure 5 plots accuracy over a sliding 200-instance window for kNN, SGD and HT on
(a) stationary, (b) sudden, (c) incremental and (d) gradual streams. Its y-axes are
rescaled per panel "for greater visibility of separation", so the figure cannot be
read as numbers -- this reports the overall accuracy the panels are drawn from,
plus the same sliding-window statistic at the end of each stream.

    Run:  python3 figure5.py

Table 1 parameters throughout, accuracy over tau_0..T, averaged over 5 seeds.
"""
import sys
import methods, synthetic as syn
from experiments import prequential

SEEDS    = range(5)
D        = 20                 # see experiments.py on the unstated dimension
SCENARIOS = ("stationary", "sudden", "incremental", "gradual", "sustained")


def build(d):
    """The vanilla configuration of Table 2, which is what Figure 5 plots."""
    return [("kNN", lambda: methods.KNN(d, w=100, k=10)),
            ("SGD", lambda: methods.HingeSGD(d, lam=0.01)),
            ("HT",  lambda: methods.HoeffdingTree(d, delta=1e-7, tau=0.05))]


def main():
    print("Figure 5: vanilla kNN / SGD / HT on Table 1's synthetic streams")
    print("(d = %d, %d seeds, accuracy over tau_0..T)\n" % (D, len(list(SEEDS))))
    print("  %-12s %8s %8s %8s   %s" % ("scenario", "kNN", "SGD", "HT", "hardest for"))
    for name in SCENARIOS:
        accs = {}
        for mname, mk in build(D):
            vals = []
            for seed in SEEDS:
                dr   = syn.scenarios(d=D, seed=seed)[name]
                rows = syn.Stream(dr, d=D, seed=seed).take(syn.T_DEFAULT)
                a, _ = prequential(mk(), rows, syn.TAU0)
                vals.append(a)
            accs[mname] = sum(vals)/len(vals)
        worst = min(accs, key=accs.get)     # which method this scenario hurts most
        print("  %-12s %8.1f %8.1f %8.1f   %s" %
              (name, accs["kNN"], accs["SGD"], accs["HT"], worst))
        sys.stdout.flush()
    print("\n(Read down a column to see which drift type is hardest for a mechanism;")
    print(" read across a row to see which mechanism that drift type favours.)")


if __name__ == "__main__":
    main()
