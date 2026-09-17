# Notation

Every symbol in Read (2018), with the formula that defines it. Column 4 gives the
value used in the worked example (`code/demo_trace.py`).

| Symbol | Meaning | Defining formula | Example value |
|---|---|---|---|
| $\Theta$ | concept space | $\theta_t \in \Theta$ | $\mathbb{R}^2$ |
| $\theta_c$ | parameters of concept c | generating dist. is $p_{\theta_c}$ | — |
| $\theta_{c_1}$ | concept 1 | — | [+0.90, −0.40] |
| $\theta_{c_2}$ | concept 2 | — | [−0.50, +0.80] |
| $\tau$ | change point | $\theta_t = \theta_{c_1}$ for $t < \tau$ ; $\theta_{c_2}$ for $t \geq \tau$ | 10 |
| $\tau_1, \tau_2$ | start / end of extended drift | $\Delta\theta = 0$ outside $\tau_1 \ldots \tau_2$ | 5K, 6K |
| $\tau_0$ | **pre-training ends** (not drift!) | accuracy recorded over $\tau_0 \ldots T$ | T/10 |
| T | stream length | — | 10K |
| $C_t$ | latent concept indicator | $p_t(y_t \mid x_t) = p(y_t \mid x_t, C_t)$ | 0 then 1 |
| $\theta_t$ | true concept now | $\theta_t = \theta_{c_t}$ | $\theta_{c_1}$ or $\theta_{c_2}$ |
| $\alpha_t$ | mixing weight (gradual only) | $c_t \sim \mathcal{B}(\alpha_t)$ | $\text{ramps } 0 \to 1$ |
| $x_t$ | instance | $(x_t, y_t) \sim p_t(\mathcal{X}, \mathcal{Y})$ | 2-D, $\sim \mathcal{N}(0, I)$ |
| f | true underlying model | $f(x_t; \theta_c) = \sigma(\theta_t^{\top} x_t)$ | $\in (0,1)$ |
| $\epsilon_t$ | irreducible noise | $\epsilon_t \sim \mathcal{N}(0, \sigma^2)$ | $\sigma = 0.30$ |
| $y_t$ | label that arrives | $y_t = f(x_t; \theta_c) + \epsilon_t$ | 0 or 1 |
| $\hat{\theta}_t$ | learner's estimate | $\hat{\theta}_{t+1} \leftarrow \hat{\theta}_t + \lambda \nabla E_{\hat{\theta}_t}$ | starts [+0.10, +0.10] |
| $h_t$ | the model | $h_t(x_t) = \sigma(\hat{\theta}_t^{\top} x_t)$ | $\in (0,1)$ |
| $\hat{y}_t$ | prediction | $\hat{y}_t = h_t(x_t)$ | 0 or 1 |
| $E_t$ | error signal | $E_t = E(h_t(x_t), y_t)$ | 0/1 loss |
| $\lambda$ | learning rate | $\Delta\hat{\theta}_t = \lambda \nabla E_{\hat{\theta}_t}$ | 0.5 |
| $\beta$ | momentum (Fig. 4 only) | $v_t = \beta v_{t-1} + \lambda \nabla E$ | 0.5 |
| $\ell$ | number of leaves in a tree | HT space is $O(\ell d)$ | $O(n)$ worst case |
| w, k, d | window, neighbours, attributes | kNN is $O(wdk)$ | — |

## Three traps

**1. $\tau_0$ is not a drift point.** It is the burn-in boundary from Table 1. Only
$\tau, \tau_1$, $\tau_2$ concern drift.

**2. $\lambda$ means two different things in Table 2.** For SGD it is the learning rate
($\lambda = 0.01$). For RF-HT it is Adaptive Random Forest's Poisson parameter for online
bagging ($\lambda = 6$). Same letter, unrelated quantities.

**3. $\theta$ is the paper's analytical language, not every algorithm's output.**
Only SGD holds a $\hat{\theta}$. kNN and Hoeffding trees have no parameters in $\Theta$ at all —
§1.1 calls this approximating the distribution "directly or indirectly". When §7
says a tree "will struggle when the true target concept $\theta_t$ is a moving target",
that is the paper describing the tree's situation in $\theta$-language; the tree itself
never computes anything like $\theta$.

## $\theta$ versus $\hat{\theta}$

| | What it is | Owner | Why it moves |
|---|---|---|---|
| $\theta_t$ | the **true** parameters of the world | nature | concept drift |
| $\hat{\theta}_t$ | the learner's **estimate** | your model | learning updates |

The thesis in one line: **make $\hat{\theta}_t$ track $\theta_t$ instead of chasing it.**

Note that $\hat{\theta}$ never needs to *equal* $\theta$. The boundary $\theta^{\top}x = 0$ is scale-invariant, so
many $\hat{\theta}$ give identical predictions. At t = 2000 in `demo_theta.py`:

$$\theta = [+0.0118,\; -0.7615] \qquad \hat\theta = [+1.0728,\; -5.9185]$$

$\hat{\theta}$ is ~8× larger, yet the two agree on **94.8%** of 10,000 random inputs — they are
only 9.4° apart in direction. "Find $\theta$" is not even well-posed; only direction matters.
