"""Table 2 of Read (2018), implemented. Pure stdlib, no scikit-multiflow.

    Vanilla     kNN        k = 10, buffer size 100
                SGD        L2 regularization; lambda = 0.01, hinge loss
                HT         10^-7 split confidence, 0.05 tie threshold,
                           naive Bayes at leaves
    Advanced    SAMkNN     self-adjusting memory kNN [Losing et al. 2016]
                PBF-SGD    SGD with degree-3 polynomial basis expansion
                RF-HT      Adaptive Random Forest [Gomes et al. 2017]:
                           100 HTs, ADWIN drift detection, lambda = 6, n_min = 50

Each method is reproduced as its OWN paper specifies, so the numbers can be put
beside Read's Table 3 directly.

Interface:  predict(x) -> P(y=1),  update(x, y),  theta_hat() -> list or None.

theta_hat() is the load-bearing one. It returns a parameter vector for the methods
whose model IS a vector (SGD, PBF-SGD) and None for the methods whose model is a
structure or a buffer (HT, RF-HT, kNN, SAMkNN). That is not an implementation
detail: it is the paper's structural claim about what "adapt" can physically mean.
A tree has no Delta-theta, so there is nothing for theta_hat() to return.

Binary throughout, because data.py binarises CoverType one-vs-rest; the paper
classifies all 7 classes there, so CoverType numbers are not comparable to its
Table 3. Electricity is natively binary and IS comparable.
"""
import heapq, math, random
from collections import deque
from itertools import islice


def dot(a, b):
    return sum(i*j for i, j in zip(a, b))       # a . b, the plain inner product


def sigmoid(z):
    if z < -60: return 0.0                      # clamp: exp(60) overflows to inf
    if z >  60: return 1.0                      # clamp: exp(-60) underflows to 0
    return 1.0 / (1.0 + math.exp(-z))           # sigma(z), the logistic link


# =========================================================================
# kNN -- the paper's vanilla configuration: k = 10, buffer size 100
# =========================================================================

class KNN:
    """Table 2 'kNN'.  A sliding buffer of the last w instances, majority of k.

    Mechanism 1 of the paper's three: the model IS the stored data, so adapting
    means REPLACING data. There is no theta_hat() here and no way to move the
    model a little -- the buffer either holds the old concept or it does not.
    Section 7's observation follows directly: "predictive power is always limited
    in proportion to the number of instances stored in this buffer".
    """
    name = "kNN"

    def __init__(self, d, w=100, k=10):
        self.w, self.k, self.buf = w, k, []     # w = window, k = neighbours, buf = model

    def theta_hat(self):
        return None                             # no parameters. ever.

    def predict(self, x):
        if not self.buf: return 0.5             # cold start: abstain at exactly 0.5
        # Squared distance is monotone in true distance, so the sqrt is skipped.
        # nsmallest is O(w log k) rather than sorted()'s O(w log w), matching the
        # paper's O(wdk) claim in Table 4 more closely.
        ds = heapq.nsmallest(self.k,
                             ((sum((a-b)**2 for a, b in zip(x, xi)), yi)
                              for xi, yi in self.buf),
                             key=lambda p: p[0])
        return sum(y for _, y in ds) / len(ds)  # vote, as a fraction in [0,1]

    def update(self, x, y):
        self.buf.append((list(x), y))           # the update IS storing the instance
        if len(self.buf) > self.w:
            self.buf.pop(0)                     # natural forgetting: drop the oldest


# =========================================================================
# SGD -- the paper's vanilla configuration: hinge loss + L2
# =========================================================================

