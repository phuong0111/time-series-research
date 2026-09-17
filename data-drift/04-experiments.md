# 4. Experiments

Two parts: what the paper reports, and what we reproduced independently.

---

# Part A — the paper's own results (§6–7)

Scikit-MultiFlow, prequential evaluation, desktop 2.60GHz / 16GB. Synthetic streams
(Table 1 parameters: $\tau_0$ = 1K, $\tau_1$ = 5K, $\tau_2$ = 6K, T = 10K) plus Electricity
(45,312 × 6), CoverType (581,012 × 54), RTG.

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

[`code/experiments.py`](code/experiments.py), pure stdlib, ~20s. T = 4000, 5 seeds,
$\sigma = 0.10$, 2-D linear concepts.

**Design difference from the paper.** Mechanisms 2 and 3 here share the *same* base
linear model and differ **only** in their drift response. The paper compares RF-HT
(100 trees + ADWIN) against PBF-SGD (one linear model), which confounds the mechanism
with model size. Holding the base model fixed isolates the mechanism.

The detect-reset learner is therefore an illustration of the reset **strategy**, not a
Hoeffding tree. A real HT cannot be written this way — which is precisely the paper's
structural point.

## B1. Three mechanisms × six scenarios (error rate)

| scenario | continuous | detect-reset | buffer-kNN | resets |
|---|--:|--:|--:|--:|
| stationary | **0.132** | 0.133 | 0.149 | 3.2 |
| sudden | **0.139** | 0.140 | 0.160 | 4.4 |
| incremental | **0.143** | 0.143 | 0.184 | 4.2 |
| gradual | **0.228** | 0.230 | 0.235 | 7.2 |
| sustained (Fig 6) | **0.152** | 0.153 | 0.218 | 3.0 |
| reoccurring | 0.154 | **0.151** | 0.201 | 8.8 |

**Findings:**

- **Buffer methods are limited — confirmed, strongly.** kNN is worst in all six, and
  the gap widens exactly where the paper predicts: sustained drift (0.218 vs 0.152)
  and incremental (0.184 vs 0.143). Under stationary conditions the gap is smallest
  (0.149 vs 0.132), consistent with its inability to accumulate.
- **Gradual drift is the hard case for everyone** (0.228–0.235 vs ~0.14). Supports the
  paper's decision to defer it.
- **Continuous ≈ detect-reset, everywhere.** Once the base model is held fixed, the
  reset strategy adds nothing. See B4 for why.

## B2. Tracking — mean angle($\theta_t$, $\hat{\theta}_t$), degrees

| scenario | continuous | detect-reset | buffer-kNN |
|---|--:|--:|--:|
| stationary | **5.8** | 6.2 | n/a |
| sudden | **6.8** | 7.0 | n/a |
| incremental | **9.5** | 9.7 | n/a |
| gradual | **27.7** | 28.1 | n/a |
| sustained (Fig 6) | 12.9 | **12.8** | n/a |
| reoccurring | 10.3 | **9.5** | n/a |

buffer-kNN has **no $\hat{\theta}$ at all** — that absence is the point, not a gap in the table.

Gradual drift's 27.7° is the standout: $\hat{\theta}$ cannot track a $\theta$ that teleports between two
fixed points. It settles near the average of the two concepts, which is optimal-ish
but not *tracking*.

## B3. The $\lambda$ condition (§5) — confirmed quantitatively

| scenario | constant $\lambda$ | decayed $\lambda$ | penalty |
|---|--:|--:|--:|
| stationary | 0.132 | **0.128** | −0.004 |
| sudden | **0.139** | 0.211 | **+0.072** |
| sustained (Fig 6) | **0.152** | 0.414 | **+0.262** |

**This is the paper's central prescription, cleanly reproduced.** Decaying $\lambda$ is
*marginally better* when stationary — which is exactly why it is standard batch
practice — and catastrophic under sustained drift, nearly tripling the error. The
mechanism is as described: $\lambda \to 0$ freezes the model into whichever concept it was in.

## B4. Cost of destructive adaptation, under sustained drift

| detector sensitivity | resets | error |
|---|--:|--:|
| δ = 0.25 | 0.0 | 0.152 |
| δ = 0.15 | 3.0 | 0.153 |
| δ = 0.08 | 16.2 | 0.153 |
| **continuous (no detector)** | **0.0** | **0.152** |

More resets never helps; it costs slightly. But the honest reading is sharper than
"resetting is costly": **when the base model can already adapt continuously, resetting
is simply redundant.** Detection earns its keep only when the base model *cannot*
move — i.e. for trees. This supports the paper's structural claim while undercutting
its framing: the problem is not that resetting is expensive, it is that resetting is a
workaround for a model class that has no $\Delta\theta$.

## B5. Momentum — the forecasting term that isn't

| scenario | $\beta = 0.0$ | $\beta = 0.5$ | $\beta = 0.9$ |
|---|--:|--:|--:|
| sustained (Fig 6) | 0.152 | **0.151** | 0.156 |
| incremental | 0.143 | **0.142** | 0.144 |
| sudden | 0.139 | **0.138** | 0.140 |

$\lambda$ scaled by (1−$\beta$) so effective step size is held constant — without that compensation
momentum merely inflates the step and looks falsely bad.

**Result: essentially neutral.** Fig. 4 shows a momentum run ($\beta = 0.5$) tracking a
rotating concept, and §7 concludes it is "more promising to model the drift and
pre-empt its development." We find no measurable benefit. See
[05-critique.md](05-critique.md) — the paper argues for forecasting and ships reactive
tracking.

## B6. The $\lambda$ tradeoff — quantified, which the paper does not do

| $\lambda$ | stationary | sustained | sudden | mean angle gap |
|--:|--:|--:|--:|--:|
| 0.05 | **0.127** | 0.282 | 0.150 | 18.6° |
| 0.10 | 0.128 | 0.222 | 0.142 | 13.9° |
| 0.30 | 0.129 | 0.165 | **0.137** | **9.3°** |
| 0.50 | 0.132 | 0.152 | 0.139 | 8.5° |
| 1.00 | 0.139 | **0.148** | 0.144 | 9.5° |

The two columns pull in **opposite directions**: small $\lambda$ wins when stationary
(0.127 at $\lambda = 0.05$), large $\lambda$ wins under sustained drift (0.148 at $\lambda = 1.0$). $\lambda \approx 0.3$–0.5
is the compromise.

§5 says only "do not decay $\lambda$ toward zero" and leaves it there. This table is what that
instruction actually costs: **$\lambda$ is a responsiveness/variance dial, not a free lunch.**
Choosing it requires knowing how much drift you expect — the very thing you claimed not
to need a detector for.
