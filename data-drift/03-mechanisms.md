# 3. The three mechanisms

From §1.2. The cleanest way to see why these are treated as exhaustive is to ask:
**what does the model store, and what can it do to that store when the world changes?**

| Mechanism | What it stores | Response to drift | Is $\Delta\theta$ defined? |
|---|---|---|---|
| 1. Forgetting | **instances** | evict old ones | n/a — no $\theta$ at all |
| 2. Detect and reset | **structure** | destroy and regrow | **no** |
| 3. Continuous adaptation | **parameters** | move them | **yes** |

The right-hand column is the paper's argument compressed to one word per row.
All three are implemented in [`code/methods.py`](code/methods.py) — not as
stand-ins, but as the paper's own Table 2 methods, one per mechanism:
`KNN`/`SAMkNN` (forgetting), `HoeffdingTree`/`AdaptiveRandomForest` (detect
and reset, via `ADWIN`), `HingeSGD`/`PBFSGD` (continuous).

The division is visible in the code itself: `theta_hat()` returns a vector for
the third group and `None` for the first two. That is not an unimplemented
method — there is no $\theta$ for a buffer or a tree to return.

## First, the thing that is easy to miss

The paper writes the true model as

$$y_t = f(x_t\,;\,\theta_c) + \epsilon_t$$

Two arguments, separated by a semicolon. **$x_t$** is the input, changing every instance.
**$\theta_c$** decides *which f you are using*, changing only at drift. It is not y = f(x)
with one f — it is a family, and $\theta$ selects the member.

Concretely, the same inputs through f before and after a drift:

| x | f before | y | f after | y | flipped? |
|---|--:|:--:|--:|:--:|:--:|
| [1.0, 0.0] | 0.711 | 1 | 0.378 | 0 | **yes** |
| [0.0, 1.0] | 0.401 | 0 | 0.690 | 1 | **yes** |
| [1.0, 1.0] | 0.622 | 1 | 0.574 | 1 | no |
| [1.72, 0.56] | 0.790 | 1 | 0.398 | 0 | **yes** |
| [−1.0, 0.5] | 0.250 | 0 | 0.711 | 1 | **yes** |

Identical input, different answer. Nothing in x announces it. Row 3 is the trap: the
answer sometimes coincides, so a stale model is right by luck and you learn nothing.

Your model has the same shape, $\hat{y}_t = h(x_t; \hat{\theta}_t)$, and the only thing anyone can modify
is **$\hat{\theta}$**. You cannot touch $\theta$; it belongs to the world. The three mechanisms are three
answers to *how you move a model*, and they differ because $\hat{\theta}$ is stored differently.

---

## 1. Forgetting — kNN, batch-incremental ensembles

**How it works.** Lazy: no training beyond storing examples in a buffer of size w,
then comparing $x_t$ by distance. There is no $\theta$, no parameters. The boundary is implicit
in the stored data.

**How it meets drift.** Passively — old instances age out:

> The limited-sized buffer of kNN methods imply a natural forgetting mechanism where
> old examples are purged... **Any impact by concept drift is inherently temporary.**

**The defining tradeoff.** The buffer must be "large enough to represent the current
concept adequately, but not too large as to be prohibitively expensive to query."
Drift makes it worse: a bigger buffer means better within-concept accuracy but a
longer $t - \tau$ before recovery.

**Failure mode, plus one striking observation.** §7 notes predictive power is capped
by buffer size. Then Fig. 5a shows something easy to miss: under a **stationary**
concept kNN shows **no upward trend** — unlike HT and SGD it does not improve with
more data. *A buffer method cannot accumulate.* Our runs reproduce this twice over
(`python3 code/figure5.py`): kNN is **worst in all five scenarios**, and its score is
**flat across every one of them** — 72.7 to 73.3, a spread of 0.6 points, against
SGD's 88.1–97.3. Drift barely changes kNN's accuracy because kNN never built anything
for drift to take away. The cap and the flatness are the same fact.

And §4 gives the hard limit: automatic recovery is "not a solution when the drift is
sustained over a long time or occurs regularly."

**Cost.** Worst time complexity of the three — $O(wdk)$ per instance, since every
prediction queries the whole buffer.

---

## 2. Detect and reset — Hoeffding trees + ADWIN, HAT, ensembles

**How it works.** The Hoeffding tree splits only when the Hoeffding bound says the
split is statistically safe. §7 calls this "fast but conservative"; the guarantee is
equivalence to a batch-built tree, but *only within a single concept*. Fig. 5a makes
the conservatism visible — accuracy jumps 10 points after t = 7000, the *initial split*
finally firing.

**Why it needs an external detector.** A tree cannot purge:

> a permanent change in concept will **permanently invalidate** the current tree

Hence the bolt-on: ADWIN, CUSUM, Page-Hinkley, or a moving-average test watches {$E_t$}
and triggers a reset. HAT runs an ADWIN at *every node* and cuts the branch where
change registers.

**Why it lives in ensembles.** Detectors mis-fire, and trees are "almost universally
employed in ensembles to mitigate potential fallout from mis-detections." Plus §4's
deeper reason — resetting cuts bias but raises variance, and ensembles reduce variance:

$$\text{harder detection} \rightarrow \text{more resets} \rightarrow \text{more variance} \rightarrow \text{bigger ensembles} \rightarrow \text{more compute}$$

