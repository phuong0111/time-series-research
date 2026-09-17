"""The paper's own synthetic streams: Read (2018) section 6, Table 1.

    "First, we generated synthetic data using a weight matrix theta_c ~ N(0, I)
     to represent the c-th concept. We introduced drift using the equations
     Eq. (3), Eq. (4), Eq. (5), under parameters in Table 1. For incremental
     drift, theta_t = A^T_0.01 theta_{t-1} = theta_{t-1} + Delta_t theta, where
     A_0.01 is a rotational matrix (of angle 0.01 in radians); for gradual drift,
     alpha_t = (t - tau_1)/(tau_2 - tau_1). And, for sudden drift a new
     theta_t ~ Theta is simply resampled after timestep tau_1."

Table 1, reproduced exactly:

    tau_0   T/10        pre-training ends
    tau_1   5K          start of drift
    tau_2   6K          end of drift (gradual, incremental)
    tau_2   tau_1 + 1   end of drift (sudden)
    T       10K         length of stream

    "In all experiments, accuracy is recorded over instances tau_0, ..., T."

WHAT THE PAPER DOES NOT SPECIFY, and what we chose:
  * the input dimension. Figure 4 is plotted in 2-D; Table 3's Synthetic row does
    not say. Default d=2, so the stream is the one Figure 4 actually shows.
  * the distribution of x_t. theta_c ~ N(0, I) is stated, x_t is not. We use
    x_t ~ N(0, I), which makes theta^T x symmetric about 0 and the classes
    balanced.
  * any label noise. None is mentioned, so the default is none: the label is the
    deterministic side of the hyperplane. `sigma` adds Bernoulli label flips if
    you want to test robustness, but sigma=0 is what reproduces the paper.
  * how A_0.01 generalises past 2-D. We use a Givens rotation in the (0,1) plane,
    which reduces to the paper's 2x2 matrix exactly when d=2.

The stream yields (t, x_t, y_t, theta_t, C_t), including the ground-truth theta_t
that no real deployment can observe -- which is exactly what the Section 4 bias
analysis needs, and what data.py cannot provide for Electricity or CoverType.
"""
import math, random

# Table 1, as module constants so no experiment can drift from them silently.
T_DEFAULT   = 10000
TAU0        = T_DEFAULT // 10     # 1000 -- pre-training ends; accuracy starts here
TAU1        = 5000                # start of drift
TAU2        = 6000                # end of drift (gradual, incremental)
ANGLE       = 0.01                # radians per step, the A_0.01 of section 6


def rotation(angle, d=2, plane=(0, 1)):
    """A_angle as a d x d Givens rotation in the given coordinate plane.

    At d=2 this IS the paper's 2x2 matrix [[cos,-sin],[sin,cos]]; at higher d it
    rotates the chosen plane and leaves the remaining axes fixed, which keeps
    ||theta|| constant exactly as a 2-D rotation does.
    """
    A = [[1.0 if i == j else 0.0 for j in range(d)] for i in range(d)]
    i, j = plane
    c, s = math.cos(angle), math.sin(angle)
    A[i][i], A[i][j] = c, -s
    A[j][i], A[j][j] = s,  c
    return A


def apply_T(A, v):
    """A^T v -- the paper writes theta_t = A^T theta_{t-1}."""
    d = len(v)
    # Row i of A^T is column i of A, hence the transposed index order A[k][i].
    return [sum(A[k][i]*v[k] for k in range(d)) for i in range(d)]


def sample_theta(d, rng):
    """theta_c ~ N(0, I), the paper's concept prior."""
    return [rng.gauss(0.0, 1.0) for _ in range(d)]


# ---------------------------------------------------------------------------
# The four drift types, as trajectories of theta through concept space Theta
# ---------------------------------------------------------------------------

class Drift:
    name = "drift"
    def theta(self, t):   raise NotImplementedError   # theta_t, the true parameters
    def concept(self, t): raise NotImplementedError   # C_t, the latent concept id


class NoDrift(Drift):
    """Stationary. The i.i.d. assumption the stream literature makes actually holds."""
    name = "stationary"
    def __init__(self, d, rng):
        self.th = sample_theta(d, rng)
    def theta(self, t):   return list(self.th)        # theta_t = theta_0 for every t
    def concept(self, t): return 0                    # one concept, forever


