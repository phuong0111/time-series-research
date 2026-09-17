# How fast does continuous adaptation recover from a SINGLE sudden drift?
# A stripped-down single-stream trace: one learner, one change point at tau=10,
# sampled at a few t to show bias collapsing and the error window healing.
import math, random
random.seed(7)                                  # fixed seed: the printed table is exact
def dot(a,b): return sum(i*j for i,j in zip(a,b))    # a . b, the inner product
def sig(z):   return 1/(1+math.exp(-z))              # sigma(z), the logistic link
# th1 -> th2 at TAU; LAM = lambda (step size); SIG = sigma (label-noise std)
th1,th2,TAU,LAM,SIG = [0.9,-0.4],[-0.5,0.8],10,0.5,0.30
th_hat=[0.10,0.10]; errs=[]                     # theta_hat_1, and the E_t history
print(" t    ||theta_t - theta_hat_t||^2   angle(deg)   err rate (last 50)")
for t in range(1,301):
    th = th1 if t<TAU else th2                  # theta_t: Eq.(3), one jump at TAU
    x=[random.gauss(0,1),random.gauss(0,1)]     # x_t ~ N(0, I_2)
    # y_t: true probability, nudged by eps_t ~ N(0, SIG^2), then thresholded
    y=1 if sig(dot(th,x))+random.gauss(0,SIG)>0.5 else 0
    # TEST before training: h_t(x_t), then E_t = 1[y_hat != y] (0/1 loss)
    p=sig(dot(th_hat,x)); errs.append(0 if (1 if p>0.5 else 0)==y else 1)
    if t in (9,10,14,20,50,100,200,300):        # sample just before/after TAU, then decay
        bias=sum((a-b)**2 for a,b in zip(th,th_hat))     # ||theta_t - theta_hat_t||^2
        # cosine between theta_t and theta_hat_t; scale-invariant, unlike bias
        c=dot(th,th_hat)/(math.sqrt(dot(th,th))*math.sqrt(dot(th_hat,th_hat)))
        ang=math.degrees(math.acos(max(-1,min(1,c))))    # clamp guards acos domain
        w=errs[-50:]                             # TRAILING window: shows recovery SPEED,
        print(f"{t:3}          {bias:7.4f}              {ang:6.2f}         {sum(w)/len(w):.3f}")
    # THEN train: theta_hat += lambda * (y - h) * x, the same step as ContinuousSGD
    th_hat=[th_hat[i]+LAM*(y-p)*x[i] for i in range(2)]
# unlike the cumulative rate in experiments.py, which averages recovery away
