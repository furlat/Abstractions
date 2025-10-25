
# Learning from the Observable Process

### Constrained Training and Minimal Traces

**Part III of the LLM Agent Series**

---

## Overview

This post unifies the practical side of the previous theoretical work.
Parts I and II established the **POMDP view of language-model agents** and the **categorical structure of their computing environment**.
Here we move to **training and data refinement**: how to make the observable process (Z) more learnable and less noisy.

The guiding idea:

> LLM agents learn on observable traces (Z=(O,A)).
> We can make those traces far more efficient by
>
> 1. separating learning signals,
> 2. constraining generation to valid actions, and
> 3. pruning each trajectory to its minimal causal path.

---

## 1 · Two Learning Channels in (Z)

The joint process factorizes as

[
P(O_{t+1},A_t\mid H_t)
= \pi_\theta(A_t\mid H_t),P_\psi(O_{t+1}\mid H_t,A_t)
]

| Channel                 | Trained on        | Objective                          | Effect                        |
| ----------------------- | ----------------- | ---------------------------------- | ----------------------------- |
| **Policy** (\pi_\theta) | Agent turns       | Reinforcement learning on feedback | Improves control              |
| **Predictor** (P_\psi)  | Environment turns | Next-token prediction              | Improves belief / world model |

We **mask** gradients so the two objectives do not interfere:

* RL affects **agent spans** only.
* NTP affects **environment spans** only.

A soft **KD/KL regularizer** stabilizes the policy between updates.

---

## 2 · Grammar Constraints (Deterministic Logit Processor)

The option space—the set of valid turn sequences—acts like a **formal grammar**.
Represent it as an automaton or trie (\mathcal{L}_{\text{valid}}) and use it to mask logits during decoding:

[
\tilde{\ell}*t[v] =
\begin{cases}
\ell_t[v] & \text{if prefix}\in \text{Prefix}(\mathcal{L}*{\text{valid}}),\
-\infty & \text{otherwise.}
\end{cases}
]

**Benefits**

* Only executable turns are sampled → lower exploration cost.
* Invalid trajectories disappear → effective sample size ↑.
* Gradient variance ↓, stability ↑.
* Token-level entropy drops to the same scale as high-level action entropy.

---

## 3 · Trace Pruning and Short-Path Reconstruction

Given purity or logged side-effects, we can compress trajectories:

1. **Parse** raw trace (Z) into a typed stack graph (objects ↔ outputs, edges ↔ function calls).
2. **Backward slice** from terminal goals → keep only causally relevant calls.
3. **Merge** identical subterms and drop dominated edges.
4. **Shortest-path** search to the goal (A* or Dijkstra on the slice).
5. **Rebuild** the minimal sequence (Z') and validate equivalence of outputs.

Result: a **minimal, bisimilar trace** carrying identical reward information but shorter and cleaner.

---

## 4 · Unified Training Objective

[
\min_{\theta,\psi};
-\mathbb E!\left[R
\sum_{t\in A}\log\pi_\theta^{\text{DLP}}(\tau_t\mid\tau_{<t})\right]

* \lambda_{\text{env}}
  !!\sum_{t\in O}!!
  -\log P_\psi^{\text{DLP}}(\tau_t\mid\tau_{<t})
* \lambda_{\text{KD}},
  D_{\mathrm{KL}}!\big(
  \pi_\theta^{\text{DLP}}|\pi_{\text{teacher}}^{\text{DLP}}\big)
  ]

All losses computed with **grammar-masked logits**
and **cleaned traces** (Z').

---

## 5 · Variance and Sample-Efficiency Gains

Let (T_{\text{raw}}) = tokens per episode, (T_{\min}) = after pruning.
Let (\rho) = fraction of invalid trajectories removed by grammar constraints.

[
\frac{\mathrm{Var}[g_{\text{clean+constr}}]}{\mathrm{Var}[g_{\text{raw}}]}
;\lesssim;
\underbrace{\alpha=T_{\min}/T_{\text{raw}}}*{\text{shorter traces}}
\cdot
\underbrace{(1-\rho)}*{\text{no invalid samples}}
]

If (\alpha=0.5,;\rho=0.25)
→ variance ≈ 0.375 × original (≈ 62 % reduction).

**Intuitive summary**

* Shorter traces → linear variance reduction.
* Grammar enforcement → removes dead rollouts & low-entropy per token.
* Combined → lower-variance REINFORCE even with terminal 0/1 reward.

---

## 6 · Blockwise Variance Collapse (Intuition)

Two noise sources:

* **High-level:** turn/option selection.
* **Low-level:** token generation inside each turn.

Grammar constraints make the **low-level generator deterministic blockwise**,
so token-level degrees of freedom collapse to the same variability as the high-level policy.

[
\mathrm{Var}[g_{\text{constrained}}]
\approx
\mathrm{Var}[g_{\text{high-level}}]
]

The sequence-level variance becomes that of the turn process, not of the raw token process.

---

## 7 · Outcomes

* Every token generated or trained on is **semantically valid**.
* Each trajectory is a **minimal causal path** to reward.
* Policy-gradient variance and entropy both drop.
* Predictive model learns a sharper, more Markov belief.
* Overall sample efficiency and stability improve dramatically.

---

## 8 · Position in the Series

| Part    | Theme                             | Focus                         |
| ------- | --------------------------------- | ----------------------------- |
| **I**   | Tokens → Agency                   | POMDP & options formalism     |
| **II**  | Environment as Category           | typed composition & semantics |
| **III** | **Training + Trace Optimization** | efficient learning from (Z)   |

---

**One-line takeaway**

> By separating learning signals, constraining the option space, and pruning traces to their minimal causal paths, we turn raw stochastic token streams into structured, low-variance data that reveal the true agency of language-model policies.

---