class HingeSGD:
    """Linear SVM by SGD.  L2-regularised hinge loss, the Table 2 'SGD' row.

    Table 2 specifies hinge loss, not the log loss a logistic model would use.
    The difference is where the gradient is zero:

        L(theta; x, y) = max(0, 1 - y' (theta . x)) + (alpha/2) ||theta||^2

    with y' in {-1, +1}. The subgradient is -y' x inside the margin and 0 outside,
    so the update only fires on margin violations -- unlike log loss, which pushes
    on every single instance. That sparsity is the practical difference.
    """
    name = "SGD"

    def __init__(self, d, lam=0.01, alpha=1e-4, decay=False):
        self.th    = [0.0]*d      # theta_hat; no separate bias -- data.py appends a 1.0
        self.lam0  = lam          # lambda_0, kept so decay divides the ORIGINAL
        self.lam   = lam          # lambda, the learning rate in force right now
        self.decay = decay        # section 5's forbidden schedule; see update()
        self.t     = 0            # update counter, so the decay is monotone
        self.alpha = alpha        # L2 strength. Table 2 says "L2 regularization" but
                                  # gives no value; scikit-multiflow's SGDClassifier
                                  # default alpha=1e-4 is used, and is recorded here
                                  # rather than silently chosen.

    def decision(self, x):
        return dot(self.th, x)                  # the raw margin theta . x

    def predict(self, x):
        # The interface is a probability, but hinge loss fits a margin, not a
        # likelihood. sigmoid() maps the margin monotonically into (0,1), so the
        # 0/1 decision at 0.5 is EXACTLY sign(margin) -- accuracy is unaffected,
        # and only probability calibration (which nothing here measures) is.
        return sigmoid(self.decision(x))

    def theta_hat(self):
        return list(self.th)

    def update(self, x, y):
        self.t += 1
        if self.decay:
            # lambda_t = lambda_0 / sqrt(t), the standard online-convex-optimisation
            # schedule behind O(sqrt(T)) regret bounds. Section 5 names exactly this
            # as the thing not to do on a stream: "to not decay the learning rate
            # lambda towards zero over time ... under a stream this would cause SGD
            # to react more and more slowly to concept drift until eventually
            # becoming stuck in one concept."
            #
            # It is NOT Robbins-Monro, which additionally needs sum(lambda_t^2) to
            # converge -- sum(1/t) diverges.
            self.lam = self.lam0 / math.sqrt(self.t)
        yp = 1.0 if y == 1 else -1.0            # y' in {-1,+1}, as hinge loss needs
        m  = yp * self.decision(x)              # the functional margin
        for i in range(len(self.th)):
            # L2 shrinkage applies EVERY step (it is part of the objective, not of
            # the loss term), the hinge gradient only when the margin is violated.
            g = self.alpha * self.th[i] - (yp * x[i] if m < 1 else 0.0)
            self.th[i] -= self.lam * g


def poly_basis(x, degree=3):
    """Degree-d polynomial basis expansion, the 'PBF' of PBF-SGD.

    Returns all monomials of total degree 1..degree over the raw features, in a
    fixed canonical order (combinations_with_replacement, ascending degree). No
    constant term is emitted: data.py already appends the bias unit, and emitting
    both would give the model two collinear intercepts.

    Size is C(d+k-1, k) summed over k=1..degree -- for Electricity's d=8 that is
    8 + 36 + 120 = 164 features, which is why PBF-SGD costs what Table 5 says.
    """
    from itertools import combinations_with_replacement
    out = []
    n = len(x)
    for k in range(1, degree + 1):
        for combo in combinations_with_replacement(range(n), k):
            p = 1.0
            for i in combo: p *= x[i]           # the monomial x_i1 * x_i2 * ...
            out.append(p)
    return out


class PBFSGD:
    """Table 2 'PBF-SGD': the same SGD, on a degree-3 polynomial basis.

    This is the paper's headline continuous-adaptation method -- the one that
    reaches 85.9 on Electricity without any drift detector at all. The point it
    makes is that a LINEAR model in an expanded basis is still a model whose
    parameters live in a continuous Theta, so it can still be tracked.
    """
    name = "PBF-SGD"

    def __init__(self, d, degree=3, lam=0.01, alpha=1e-4):
        self.degree = degree
        # The expanded dimension is computed by expanding a dummy vector once,
        # rather than by a binomial formula -- one fewer thing to get wrong.
        self.sgd = HingeSGD(len(poly_basis([0.0]*d, degree)), lam=lam, alpha=alpha)

    def _phi(self, x):
        return poly_basis(x, self.degree)       # phi(x), the expanded feature vector

    def predict(self, x):
        return self.sgd.predict(self._phi(x))

    def theta_hat(self):
        return self.sgd.theta_hat()             # lives in the EXPANDED Theta

    def update(self, x, y):
        self.sgd.update(self._phi(x), y)


# =========================================================================
# Hoeffding Tree -- Domingos & Hulten (2000), as parameterised in Table 2
# =========================================================================

