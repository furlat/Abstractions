# Notation Reference & Consistency Guide

## Core Notation Dictionary

### States, Observations, Actions

| Symbol | Meaning | Notes |
|--------|---------|-------|
| $\mathcal{S}$ | State space | Hidden environment state |
| $s_t$ | True state at time $t$ | Generally unobservable |
| $s_0$ | Initial state | Treat as known/deterministic; condition on $s_0$ not $P(s_0)$ or $p(s_0)$ |
| $\mathcal{O}$ | Observation space | Use $y$ for observations, not $o$ |
| $y_t$ | Observation at time $t$ | Environment output (JSON, tool result, etc.) |
| $\mathcal{A}$ | Action space | Turn-level function calls |
| $a_t$ | Action at time $t$ | Equals $(f_t, x_t)$ in function-calling setting |
| $\mathcal{A}_{\text{env}}$ | Valid action subset | Actions parseable and executable by environment |

### Histories and Beliefs

| Symbol | Meaning | Notes |
|--------|---------|-------|
| $h_t$ | Observable history up to $t$ | $h_t = ((y_i, (f_i, x_i)))_{i < t}$ |
| $b_t$ | Belief (distribution over states) | $b_t = P(s_t \mid h_t, s_0)$ |
| $\Phi$ | Parsing function | $\Phi: \mathcal{H} \to \mathcal{S}_{\text{eff}}$ extracts stack from history |
| $\text{Stack}_t$ | Parsed agent stack | $\text{Stack}_t = \Phi(h_t)$ when parser exists |
| $\mathcal{S}_{\text{eff}}$ | Effective state space | Space of parsed stacks |

**KEY NOTE ON BELIEF**: 
- In general POMDP: $b_t$ is a *distribution* $P(s_t \mid h_t, s_0)$
- When $\Phi$ exists: belief *collapses* to point mass $b_t = \delta_{\Phi(h_t)}$
- This collapse transforms POMDP → History-Markov Model → MDP on $\text{Stack}_t$

### Kernels and Dynamics

