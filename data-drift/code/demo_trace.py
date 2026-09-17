import math, random
random.seed(7)

def dot(a,b): return sum(i*j for i,j in zip(a,b))
def sig(z):   return 1/(1+math.exp(-z))
def v(a,n=2): return "[" + ",".join(f"{x:+.{n}f}" for x in a) + "]"

# ===== Theta : concept space, two concepts, drift at tau ==================
theta_c1 = [ 0.90, -0.40]      # concept 1
theta_c2 = [-0.50,  0.80]      # concept 2
TAU      = 10                  # tau : the change point
T        = 20                  # stream length
LAM      = 0.5                 # lambda : learning rate
SIGMA    = 0.30                # sigma : std of irreducible noise eps

def theta_at(t):               # Eq.(3)  abrupt drift
    return theta_c1 if t < TAU else theta_c2

theta_hat = [0.10, 0.10]       # theta_hat_1 : learner's initial estimate

print("Theta = R^2 | theta_c1 =", v(theta_c1), " theta_c2 =", v(theta_c2),
      "| tau =", TAU, "| lambda =", LAM, "| sigma =", SIGMA, "\n")
hdr = (" t  C_t  theta_t        x_t            f(x;th)  eps_t   y_t | "
       "theta_hat_t    h_t(x)  y_hat  E_t | bias=||th-thhat||^2")
print(hdr); print("-"*len(hdr))

cum_err = 0
for t in range(1, T+1):
    C_t   = 0 if t < TAU else 1            # C_t : latent concept indicator
    th_t  = theta_at(t)                    # theta_t : true concept NOW
    x_t   = [random.gauss(0,1), random.gauss(0,1)]   # x_t ~ p_t(X)
    f     = sig(dot(th_t, x_t))            # f(x_t ; theta_c) : true model
    eps   = random.gauss(0, SIGMA)         # eps_t ~ N(0, sigma^2)
    y_t   = 1 if f + eps > 0.5 else 0      # y_t : the label that arrives

    # --- TEST first (prequential): predict with the CURRENT estimate -----
    p_hat = sig(dot(theta_hat, x_t))       # h_t(x_t)
    y_hat = 1 if p_hat > 0.5 else 0        # y_hat_t = h_t(x_t)
    E_t   = 0 if y_hat == y_t else 1       # E_t = E(h_t(x_t), y_t)
    cum_err += E_t

    bias = sum((a-b)**2 for a,b in zip(th_t, theta_hat))   # (theta_t - theta_hat_t)^2

    mark = "  <-- tau" if t == TAU else ""
    print(f"{t:2}   {C_t}   {v(th_t)}  {v(x_t)}   {f:.3f}  {eps:+.3f}   {y_t}  | "
          f"{v(theta_hat)}   {p_hat:.3f}    {y_hat}     {E_t}  |  {bias:.4f}{mark}")

    # --- then TRAIN : theta_hat_{t+1} <- theta_hat_t + lambda * grad E ---
    theta_hat = [theta_hat[i] + LAM*(y_t - p_hat)*x_t[i] for i in range(2)]

print(f"\nprequential error rate over t=1..{T}: {cum_err}/{T} = {cum_err/T:.3f}")
print("final theta_hat =", v(theta_hat), " true theta_T =", v(theta_at(T)))
cos = dot(theta_at(T), theta_hat)/(math.sqrt(dot(theta_at(T),theta_at(T)))*math.sqrt(dot(theta_hat,theta_hat)))
print(f"angle(theta_T, theta_hat) = {math.degrees(math.acos(max(-1,min(1,cos)))):.2f} deg")

# ===== Lemma 1 : P(C_t) vs P(C_t | C_{t-1}) ==============================
print("\n--- Lemma 1, counted over this stream (t=1..20) ---")
Cs = [0 if t < TAU else 1 for t in range(1, T+1)]
n0 = Cs.count(0)
pairs = list(zip(Cs, Cs[1:]))                      # (C_{t-1}, C_t)
given1 = [c for (p,c) in pairs if p == 1]
print(f"P(C_t = 0)              = {n0}/{T}  = {n0/T:.3f}")
print(f"P(C_t = 0 | C_t-1 = 1)  = {given1.count(0)}/{len(given1)}   = "
      f"{given1.count(0)/len(given1):.3f}   -> not equal, so C is NOT independent over t")

# ===== gradual variant : alpha_t and B(alpha_t) ==========================
print("\n--- same two concepts under GRADUAL drift, tau1=5 tau2=15 ---")
t1, t2 = 5, 15
random.seed(3)
print(" t   alpha_t   c_t ~ B(alpha_t)   theta_t")
for t in range(1, T+1):
    a_t = 0.0 if t <= t1 else (1.0 if t >= t2 else (t - t1)/(t2 - t1))
    c_t = 2 if random.random() < a_t else 1
    print(f"{t:2}    {a_t:.2f}          c_t = {c_t}        "
          f"{v(theta_c1 if c_t==1 else theta_c2)}")
