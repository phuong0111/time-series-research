# data-drift

A worked knowledge base on concept drift, built from:

> Jesse Read, **Concept-drifting Data Streams are Time Series; The Case for Continuous
> Adaptation**, [arXiv:1810.02266v1](https://arxiv.org/abs/1810.02266v1), Oct 2018.
> PDF at `../papers/1810.02266v1.pdf`, extracted text at `code/paper.txt`.

Everything here is either sourced to the paper or reproduced in `code/` (pure Python
stdlib — no dependencies). Numbers marked *ours* are independent reproductions, not
the paper's claims.

## The argument in five steps

1. Streams are assumed i.i.d. within a concept, so drift is treated as something to
   **detect** and reset around.
2. That is self-contradictory: **drift implies temporal dependence**, so a drifting
   stream *is* a time series. (Lemma 1)
3. Recast concepts as points $\theta \in \Theta$. Drift becomes a **trajectory through $\Theta$**.
4. Detect-and-reset cuts bias by destroying the model, which raises variance, which
   forces ever-larger ensembles — a spiral, costly under sustained drift.
5. If drift is a trajectory, **track it instead**: $\hat{\theta}_{t+1} \leftarrow \hat{\theta}_t + \lambda \nabla E$, no detector, no
   reset. Available only to models whose parameters live in a continuous space.

## Read in this order

| File | Contents |
|---|---|
| [NOTATION.md](NOTATION.md) | Every symbol with its defining formula. **Start here.** |
| [01-core-argument.md](01-core-argument.md) | Lemma 1, why $\tau$'s unobservability matters, the graphical model |
| [02-taxonomy.md](02-taxonomy.md) | The four drift types as trajectories of $\theta$ |
| [03-mechanisms.md](03-mechanisms.md) | Forgetting / detect-reset / continuous, and why exactly three |
| [04-experiments.md](04-experiments.md) | The paper's results, then our reproduction |
| [05-critique.md](05-critique.md) | What it does and doesn't deliver; what to watch when citing |

## The one-table summary

The three mechanisms differ in **what the model is made of**, which decides what
"adapt" can physically mean:

| Mechanism | Model is made of | Adapts by | Lives in $\Theta$? | Can move *a little*? |
|---|---|---|---|---|
| Forgetting (kNN) | data | replacing data | no | no — swap |
| Detect-and-reset (HT) | structure | rebuilding structure | no | **no — rebuild** |
| Continuous (SGD) | numbers | shifting numbers | **yes** | **yes** |

A tree has no $\Delta\theta$. That is the paper's most durable finding, and it needs no benchmark.

## Code

```bash
cd code
python3 experiments.py     # the full suite, ~20s, all of Part B in 04-experiments.md
python3 demo_trace.py      # 20-step stream with every symbol printed per step
python3 demo_theta.py      # theta as a hyperplane; the rotation drift; SGD tracking
python3 demo_recovery.py   # 300-step recovery after a total concept reversal
```

| Module | Contents |
|---|---|
| `drift.py` | The four drift types as $\theta$-trajectories + a prequential `Stream` |
| `learners.py` | One learner per mechanism, sharing a base model where possible |
| `experiments.py` | Six comparison tables |
| `paper.txt` | Extracted PDF text, grep-able |

`Stream` yields `(t, x_t, y_t, theta_t, C_t)` — including the ground-truth $\theta_t$, which no
real deployment can see, but which is exactly what §4's bias analysis needs.

## Headline reproductions

| Claim | Result |
|---|---|
| Buffer methods limited, worst under sustained drift | confirmed: 0.218 vs 0.152 |
| Decaying $\lambda$ is catastrophic under drift | confirmed: **+0.262** error |
| ...but marginally *better* when stationary | −0.004 — why it's standard batch practice |
| Gradual drift is the hard case | confirmed: 0.228 vs ~0.14, 27.7° tracking gap |
| Momentum as a "forecasting" term helps | **not reproduced** — neutral |

## Caveats

- Section 5 of the critique lists what the paper does *not* provide. In short: no new
  algorithm, and no model *of* drift — forecasting is argued for, not built.
- Our reproductions use 2-D linear concepts and a from-scratch reset learner, not
  Hoeffding trees. They isolate *mechanisms*; they are not a replication of the
  paper's benchmark numbers.
- Observations marked as ours in [05-critique.md](05-critique.md) — the $\lambda$ tradeoff, the
  "resetting is redundant not costly" reading, the "no $\Delta\theta$ for a tree" framing — are not
  claims Read makes. Do not cite them to him.
