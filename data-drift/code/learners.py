"""The three mechanisms of Read (2018) §1.2, as learners over a common stream.

    1. Forgetting          -> BufferLearner      (kNN; model IS the stored data)
    2. Detect and reset    -> DetectResetLearner (model is destroyed and regrown)
    3. Continuous adapt.   -> ContinuousSGD      (model is numbers; they move)

DESIGN NOTE. Mechanisms 2 and 3 here share the SAME underlying linear model and
differ ONLY in how they respond to drift. That is deliberate: the paper compares
RF-HT (100 trees + ADWIN) against PBF-SGD (one linear model), so its timing gap
confounds the mechanism with model size. Holding the base model fixed isolates
the mechanism itself.

DetectResetLearner is therefore an illustration of the reset STRATEGY, not a
Hoeffding tree. A real HT cannot be written this way -- and that is the paper's
structural point: a tree's parameters are a discrete structure, so no Delta-theta
exists for it. It can only be destroyed and regrown.
"""
import heapq, math
from collections import deque
from itertools import islice
from drift import sigmoid, dot


class Learner:
    def predict(self, x):  raise NotImplementedError   # h_t(x_t) -> probability
    def update(self, x, y): raise NotImplementedError  # observe y_t, adapt
    def theta_hat(self):   return None                 # None if not in Theta
    name = "learner"


class ContinuousSGD(Learner):
    """Mechanism 3.  theta_hat_{t+1} <- theta_hat_t + lambda * grad E

    No detector, no branch, no reset: the same update runs whether or not drift
    is happening. The one condition from Section 5 is that lambda must NOT decay
    toward zero, or the model freezes into one concept (see decay= below).
    """
    name = "continuous-sgd"

    def __init__(self, d, lam=0.5, momentum=0.0, decay=False):
        self.th   = [0.0]*d           # theta_hat_1 = 0; sigmoid(0)=0.5 -> predicts 0 at t=1
        self.lam0, self.lam = lam, lam  # lambda_0 kept so decay can divide the ORIGINAL
        self.beta = momentum          # beta, the velocity term sketched in Fig. 4
        self.vel  = [0.0]*d           # v_t, the momentum accumulator (unused when beta=0)
        self.decay, self.t = decay, 0 # t counts updates; never reset, so decay is monotone

    def predict(self, x):
        return sigmoid(dot(self.th, x))   # h_t(x) = sigma(theta_hat . x), in (0,1)

    def theta_hat(self):
        return list(self.th)              # a copy, so callers cannot mutate our state

    def update(self, x, y):
        self.t += 1                          # one more instance seen
        if self.decay:                       # the mistake Section 5 warns about
            # lambda_t = lambda_0 / sqrt(t): the standard online-convex-optimisation
            # schedule (the one behind O(sqrt(T)) regret bounds). NOT Robbins-Monro,
            # which also needs sum(lambda_t^2) < infinity -- sum(1/t) diverges.
            # After T=4000 this is a 63x shrink. Since theta_t here rotates at a
            # CONSTANT 0.01 rad/step, any schedule decaying to zero is eventually
            # outrun: by t=4000 theta_hat sits ~74 deg from theta, i.e. no better
            # than chance. That is the Section 5 failure mode, worth +0.262 error.
            self.lam = self.lam0 / math.sqrt(self.t)
        # g = y - h is the NEGATIVE gradient of log-loss wrt the logit z = theta_hat.x:
        #   L = -[y log h + (1-y) log(1-h)],  dL/dz = h - y,  dL/dtheta_i = (h-y) x_i
        # so descending L means theta_i += lambda * (y-h) * x_i. The sigmoid's own
        # derivative h(1-h) cancels out exactly -- that is why this costs O(d).
        # NOTE g uses the OLD theta_hat, computed once before the loop, so all d
        # components step simultaneously (not a Gauss-Seidel sweep).
        g = y - self.predict(x)              # signed residual on the label, in (-1, 1)
        for i in range(len(self.th)):
            step = self.lam * g * x[i]       # the step moves theta_hat ALONG x
            # Heavy-ball momentum: at beta=0 this is v=step, i.e. plain SGD. At
            # beta>0 a sustained direction is amplified by 1/(1-beta) in steady
            # state -- which is why callers scale lambda by (1-beta) to compare.
            self.vel[i] = self.beta*self.vel[i] + step
            self.th[i] += self.vel[i]        # theta_hat_{t+1} <- theta_hat_t + v_t