class GaussianEstimator:
    """Per-(attribute, class) Gaussian, for numeric split evaluation.

    This is MOA's GaussianNumericAttributeClassObserver: instead of storing every
    observed value, keep a running Normal per class and read off the implied
    counts either side of a candidate threshold v via the normal CDF. That makes
    a split evaluation O(1) in the number of instances seen.
    """
    __slots__ = ("n", "mean", "m2", "lo", "hi")

    def __init__(self):
        self.n, self.mean, self.m2 = 0, 0.0, 0.0    # Welford accumulators
        self.lo, self.hi = None, None                # observed range, for candidates

    def add(self, v):
        self.n += 1
        d = v - self.mean
        self.mean += d / self.n                      # incremental mean
        self.m2   += d * (v - self.mean)             # incremental sum of squares
        self.lo = v if self.lo is None else min(self.lo, v)
        self.hi = v if self.hi is None else max(self.hi, v)

    def std(self):
        # Sample std; floored so a zero-variance attribute cannot divide by zero.
        return math.sqrt(self.m2 / (self.n - 1)) if self.n > 1 else 0.0

    def lt(self, v):
        """Estimated count of observations < v, from the fitted Normal."""
        if self.n == 0: return 0.0
        s = self.std()
        if s <= 0.0:                                  # degenerate: all mass at mean
            return float(self.n) if self.mean < v else 0.0
        # Phi(z) = (1 + erf(z/sqrt2))/2, and math.erf is stdlib.
        z = (v - self.mean) / s
        return self.n * 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def entropy(counts):
    """H(y) in bits, over a dict/list of class counts."""
    tot = sum(counts)
    if tot <= 0: return 0.0
    h = 0.0
    for c in counts:
        if c > 0:
            p = c / tot
            h -= p * math.log2(p)
    return h


class HTLeaf:
    """A leaf: class counts, per-attribute Gaussians, and a naive Bayes predictor."""

    def __init__(self, d, n_classes=2, attrs=None):
        self.d = d
        # attrs = the attribute indices this leaf tracks at all. Everything else
        # is invisible to it -- both for splitting and for naive Bayes. ARF gives
        # each tree a random subspace this way (Gomes et al. 2017 §3); a plain HT
        # passes attrs=None and tracks all d.
        self.attrs = list(range(d)) if attrs is None else list(attrs)
        self.counts = [0]*n_classes             # n_c, the class distribution here
        self.n = 0                              # instances seen since this leaf was made
        # One Gaussian per (tracked attribute, class), indexed positionally against
        # self.attrs rather than against the raw feature index.
        self.est = [[GaussianEstimator() for _ in range(n_classes)]
                    for _ in self.attrs]
        self.last_split_attempt = 0             # for the n_min grace period

    def learn(self, x, y):
        self.counts[y] += 1
        self.n += 1
        for j, i in enumerate(self.attrs):
            self.est[j][y].add(x[i])            # update only the observed class's Gaussian

    def predict(self, x):
        """Naive Bayes at the leaf -- Table 2's 'naive Bayes at leaves'.

        Falls back to the majority class until each class has enough observations
        to have a defined variance (MOA does the same): with n<2 the Gaussian is
        degenerate and NB would be arbitrary.
        """
        tot = sum(self.counts)
        if tot == 0: return 0.5
        if min(self.counts) < 2:                    # not enough to fit both Gaussians
            return self.counts[1] / tot             # majority-class / prior estimate
        logp = []
        for c in range(len(self.counts)):
            # log P(c) + sum_i log P(x_i | c), the naive Bayes score in log space
            # (log space because a product of 54 densities underflows on CoverType).
            lp = math.log(self.counts[c] / tot)
            for j, i in enumerate(self.attrs):
                e = self.est[j][c]
                s = e.std()
                if s <= 0.0: continue               # uninformative attribute: skip
                z = (x[i] - e.mean) / s
                lp += -0.5*z*z - math.log(s * math.sqrt(2*math.pi))
            logp.append(lp)
        m = max(logp)                               # subtract the max before exp:
        ps = [math.exp(l - m) for l in logp]        # standard log-sum-exp guard
        return ps[1] / sum(ps)

    # --- split search ----------------------------------------------------

    def candidates(self, j):
        """Candidate thresholds for numeric attribute i: 10 points across its range.

        MOA's default. Fewer points than the classic 'every observed value' rule,
        which is exactly the trade the Gaussian observer is making -- O(1) memory
        for an approximate split location.
        """
        lo = min((e.lo for e in self.est[j] if e.lo is not None), default=None)
        hi = max((e.hi for e in self.est[j] if e.hi is not None), default=None)
        if lo is None or hi is None or hi <= lo: return []
        step = (hi - lo) / 11.0
        return [lo + step*(k+1) for k in range(10)]

    def best_splits(self):
        """Return (best, second_best, (attr, threshold)) by information gain.

        Gain is measured against the leaf's own entropy, so the returned values
        are directly comparable to the Hoeffding bound epsilon.
        """
        tot = sum(self.counts)
        if tot == 0: return 0.0, 0.0, None
        base = entropy(self.counts)
        best, second, arg = -1.0, -1.0, None
        for j, i in enumerate(self.attrs):
            for v in self.candidates(j):
                # Split the class counts by the Gaussians' implied mass below v.
                left  = [self.est[j][c].lt(v) for c in range(len(self.counts))]
                right = [self.counts[c] - left[c] for c in range(len(self.counts))]
                nl, nr = sum(left), sum(right)
                if nl < 1 or nr < 1: continue       # a split that isolates nothing
                g = base - (nl/tot)*entropy(left) - (nr/tot)*entropy(right)
                if g > best:
                    second, best, arg = best, g, (i, v)
                elif g > second:
                    second = g
        return max(best, 0.0), max(second, 0.0), arg


