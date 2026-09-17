# What theta IS, and what the four drift types do to it -- the smallest possible
# tour of concept space Theta before any learner or stream gets involved.
import math, random
random.seed(0)                                   # fixed seed: printed numbers are exact

def rnd(v, n=5): return "[" + ", ".join(f"{x:+.{n}f}" for x in v) + "]"  # pretty-print
def dot(a, b):   return sum(i*j for i, j in zip(a, b))       # a . b
def norm(v):     return math.sqrt(dot(v, v))                 # ||v||, Euclidean length
def ang(v):      return math.degrees(math.atan2(v[1], v[0])) # v's heading in degrees
def sig(z):      return 1/(1+math.exp(-z))                   # sigma(z), logistic link

# ---- theta as a concept: a 2-D hyperplane through the origin -----------
theta = [0.70, -0.30]                            # one point in Theta = R^2
print("theta_0 =", rnd(theta, 2))
# theta . x = 0 defines the boundary; no bias term, so it passes through the origin
print("boundary: 0.70*x1 - 0.30*x2 = 0   ->   x2 = 2.3333*x1\n")
for x in ([1.0, 1.0], [1.0, 3.0], [-2.0, 0.5]):  # one point per side, one near it
    z = dot(theta, x)                            # the logit
    # sign(z) is the label; sigma(z) is only the confidence attached to it
    print(f"  x={rnd(x,1)}  theta.x={z:+.3f}  sigma={sig(z):.3f}  y={int(z>0)}")

# ---- incremental drift: theta_t = A_0.01^T theta_{t-1} -----------------
a = 0.01                                         # the per-step rotation, in radians
c, s = math.cos(a), math.sin(a)                  # reused below to build A
print(f"\nA_0.01 = [[{c:.6f}, {-s:.6f}], [{s:.6f}, {c:.6f}]]")
def step(th):                      # A^T @ th
    # Transposed multiply, so this rotates CLOCKWISE by a -- matching drift.apply_T
    return [c*th[0] + s*th[1], -s*th[0] + c*th[1]]

print("\n  t     theta_t                    |theta|   angle(deg)   Delta_t theta")
th = theta[:]                                    # copy: leave `theta` intact for later
print(f"  0   {rnd(th)}   {norm(th):.4f}   {ang(th):8.4f}      --")
for t in range(1, 6):
    prev, th = th[:], step(th)                   # keep theta_{t-1} to difference against
    d = [th[0]-prev[0], th[1]-prev[1]]           # Delta_t theta, Eq.(4)'s increment
    # Delta is TINY and non-zero: intermediate states are real, reachable concepts
    print(f"  {t}   {rnd(th)}   {norm(th):.4f}   {ang(th):8.4f}   {rnd(d)}")

th100 = theta[:]
for _ in range(100): th100 = step(th100)         # 100 steps x 0.01 rad = 1.00 rad
# The key check: the ANGLE moved 57.3 deg but the NORM is unchanged -- rotation is
# an isometry, so the label-noise floor is identical before and after the drift.
print(f"\n  after 100 steps: {rnd(th100)}  angle {ang(th100):.4f} deg "
      f"(rotated 1.00 rad = {math.degrees(1.0):.2f} deg), norm {norm(th100):.4f}")

# ---- sudden drift: resample -------------------------------------------
# Contrast with the above: no trajectory at all, just independent draws from Theta
print("\nsudden: theta_c ~ N(0, I)")
for k in range(1, 4):
    print(f"  theta_c{k} = {rnd([random.gauss(0,1) for _ in range(2)], 4)}")

# ---- SGD tracking the moving concept ----------------------------------
# Now add a learner: can theta_hat chase a theta that never stops moving?
print("\nSGD tracking (lambda=0.5), true theta rotating 0.01 rad/step")
th_true, th_hat, lam = theta[:], [0.10, 0.10], 0.5    # theta_1, theta_hat_1, lambda
# Initial angle gap, before any data has been seen at all
gap0 = math.degrees(math.acos(max(-1, min(1, dot(th_true, th_hat)/(norm(th_true)*norm(th_hat))))))
print(f"  t=0     true={rnd(th_true,4)}  hat={rnd(th_hat,4)}  angle gap={gap0:6.2f} deg")
for t in range(1, 2001):
    th_true = step(th_true)                      # theta_t moves FIRST, every step
    x = [random.gauss(0,1) for _ in range(2)]    # x_t ~ N(0, I_2)
    y = 1.0 if dot(th_true, x) > 0 else 0.0      # NOISELESS labels here (no eps_t)
    p = sig(dot(th_hat, x))                      # h_t(x_t), the learner's probability
    th_hat = [th_hat[i] + lam*(y-p)*x[i] for i in range(2)]   # + lambda * grad E
    if t in (1, 2, 10, 100, 500, 2000):          # log at log-spaced checkpoints
        cos = dot(th_true, th_hat)/(norm(th_true)*norm(th_hat))   # scale-invariant
        g = math.degrees(math.acos(max(-1, min(1, cos))))        # the angle gap
        # The gap converges to a small NON-ZERO value: continuous adaptation tracks
        # but always lags, which is the bias term of Read's Section 4.
        print(f"  t={t:<5}  true={rnd(th_true,4)}  hat={rnd(th_hat,4)}  angle gap={g:6.2f} deg")
