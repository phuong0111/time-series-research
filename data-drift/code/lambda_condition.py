"""Section 5's one prescription, tested on the paper's own stream and method.

    "We remark that for SGD to perform robustly over the length of a stream, we
     have to ensure certain conditions. In particular, to not decay the learning
     rate lambda towards zero over time. In batch scenarios we wish to converge
     to a fixed point and such learning rate scheduling is common and effective
     practice. However, under a stream this would cause SGD to react more and
     more slowly to concept drift until eventually becoming stuck in one concept."

The paper states this and moves on; it reports no experiment isolating it. This
one does, using Table 2's SGD (hinge + L2, lambda = 0.01) on Table 1's synthetic
streams, with accuracy recorded over tau_0..T as Table 1 directs.

    Run:  python3 lambda_condition.py
"""
import sys
import methods, synthetic as syn
from experiments import prequential

SEEDS = range(5)          # the concepts theta_c ~ N(0,I) are redrawn per seed
D     = 20                # see the note in experiments.py on the unstated dimension


def main():
    print("Section 5: constant vs decayed lambda  (Table 2 SGD, Table 1 streams,")
    print("d = %d, %d seeds, accuracy over tau_0..T)\n" % (D, len(list(SEEDS))))
    print("  %-12s %10s %10s %10s" % ("scenario", "constant", "decayed", "penalty"))
    for name in ("stationary", "sudden", "incremental", "gradual", "sustained"):
        accs = {True: [], False: []}
        for seed in SEEDS:
            dr   = syn.scenarios(d=D, seed=seed)[name]
            rows = syn.Stream(dr, d=D, seed=seed).take(syn.T_DEFAULT)
            for dec in (False, True):
                # Same stream, same seed, same lambda_0 -- the ONLY difference is
                # whether lambda is allowed to fall.
                l = methods.HingeSGD(D, lam=0.01, decay=dec)
                a, _ = prequential(l, rows, syn.TAU0)
                accs[dec].append(a)
        c = sum(accs[False])/len(accs[False])
        d_ = sum(accs[True])/len(accs[True])
        # Penalty is in accuracy points LOST by decaying; positive means decay hurt.
        print("  %-12s %10.1f %10.1f %+10.1f" % (name, c, d_, c - d_))
        sys.stdout.flush()


if __name__ == "__main__":
    main()