class HTNode:
    """An internal node: a numeric test x[i] < v, and two children."""
    __slots__ = ("i", "v", "left", "right")

    def __init__(self, i, v, left, right):
        self.i, self.v, self.left, self.right = i, v, left, right


class HoeffdingTree:
    """Table 2 'HT'.  delta = 1e-7 split confidence, tau = 0.05 tie threshold.

    The Hoeffding bound says that after n independent observations of a variable
    in a range of size R, the true mean is within epsilon of the observed mean
    with probability 1 - delta:

        epsilon = sqrt( R^2 ln(1/delta) / (2n) )

    A leaf splits when the best attribute beats the runner-up by more than
    epsilon -- i.e. when the ranking is statistically safe -- or when epsilon has
    fallen below the tie threshold tau, which breaks deadlocks between two
    genuinely equivalent attributes.

    THE POINT FOR THIS REPO: there is no theta_hat() here, and that is not an
    omission. The model is a discrete structure -- a set of nodes and thresholds.
    No Delta-theta exists for it; it can only be grown or destroyed. That is the
    paper's structural claim, and this class is what it is a claim ABOUT.
    """
    name = "HT"

    def __init__(self, d, n_classes=2, delta=1e-7, tau=0.05, n_min=200, attrs=None):
        self.d, self.n_classes = d, n_classes
        self.delta, self.tau, self.n_min = delta, tau, n_min
        self.attrs = attrs                      # None = all d; a list = ARF subspace
        self.root = HTLeaf(d, n_classes, attrs) # a single leaf, until it splits
        self.n_leaves, self.n_splits = 1, 0     # diagnostics: the growth Table 4 discusses

    def theta_hat(self):
        return None                             # no parameters. ever. (see docstring)

    def _leaf(self, x):
        """Route x down to its leaf, following the numeric tests."""
        node = self.root
        while isinstance(node, HTNode):
            node = node.left if x[node.i] < node.v else node.right
        return node

    def predict(self, x):
        return self._leaf(x).predict(x)

    def _hoeffding_bound(self, n):
        # R = log2(k) is the range of the information-gain statistic for k classes.
        R = math.log2(self.n_classes)
        return math.sqrt(R*R * math.log(1.0/self.delta) / (2.0*n))

    def update(self, x, y):
        # Route, then learn at the leaf. Internal nodes hold no statistics -- once
        # a split is made it is never revisited, which is what makes HT fast and
        # also what makes it unable to adapt without an external detector.
        node, parent, went_left = self.root, None, None
        while isinstance(node, HTNode):
            parent, went_left = node, x[node.i] < node.v
            node = node.left if went_left else node.right
        node.learn(x, y)

        # Only attempt a split every n_min instances (the grace period), and only
        # once the leaf is not already pure -- a pure leaf has zero gain available.
        if node.n - node.last_split_attempt < self.n_min: return
        node.last_split_attempt = node.n
        if sum(1 for c in node.counts if c > 0) < 2: return

        best, second, arg = node.best_splits()
        if arg is None: return
        eps = self._hoeffding_bound(node.n)
        # The two firing conditions, exactly as Domingos & Hulten state them.
        if (best - second > eps) or (eps < self.tau):
            i, v = arg
            left  = HTLeaf(self.d, self.n_classes, self.attrs)
            right = HTLeaf(self.d, self.n_classes, self.attrs)
            new = HTNode(i, v, left, right)
            if parent is None:                  # the root leaf is splitting
                self.root = new
            elif went_left:
                parent.left = new
            else:
                parent.right = new
            self.n_splits += 1
            self.n_leaves += 1                  # one leaf replaced by two


