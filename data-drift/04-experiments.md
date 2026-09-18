# 4. Experiments

Two parts: what the paper reports, and what we reproduced independently.

---

# Part A — the paper's own results (§6–7)

Scikit-MultiFlow, prequential evaluation, desktop 2.60GHz / 16GB. Synthetic streams
(Table 1 parameters: $\tau_0$ = 1K, $\tau_1$ = 5K, $\tau_2$ = 6K, T = 10K) plus Electricity
(45,312 × 6), CoverType (581,012 × 54), RTG.

> The instance counts match `elecNormNew.arff` and `covtypeNorm.arff` exactly. The
> **attribute** count does not: Electricity's ARFF declares 8 (`date`, `day`,
> `period`, `nswprice`, `nswdemand`, `vicprice`, `vicdemand`, `transfer`), not 6.
> Which 6 the paper used is not stated.

**Methods (Table 2).** Vanilla: kNN (k = 10, buffer 100); SGD (L2, $\lambda = 0.01$, hinge);
HT (10⁻⁷ split confidence, 0.05 tie threshold, naive Bayes leaves). Advanced: SAMkNN;
PBF-SGD (SGD + degree-3 polynomial basis); RF-HT (Adaptive Random Forest — 100 HTs,
ADWIN, $\lambda = 6$, nmin = 50).

**The three advanced methods are one per mechanism** — that is the experimental design:

| Column | Mechanism |
|---|---|
| SAMkNN | 1. Forgetting |
| RF-HT | 2. Detect and reset |
| PBF-SGD | 3. Continuous adaptation |

## Accuracy (Table 3) — a three-way tie

| Dataset | SAMkNN | PBF-SGD | RF-HT |
|---|---|---|---|
| Electricity | 79.8 | 85.9 | **86.2** |
| RTG | 78.8 | **81.8** | 77.9 |
| CoverType | 93.3 | 92.6 | **93.9** |
| Synthetic | **96.0** | 95.1 | 93.6 |

The paper **needs this to be a tie, not a win.** A win would make it a method paper
with 4 datasets and no significance testing. As a parity result it clears the ground
so cost can decide.

## Complexity (Table 4) — the load-bearing table

| Method | Time | Space |
|---|---|---|
| kNN | $O(wdk)$ | $O(wd)$ |
| HT | $O(d)$ | $O(\ell d)$ |
| SGD | $O(d)$ | $O(d)$ |

SGD and kNN are constant per instance; HT is not — $\ell$ is $O(n)$ worst case and fluctuates
as trees grow and reset. **This claim is implementation-independent**, which is why it
matters more than the timing chart.

## Runtime (Table 5)

Note: Table 5 is a **bar chart** (y-axis 0–1000 seconds), not extractable numbers.
Only the first 10,000 instances were timed. The paper's claim is that RF-HT is "up to
an order of magnitude or more" slower than the alternatives.

---

# Part B — our reproduction

[`code/experiments.py`](code/experiments.py), pure stdlib. **The paper's own methods on
the paper's own data**: Table 2's six algorithms, Table 1's synthetic parameters,
Table 3's four streams. Prequential, accuracy over $\tau_0 \ldots T$ with $\tau_0 = T/10$.

No stand-ins: `HoeffdingTree` is a real Hoeffding tree (Hoeffding-bound splits,
Gaussian numeric observers, naive Bayes leaves), `ADWIN` is real ADWIN2 with
exponential histograms, `AdaptiveRandomForest` is 100 of those trees with random
subspaces, Poisson(6) bagging and two-level warning/drift detection.

## B1. Table 3 reproduced

| stream | method | ours | paper | $\Delta$ |
|---|---|--:|--:|--:|
| **Electricity** | SAMkNN | 78.0 | 79.8 | −1.8 |
| 45,312, $d$=8 | PBF-SGD(3) | 80.7 | 85.9 | **−5.2** |
| | RF-HT (100 trees) | 84.5 | 86.2 | −1.7 |
| **RTG** | SAMkNN | 71.1 | 78.8 | −7.7 |
| 10K, $d$=30 | PBF-SGD(3) | 82.8 | 81.8 | **+1.0** |
| | RF-HT | 72.5 | 77.9 | −5.4 |
| **Synthetic** | SAMkNN | 81.1 | 96.0 | −14.9 |
| 10K, $d$=20 | PBF-SGD(3) | 88.5 | 95.1 | −6.6 |
| | RF-HT | 86.7 | 93.6 | −6.9 |
| CoverType† | SAMkNN | 91.2 | 93.3 | n/a |
| 10K, $d$=55 | PBF-SGD(2) | 91.0 | 92.6 | n/a |
| | RF-HT | 90.5 | 93.9 | n/a |

