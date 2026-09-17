# 1. The core argument: drifting streams are time series

## The contradiction

The data-stream literature assumes instances are i.i.d. *within* a concept, and
treats drift as a change to **detect** so that an off-the-shelf i.i.d. model can be
re-deployed. Read's §2 shows this assumption is self-contradictory.

**Lemma 1.** A data stream that exhibits concept drift also exhibits temporal
dependence.

*Proof sketch.* Let $p_t(y_t \mid x_t) = p(y_t \mid x_t, C_t)$ where $C_t$ is the concept at time t, and
let drift occur at $0 < \tau < \infty$. Under independence we would need $P(C_t) = P(C_t \mid C_{t-1})$.
But obviously

$$P(C_t = 0) \;\neq\; P(C_t = 0 \mid C_{t-1} = 1)$$

— after drift you no longer expect instances from the first concept. Marginalizing
out the unobserved C from the joint:

$$p(y_t \mid x_t, x_{t-1}) \;=\; p(y_t \mid x_t)\, p(x_t \mid x_{t-1})$$

which is **not** the independence factorization $p(y_t \mid x_t, x_{t-1}) = p(y_t \mid x_t)$.
The surviving $x_{t-1}$ term *is* temporal dependence. ∎

Counted on the 20-step worked stream (`python3 code/demos.py chain`, $\tau = 10$):

$$P(C_t = 0) = \tfrac{9}{20} = 0.450 \qquad P(C_t = 0 \mid C_{t-1} = 1) = \tfrac{0}{10} = 0.000$$

## Why the asymptotic objection fails

One could argue: as $t \to \infty$ we have $P(C_t = 1) = P(C_{t-1}) = 1$, so the indicator becomes
a constant and independence is effectively restored within each concept. The reply
turns on a single fact:

> However **we do not observe $\tau$**; we cannot know exactly when the drift will occur
> or if it has occurred. As a result, an instantaneous drift between two time steps
> can manifest itself as temporal dependence in the error signal over many instances.

If you knew $\tau$ you could partition the stream at it and treat each side as i.i.d.,
and the whole paper would collapse. You don't, so you can't. **The unobservability
of $\tau$ is what converts a one-step jump into an extended time series.**

The paper adds that this is already implicit in the field's own tools, "since they
measure the change in the error signal of predictive models":

$$E_t = E(h_t(x_t), y_t)$$

If $h_t$ is poorly adapted to a drift, that shows up as increasing $E_t$ — i.e. as a time
series. Every drift detector is a time-series method that declines to call itself one.

## The graphical model

This is the paper's main formal deliverable — a model **of the problem**, not of the
solution:

| Figure | What it shows |
|---|---|
| 1a, 1b | The *assumed* stream: discriminative and generative, no edges between time steps |
| 2a | Reality: a concept chain $c_{t-1} \to c_t \to c_{t+1}$ sits above the data |
| 2b | Same, with C marginalized out — **the inputs are now connected to each other** |

## Five differences from classical time series

The paper is careful not to claim streams *are* ordinary time-series problems:

1. Only drifting portions are guaranteed to have time-series structure.
2. Streams treat dependence as a problem to remove, not signal to model.
3. Prediction is needed at time t — no smoothing / forward-backward inference.
4. Labels arrive at t−1, so training is online; time-series models are built offline.
5. Streams are assumed infinite.

Nearest analogue: **filtering** (Kalman, particle, HMM). Indeed the marginalization
above "is a starting point for state space models."

## What follows from it

If drift is a time series, it is in principle *predictable*, which reframes the whole
problem (§5):

> solving the concept drift problem is identical to solving the forecasting problem
> of predicting $\theta_t$

That reframing is what licenses mechanism 3 — see [03-mechanisms.md](03-mechanisms.md).
Whether the paper actually delivers forecasting is a separate question, taken up in
[05-critique.md](05-critique.md).