# =========================================================================
# ADWIN -- Bifet & Gavalda (2007), the detector RF-HT uses
# =========================================================================

class ADWIN:
    """ADaptive WINdowing: keep a window W, cut it whenever two halves differ.

    The guarantee is what makes it the field's default detector. For every split
    W = W0 . W1 it tests

        |mu_W0 - mu_W1|  >  eps_cut,
        eps_cut = sqrt(2 m sigma^2_W ln(2/delta')) + (2/3) m ln(2/delta'),
        m = 1/(n0 - k + 1) + 1/(n1 - k + 1),   delta' = delta / ln(W)

    and drops the older half when it fires -- so the window length itself is the
    estimate of "how far back the current concept extends". False positives are
    bounded by delta, and the memory is O(log W) rather than O(W) because the
    window is stored as an EXPONENTIAL HISTOGRAM: buckets at row i each summarise
    2^i items, at most M+1 rows deep.

    This is the ADWIN2 variant and follows MOA's parameterisation (M=5, k=5,
    clock=32), which scikit-multiflow copies -- so it is the same detector the
    paper's RF-HT row was produced with.
    """

    def __init__(self, delta=0.002, max_buckets=5, min_win=5, clock=32):
        self.delta = delta          # confidence; MOA's default for ARF's drift level
        self.M     = max_buckets    # max buckets per row before the row is compressed
        self.k     = min_win        # minimum sub-window length either side of a cut
        self.clock = clock          # only test for a cut every `clock` insertions
        self.rows  = []             # rows[i] = list of [size, sum, var] buckets, 2^i each
        self.width = 0              # |W|
        self.total = 0.0            # sum over W
        self.var   = 0.0            # sum of squared deviations over W
        self.t     = 0              # insertions since construction
        self.detected = False       # True on the insertion that fired a cut

    # --- exponential histogram bookkeeping -------------------------------

    @staticmethod
    def _merge(n1, s1, v1, n2, s2, v2):
        """Combine two adjacent summaries into one, exactly (no approximation).

        The cross term n1 n2 (mu1 - mu2)^2 / n is the between-group sum of squares
        -- dropping it is the classic way to get variance bookkeeping wrong.
        """
        n = n1 + n2
        if n == 0: return 0, 0.0, 0.0
        d = (s1/n1 if n1 else 0.0) - (s2/n2 if n2 else 0.0)
        return n, s1 + s2, v1 + v2 + (n1*n2*d*d/n if n1 and n2 else 0.0)

    def _compress(self):
        """Enforce at most M+1 buckets per row, merging the two oldest upward."""
        i = 0
        while i < len(self.rows):
            if len(self.rows[i]) <= self.M + 1:
                break                              # rows above are never fuller
            b1 = self.rows[i].pop(0)               # the two OLDEST at this row
            b2 = self.rows[i].pop(0)
            merged = self._merge(b1[0], b1[1], b1[2], b2[0], b2[1], b2[2])
            if i + 1 == len(self.rows): self.rows.append([])
            self.rows[i+1].append(list(merged))    # one bucket of twice the size
            i += 1

    def _buckets(self):
        """All buckets, oldest first. Row order is oldest-row-last, hence reversed."""
        out = []
        for row in reversed(self.rows):            # bigger buckets are older
            out.extend(row)
        return out

    def _drop_oldest(self):
        """Remove the oldest bucket, correcting the window's total and variance."""
        for row in reversed(self.rows):
            if row:
                n, s, v = row.pop(0)
                nr = self.width - n                # what remains after the drop
                if nr > 0:
                    mu_d = s / n
                    mu_r = (self.total - s) / nr
                    self.var -= v + n*nr*(mu_d - mu_r)**2 / self.width
                else:
                    self.var = 0.0
                self.total -= s
                self.width  = nr
                if self.var < 0: self.var = 0.0    # guard against float drift
                return True
        return False

    # --- the test --------------------------------------------------------

    def add(self, value):
        """Insert one observation (here: 0/1 correctness). Returns True on drift."""
        self.detected = False
        # Window mean/variance, updated incrementally BEFORE the bucket insert.
        if self.width > 0:
            d = value - self.total/self.width
            self.var += d*d*self.width/(self.width + 1)
        self.total += value
        self.width += 1
        if not self.rows: self.rows.append([])
        self.rows[0].append([1, float(value), 0.0])   # a fresh size-1 bucket
        self._compress()
        self.t += 1
        if self.t % self.clock == 0 and self.width >= 2*self.k:
            self.detected = self._check()
        return self.detected

    def _check(self):
        """Scan every cut point; drop the oldest bucket while any cut fires."""
        fired = False
        shrunk = True
        while shrunk and self.width >= 2*self.k:
            shrunk = False
            n0, u0 = 0, 0.0
            bs = self._buckets()
            for b in bs[:-1]:                      # the newest bucket cannot be W0
                n0 += b[0]; u0 += b[1]
                n1, u1 = self.width - n0, self.total - u0
                if n0 < self.k or n1 < self.k: continue
                if abs(u0/n0 - u1/n1) > self._eps(n0, n1):
                    fired = True
                    if self._drop_oldest(): shrunk = True
                    break                          # recompute buckets after a drop
        return fired

    def _eps(self, n0, n1):
        m  = 1.0/(n0 - self.k + 1) + 1.0/(n1 - self.k + 1)
        dd = math.log(2.0*math.log(max(self.width, 2))/self.delta)   # delta' = delta/ln W
        v  = self.var/self.width                                     # sigma^2_W
        return math.sqrt(2.0*m*v*dd) + (2.0/3.0)*dd*m

    def reset(self):
        self.__init__(self.delta, self.M, self.k, self.clock)