**The structural limitation — the paper's most durable finding.** A tree's parameters
are a discrete structure: which attribute splits where. No metric, no meaningful
increment, no way to nudge it slightly. **There is no $\Delta\theta$ for a tree.** Continuous
adaptation is not merely unimplemented for trees; it is undefined. Hence §7: a tree
"will struggle when the true target concept $\theta_t$ is a moving target rather than a fixed
point in concept space."

**Cost.** $O(d)$ time but $O(\ell d)$ space with $\ell = O(n)$ worst case, and crucially *not
constant*:

> as trees in an ensemble grow and are reset under drift, time and space complexity
> **fluctuates** — making practical requirements difficult to estimate precisely in
> advance. If there is no drift, the trees may in theory grow unbounded.

---

## 3. Continuous adaptation — SGD, neural networks

**How it works.** $\hat{\theta}$ lives in the same continuous space as $\theta$, so the model can travel.
Every instance gets the same update, unconditionally:

$$\hat\theta_{t+1} \leftarrow \hat\theta_t + \lambda\nabla E_{\hat\theta_t}$$

Derived in §5 from recursive least squares,

$$\hat{\theta}_t = \hat{\theta}_{t-1} + R_t^{-1} x_t\left(y_t - x_t^{\top}\hat{\theta}_{t-1}\right)$$

by noting that $x_t(y_t - x_t^{\top}\hat\theta_{t-1}) = \nabla E_{\hat\theta_t}$ and
replacing $R_t^{-1}$ with a fixed $\lambda$.

Note what is absent: no drift test, no branch, no reset, no $\hat{\tau}$, no concept identity.
**The same update runs whether or not drift is happening.** Adaptation is not
triggered by drift — it is the ordinary learning step, which happens to absorb drift.

**How it meets drift.** By transfer, not replacement:

> knowledge is **transferred** as best as possible to a newer/updated concept rather
> than discarded or reset

— "a kind of transfer learning; namely **continuous** transfer learning." The
justification traces to the taxonomy: under *partial* change the old $\theta$ is partly
right, so discarding it destroys usable information.

**The one condition.** Do not decay $\lambda$ toward zero. Batch practice decays it to
converge on a fixed point, but a stream has no fixed point, and decay makes the model
"react more and more slowly to concept drift until eventually becoming stuck in one
concept." [`code/lambda_condition.py`](code/lambda_condition.py) quantifies it — and
corrects the intuition. Decay costs **+18.6 accuracy points after sudden drift** but
only **+0.8 under sustained drift**. Under sustained rotation a constant $\lambda$ never
tracks well either (88.1), so decay destroys little; after a sudden resample a live $\lambda$
relearns and a frozen one cannot. The condition is really about **recovery from
discontinuities**. See [04-experiments.md](04-experiments.md) §B3.

**Why the field discarded it.** §7 is candid, and this is the most useful diagnostic
in the paper:

> We suspect that SGD has not been widely considered in state-of-the-art data-stream
> evaluations because it performs poorly on real-world and complex data when deployed
> in an off-the-shelf manner, **especially if the learning rate is decayed – as is
> often the standard.**

Two compounding mistakes: decaying $\lambda$, and using it linearly. Fix both — constant $\lambda$
plus a basis expansion — and it is competitive.

**Cost.** $O(d)$ time, $O(d)$ space, **constant across time**.

---

## Which mechanism suits which drift type

| Drift type | Best suited | Why |
|---|---|---|
| Sudden, **total** | detect-and-reset | old $\theta$ genuinely worthless; the paper concedes this case |
| Sudden, **partial** | continuous | old $\theta$ partly valid — resetting discards usable structure |
| **Incremental** | continuous | $\theta_t = \theta_{t-1} + \Delta_t\theta$ and the SGD update have the same form |
| **Gradual** | unresolved | $\alpha_t$ evolves, not $\theta_t$ — deferred to future work |
| **Sustained / constant** | continuous | detect-and-reset never stops paying |

## The asymmetry being driven at

| | Forgetting | Detect-and-reset | Continuous |
|---|---|---|---|
| Triggered by | buffer overflow | a detector firing | nothing — always on |
| Knowledge retained | last w instances | none in the reset subtree | all of it, shifted |
| Latency | buffer size | $\hat{\tau} - \tau$, then regrowth | one step |
| Cost profile | flat but high, $O(wdk)$ | spikes at resets; $\ell$ fluctuates | flat and low, $O(d)$ |
| Improves on stationary data | **no** | yes, conservatively | yes |
| Handles sustained drift | no | expensively | yes |

Forgetting cannot accumulate; detect-and-reset accumulates but must periodically burn
what it accumulated; continuous adaptation accumulates *and* carries it forward. That
option is available only to the mechanism whose store is a point in a continuous space
— which is why §3's reframing of concepts as $\theta \in \Theta$ had to come before the argument.

## Detection as $\tau$-estimation

A compact way to state the contribution:

- **Detect-and-reset** estimates $\tau$. Every detector produces a $\hat{\tau}$, necessarily with
  $\hat{\tau} > \tau$, since it cannot fire until {$E_t$} has already shifted. The lag $\hat{\tau} - \tau$ is where
  the biased predictions live; a false positive is a $\hat{\tau}$ with no real $\tau$ behind it.
- **Continuous adaptation never estimates $\tau$ at all.**

The contribution is *eliminating* a latent variable, not estimating it better.
