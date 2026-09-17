import math, random
random.seed(0)

def rnd(v, n=5): return "[" + ", ".join(f"{x:+.{n}f}" for x in v) + "]"
def dot(a, b):   return sum(i*j for i, j in zip(a, b))
def norm(v):     return math.sqrt(dot(v, v))
def ang(v):      return math.degrees(math.atan2(v[1], v[0]))
def sig(z):      return 1/(1+math.exp(-z))

# ---- theta as a concept: a 2-D hyperplane through the origin -----------
theta = [0.70, -0.30]
print("theta_0 =", rnd(theta, 2))
print("boundary: 0.70*x1 - 0.30*x2 = 0   ->   x2 = 2.3333*x1\n")
for x in ([1.0, 1.0], [1.0, 3.0], [-2.0, 0.5]):
    z = dot(theta, x)
    print(f"  x={rnd(x,1)}  theta.x={z:+.3f}  sigma={sig(z):.3f}  y={int(z>0)}")

# ---- incremental drift: theta_t = A_0.01^T theta_{t-1} -----------------
a = 0.01
c, s = math.cos(a), math.sin(a)
print(f"\nA_0.01 = [[{c:.6f}, {-s:.6f}], [{s:.6f}, {c:.6f}]]")
def step(th):                      # A^T @ th
    return [c*th[0] + s*th[1], -s*th[0] + c*th[1]]

print("\n  t     theta_t                    |theta|   angle(deg)   Delta_t theta")
th = theta[:]
print(f"  0   {rnd(th)}   {norm(th):.4f}   {ang(th):8.4f}      --")
for t in range(1, 6):
    prev, th = th[:], step(th)
    d = [th[0]-prev[0], th[1]-prev[1]]
    print(f"  {t}   {rnd(th)}   {norm(th):.4f}   {ang(th):8.4f}   {rnd(d)}")

th100 = theta[:]
for _ in range(100): th100 = step(th100)
print(f"\n  after 100 steps: {rnd(th100)}  angle {ang(th100):.4f} deg "
      f"(rotated 1.00 rad = {math.degrees(1.0):.2f} deg), norm {norm(th100):.4f}")

# ---- sudden drift: resample -------------------------------------------
print("\nsudden: theta_c ~ N(0, I)")
for k in range(1, 4):
    print(f"  theta_c{k} = {rnd([random.gauss(0,1) for _ in range(2)], 4)}")

# ---- SGD tracking the moving concept ----------------------------------
print("\nSGD tracking (lambda=0.5), true theta rotating 0.01 rad/step")
th_true, th_hat, lam = theta[:], [0.10, 0.10], 0.5
gap0 = math.degrees(math.acos(max(-1, min(1, dot(th_true, th_hat)/(norm(th_true)*norm(th_hat))))))
print(f"  t=0     true={rnd(th_true,4)}  hat={rnd(th_hat,4)}  angle gap={gap0:6.2f} deg")
for t in range(1, 2001):
    th_true = step(th_true)
    x = [random.gauss(0,1) for _ in range(2)]
    y = 1.0 if dot(th_true, x) > 0 else 0.0
    p = sig(dot(th_hat, x))
    th_hat = [th_hat[i] + lam*(y-p)*x[i] for i in range(2)]   # + lambda * grad E
    if t in (1, 2, 10, 100, 500, 2000):
        cos = dot(th_true, th_hat)/(norm(th_true)*norm(th_hat))
        g = math.degrees(math.acos(max(-1, min(1, cos))))
        print(f"  t={t:<5}  true={rnd(th_true,4)}  hat={rnd(th_hat,4)}  angle gap={g:6.2f} deg")