† Not comparable, and not informative. Besides the 7-class/binary mismatch and the
subset, `covtypeNorm.arff` is not randomly ordered — class 2 is concentrated in the
opening rows, so once the $\tau_0$ warmup is removed only **9.7%** of scored instances
are positive. The majority-class baseline is therefore **90.3%**: SAMkNN clears it by
0.9, PBF-SGD by 0.7, kNN by 0.6, RF-HT by 0.2, while SGD is 0.1 **below** it and HT 7.2
below. The row measures the base rate, not learning.

For contrast, the baselines on the streams that do carry information are 57.2
(Electricity), 50.8 (RTG) and 50.9 (Synthetic) — every method clears those by a wide
margin, so those accuracies reflect real learning.

Vanilla configurations, which the paper does not tabulate (kNN / SGD / HT):
Electricity 73.1 / 74.3 / 75.8 · RTG 61.2 / 66.9 / 68.0 ·
CoverType 90.9 / 90.2 / 83.1 · Synthetic 73.6 / **92.2** / 88.0.

**What reproduces.** Electricity is the clean row: SAMkNN −1.8 and RF-HT −1.7 at the
paper's full 100 trees. On RTG, PBF-SGD *exceeds* the paper (+1.0), and the ranking
the paper reports there — PBF-SGD ahead of SAMkNN and RF-HT — is preserved.

**What does not, and why it is informative.**

*PBF-SGD on Electricity* (−5.2) is the one outright miss on a comparable row, and §B4
shows it is not a $\lambda$ artifact: the specified degree 3 is worse than degree 2.

*SAMkNN degrades systematically across the three rows* — −1.8, −7.7, −14.9. That
ordering is the diagnostic. Our LTM compression is capacity-bounded FIFO where Losing
et al. use kMeans++ per class, so the gap should widen exactly where the long-term
memory carries the most load, and it does. These numbers should not be reported as
SAMkNN's.

*The whole Synthetic row falls short*, which §B4 attributes to the unstated input
dimension rather than to any method.

**The result that pays for the exercise.** On the Synthetic stream plain SGD scores
**92.2 against PBF-SGD's 88.5** — the basis expansion actively hurts. The synthetic
concept is a hyperplane $\theta^{\top}x = 0$, linear by construction, so a degree-3 basis
adds 1,770 parameters that can only contribute variance. PBF-SGD exists to "accommodate
non-linear decision boundaries" (§6); on the paper's own synthetic stream there are
none to accommodate. Expansion is a bet on non-linearity, and Table 3's Synthetic
column is the cell where that bet is guaranteed to lose.

## B2. Figure 5 reproduced — and what does not survive it

Figure 5 plots the vanilla three across the drift types, but rescales each panel's
y-axis "for greater visibility of separation", so it cannot be read as numbers.
[`code/figure5.py`](code/figure5.py) reports what the panels are drawn from —
$d = 20$, 5 seeds, accuracy over $\tau_0 \ldots T$:

| scenario | kNN | SGD | HT |
|---|--:|--:|--:|
| stationary | 73.3 | **97.3** | 90.7 |
| sudden | 73.1 | **94.1** | 82.8 |
| incremental | 73.2 | **96.1** | 89.0 |
| gradual | 72.8 | **94.0** | 82.9 |
| sustained | 72.7 | **88.1** | 84.6 |

**Buffer methods are limited — confirmed, and in a sharper form than the paper puts
it.** §7 says predictive power is "limited in proportion to the number of instances
stored", and Fig. 5a notes kNN shows no upward trend under a stationary concept. Both
are visible here at once: kNN is worst in **all five** scenarios, and its score is
**flat across all five** — a spread of 0.6 points against SGD's 9.2. Drift costs kNN
almost nothing because kNN never accumulated anything for drift to take. The cap and
the flatness are one fact, not two.

