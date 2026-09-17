# 5. Critique — what to watch when citing

## What the paper is

**A position paper, not a method paper.** The title says so: "*The Case for* Continuous
Adaptation." The author is explicit throughout:

| Location | Phrasing |
|---|---|
| Abstract | "we develop and **parameterize** gradient-descent methods" |
| §6 | "we **simply employed** basis expansion" |
| §7 | "we put together the PBF-SGD method from **elementary components**" |
| §8 | "The **method we used was simple**" |

"Parameterize," not "propose." PBF-SGD is stock SGD + degree-3 polynomial features +
one rule (don't decay $\lambda$). Every component was already on the shelf.

**What it does deliver:**

1. A corrected **graphical model of the problem** (Figs. 1–2) — the main formal object.
2. **Lemma 1** — drift implies temporal dependence.
3. A **diagnosis of the field's behaviour** (§4): the bias–variance analysis explains
   *why* HT ensembles dominate and why that spirals under sustained drift. This is the
   real intellectual payload.
4. A **configuration recipe**, not an algorithm.

## The gap between rhetoric and method

§5 says:

> solving the concept drift problem is identical to solving the forecasting problem of
> predicting $\theta_t$

and then delivers SGD, which **tracks reactively rather than forecasting**. The update

$$\hat\theta_{t+1} \leftarrow \hat\theta_t + \lambda\nabla E_{\hat\theta_t}$$

uses only the *current* error. No velocity term, no extrapolation of $\theta$'s trajectory, no
state-space model of the drift. The paper derives SGD *from* RLS, name-checks
forgetting-RLS and Kalman filters as the natural extensions — and does not build one.

The single gesture toward real forecasting is Fig. 4's momentum term ($\beta = 0.5$), which
*is* a velocity estimate. But momentum is absent from Table 2's PBF-SGD configuration,
no experiment isolates it, and **our B5 finds it neutral** once step size is
compensated. So "model the drift and pre-empt its development" (§7) is stated as a
conclusion while the delivered method is one-step reactive tracking with a bounded lag.

## The load-bearing assumption, never flagged as one

The framework presumes $\hat{\theta}$ and $\theta$ live in the **same continuous, additively-updatable
space**. That is what licenses $\theta_t = \theta_{t-1} + \Delta_t\theta$ as a model of drift and
$\hat{\theta}_{t+1} \leftarrow \hat{\theta}_t + \lambda \nabla E$ as a way to track it — the two equations are structurally identical,
which is exactly the resemblance the argument leans on.

True for SGD on a hyperplane. **False for a Hoeffding tree**, whose parameters are a
discrete structure with no metric and no meaningful increment. There is no $\Delta\theta$ for a
tree; you can only regrow it.

This cuts both ways:

- **A genuine finding** — it names *why* trees must destroy and rebuild, rather than
  just measuring the symptom. This is the paper's most durable result and it depends
  on no benchmark.
- **Somewhat question-begging** — choosing to define concepts as points in a continuous
  $\Theta$ builds in a representation gradient methods inhabit natively and trees cannot
  inhabit at all. "Gradient methods suit drift better" is partly downstream of the
  modelling choice.

The three-way accuracy tie in Table 3 is consistent with the second reading: the
formalism explains *why costs differ*, not that one method predicts better.

## Weaknesses in the evidence

**Table 3 cannot support "tie."** Four datasets, single runs, no error bars, no
significance tests. 85.9 vs 86.2 on Electricity is not distinguishable from noise — but
neither is it *demonstrated* to be a tie. The conclusion is the safe one, but the table
lacks the statistical weight to establish parity any more than it could establish a win.

**Table 5's timing is confounded, and the paper says so:**

> more efficient implementations exist than the Python framework we used in this work

Everything runs in scikit-multiflow. Optimized C++ Hoeffding trees (MOA) would narrow
the gap by an unknown amount. The measured order of magnitude partly measures the
implementation, not the mechanism — which is why Table 4 matters more than Table 5.

**Not like-for-like on model size.** RF-HT is 100 trees; PBF-SGD is one linear model
over expanded features. Of course 100 models cost more. The paper's reply — that the
ensemble *is* the cost of resetting — is a fair defence of the framing but does not
make the raw timing a clean mechanism comparison. A single HAT would have been the
honest middle case; it is surveyed in §1.2 and absent from the experiments. (Our Part B
fixes this by holding the base model fixed.)

**One point in the paper's favour:** timing was truncated to the first 10,000 instances
on CoverType, which has 581,012. Since HT cost grows with $\ell$, truncating *understates*
the tree overhead. That choice works against the paper's own thesis, so the reported
gap is conservative on that axis.

## What our reproduction adds

Reproducing Table 2's methods on Table 3's data, prequentially, over $\tau_0 \ldots T$:

| Finding | Status |
|---|---|
| SAMkNN on Electricity (79.8) | **reproduced** — 78.0, −1.8 |
| RF-HT on Electricity (86.2) | **reproduced** — 84.5, −1.7, at the full 100 trees |
| PBF-SGD on Electricity (85.9) | **not reproduced** — 80.7, −5.2 |
| PBF-SGD's specified degree 3 beats degree 2 | **contradicted** — degree 2 is 3.3 points better |
| Decaying $\lambda$ is catastrophic under drift | **confirmed, with a correction** — see below |
| A tree has no $\Delta\theta$ | **structural**, and now visible in the code |

**The $\lambda$ correction.** §5 warns against decaying $\lambda$ because the model would
"react more and more slowly to concept drift". Tested on Table 1's streams with
Table 2's SGD, the penalty is **+18.6 points after sudden drift and +0.8 under
sustained drift** — the reverse of what the wording suggests. Under sustained rotation
a constant $\lambda$ never tracks well either (88.1), so decay destroys little; after a
sudden resample a live $\lambda$ relearns and a frozen one cannot. The warning is really
about **recovery from discontinuities**, not about tracking continuous drift. Full
tables and the $\lambda_0$ sensitivity check in [04-experiments.md](04-experiments.md) §B3.

**"A tree has no $\Delta\theta$" is no longer an argument — it is a signature.** In
[`code/methods.py`](code/methods.py), `theta_hat()` returns a vector for `HingeSGD` and
`PBFSGD` and `None` for `KNN`, `SAMkNN`, `HoeffdingTree` and `AdaptiveRandomForest`.
That is not an unimplemented method; there is no $\theta$ for a buffer or a structure to
return. The paper's most durable claim needs no benchmark, and the type signature is
the whole proof.

**What the paper does not pin down matters more than any method here.** The synthetic
stream's dimension is never stated, and it moves SGD from 57.7 to 92.2 (§B4). The
paper's own Synthetic row is only reachable at the high end — not at the $d = 2$ its
Figure 4 plots. Anyone citing Table 3's Synthetic column should know that.

> **Removed claim.** Earlier revisions of these notes carried a reading that
> "resetting is redundant, not costly", derived from a mechanism-isolating harness
> that held the base model fixed across detect-reset and continuous learners. That
> harness is no longer in the repo — everything now runs the paper's own methods, and
> HT vs RF-HT confounds the detector with a 100× ensemble, so it cannot test the same
> thing. The claim is withdrawn rather than left unsourced.

## Other things to know

- **No recommendations list.** The abstract promises "a number of recommendations for
  deploying methods in concept-drifting streams," but there is no explicit list — it is
  dissolved into §7 and §8. Citing it means paraphrasing.
- **Own-stated limitations:** Python implementations only; gradual drift deferred; no
  deep-learning comparison despite the conclusion pointing at neural networks; more
  work needed on sudden, gradual and mixed drift.
- **$\lambda$ is overloaded in Table 2** — learning rate for SGD (0.01), Poisson bagging
  parameter for RF-HT (6). Unrelated quantities.