class SuddenDrift(Drift):
    """Eq. (3). "a new theta_t ~ Theta is simply resampled after timestep tau_1".

    Note what resampling from the PRIOR means: the two concepts are unrelated
    draws, so nothing transfers. Section 5 flags this as the one case where the
    detect-and-reset argument is actually sound -- "this argument can be clearly
    accepted only under the condition of a complete change in concept".
    """
    name = "sudden"
    def __init__(self, d, rng, tau1=TAU1):
        self.a = sample_theta(d, rng)                 # theta_c1
        self.b = sample_theta(d, rng)                 # theta_c2, an INDEPENDENT draw
        self.tau1 = tau1
    def theta(self, t):   return list(self.a if t < self.tau1 else self.b)
    def concept(self, t): return 0 if t < self.tau1 else 1


class IncrementalDrift(Drift):
    """Eq. (4). theta_t = A^T_0.01 theta_{t-1}, active over tau_1 .. tau_2.

    The intermediate states are REAL concepts -- that is what separates
    incremental from gradual drift, where theta only ever takes two values.
    """
    name = "incremental"
    def __init__(self, d, rng, tau1=TAU1, tau2=TAU2, angle=ANGLE):
        self.th0 = sample_theta(d, rng)
        self.A = rotation(angle, d)
        self.t1, self.t2 = tau1, tau2
        self._cache = [list(self.th0)]                # trajectory memo, index = steps
    def theta(self, t):
        steps = max(0, min(t, self.t2) - self.t1)     # 0 before tau1, frozen after tau2
        while len(self._cache) <= steps:
            self._cache.append(apply_T(self.A, self._cache[-1]))   # O(1) amortised
        return list(self._cache[steps])
    def concept(self, t):
        return 0 if t < self.t1 else (1 if t >= self.t2 else -1)   # -1 = mid-drift


class GradualDrift(Drift):
    """Eq. (5). c_t ~ B(alpha_t), alpha_t = (t - tau_1)/(tau_2 - tau_1).

    The asymmetry the paper flags and then defers: here it is alpha_t, not
    theta_t, that forms the time series. theta_t TELEPORTS between two fixed
    points rather than travelling between them, so there is no trajectory to
    track -- which is why section 6 says "a detailed treatment is left for
    future work".
    """
    name = "gradual"
    def __init__(self, d, rng, tau1=TAU1, tau2=TAU2):
        self.a = sample_theta(d, rng)
        self.b = sample_theta(d, rng)
        self.t1, self.t2 = tau1, tau2
        self.rng = rng                                # the Bernoulli draws for c_t
    def alpha(self, t):
        if t <= self.t1: return 0.0
        if t >= self.t2: return 1.0
        return (t - self.t1) / (self.t2 - self.t1)    # the linear ramp of Eq. (5)
    def theta(self, t):
        return list(self.b if self.rng.random() < self.alpha(t) else self.a)
    def concept(self, t):
        return 0 if t <= self.t1 else (1 if t >= self.t2 else -1)


class SustainedDrift(IncrementalDrift):
    """Figure 6: "drift is constant across the entire stream (tau_1 = tau_0,
    tau_2 = T wrt Table 1)".

    This is the paper's hardest scenario and the one its whole argument turns on:
    under drift that never stops, there is no post-drift concept to converge to,
    so a detector fires forever and a reset never pays for itself.
    """
    name = "sustained"
    def __init__(self, d, rng, tau0=TAU0, T=T_DEFAULT, angle=ANGLE):
        super().__init__(d, rng, tau1=tau0, tau2=T, angle=angle)


# ---------------------------------------------------------------------------

class Stream:
    """Prequential hyperplane stream:  y_t = 1[ theta_t . x_t > 0 ],  x_t ~ N(0, I).

    Figure 4's caption: "the true concept is represented as a decision boundary
    theta^T x = 0 (shown in green) which is rotating clockwise".
    """

    def __init__(self, drift, d=2, seed=0, sigma=0.0, T=T_DEFAULT, tau0=TAU0):
        self.drift, self.d = drift, d
        self.rng   = random.Random(seed)   # draws x_t, and the label flip if sigma>0
        self.sigma = sigma                 # P(label flip); 0 reproduces the paper
        self.T, self.tau0 = T, tau0        # tau0 is where accuracy starts being recorded

    def __iter__(self):
        t = 1                              # the paper indexes instances from 1
        while True:
            th = self.drift.theta(t)                           # theta_t, right now
            x  = [self.rng.gauss(0.0, 1.0) for _ in range(self.d)]
            y  = 1 if sum(a*b for a, b in zip(th, x)) > 0 else 0   # the hyperplane
            if self.sigma and self.rng.random() < self.sigma:
                y = 1 - y                                      # optional label noise
            yield t, x, y, th, self.drift.concept(t)
            t += 1

    def take(self, n):
        out = []
        for row in self:
            out.append(row)
            if len(out) >= n: break
        return out