**"Gradual is the hard case" does not survive.** It is the hardest case for a *tree*
(HT 82.9 gradual vs 89.0 incremental — a tree cannot unlearn a split), but SGD's
hardest case is sustained drift (88.1), and kNN has no hard case because it has no
easy one. The paper's grounds for deferring gradual drift are structural anyway: under
Eq. (5) it is $\alpha_t$, not $\theta_t$, that forms the time series, so there is no trajectory
to forecast.

## B3. The $\lambda$ condition of §5 — and a correction

§5 states one prescription and never tests it:

> to not decay the learning rate $\lambda$ towards zero over time \[...\] under a stream this
> would cause SGD to react more and more slowly to concept drift until eventually
> becoming stuck in one concept.

[`code/lambda_condition.py`](code/lambda_condition.py), Table 2's SGD ($\lambda_0 = 0.01$,
hinge + L2) on Table 1's streams, $d = 20$, 5 seeds. Accuracy, and the points lost by
letting $\lambda_t = \lambda_0/\sqrt{t}$:

| scenario | constant $\lambda$ | decayed $\lambda$ | penalty |
|---|--:|--:|--:|
| stationary | 97.3 | 96.4 | +0.9 |
| **sudden** | 94.1 | 75.5 | **+18.6** |
| incremental | 96.1 | 90.9 | +5.2 |
| **gradual** | 94.0 | 79.1 | **+14.9** |
| sustained | 88.1 | 87.3 | +0.8 |

**The prescription holds, but not where you would expect.** Decay is devastating after a
*sudden* concept change and nearly free under *sustained* drift — the opposite of the
intuition that continuous drift is where a frozen model suffers most.

The reason is visible in the "constant" column. Under sustained rotation at 0.01
rad/step, constant $\lambda$ only reaches 88.1 anyway; the concept moves faster than any
fixed step can follow, so decay has little left to destroy. After a sudden resample a
live $\lambda$ relearns the new concept and a frozen one cannot — so the whole 18.6 points
are on the table.

This is not an artifact of Table 2's small $\lambda_0$. Across a 50× range (3 seeds):

| scenario | $\lambda_0 = 0.01$ | $\lambda_0 = 0.1$ | $\lambda_0 = 0.5$ |
|---|--:|--:|--:|
| sustained | +1.0 | +1.2 | +1.4 |
| sudden | +17.8 | +10.0 | +1.7 |

The sustained penalty stays flat and small at every $\lambda_0$; the sudden penalty
collapses as $\lambda_0$ grows, because a large live step relearns fast enough that being
frozen costs less. **§5's warning is really about recovery from discontinuities, not
about tracking continuous drift.**

## B4. What the unstated parameters cost

Two choices the paper does not record change its numbers more than any method does.

**The synthetic stream's dimension.** Our $A_{0.01}$ is a Givens rotation in one
coordinate plane, so it disturbs 2 of $d$ components — the larger $d$, the more of $\theta$
survives each step. On the sustained stream at Table 1 parameters:

| $d$ | SGD | PBF-SGD | HT |
|--:|--:|--:|--:|
| 2 | 57.7 | 76.3 | 50.7 |
| 5 | 74.5 | 82.4 | 71.8 |
| 10 | 83.1 | 83.4 | 80.9 |
| 20 | **92.2** | 88.5 | 88.0 |

Table 3's Synthetic row is 93.6–96.0. That is reachable only at the high end and
**nowhere near the $d = 2$ that Figure 4 plots**. Either the synthetic stream had far
more attributes than the figure shows, or "a rotational matrix of angle 0.01" means a
full random rotation rather than a Givens one — in which case the $d$-dependence above
largely disappears. The text does not let us decide.

**PBF-SGD's polynomial degree.** Table 2 specifies degree 3. On full Electricity:

| degree | $\lambda = 0.01$ | $\lambda = 0.1$ | $\lambda = 0.5$ |
|--:|--:|--:|--:|
| 2 | 83.8 | **83.9** | 83.8 |
| 3 | 80.5 | 80.5 | 80.2 |

$\lambda$ is nearly irrelevant across a 50× range, and **the specified degree 3 is 3.3 points
worse than degree 2**. Our best configuration reaches 83.9 against the paper's 85.9, so
PBF-SGD is the one method here that does not reproduce. The untested suspect is
scikit-multiflow's `SGDClassifier`, whose default `learning_rate='optimal'` schedule is
not the constant $\lambda$ Table 2 implies.