# =========================================================================
# RF-HT -- Adaptive Random Forest, Gomes et al. (2017)
# =========================================================================

def _poisson(lam, rng):
    """Knuth's algorithm. ARF's online bagging draws k ~ Poisson(lambda=6)."""
    L, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= rng.random()
        if p <= L: return k
        k += 1
        if k > 1000: return k       # lambda=6 never gets near this; guard only


class AdaptiveRandomForest:
    """Table 2 'RF-HT': 100 Hoeffding trees, ADWIN, lambda = 6, n_min = 50.

    Three things distinguish it from plain bagged trees, all of them in
    Gomes et al. 2017 section 3:

      1. RANDOM SUBSPACE. Each tree considers only m = floor(sqrt(d)) + 1
         attributes, redrawn per tree, which is what decorrelates them.
      2. ONLINE BAGGING. Each instance is presented k ~ Poisson(6) times to each
         tree. lambda=6 (not Oza & Russell's 1) is ARF's own choice: it makes the
         effective training set larger and the trees grow faster.
      3. PER-TREE DRIFT DETECTION AT TWO LEVELS. A WARNING (loose delta) starts a
         background tree trained in parallel; a DRIFT (tight delta) promotes that
         background tree over the primary. The background tree is why ARF recovers
         without the accuracy hole a bare reset leaves.

    And it is the cost of this that the paper's Table 5 is about: 100 trees, each
    growing, each with its own detectors.
    """
    name = "RF-HT"

    def __init__(self, d, n_trees=100, n_classes=2, lam=6.0, n_min=50,
                 delta_w=0.01, delta_d=0.001, seed=0, subspace=None):
        self.d, self.n_trees, self.lam = d, n_trees, lam
        self.n_classes, self.n_min = n_classes, n_min
        self.delta_w, self.delta_d = delta_w, delta_d   # warning / drift confidences
        self.rng = random.Random(seed)
        m = subspace or (int(math.sqrt(d)) + 1)         # attributes per tree
        self.m = min(m, d)
        self.trees, self.bg = [], []                    # primary and background trees
        self.warn, self.drift = [], []                  # one ADWIN pair per tree
        self.acc = []                                   # [correct, seen] per tree
        for _ in range(n_trees):
            self.trees.append(self._new_tree())
            self.bg.append(None)                        # no background tree yet
            self.warn.append(ADWIN(delta_w))
            self.drift.append(ADWIN(delta_d))
            self.acc.append([1.0, 1.0])                 # Laplace-ish start, avoids 0/0
        self.n_drifts, self.n_warnings = 0, 0           # diagnostics

    def _new_tree(self):
        attrs = self.rng.sample(range(self.d), self.m)  # this tree's random subspace
        return HoeffdingTree(self.d, self.n_classes, n_min=self.n_min, attrs=attrs)

    def theta_hat(self):
        return None                 # an ensemble of trees: still no Delta-theta

    def predict(self, x):
        """Accuracy-weighted vote, as ARF does (not a plain majority)."""
        num, den = 0.0, 0.0
        for t, a in zip(self.trees, self.acc):
            w = a[0]/a[1]                               # this tree's running accuracy
            num += w * t.predict(x)
            den += w
        return num/den if den else 0.5

    def update(self, x, y):
        for j, tree in enumerate(self.trees):
            # --- per-tree correctness, feeding both its detectors and its weight
            correct = 1 if (1 if tree.predict(x) > 0.5 else 0) == y else 0
            self.acc[j][0] += correct
            self.acc[j][1] += 1
            # ADWIN monitors the ERROR signal, so feed it 1 - correct.
            err = 1 - correct
            warned  = self.warn[j].add(err)
            drifted = self.drift[j].add(err)

            # --- online bagging: k ~ Poisson(lambda) presentations
            k = _poisson(self.lam, self.rng)
            for _ in range(k):
                tree.update(x, y)
            if self.bg[j] is not None:
                for _ in range(k):
                    self.bg[j].update(x, y)             # the background tree learns too

            # --- the two-level reaction
            if drifted:
                # Promote the background tree if one exists, else start clean. The
                # tree's accuracy counter resets with it, or a stale weight would
                # follow the new tree around.
                self.trees[j] = self.bg[j] if self.bg[j] is not None else self._new_tree()
                self.bg[j] = None
                self.warn[j].reset(); self.drift[j].reset()
                self.acc[j] = [1.0, 1.0]
                self.n_drifts += 1
            elif warned and self.bg[j] is None:
                self.bg[j] = self._new_tree()           # start growing a replacement
                self.n_warnings += 1


