Why these 
𝜃
θ and not others

We assumed a stationary agent. That still leaves which 
𝜃
=
(
𝜃
𝜋
,
𝜃
𝑀
)
θ=(θ
π
	​

,θ
M
	​

) we converge to. There are two natural setups.

Reward setup. We already wrote the objective 
𝐽
(
𝜃
)
J(θ). A stationary maximizer 
𝜃
∗
θ
∗
 induces an occupancy over the environment states and turns. Let

𝑑
𝜋
(
𝑠
)
  
  
be the stationary visitation of 
𝑠
 under 
𝜋
(
⋅
∣
𝑠
^
)
.
d
π
(s)be the stationary visitation of s under π(⋅∣
s
^
).

All expectations in 
𝐽
(
𝜃
)
J(θ) are taken on this support. In plain terms: an optimal policy only needs to model the slice of the world it actually visits from the starting distribution. The predictive state 
ℎ
𝜃
𝐺
h
θ
G
	​

	​

 will compress exactly the subset of latent structure that lives on that support.

Goal-directed setup. Instead of a single reward, we have a family of tasks or goals 
𝑔
g. Each goal defines a reward 
𝑅
𝑔
R
g
	​

 or a termination condition. A goal-conditioned policy 
𝜋
(
𝑎
∣
𝑠
^
,
𝑔
)
π(a∣
s
^
,g) and model 
𝑀
(
⋅
∣
⋅
,
𝑔
)
M(⋅∣⋅,g) maximize

𝐸
𝑔
∼
𝐺
  
𝐸
𝑍
∼
𝑃
(
 
⋅
∣
𝑔
,
𝜃
)
[
∑
𝑡
𝑅
𝑔
(
𝑠
𝑡
,
𝑎
𝑡
)
]
.
E
g∼G
	​

E
Z∼P(⋅∣g,θ)
	​

[
t
∑
	​

R
g
	​

(s
t
	​

,a
t
	​

)].

Now coverage depends on the goal distribution 
𝐺
G. A “generalist” policy that solves many goals increases state coverage and forces the predictive state to carry more of the environment channel.

Coverage and what can be learned

Call the reachable set under a policy:

𝑆
𝜋
=
{
𝑠
  
:
  
Pr
⁡
(
𝑠
𝑡
=
𝑠
 for some 
𝑡
∣
𝜋
)
>
0
}
.
S
π
={s:Pr(s
t
	​

=s for some t∣π)>0}.

Call the minimal sufficient set for an optimal policy from start distribution 
𝜇
μ the states that lie on optimal trajectories:

𝑆
∗
=
{
𝑠
  
:
  
∃
 
𝜋
∗
 optimal, 
Pr
⁡
𝜋
(
𝑠
𝑡
=
𝑠
∣
𝑠
0
∼
𝜇
)
>
0
}
.
S
∗
={s:∃π
∗
 optimal, 
Pr
π
(s
t
	​

=s∣s
0
	​

∼μ)>0}.

A world model trained from rollouts of 
𝜋
π can only identify 
𝑃
(
𝑜
𝑡
+
1
∣
𝑠
𝑡
,
𝑎
𝑡
+
1
)
P(o
t+1
	​

∣s
t
	​

,a
t+1
	​

) on 
𝑆
𝜋
S
π
. It cannot learn the environment channel outside that support. This is the practical link between exploration and identifiability: exploration enlarges 
𝑆
𝜋
S
π
, which enlarges what the model can actually learn.

In the reward setup, if you only ever collect near-optimal data, the learned kernels concentrate on 
𝑆
∗
S
∗
. That is enough to implement the optimal policy, but it is not enough to know the full environment. In the goal-directed setup, if 
𝐺
G covers goals whose optimal paths union to the whole environment graph, then the induced policy family covers all states and the model can, in principle, learn the entire environment channel.

Tasks as coverage devices

Think of a task family 
𝑇
=
{
𝑔
}
T={g} as a covering of the state graph. If

⋃
𝑔
∈
𝑇
𝑆
𝜋
𝑔
∗
=
𝑆
,
g∈T
⋃
	​

S
π
g
∗
	​

=S,

then optimal policies for those tasks jointly visit all states. Training on this family makes the predictive state carry everything needed to forecast observations across the graph. If the union is smaller, the learned predictive state is minimal for that subset.

Dataset support and the transformer

Everything above shows up in the data. The transformer trained on 
𝑍
Z learns the macro kernels only on the support of 
𝑍
Z. With turns 
𝑧
𝑡
=
(
𝑎
𝑡
,
𝑜
𝑡
)
z
t
	​

=(a
t
	​

,o
t
	​

) the factorization is

𝑃
(
𝑎
𝑡
+
1
∣
𝑧
≤
𝑡
)
and
𝑃
(
𝑜
𝑡
+
1
∣
𝑎
𝑡
+
1
,
𝑧
≤
𝑡
)
.
P(a
t+1
	​

∣z
≤t
	​

)andP(o
t+1
	​

∣a
t+1
	​

,z
≤t
	​

).

If the dataset never visits a region, the observation head cannot learn that region’s emission kernel. If the dataset visits a region only under a narrow action distribution, the action head will learn that slice of the policy. Broader task sets or explicit exploration widen both supports.

Minimal sufficient predictive state

For a fixed objective and start distribution, there is a smallest predictive state that suffices:

for reward maximization, the minimal state that supports 
𝜋
∗
π
∗
 on 
𝑆
∗
S
∗
;

for goal-directed behavior, the minimal state that supports 
{
𝜋
𝑔
∗
}
𝑔
∈
𝐺
{π
g
∗
	​

}
g∈G
	​

 on 
⋃
𝑔
𝑆
𝜋
𝑔
∗
⋃
g
	​

S
π
g
∗
	​

.

That is what a well-trained predictor will converge to. It will not carry structure it never needs. If you later ask it to solve unseen goals or act in unseen regions, it will fail unless the dataset support already covered them.

Exploration in this frame

Exploration is not a philosophical add-on. It is a statement about support. Maximum-entropy or curiosity objectives increase 
𝑆
𝜋
S
π
 early so that later, when you compress into a predictive state for performance, you do not miss parts of the environment channel you will need. In goal-directed training, a curriculum over goals serves the same role: expand coverage first, then specialize.

So, why these 
𝜃
θ. Because 
𝜃
θ is selected by the training objective and the dataset support. Reward-only with expert rollouts gives a predictive state just big enough for 
𝑆
∗
S
∗
. Goal-directed across many tasks gives a larger predictive state that spans the union of optimal paths. Both are consistent with the two-step turn prediction we use. After predicting 
𝑎
a we hold a sufficient statistic for the agent side on the visited slice. After observing 
𝑜
o we update the environment slice on the visited states. The rest simply does not exist for the model unless the data makes it real.