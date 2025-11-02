[till here good from here on need to rewrite]

### Hierarchical reinforcement learning link

The same parameters $\theta$ that define the token-level generator $\sigma_\theta$ also determine the induced macro policy $\pi_\theta$ through class marginalization.  
The generator is **optimal** if and only if its induced class-marginal matches the optimal high-level policy on admissible turns:
$$
\forall b_t,\; \forall z \in \mathcal{Z}_{\mathrm{env}}(s_t): \quad
\sum_{x \in [z]} P_\theta(x \mid \text{turn}_{\lt t}) = \pi^*(z \mid b_t).
$$
Within each equivalence class $[z]$, any distribution over token realizations that respects termination and admissibility yields the same macro return.  
[here instead of tilting we can express the likelihood only for the tokens that are valid sequences and speak about structured generation, grammar based constraints of the low level policy with e.g. outlines library]
A constructive parameterization that aligns the micro generator with the high-level reward is obtained by exponentially tilting the token likelihood with the class value at termination:
$$
P_\lambda(x \mid \text{turn}_{\lt t})
\;\propto\;
\Bigg(\prod_{k=m}^{n} \sigma_\theta(\tau_k \mid \tau_{\lt k})\Bigg)
\exp\!\big(\lambda\, Q(b_t, \rho_{\mathcal{Z}}(x))\big)
\mathbb{I}_{\mathrm{env}}(x, s_t),
\quad x \text{ ends at the delimiter.}
$$
Marginalizing over $[z]$ yields the soft-optimal turn policy
$$
\pi_\lambda(z \mid b_t)
\;\propto\;
\exp\!\big(\lambda\, Q(b_t, z)\big),
\qquad z \in \mathcal{Z}_{\mathrm{env}}(s_t),
$$
so that the micro dynamics implement the macro-optimal behavior by allocating token probability mass within each class according to value-weighted preference.



### Options as micro controllers

The same hierarchy can be framed through **options**.  
Let $\mathcal{W}$ be a set of token-level controllers $\omega \in \mathcal{W}$, each defined by an initiation set $\mathcal{I}^\omega$, a local token policy $\sigma_\theta^\omega(\tau_k \mid \tau_{\lt k}, b_t)$, and a stopping rule $\beta^\omega(\tau_k = \text{EOT} \mid \tau_{\lt k}, b_t)$.  
A high-level selector $\mu(\omega_t \mid b_t)$ chooses which option to activate.  
The induced turn distribution then becomes
$$
P_\theta(z_t \mid b_t)
=
\sum_{\omega \in \mathcal{W}}
\mu(\omega \mid b_t)
\sum_{x \in [z_t]}
P_\theta^\omega(x \mid \text{turn}_{\lt t})
\,\mathbb{I}_{\mathrm{env}}(x, s_t),
$$
where $P_\theta^\omega$ is defined by $\sigma_\theta^\omega$ and $\beta^\omega$.  
Optimality holds whenever this marginal equals $\pi^*(\cdot \mid b_t)$ on the admissible turn space $\mathcal{Z}_{\mathrm{env}}(s_t)$, thus making each option a consistent micro realization of a high-level action.



[at the end we need to give a global picture writing the full policy optimization problem (basically global policy AND microcontrollers simultaneously) e.g. with a P.P.O like formulation starting from macropolicy into microcontrollers]




