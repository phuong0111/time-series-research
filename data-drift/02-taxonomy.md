# 2. Drift taxonomy in parameter space

§3 is titled "A Fresh Analysis". The freshness is not a new list of drift types — it
inherits Gama et al.'s — it is the **restatement of each type as a trajectory of $\theta$
through concept space $\Theta$**, which is what makes the forecasting argument possible.

All four are implemented in [`code/drift.py`](code/drift.py).

## The setup

$\theta_t \in \Theta$ = the true (unknown) parameters defining the concept at time t; the generating
distribution is $p_{\theta_t}$. One move does all the work:

> concept → a distribution p → the parameter vector $\theta$ pinning it down → a point in $\Theta$

This covers the smooth case ($\theta$ = hyperplane coefficients, Fig. 3 shows a rotating
boundary) *and* the categorical case (concepts $C \in \{1,\ldots,K\}$ with $\theta_c$ the c-th one).

*Terminology aside (footnote 5):* "drift" implies slow movement, so the author would
prefer **shift** for the abrupt case, and keeps "drift" only for consistency with the
literature.

## Abrupt / sudden (§3.1)

$$\theta_t = \begin{cases}\theta_{c_1} & t < \tau\\[2pt] \theta_{c_2} & t \geq \tau\end{cases}$$

Subdivided by *extent*, which matters more than the suddenness:

- **Total** — $\theta_{c_1}, \theta_{c_2}$ drawn independently from $\Theta$. Unrelated concepts; you have
  changed problem domains.
- **Partial** — a local change to some component of $\theta$ ($\theta$ is multi-dimensional).

This is the hinge of the §5 rebuttal. Detect-and-reset is defensible **only** under
total change. Under partial change the old parameters are partly reusable, so
discarding them throws away transfer — "a scenario unlikely to be the case in practice."

## Incremental (§3.2)

$$\theta_t = \theta_{t-1} + \Delta_t\theta$$

with $\Delta\theta = 0$ outside $\tau_1 \leq t \leq \tau_2$. **Intermediate states are real concepts** — $\theta$ passes
through genuine points in $\Theta$.

Read §6 realises this as a rotation, $\theta_t = A_{0.01}^{\top}\theta_{t-1}$ (`code/demo_theta.py`):

| t | $\theta_t$ | ‖$\theta$‖ | angle | $\Delta_t\theta$ |
|---|---|---|---|---|
| 0 | [+0.70000, −0.30000] | 0.7616 | −23.1986° | — |
| 1 | [+0.69697, −0.30698] | 0.7616 | −23.7715° | [−0.00303, −0.00698] |
| 2 | [+0.69386, −0.31394] | 0.7616 | −24.3445° | [−0.00310, −0.00695] |
| 3 | [+0.69069, −0.32086] | 0.7616 | −24.9175° | [−0.00317, −0.00692] |
| 4 | [+0.68744, −0.32775] | 0.7616 | −25.4904° | [−0.00324, −0.00689] |
| 5 | [+0.68413, −0.33461] | 0.7616 | −26.0634° | [−0.00331, −0.00686] |

Three readings:

- The last column **is** $\Delta_t\theta$ — tiny (~0.0076/step) and *not constant*; it rotates with
  $\theta$. The additive form is exact, but $\Delta\theta$ is state-dependent, not a fixed offset.
- ‖$\theta$‖ never changes: the concept travels on a circle in $\Theta$ at 0.5730° = 0.01 rad/step.
- Every intermediate row is a **genuine concept**, not a blend.

Note the structural match to the SGD update $\hat{\theta}_{t+1} \leftarrow \hat{\theta}_t + \lambda \nabla E$. That resemblance is the
argument.

## Gradual (§3.3)

$$\theta_t = \theta_{c_t} \quad \text{where} \quad c_t \sim \mathcal{B}(\alpha_t)$$

Two *fixed* concepts; what changes is the mixing probability $\alpha_t$, with $\alpha_{t<\tau_1} = 0$ and
$\alpha_{t>\tau_2} = 1$. And $\alpha_t$ is itself an incremental drift between 0 and 1.

| | What moves | Intermediate concepts | Time series lives in |
|---|---|---|---|
| **Incremental** | $\theta_t$ itself, through $\Theta$ | real, genuinely occupied | $\theta_t$ |
| **Gradual** | the mixing weight | none — one of two fixed concepts | $\alpha_t$ |

That last column is why the paper **explicitly defers gradual drift**: its method
forecasts $\theta_t$, but under gradual drift $\theta_t$ is not the thing evolving. "A detailed
treatment is left for future work."

Our experiments confirm it is the hard case: gradual is the worst scenario for every
mechanism (error 0.228–0.235 vs ~0.14 elsewhere) and gives the worst tracking gap
(27.7° vs 5.8–12.9°). See [04-experiments.md](04-experiments.md).

## Re-occurring (§3.4)

Any of the above, repeating. Connected to HMMs and switching models, with a claim
worth sitting with:

> there is no technical difference between modelling states, and tracking concepts.

The distinction is pragmatic, not mathematical: a **state** is something you want to
model (a weather system); a **drift** is something you want to adapt to or factor out
(sensor degradation, climate change).

## Not drift: outliers

Listed alongside as explicitly excluded. A single anomalous point is not a change in
$p_{\theta}$, and conflating them is how detectors generate the false positives that ensembles
exist to mitigate.

## Two qualifications

**Smoothness is an assumption, not a property.** Neither incremental nor gradual drift
need be smooth or monotonic — that is a common simplification. A sigmoid is the usual
choice and what many MOA generators use, so synthetic benchmarks partly measure how
well a method handles *sigmoids*.

**How §6 instantiated each type:**

| Type | Instantiation | Note |
|---|---|---|
| Incremental | $\theta_t = A_{0.01}^{\top}\theta_{t-1}$ | constant-speed circular path |
| Gradual | $\alpha_t = (t-\tau_1)/(\tau_2-\tau_1)$ | a linear ramp, not the sigmoid just mentioned |
| Sudden | resample $\theta_t \sim \Theta$ after $\tau_1$ | the **total** case — most favourable to detectors |
