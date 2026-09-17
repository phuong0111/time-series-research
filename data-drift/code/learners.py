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
import math
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
        self.th   = [0.0]*d
        self.lam0, self.lam = lam, lam
        self.beta = momentum          # the velocity term sketched in Fig. 4
        self.vel  = [0.0]*d
        self.decay, self.t = decay, 0

    def predict(self, x):     return sigmoid(dot(self.th, x))
    def theta_hat(self):      return list(self.th)

    def update(self, x, y):
        self.t += 1
        if self.decay:                       # the mistake Section 5 warns about
            self.lam = self.lam0 / math.sqrt(self.t)
        g = y - self.predict(x)              # grad of log-loss wrt the logit
        for i in range(len(self.th)):
            step = self.lam * g * x[i]
            self.vel[i] = self.beta*self.vel[i] + step
            self.th[i] += self.vel[i]


class DetectResetLearner(Learner):
    """Mechanism 2.  Monitor the error signal {E_t}; on detection, destroy theta_hat.

    The detector is a two-window mean-error test in the spirit of ADWIN: compare
    recent error against a longer reference window, fire when recent is worse by
    more than `delta`. Firing resets theta_hat to zero -- 'destructive adaptation'.
    """
    name = "detect-reset"

    def __init__(self, d, lam=0.5, short=30, long=150, delta=0.15, cooldown=50):
        self.d, self.lam = d, lam
        self.th = [0.0]*d
        self.errs = []
        self.short, self.long, self.delta = short, long, delta
        self.cooldown, self.since_reset = cooldown, 0
        self.resets, self.reset_times = 0, []

    def predict(self, x):     return sigmoid(dot(self.th, x))
    def theta_hat(self):      return list(self.th)

    def update(self, x, y):
        yhat = 1 if self.predict(x) > 0.5 else 0
        self.errs.append(0 if yhat == y else 1)
        self.since_reset += 1

        g = y - self.predict(x)
        for i in range(self.d):
            self.th[i] += self.lam * g * x[i]

        if len(self.errs) >= self.long and self.since_reset >= self.cooldown:
            recent = sum(self.errs[-self.short:]) / self.short
            ref    = sum(self.errs[-self.long:]) / self.long
            if recent - ref > self.delta:            # detector fires
                self.th = [0.0]*self.d               # DESTRUCTIVE adaptation
                self.errs = []
                self.since_reset = 0
                self.resets += 1
                self.reset_times.append(len(self.errs))


class BufferLearner(Learner):
    """Mechanism 1.  The model IS the buffer; adaptation is data replacement.

    There is no theta_hat anywhere in this class -- that absence is the point.
    It approximates the boundary non-parametrically, so it can never be compared
    against theta directly (Section 1.1: 'directly or indirectly').
    """
    name = "buffer-knn"

    def __init__(self, d, w=100, k=10):
        self.w, self.k, self.buf = w, k, []

    def theta_hat(self):      return None            # no parameters. ever.

    def predict(self, x):
        if not self.buf: return 0.5
        ds = sorted(((sum((a-b)**2 for a, b in zip(x, xi)), yi) for xi, yi in self.buf),
                    key=lambda p: p[0])[:self.k]
        return sum(y for _, y in ds) / len(ds)

    def update(self, x, y):
        self.buf.append((list(x), y))
        if len(self.buf) > self.w:
            self.buf.pop(0)                          # natural forgetting
