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
    c, s = math.cos(angle), math.sin(angle)   # cos/sin of the per-step rotation
    return ((c, -s), (s, c))                  # standard 2x2 CCW rotation matrix


def apply_T(A, v):
    """A^T @ v  (the paper writes theta_t = A^T theta_{t-1})."""
    # Row i of A^T is column i of A, hence the transposed index order A[k][i].
    return [A[0][0]*v[0] + A[1][0]*v[1],      # (A^T v)_0 = A_00 v_0 + A_10 v_1
            A[0][1]*v[0] + A[1][1]*v[1]]      # (A^T v)_1 = A_01 v_0 + A_11 v_1


class Drift:
    """Base: a drift is a rule mapping t -> (theta_t, C_t)."""
    def theta(self, t):  raise NotImplementedError   # theta_t, the true parameters
    def concept(self, t): raise NotImplementedError  # C_t, the latent concept id
    name = "drift"


class NoDrift(Drift):
    """Stationary stream. The i.i.d. assumption actually holds here."""
    name = "stationary"
    def __init__(self, theta0):
        self.th = list(theta0)                # copy: callers must not alias our state
    def theta(self, t):
        return list(self.th)                  # theta_t = theta_0 for every t
    def concept(self, t):
        return 0                              # C_t = 0 always; one concept, forever


class SuddenDrift(Drift):
    """Eq.(3): theta_t = theta_c1 for t < tau, theta_c2 for t >= tau.

    total=True  -> the two concepts are unrelated draws from Theta
    total=False -> partial drift: only some components change (transfer is possible)
    """
    name = "sudden"
    def __init__(self, theta_c1, theta_c2, tau):
        self.a = list(theta_c1)               # theta_c1, the pre-drift concept
        self.b = list(theta_c2)               # theta_c2, the post-drift concept
        self.tau = tau                        # tau, the single change point
    def theta(self, t):
        # A step function of t: no intermediate states exist at all.
        return list(self.a if t < self.tau else self.b)
    def concept(self, t):
        return 0 if t < self.tau else 1       # C_t flips exactly once, at tau


class IncrementalDrift(Drift):
    """Eq.(4): theta_t = theta_{t-1} + Delta_t theta, active on tau1..tau2.

    Realised as a rotation, exactly as Read §6 does it. Intermediate states are
    REAL concepts -- this is what separates incremental from gradual drift.
    """
    name = "incremental"
    def __init__(self, theta0, angle, tau1, tau2):
        self.th0 = list(theta0)               # theta_0, the starting concept
        self.A   = rotation(angle)            # A_angle; Delta_t theta = (A^T - I) theta_t
        self.t1, self.t2 = tau1, tau2         # tau1..tau2, the window drift is active in
        self._cache = [list(theta0)]          # trajectory memo: index = steps taken
    def theta(self, t):
        # How many rotations have been applied by time t: 0 before tau1, then
        # one per step, frozen once t passes tau2.
        steps = max(0, min(t, self.t2) - self.t1)
        while len(self._cache) <= steps:      # extend the path only as far as asked
            # Each entry is one more A^T applied -- O(1) amortised per new step.
            self._cache.append(apply_T(self.A, self._cache[-1]))
        return list(self._cache[steps])       # theta_t = (A^T)^steps theta_0
    def concept(self, t):
        return 0 if t < self.t1 else (1 if t >= self.t2 else -1)   # -1 = mid-drift