def scenarios(d=2, seed=0, T=T_DEFAULT):
    """The paper's five synthetic streams, all at Table 1's parameters."""
    rng = random.Random(seed)              # one RNG so the concepts differ per seed
    return {
        "stationary":  NoDrift(d, rng),
        "sudden":      SuddenDrift(d, rng),          # tau_2 = tau_1 + 1, i.e. a step
        "incremental": IncrementalDrift(d, rng),     # tau_1=5K .. tau_2=6K
        "gradual":     GradualDrift(d, rng),         # alpha_t ramps over the same span
        "sustained":   SustainedDrift(d, rng, T=T),  # Figure 6: tau_1=tau_0, tau_2=T
    }


# ---------------------------------------------------------------------------
# RTG -- the Random Tree Generator of Table 3's second row
# ---------------------------------------------------------------------------

class RandomTreeGenerator:
    """Domingos & Hulten (2000)'s random tree stream, at scikit-multiflow defaults.

    Table 2 says "values for any parameters not shown can be found as the default
    parameters in ScikitMultiflow (v0.1.0 used here)", so those defaults are what
    is used: 5 numeric + 5 categorical attributes (5 levels each), max depth 5,
    min leaf depth 3, 0.15 chance of a node becoming a leaf per level past the
    minimum, 2 classes.

    A random tree is built once, then instances are sampled uniformly and labelled
    by routing them down it. There is NO drift in this stream -- it is in the
    paper as a hard stationary problem with a non-linear boundary, which is what
    makes it the row where a linear SGD should struggle and a tree should not.
    """
    name = "RTG"

    def __init__(self, n_num=5, n_cat=5, n_cat_levels=5, max_depth=5,
                 min_leaf_depth=3, frac_leaves=0.15, n_classes=2, seed=0):
        self.n_num, self.n_cat = n_num, n_cat
        self.n_cat_levels, self.n_classes = n_cat_levels, n_classes
        self.rng = random.Random(seed)
        self.tree = self._build(0, max_depth, min_leaf_depth, frac_leaves)
        # One-hot for the categoricals, raw value for the numerics.
        self.d = n_num + n_cat * n_cat_levels

    def _build(self, depth, max_depth, min_leaf_depth, frac_leaves):
        # A node becomes a leaf at max depth, or probabilistically once past the
        # minimum leaf depth -- this is what gives the tree ragged, uneven branches.
        if depth >= max_depth or (depth >= min_leaf_depth
                                  and self.rng.random() < frac_leaves):
            return ("leaf", self.rng.randrange(self.n_classes))
        a = self.rng.randrange(self.n_num + self.n_cat)
        if a < self.n_num:
            # Numeric test: split at a uniform point in [0,1).
            return ("num", a, self.rng.random(),
                    self._build(depth+1, max_depth, min_leaf_depth, frac_leaves),
                    self._build(depth+1, max_depth, min_leaf_depth, frac_leaves))
        # Categorical test: one child per level.
        return ("cat", a - self.n_num,
                [self._build(depth+1, max_depth, min_leaf_depth, frac_leaves)
                 for _ in range(self.n_cat_levels)])

    def _label(self, nums, cats, node):
        while node[0] != "leaf":
            if node[0] == "num":
                node = node[3] if nums[node[1]] < node[2] else node[4]
            else:
                node = node[2][cats[node[1]]]
        return node[1]

    def __iter__(self):
        t = 1
        while True:
            nums = [self.rng.random() for _ in range(self.n_num)]
            cats = [self.rng.randrange(self.n_cat_levels) for _ in range(self.n_cat)]
            y = self._label(nums, cats, self.tree)
            # Flatten to a feature vector the linear methods can consume: numerics
            # as-is, categoricals one-hot (an ordinal encoding would invent an
            # ordering the generator never had).
            x = list(nums)
            for c in cats:
                oh = [0.0]*self.n_cat_levels
                oh[c] = 1.0
                x.extend(oh)
            yield t, x, y, None, None      # no theta: the concept is a TREE, not a vector
            t += 1

    def take(self, n):
        out = []
        for row in self:
            out.append(row)
            if len(out) >= n: break
        return out