| Symbol | Meaning | Notes |
|--------|---------|-------|
| $P(s' \mid s, a)$ | Transition kernel | How environment state evolves |
| $\Omega(y \mid s', a)$ | Observation kernel | **Use $\Omega$ consistently, not $P$ for observations** |
| $R(s, a)$ or $R(s, a, g)$ | Reward function | May be goal-conditioned |
| $\mathcal{G}$ | Goal space | User specifications, task objectives |

### Functions and Composition

| Symbol | Meaning | Notes |
|--------|---------|-------|
| $f_t$ | Function selected at time $t$ | From finite callable set |
| $x_t$ | Input to function $f_t$ | Must satisfy $x_t \in \mathcal{X}(s_t)$ |
| $\mathcal{X}(s_t)$ | Admissible inputs given state | Enforces compositionality |
| $(f_t, x_t)$ | Function call (action) | $a_t = (f_t, x_t)$ |

**COMPOSITIONALITY CONSTRAINT**: $x_t \in \{y_i \mid i < t\} \cup s_0$
- Inputs reference only prior outputs or initial objects
- Prevents "inventing" ungrounded data

### Tokens and Turns

| Symbol | Meaning | Notes |
|--------|---------|-------|
| $\tau_t$ | Token at position $t$ | Basic unit of LLM generation |
| $\tau_{<t}$ | Token prefix before $t$ | **Use $<$ consistently, not $\lt$** |
| $\text{turn}_t$ | Complete turn (token sequence) | $(\tau_{k_t}, \ldots, \tau_{k_{t+1}-1})$ |
| $k_t$ | Starting token index of turn $t$ | Marks SOT (start-of-turn) |
| EOT | End-of-turn token | Marks turn boundary |
| $P_\theta(\tau_t \mid \tau_{<t})$ | Token-level policy | Base autoregressive distribution |
| $P_\theta(\text{turn}_t \mid \text{turn}_{<t})$ | Turn-level policy | Aggregated from tokens |

**TURN PROBABILITY** (corrected to enforce first EOT):
$$P_\theta(\text{turn}_t) = \sum_{L} \left(\prod_{k=0}^{L-1} P_\theta(\tau_{k_t+k} \mid \tau_{<k_t+k}) \cdot \mathbb{I}[\tau_{k_t+k} \neq \text{EOT}]\right) \cdot P_\theta(\tau_{k_t+L} = \text{EOT} \mid \tau_{<k_t+L})$$

### Options (Hierarchical RL)

| Symbol | Meaning | Notes |
|--------|---------|-------|
| $\mathcal{W}$ | Option set | Not $\Omega$ (that's observation kernel) |
| $\omega$ | Specific option | Temporally extended action |
| $\mathcal{I}^\omega$ | Initiation set for option $\omega$ | When option is admissible |
| $\pi_\theta^\omega$ | Token-level policy within option | Generates subsequence |
| $\beta^\omega$ | Termination condition for option | Aligns with EOT |
| $\mu$ | High-level policy over options | $\mu(\omega_t \mid b_t, g)$ |

### Policy Notation Conventions

| Context | Notation | Notes |
|---------|----------|-------|
| Agent distributions | $P_\theta(\cdot)$ or $\pi_\theta(\cdot)$ | Subscript $\theta$ for learned parameters |
| Environment distributions | $P(\cdot)$ | No subscript |
| Turn-level policy | $\pi(a_t \mid b_t)$ | Can write as $P_\theta(\text{turn}_t \mid h_{<t})$ |
| Behavioral policy | $P_\theta(f_t, x_t \mid b_t, s_0)$ | Includes initial objects |

---

## Conceptual Bridging Notes

### 1. Belief Collapse: POMDP → MDP

**The Question**: When does $b_t = P(s_t \mid h_t, s_0)$ collapse from a distribution to a point mass?

**The Answer**: When a parsing function $\Phi: \mathcal{H} \to \mathcal{S}_{\text{eff}}$ exists such that:
$$P(s_{t+1} \mid h_{\leq t}, a_t) = P(s_{t+1} \mid \Phi(h_t), a_t)$$

Then: $b_t = \delta_{\Phi(h_t)}$ (point mass), and we have an **MDP on the parsed stack**.

**Where to add this**: 
- At start of "Can We Make It an MDP?" section, add:
  > "In the general POMDP, the agent maintains a belief distribution $b_t = P(s_t \mid h_t, s_0)$ over hidden states. The key question is: *when does this belief collapse to a point mass?* This happens when the visible history is sufficient to deterministically reconstruct the environment state, transforming the POMDP into a history-Markov model and ultimately an MDP on the parsed state."

### 2. Valid Actions and Joint Support

**The Constraint**: $\pi(a_t \mid b_t) \propto P_\theta(\text{turn}_t \mid \text{turn}_{<t}) \cdot \mathbb{I}[\text{turn}_t \in \mathcal{A}_{\text{env}}]$

**What it means**: The agent's effective policy is the LLM's autoregressive distribution *restricted* to the subset of turns that:
1. Parse successfully into function calls
2. Have inputs satisfying $x_t \in \mathcal{X}(s_t)$

**Where to clarify**:
- After "Turns as Options" section, add:
  > "Under the valid-action constraint $x_t \in \mathcal{X}(s_t)$, each admissible option $\omega$ produces turns that parse into typed function compositions over the current agent stack $\Phi(h_t)$; options that would yield ungrounded inputs have zero support."

### 3. Role of $s_0$

**Why condition on $s_0$ separately?**

$s_0$ contains:
- Initial available objects (not in $h_t$)
- Tool/function definitions
- Database schemas, constants
- Any persistent context not logged in history

**Where to add**:
- In "Observation Space" section, after defining $h_t$:
  > "Note that $s_0$ represents the initial configuration: available tools, constants, and objects that persist throughout the interaction but do not appear in $h_t$."

### 4. Compositionality: Two Formulations

**General**: $x_t \in \mathcal{X}(s_t)$ (admissible inputs given state)

**Strict**: $\mathcal{X}(s_t) = \{y_i \mid i < t\} \cup s_0$ (direct references only)

**Recommended clarification**:
- In "Valid actions and compositionality":
  > "In practice, we enforce the **strict compositionality constraint** $\mathcal{X}(s_t) = \{y_i \mid i < t\} \cup s_0$, meaning inputs must reference only objects already present in the environment: either initial objects from $s_0$ or outputs $y_i$ from previous function calls."

### 5. Determinism in Pure Functional Regime

**For MDP collapse, need**:
1. Immutability (no side effects)
2. **Determinism** (or logged stochasticity)
3. Complete serialization

**Where to strengthen**:
- At start of "When does such a parser exist?":
  > "A natural sufficient condition is the **pure functional regime** with **determinism**, immutability, and no side effects beyond return values."

---

## Specific Formula Replacements

### Replace in POMDP Frame

**Old**:
$$b_t = P(s_t \mid h_t, P(s_0))$$

**New**:
$$b_t = P(s_t \mid h_t, s_0)$$

---

### Replace in Environment Response

**Old**:
"In POMDP terms, $P(s_{t+1} \mid s_t, f_t, x_t)$ corresponds to the transition kernel, and $P(y_t \mid s_t, f_t, x_t)$ to the observation kernel $\Omega(o_t \mid s_t, a_t)$."

**New**:
"In POMDP terms, $P(s_{t+1} \mid s_t, f_t, x_t)$ corresponds to the transition kernel, and $P(y_t \mid s_t, f_t, x_t)$ to the observation kernel $\Omega(y_t \mid s_t, a_t)$."

---

### Replace in MDP Section

**Old**:
$$b_t(s) = P(s_t = s \mid h_t, P(s_0))$$

**New**:
$$b_t(s) = P(s_t = s \mid h_t, s_0)$$

**Old**:
$$P(s_t \mid h_t, P(s_0)) = \mathbb{I}[s_t = \text{construct}(s_0, h_t)]$$

**New**:
$$P(s_t \mid h_t, s_0) = \mathbb{I}[s_t = \text{construct}(s_0, h_t)]$$

---

## Global Find-Replace Operations

1. **History indices**: `\lt` → `<` throughout
   - `$\tau_{\lt t}$` → `$\tau_{<t}$`
   - `$\text{turn}_{\lt t}$` → `$\text{turn}_{<t}$`
   - `$h_{\le t}$` → `$h_{\leq t}$` (if using $\leq$) or `$h_{<t+1}$`

2. **Observation variable**: Ensure all observation kernels use $y$, not $o$
   - `$\Omega(o \mid s', a)$` → `$\Omega(y \mid s', a)$`

3. **Hyphenation**: "end of turn" → "end-of-turn" (when used as compound modifier)

---

## Simplified Options Formula (Optional Replacement)

**Current** (overcomplicated):
$$P_\theta(\text{turn}_t \mid b_t, g) \propto \sum_{\omega \in \mathcal{W}} \mu(\omega \mid b_t, g) \sum_{L} \left(\prod_{k=0}^{L-1} \pi_\theta^{\omega}(\tau_{k_t+k} \mid \tau_{<k_t+k}, b_t)\right) \beta^\omega(\tau_{k_t+L} = \text{EOT} \mid \tau_{<k_t+L}, b_t) \cdot \mathbb{I}[\text{turn}_t \in \mathcal{A}_{\text{env}}]$$

**Simplified alternative**:
$$P_\theta(\text{turn}_t \mid h_{<t}, g) = \sum_{\omega \in \mathcal{W}} \mu(\omega \mid h_{<t}, g) \cdot P_\theta^\omega(\text{turn}_t \mid h_{<t}) \cdot \mathbb{I}[\text{turn}_t \in \mathcal{A}_{\text{env}}]$$

where $P_\theta^\omega(\text{turn}_t \mid h_{<t})$ encapsulates the token-level generation and stopping.

**Note**: The simplified version hides the token-level detail but is cleaner. Choose based on how much you want to emphasize the internal structure of options.

---

## Minor Wording Fixes

1. **Intro**: "end of turn tokens (EOTs)" → "end-of-turn tokens (EOTs)"

2. **Intro paragraph**: 
   - Old: "This step will give us a target for the abstractions that must be derived from the underlying transformer model for a proper POMDP to emerge."
   - New: "This gives us a target for the abstractions we must extract from the transformer so that a proper POMDP emerges."

3. **Avoid redundant display**: In "From Tokens to Turns", the line
   $$P_\theta(\text{turn}_t \mid \text{turn}_{<t})$$
   appears both in prose and standalone. Keep first occurrence, drop standalone repeat.

---

## Summary Checklist for Editing Pass

- [ ] Replace all $P(s_0)$ or $p(s_0)$ with conditioning on $s_0$ directly
- [ ] Unify observation symbol: use $y$ consistently, update $\Omega(y \mid s', a)$
- [ ] Global replace: `\lt` → `<` for all history/prefix notation
- [ ] Add belief collapse explanation at start of "Can We Make It an MDP?"
- [ ] Add note on $s_0$ contents in "Observation Space" section
- [ ] Strengthen determinism requirement in pure functional regime
- [ ] Add option admissibility note after "Turns as Options"
- [ ] Fix turn probability formula to enforce first EOT
- [ ] Clarify strict compositionality in "Valid actions" section
- [ ] Standardize $P_\theta$ (agent) vs $P$ (environment) convention
- [ ] Soften or defer functor claim in final paragraph