# data-drift

A **reproduction** of:

> Jesse Read, **Concept-drifting Data Streams are Time Series; The Case for Continuous
> Adaptation**, [arXiv:1810.02266v1](https://arxiv.org/abs/1810.02266v1), Oct 2018.
> PDF at `../papers/1810.02266v1.pdf`, extracted text at `code/paper.txt`.

Everything in `code/` runs **the paper's own experiments on the paper's own data**:
Table 1's synthetic streams, Table 2's six methods, Table 3's four datasets. Pure
Python stdlib — no scikit-multiflow, no numpy — so every number is traceable to a
line you can read.

The notes alongside are the argument the experiments test.

## Run it

```bash
cd data && ./fetch.sh          # Electricity + CoverType from MOA, the paper's own source
cd ../code
python3 experiments.py         # Table 3, all four streams  (~50 min; --quick for 10k caps)
python3 lambda_condition.py    # section 5's lambda condition  (~1 min)
python3 figure5.py             # Figure 5: the vanilla three across the drift types (~4 min)
python3 demos.py               # the three worked figures the notes cite  (instant)
```

`fetch.sh` verifies both downloads against the instance counts the paper states —
45,312 for Electricity and 581,012 for CoverType. Both match exactly.

Most of that 50 minutes is SAMkNN, which alone takes 21 minutes on RTG: its STM size
adaptation re-evaluates candidate window suffixes by interleaved kNN, so cost grows
with the square of the memory it decides to keep. `--quick` caps every stream at 10K
and drops RF-HT to 10 trees.

## What reproduces

Prequential, accuracy over $\tau_0 \ldots T$ with $\tau_0 = T/10$, as Table 1 directs
and Table 5 confirms ("the initial block, which is not evaluated in terms of accuracy").

| stream | SAMkNN | | PBF-SGD | | RF-HT | |
|---|--:|:--|--:|:--|--:|:--|
| | *ours* | *paper* | *ours* | *paper* | *ours* | *paper* |
| **Electricity** (45,312) | 78.0 | 79.8 | 80.7 | 85.9 | **84.5** | 86.2 |
| **RTG** (10K) | 71.1 | 78.8 | **82.8** | 81.8 | 72.5 | 77.9 |
| **Synthetic** (10K) | 81.1 | 96.0 | 88.5 | 95.1 | 86.7 | 93.6 |
| CoverType (10K)† | 91.2 | 93.3 | 91.0 | 92.6 | 90.5 | 93.9 |

† not comparable — the paper classifies all 7 classes, we binarise one-vs-rest on a subset.

**Electricity is the clean result**: SAMkNN within 1.8 points and RF-HT within 1.7 at
the full 100 trees. **On RTG, PBF-SGD exceeds the paper** (82.8 vs 81.8) and the
paper's ranking there — PBF-SGD ahead of both rivals — is preserved.

Three things do not reproduce, and each is informative:

- **PBF-SGD on Electricity** (−5.2). Not a $\lambda$ problem: $\lambda$ is inert across a 50×
  range. The specified degree 3 is *worse* than degree 2 (80.5 vs 83.9).
- **SAMkNN, increasingly** (−1.8, −7.7, −14.9). Our LTM compression is capacity-bounded
  FIFO where Losing et al. use kMeans++ per class, and the miss scales with how much
  the long-term memory ought to matter.
- **The Synthetic row generally**. See the dimension problem below — the paper's 93–96%
  is unreachable at the $d$ its own Figure 4 plots.

One result worth the detour: on the Synthetic stream plain **SGD (92.2) beats PBF-SGD
(88.5)**. The true boundary there is $\theta^{\top}x = 0$ — linear by construction — so a
degree-3 basis contributes 1,770 parameters of pure variance. Basis expansion is not
free, and the paper's own synthetic stream is the case where it cannot help.

## What the paper leaves unstated

These are not quibbles — each one changes the numbers, and none is recoverable from
the text. Our choices are recorded in the code, not silently applied:

| Unstated | Effect | What we did |
|---|---|---|
| Synthetic input dimension | **Decisive.** SGD scores 57.7 / 74.5 / 83.1 / 92.2 at $d$ = 2 / 5 / 10 / 20 under sustained drift | $d = 20$; the paper's 93–96% is unreachable at the $d = 2$ its Figure 4 plots |
| Meaning of "a rotational matrix of angle 0.01" past 2-D | Sets how much of $\theta$ each step disturbs | Givens rotation in one plane; exact at $d=2$ |
| L2 strength for SGD | Minor | scikit-multiflow's default $\alpha = 10^{-4}$ |
| Which 6 Electricity attributes | Minor | The paper says 6; `elecNormNew.arff` declares **8**. We drop `date` and use 7 + bias |
| Label noise on the synthetic stream | Minor | None, since none is mentioned |

## The argument being tested

1. Streams are assumed i.i.d. within a concept, so drift is treated as something to
   **detect** and reset around.
2. That is self-contradictory: **drift implies temporal dependence**, so a drifting
   stream *is* a time series. (Lemma 1)
3. Recast concepts as points $\theta \in \Theta$. Drift becomes a **trajectory through $\Theta$**.
4. Detect-and-reset cuts bias by destroying the model, which raises variance, which
   forces ever-larger ensembles — a spiral, costly under sustained drift.
5. If drift is a trajectory, **track it instead**: $\hat{\theta}_{t+1} \leftarrow \hat{\theta}_t + \lambda \nabla E$, no detector, no
   reset. Available only to models whose parameters live in a continuous space.

Step 5 is visible in the code itself: `theta_hat()` returns a vector for `HingeSGD`
and `PBFSGD`, and `None` for `KNN`, `SAMkNN`, `HoeffdingTree` and
`AdaptiveRandomForest`. That is not an unimplemented method — **a tree has no
$\Delta\theta$**. It is the paper's most durable claim and it needs no benchmark.

## Read in this order

| File | Contents |
|---|---|
| [NOTATION.md](NOTATION.md) | Every symbol with its defining formula. **Start here.** |
| [01-core-argument.md](01-core-argument.md) | Lemma 1, why $\tau$'s unobservability matters, the graphical model |
| [02-taxonomy.md](02-taxonomy.md) | The four drift types as trajectories of $\theta$ |
| [03-mechanisms.md](03-mechanisms.md) | Forgetting / detect-reset / continuous, and why exactly three |
| [04-experiments.md](04-experiments.md) | The paper's results, then our reproduction |
| [05-critique.md](05-critique.md) | What it does and doesn't deliver; what to watch when citing |

## Code

| Module | Contents |
|---|---|
| `synthetic.py` | Table 1's four drift types as $\theta$-trajectories, Figure 6's sustained stream, and the RTG generator |
| `data.py` | Electricity + CoverType as prequential streams (stdlib ARFF reader) |
| `methods.py` | Table 2's six methods — kNN, SGD, HT, SAMkNN, PBF-SGD, RF-HT — plus ADWIN |
| `experiments.py` | Table 3 reproduction |
| `figure5.py` | Figure 5: vanilla kNN / SGD / HT across Table 1's drift types |
| `lambda_condition.py` | Section 5's $\lambda$ condition, which the paper states but never tests |
| `demos.py` | The three worked figures the notes cite |
| `paper.txt` | Extracted PDF text, grep-able |

`synthetic.Stream` yields `(t, x_t, y_t, theta_t, C_t)` — including the ground-truth
$\theta_t$, which no real deployment can see, but which is exactly what §4's bias analysis
needs. `data.ArffStream` yields the same 5-tuple with `theta_t = None`: on real data
there is no ground-truth concept, so every $\theta$-based metric is **structurally**
unavailable, not merely unimplemented.

## Caveats

- **CoverType is not comparable, and is not informative either.** The paper classifies
  all 7 classes; `data.py` binarises one-vs-rest and we evaluate a 10k subset. Worse,
  `covtypeNorm.arff` is not randomly ordered: class 2 is concentrated early, so after
  the $\tau_0$ warmup only **9.7%** of the scored instances are positive and the
  majority-class baseline is **90.3%**. Every method lands within a point of it and two
  fall below. Those numbers measure the base rate, not learning — do not read the row
  as "all methods do well here". The other three streams have baselines of 57.2, 50.8
  and 50.9, and every method clears them comfortably.
- **SAMkNN is structural, not a port.** LTM compression is capacity-bounded FIFO where
  Losing et al. use kMeans++ per class. Do not cite our SAMkNN numbers as theirs.
- **PBF-SGD on CoverType runs at degree 2, not 3.** Degree 3 there is 30,855 monomials
  per instance and not feasible in pure Python. The harness prints which degree ran.
- Observations marked as ours in [05-critique.md](05-critique.md) are not claims Read
  makes. Do not cite them to him.
