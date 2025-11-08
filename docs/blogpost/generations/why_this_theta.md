## Why these $\theta$ and not others

We assumed a stationary agent. That still leaves which $\theta=(\theta_\pi,\theta_{\mathcal{M}})$ we converge to. There are two natural setups.

**Reward setup.** We already wrote the objective $J(\theta)$. A stationary maximizer $\theta^*$ induces an occupancy over the environment states and turns. Let $d_\pi(s)$ be the stationary visitation of $s$ under $\pi(\cdot\mid \hat{s})$.

All expectations in $J(\theta)$ are taken on this support. In plain terms: an optimal policy only needs to model the slice of the world it actually visits from the starting distribution. The predictive state $h_{\theta_G}$ will compress exactly the subset of latent structure that lives on that support.

**Goal-directed setup.** Instead of a single reward, we have a family of tasks or goals $g$. Each goal defines a reward $R_g$ or a termination condition. A goal-conditioned policy $\pi(a\mid \hat{s},g)$ and model $\mathcal{M}(\cdot\mid \cdot,g)$ maximize
$$
\mathbb{E}_{g\sim G}\,\mathbb{E}_{Z\sim P(\cdot\mid g,\theta)}\left[\sum_t R_g(s_t,a_t)\right].
$$

Now coverage depends on the goal distribution $G$. A "generalist" policy that solves many goals increases state coverage and forces the predictive state to carry more of the environment channel.

### Coverage and what can be learned

Call the reachable set under a policy:
$$
S_\pi = \{s : \Pr(s_t=s \text{ for some } t\mid \pi)>0\}.
$$

Call the minimal sufficient set for an optimal policy from start distribution $\mu$ the states that lie on optimal trajectories:
$$
S^* = \{s : \exists\, \pi^* \text{ optimal, } \Pr_\pi(s_t=s\mid s_0\sim \mu)>0\}.
$$

A world model trained from rollouts of $\pi$ can only identify $P(o_{t+1}\mid s_t,a_{t+1})$ on $S_\pi$. It cannot learn the environment channel outside that support. This is the practical link between exploration and identifiability: exploration enlarges $S_\pi$, which enlarges what the model can actually learn.

In the reward setup, if you only ever collect near-optimal data, the learned kernels concentrate on $S^*$. That is enough to implement the optimal policy, but it is not enough to know the full environment. In the goal-directed setup, if $G$ covers goals whose optimal paths union to the whole environment graph, then the induced policy family covers all states and the model can, in principle, learn the entire environment channel.

### Tasks as coverage devices

Think of a task family $T=\{g\}$ as a covering of the state graph. If
$$
\bigcup_{g\in T} S_{\pi_g^*} = S,
$$
then optimal policies for those tasks jointly visit all states. Training on this family makes the predictive state carry everything needed to forecast observations across the graph. If the union is smaller, the learned predictive state is minimal for that subset.

### Dataset support and the transformer

Everything above shows up in the data. The transformer trained on $Z$ learns the macro kernels only on the support of $Z$. With turns $z_t=(a_t,o_t)$ the factorization is
$$
P(a_{t+1}\mid z_{\le t}) \quad \text{and} \quad P(o_{t+1}\mid a_{t+1},z_{\le t}).
$$

If the dataset never visits a region, the observation head cannot learn that region's emission kernel. If the dataset visits a region only under a narrow action distribution, the action head will learn that slice of the policy. Broader task sets or explicit exploration widen both supports.

### Minimal sufficient predictive state

For a fixed objective and start distribution, there is a smallest predictive state that suffices:

- for reward maximization, the minimal state that supports $\pi^*$ on $S^*$;
- for goal-directed behavior, the minimal state that supports $\{\pi_g^*\}_{g\in G}$ on $\bigcup_g S_{\pi_g^*}$.

That is what a well-trained predictor will converge to. It will not carry structure it never needs. If you later ask it to solve unseen goals or act in unseen regions, it will fail unless the dataset support already covered them.

### Exploration in this frame

Exploration is not a philosophical add-on. It is a statement about support. Maximum-entropy or curiosity objectives increase $S_\pi$ early so that later, when you compress into a predictive state for performance, you do not miss parts of the environment channel you will need. In goal-directed training, a curriculum over goals serves the same role: expand coverage first, then specialize.

### So, why these $\theta$?

Because $\theta$ is selected by the training objective and the dataset support. Reward-only with expert rollouts gives a predictive state just big enough for $S^*$. Goal-directed across many tasks gives a larger predictive state that spans the union of optimal paths. Both are consistent with the two-step turn prediction we use. After predicting $a$ we hold a sufficient statistic for the agent side on the visited slice. After observing $o$ we update the environment slice on the visited states. The rest simply does not exist for the model unless the data makes it real.