class GradualDrift(Drift):
    """Eq.(5): theta_t = theta_{c_t}, c_t ~ B(alpha_t), alpha_t ramps 0 -> 1.

    NOTE the asymmetry the paper flags and then defers: here it is alpha_t, not
    theta_t, that forms the time series. theta_t only ever takes two values.
    """
    name = "gradual"
    def __init__(self, theta_c1, theta_c2, tau1, tau2, rng=None):
        self.a = list(theta_c1)               # theta_c1, the concept being left
        self.b = list(theta_c2)               # theta_c2, the concept being entered
        self.t1, self.t2 = tau1, tau2         # tau1..tau2, the span alpha_t ramps over
        self.rng = rng or random.Random(0)    # own RNG: the Bernoulli draws for c_t
    def alpha(self, t):
        if t <= self.t1: return 0.0           # before tau1: always the old concept
        if t >= self.t2: return 1.0           # after tau2: always the new concept
        return (t - self.t1) / (self.t2 - self.t1)   # alpha_t, a linear ramp 0 -> 1
    def theta(self, t):
        # c_t ~ B(alpha_t): a coin flip per instance, so theta_t TELEPORTS between
        # two fixed points rather than travelling between them.
        return list(self.b if self.rng.random() < self.alpha(t) else self.a)
    def concept(self, t):
        return 0 if t <= self.t1 else (1 if t >= self.t2 else -1)  # -1 = mixing


class ReoccurringDrift(Drift):
    """Section 3.4: concepts repeat. Formally identical to a switching state-space
    model -- 'there is no technical difference between modelling states, and
    tracking concepts'."""
    name = "reoccurring"
    def __init__(self, concepts, period):
        self.cs = [list(c) for c in concepts] # the finite set of concepts cycled through
        self.p  = period                      # dwell time in each concept before switching
    def theta(self, t):
        # Integer division picks the block, modulo wraps it into a cycle.
        return list(self.cs[(t // self.p) % len(self.cs)])
    def concept(self, t):
        return (t // self.p) % len(self.cs)   # C_t is periodic with period p*|C|


# ---------------------------------------------------------------------------

def sigmoid(z):
    if z < -60: return 0.0                    # clamp: exp(60) overflows to inf
    if z >  60: return 1.0                    # clamp: exp(-60) underflows to 0
    return 1.0 / (1.0 + math.exp(-z))         # sigma(z), the logistic link


def dot(a, b):
    return sum(i*j for i, j in zip(a, b))     # a . b, the plain inner product


class Stream:
    """A prequential data stream:  (x_t, y_t) ~ p_t(X, Y),  y_t = f(x_t; theta_c) + eps_t

    Yields (t, x_t, y_t, theta_t, C_t) so an experiment can compare a learner's
    theta_hat against the ground-truth theta_t -- something no real deployment
    can do, but which is exactly what Read's Section 4 bias analysis needs.
    """
    def __init__(self, drift, d=2, sigma=0.30, seed=0):
        self.drift = drift                    # the theta_t trajectory to sample along
        self.d     = d                        # d, the dimension of Theta and of X
        self.sigma = sigma                    # sigma, std of the irreducible noise eps_t
        self.rng   = random.Random(seed)      # draws BOTH x_t and eps_t, in that order

    def __iter__(self):
        t = 1                                 # the paper indexes instances from 1
        while True:                           # unbounded: callers decide where to stop
            th  = self.drift.theta(t)                    # theta_t, the concept RIGHT NOW
            x   = [self.rng.gauss(0, 1) for _ in range(self.d)]   # x_t ~ N(0, I_d)
            f   = sigmoid(dot(th, x))                    # f(x_t ; theta_c), true P(y=1)
            eps = self.rng.gauss(0, self.sigma)          # eps_t ~ N(0, sigma^2)
            # NOTE: eps is added in PROBABILITY space, after the squashing. Since
            # sigmoid'(0) = 1/4 compresses the margin 4x, the resulting label-noise
            # floor is (1/pi)*arctan(4*sigma/||theta||) -- ~12.6% at sigma=0.10.
            y   = 1 if f + eps > 0.5 else 0              # y_t, the label that arrives
            yield t, x, y, th, self.drift.concept(t)     # test-then-train tuple
            t += 1                                       # advance the stream clock

    def take(self, n):
        out = []
        for row in self:                      # pull from the infinite generator
            out.append(row)
            if len(out) >= n: break           # stop at n: O(n*d) memory, fine for T=4000
        return out
