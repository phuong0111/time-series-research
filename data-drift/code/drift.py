"""Drift generators — the four drift types of Read (2018) §3, in parameter space.

Every type is expressed as a trajectory of theta_t through concept space Theta.
That reframing is the paper's contribution; this module is it, executable.

    theta_t in Theta     true (unknown) parameters of the concept at time t
    tau                  change point;  tau1..tau2 for extended drift
    C_t                  latent concept indicator
    alpha_t              mixing weight (gradual drift only)
"""
import math, random


def rotation(angle):
    """A_angle, the rotation matrix used for incremental drift in Read §6."""
    c, s = math.cos(angle), math.sin(angle)
    return ((c, -s), (s, c))


def apply_T(A, v):
    """A^T @ v  (the paper writes theta_t = A^T theta_{t-1})."""
    return [A[0][0]*v[0] + A[1][0]*v[1], A[0][1]*v[0] + A[1][1]*v[1]]


class Drift:
    """Base: a drift is a rule mapping t -> (theta_t, C_t)."""
    def theta(self, t):  raise NotImplementedError
    def concept(self, t): raise NotImplementedError
    name = "drift"


class NoDrift(Drift):
    """Stationary stream. The i.i.d. assumption actually holds here."""
    name = "stationary"
    def __init__(self, theta0):        self.th = list(theta0)
    def theta(self, t):                return list(self.th)
    def concept(self, t):              return 0


class SuddenDrift(Drift):
    """Eq.(3): theta_t = theta_c1 for t < tau, theta_c2 for t >= tau.

    total=True  -> the two concepts are unrelated draws from Theta
    total=False -> partial drift: only some components change (transfer is possible)
    """
    name = "sudden"
    def __init__(self, theta_c1, theta_c2, tau):
        self.a, self.b, self.tau = list(theta_c1), list(theta_c2), tau
    def theta(self, t):                return list(self.a if t < self.tau else self.b)
    def concept(self, t):              return 0 if t < self.tau else 1


class IncrementalDrift(Drift):
    """Eq.(4): theta_t = theta_{t-1} + Delta_t theta, active on tau1..tau2.

    Realised as a rotation, exactly as Read §6 does it. Intermediate states are
    REAL concepts -- this is what separates incremental from gradual drift.
    """
    name = "incremental"
    def __init__(self, theta0, angle, tau1, tau2):
        self.th0, self.A, self.t1, self.t2 = list(theta0), rotation(angle), tau1, tau2
        self._cache = [list(theta0)]          # trajectory memo: index = steps taken
    def theta(self, t):
        steps = max(0, min(t, self.t2) - self.t1)
        while len(self._cache) <= steps:      # extend the path only as far as asked
            self._cache.append(apply_T(self.A, self._cache[-1]))
        return list(self._cache[steps])
    def concept(self, t):
        return 0 if t < self.t1 else (1 if t >= self.t2 else -1)   # -1 = mid-drift


class GradualDrift(Drift):
    """Eq.(5): theta_t = theta_{c_t}, c_t ~ B(alpha_t), alpha_t ramps 0 -> 1.

    NOTE the asymmetry the paper flags and then defers: here it is alpha_t, not
    theta_t, that forms the time series. theta_t only ever takes two values.
    """
    name = "gradual"
    def __init__(self, theta_c1, theta_c2, tau1, tau2, rng=None):
        self.a, self.b, self.t1, self.t2 = list(theta_c1), list(theta_c2), tau1, tau2
        self.rng = rng or random.Random(0)
    def alpha(self, t):
        if t <= self.t1: return 0.0
        if t >= self.t2: return 1.0
        return (t - self.t1) / (self.t2 - self.t1)
    def theta(self, t):
        return list(self.b if self.rng.random() < self.alpha(t) else self.a)
    def concept(self, t):
        return 0 if t <= self.t1 else (1 if t >= self.t2 else -1)


class ReoccurringDrift(Drift):
    """Section 3.4: concepts repeat. Formally identical to a switching state-space
    model -- 'there is no technical difference between modelling states, and
    tracking concepts'."""
    name = "reoccurring"
    def __init__(self, concepts, period):
        self.cs, self.p = [list(c) for c in concepts], period
    def theta(self, t):                return list(self.cs[(t // self.p) % len(self.cs)])
    def concept(self, t):              return (t // self.p) % len(self.cs)


# ---------------------------------------------------------------------------

def sigmoid(z):
    if z < -60: return 0.0
    if z >  60: return 1.0
    return 1.0 / (1.0 + math.exp(-z))


def dot(a, b): return sum(i*j for i, j in zip(a, b))


class Stream:
    """A prequential data stream:  (x_t, y_t) ~ p_t(X, Y),  y_t = f(x_t; theta_c) + eps_t

    Yields (t, x_t, y_t, theta_t, C_t) so an experiment can compare a learner's
    theta_hat against the ground-truth theta_t -- something no real deployment
    can do, but which is exactly what Read's Section 4 bias analysis needs.
    """
    def __init__(self, drift, d=2, sigma=0.30, seed=0):
        self.drift, self.d, self.sigma = drift, d, sigma
        self.rng = random.Random(seed)

    def __iter__(self):
        t = 1
        while True:
            th  = self.drift.theta(t)
            x   = [self.rng.gauss(0, 1) for _ in range(self.d)]
            f   = sigmoid(dot(th, x))                    # f(x_t ; theta_c)
            eps = self.rng.gauss(0, self.sigma)          # eps_t ~ N(0, sigma^2)
            y   = 1 if f + eps > 0.5 else 0              # y_t
            yield t, x, y, th, self.drift.concept(t)
            t += 1

    def take(self, n):
        out = []
        for row in self:
            out.append(row)
            if len(out) >= n: break
        return out