# =========================================================================
# SAMkNN -- Losing, Hammer & Wersing (2016)
# =========================================================================

def _sqdist(a, b):
    return sum((p-q)*(p-q) for p, q in zip(a, b))


def _knn_vote(mem, x, k):
    """P(y=1) from the k nearest neighbours in `mem`; None if mem is empty."""
    if not mem: return None
    import heapq as _h
    near = _h.nsmallest(min(k, len(mem)), mem, key=lambda p: _sqdist(x, p[0]))
    return sum(p[1] for p in near) / len(near)


class SAMkNN:
    """Table 2 'SAMkNN': kNN with a Short-Term and a Long-Term Memory.

    The idea (Losing et al. 2016) is that the two drift regimes want opposite
    things, so keep one memory for each and let recent accuracy choose:

      STM  a sliding window holding only the CURRENT concept. Its size is adapted
           by trying bisected suffixes and keeping whichever minimises interleaved
           test-train error -- so after an abrupt drift the STM collapses to just
           the post-drift instances.
      LTM  compressed knowledge that does NOT contradict the STM. It is what lets
           a REOCCURRING concept be answered immediately instead of relearned.
      CM   the union. Predictions come from whichever of the three has been most
           accurate over the recent evaluation window.

    This is the structure of the algorithm, not a line-for-line port. Two
    documented departures from the paper: (1) LTM compression is by simple
    capacity-bounded FIFO, where the paper uses kMeans++ clustering of each class;
    (2) STM sizes are tested by bisection over suffixes, which is the paper's
    scheme, but the error is evaluated on the suffix itself rather than with the
    paper's incremental caching. Both affect cost more than behaviour, but neither
    should be reported as a faithful SAMkNN number.
    """
    name = "SAMkNN"

    def __init__(self, d, k=5, max_stm=5000, max_ltm=5000, eval_win=500,
                 min_stm=50):
        self.d, self.k = d, k
        self.stm, self.ltm = [], []          # lists of (x, y)
        self.max_stm, self.max_ltm = max_stm, max_ltm
        self.min_stm = min_stm               # never bisect below this
        # Rolling correctness of each of the three predictors, for model selection.
        self.hist = {"stm": deque(maxlen=eval_win),
                     "ltm": deque(maxlen=eval_win),
                     "cm":  deque(maxlen=eval_win)}
        self.adapt_every = 50                # how often to re-tune the STM length
        self.t = 0

    def theta_hat(self):
        return None                          # non-parametric, like every kNN

    def _preds(self, x):
        return {"stm": _knn_vote(self.stm, x, self.k),
                "ltm": _knn_vote(self.ltm, x, self.k),
                "cm":  _knn_vote(self.stm + self.ltm, x, self.k)}

    def predict(self, x):
        p = self._preds(x)
        # Model selection: the memory with the best recent interleaved accuracy.
        # Ties and empty histories fall back to the STM, which is the paper's
        # behaviour at the start of a stream.
        best, best_acc = "stm", -1.0
        for name, h in self.hist.items():
            if p[name] is None or not h: continue
            a = sum(h)/len(h)
            if a > best_acc: best, best_acc = name, a
        return p[best] if p[best] is not None else 0.5

    def _clean(self, x, y):
        """Drop LTM instances that CONTRADICT the new STM instance.

        The paper's cleaning rule: take the distance to the k-th nearest STM
        neighbour OF THE SAME class as (x,y); any LTM point inside that radius
        with a DIFFERENT label is inconsistent with the current concept and is
        removed. That is what keeps the LTM from poisoning the CM after a drift.
        """
        same = [p for p in self.stm if p[1] == y]
        if len(same) < self.k: return
        import heapq as _h
        r = max(_h.nsmallest(self.k, (_sqdist(x, p[0]) for p in same)))
        self.ltm[:] = [p for p in self.ltm
                       if not (p[1] != y and _sqdist(x, p[0]) <= r)]

    def _adapt_stm(self):
        """Bisection over suffix lengths; the discarded prefix is offered to the LTM."""
        n = len(self.stm)
        if n < 2*self.min_stm: return
        sizes, s = [n], n//2
        while s >= self.min_stm:
            sizes.append(s); s //= 2
        best, best_err = n, None
        for sz in sizes:
            sub = self.stm[-sz:]
            # Interleaved test-then-train error on the candidate window. Start at
            # k so the first predictions are not made on an almost-empty memory.
            err, cnt = 0, 0
            for i in range(self.k, len(sub)):
                p = _knn_vote(sub[:i], sub[i][0], self.k)
                if p is None: continue
                err += 0 if (1 if p > 0.5 else 0) == sub[i][1] else 1
                cnt += 1
            if cnt == 0: continue
            e = err/cnt
            if best_err is None or e < best_err:
                best, best_err = sz, e
        if best < n:
            # The STM shrank: the evicted prefix is knowledge about a PAST concept,
            # which is exactly what the LTM is for -- after cleaning it against the
            # concept that survived.
            dropped, self.stm = self.stm[:n-best], self.stm[n-best:]
            for xx, yy in dropped:
                self.ltm.append((xx, yy))
            self._clean(self.stm[-1][0], self.stm[-1][1])
            if len(self.ltm) > self.max_ltm:
                del self.ltm[:len(self.ltm) - self.max_ltm]   # FIFO compression

    def update(self, x, y):
        self.t += 1
        # Record which memory WOULD have been right, before absorbing the instance.
        p = self._preds(x)
        for name, v in p.items():
            if v is not None:
                self.hist[name].append(1 if (1 if v > 0.5 else 0) == y else 0)
        self.stm.append((list(x), y))
        if len(self.stm) > self.max_stm:
            self.stm.pop(0)
        self._clean(x, y)
        if self.t % self.adapt_every == 0:
            self._adapt_stm()