class DetectResetLearner(Learner):
    """Mechanism 2.  Monitor the error signal {E_t}; on detection, destroy theta_hat.

    The detector is a two-window mean-error test in the spirit of ADWIN: compare
    recent error against a longer reference window, fire when recent is worse by
    more than `delta`. Firing resets theta_hat to zero -- 'destructive adaptation'.
    """
    name = "detect-reset"

    def __init__(self, d, lam=0.5, short=30, long=150, delta=0.15, cooldown=50):
        self.d, self.lam = d, lam        # d = dim of Theta; lambda = SGD step size
        self.th = [0.0]*d                # theta_hat, the SAME base model as ContinuousSGD
        # Ring buffer of the last `long` values of E_t. maxlen caps space at O(long)
        # instead of the O(T) an unbounded list would grow to; only the last `long`
        # entries were ever read, so the detector's decisions are unchanged.
        self.errs = deque(maxlen=long)
        self.short, self.long, self.delta = short, long, delta  # window sizes; firing gap
        self.cooldown, self.since_reset = cooldown, 0   # min instances between two resets
        self.resets, self.reset_times = 0, []           # diagnostics: count and when
        self.t = 0                       # instance counter, so reset_times is meaningful

    def predict(self, x):
        return sigmoid(dot(self.th, x))  # h_t(x) = sigma(theta_hat . x); same form as SGD

    def theta_hat(self):
        return list(self.th)             # a copy; this learner DOES live in Theta

    def update(self, x, y):
        self.t += 1                      # one more instance seen
        # One predict() call serves both the detector and the gradient: theta_hat
        # cannot change between them, so the two former calls were redundant work.
        p = self.predict(x)              # h_t(x_t), reused twice below
        yhat = 1 if p > 0.5 else 0       # y_hat_t: threshold at 0.5, ties -> class 0
        self.errs.append(0 if yhat == y else 1)   # E_t = 1[y_hat != y], the 0/1 loss
        self.since_reset += 1            # age since the last destructive reset

        # --- the same continuous SGD step as mechanism 3 -----------------------
        g = y - p                        # negative gradient wrt the logit (see above)
        for i in range(self.d):
            self.th[i] += self.lam * g * x[i]     # theta_hat += lambda * (y-h) * x

        # --- the detector: this is the ONLY thing mechanism 2 adds -------------
        # Needs a full reference window, and must respect the cooldown or a single
        # drift would trigger a burst of resets while the model is still recovering.
        if len(self.errs) >= self.long and self.since_reset >= self.cooldown:
            # recent: mean E_t over the last `short` instances (the fast signal).
            # islice is used because a deque cannot be sliced like a list.
            recent = sum(islice(self.errs, len(self.errs) - self.short, None)) / self.short
            # ref: mean E_t over the whole `long` window (the slow baseline).
            ref    = sum(self.errs) / self.long
            if recent - ref > self.delta:            # detector fires
                self.th = [0.0]*self.d               # DESTRUCTIVE adaptation
                self.errs.clear()                    # forget the error history too
                self.since_reset = 0                 # restart the cooldown clock
                self.resets += 1                     # count it (reported in table 1)
                self.reset_times.append(self.t)      # record WHEN, for diagnostics


class BufferLearner(Learner):
    """Mechanism 1.  The model IS the buffer; adaptation is data replacement.

    There is no theta_hat anywhere in this class -- that absence is the point.
    It approximates the boundary non-parametrically, so it can never be compared
    against theta directly (Section 1.1: 'directly or indirectly').
    """
    name = "buffer-knn"

    def __init__(self, d, w=100, k=10):
        self.w, self.k, self.buf = w, k, []   # w = window size, k = neighbours, buf = model

    def theta_hat(self):
        return None                      # no parameters. ever.

    def predict(self, x):
        if not self.buf: return 0.5      # cold start: no data, so abstain at exactly 0.5
        # Squared distance to every stored point (monotone in true distance, so the
        # sqrt is unnecessary). nsmallest is equivalent to sorted(...)[:k] but runs
        # in O(w log k) instead of O(w log w) -- matching the paper's O(wdk) claim
        # more closely, and the reason this is the slowest learner regardless.
        ds = heapq.nsmallest(self.k,
                             ((sum((a-b)**2 for a, b in zip(x, xi)), yi)
                              for xi, yi in self.buf),
                             key=lambda p: p[0])
        return sum(y for _, y in ds) / len(ds)   # majority vote as a fraction in [0,1]

    def update(self, x, y):
        self.buf.append((list(x), y))    # the update IS storing the instance
        if len(self.buf) > self.w:
            self.buf.pop(0)              # natural forgetting: drop the oldest
