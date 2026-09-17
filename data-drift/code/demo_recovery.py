import math, random
random.seed(7)
def dot(a,b): return sum(i*j for i,j in zip(a,b))
def sig(z):   return 1/(1+math.exp(-z))
th1,th2,TAU,LAM,SIG = [0.9,-0.4],[-0.5,0.8],10,0.5,0.30
th_hat=[0.10,0.10]; errs=[]
print(" t    ||theta_t - theta_hat_t||^2   angle(deg)   err rate (last 50)")
for t in range(1,301):
    th = th1 if t<TAU else th2
    x=[random.gauss(0,1),random.gauss(0,1)]
    y=1 if sig(dot(th,x))+random.gauss(0,SIG)>0.5 else 0
    p=sig(dot(th_hat,x)); errs.append(0 if (1 if p>0.5 else 0)==y else 1)
    if t in (9,10,14,20,50,100,200,300):
        bias=sum((a-b)**2 for a,b in zip(th,th_hat))
        c=dot(th,th_hat)/(math.sqrt(dot(th,th))*math.sqrt(dot(th_hat,th_hat)))
        ang=math.degrees(math.acos(max(-1,min(1,c))))
        w=errs[-50:]
        print(f"{t:3}          {bias:7.4f}              {ang:6.2f}         {sum(w)/len(w):.3f}")
    th_hat=[th_hat[i]+LAM*(y-p)*x[i] for i in range(2)]
