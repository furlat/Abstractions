# From Laplace’s demon to the **ledger demon**

* **Laplace’s demon** (1814) assumes an intellect that **knows at an instant** the exact position and momentum of every particle in the universe and therefore can compute *both* the past and the future.
* In modern information‐theoretic language that means the demon must **store in working memory** a complete state description $x_t$ and, as time flows, **update** a posterior

  $$
     p(x_{t+1}\,|\,y_{1..t+1})\;=\;\mathcal F\!\bigl(p(x_{t}\,|\,y_{1..t}),\,y_{t+1}\bigr)
  $$

  for *every* degree of freedom.
* Each update is a read–modify–write cycle; the demon’s memory is therefore a **growing ledger** of micro‑state information.
  We call that idealised agent the **ledger demon**.

\### 2 Why the ledger explodes

Let

* $N_\text{dof}$ = number of independent degrees of freedom in the causal horizon
* $H$ = Shannon entropy per degree of freedom (≈ few bits for coarse‑grained state)

Then the demon’s memory demand is

$$
   S_{\text{ledger}}(t)\;=\;N_\text{dof}(t)\,H.
$$

Because $N_\text{dof}\propto V(t)$ (volume of the light‑cone), $S$ grows as $ct^3$ in flat space.
The **marginal bits written per second** therefore grow as $O(t^2)$.

\### 3 Thermodynamic back‑reaction

Landauer (1961): *erasing or irreversibly overwriting* one bit dissipates
$Q_{\min}=kT\ln 2$.

*Heat generation rate* of the demon becomes

$$
   \dot Q(t) \;=\; \frac{dS_{\text{ledger}}}{dt}\,kT\ln 2
               \;=\; O(t^2)\,kT\ln 2.
$$

With no external coolant the ledger demon’s temperature rises without
bound—**heat death in finite proper time**.

\### 4 Relativistic impossibility of instantaneous information

The demon cannot *obtain* the full micro‑state faster than light:

* To synchronise a sphere of radius $r$ it must wait at least $r/c$.
* During that latency the state evolves; the ledger is already stale.

Hence *complete* knowledge demands that the demon’s spatial extent shrink to zero **and** its mass tend to infinity (so signals arrive instantly in proper frames) – precisely the conditions of a black‑hole singularity.

\### 5 Black‑hole horizon as the ultimate ledger

Bekenstein–Hawking entropy

$$
   S_{\text{BH}}=\frac{kA}{4\ell_P^2}
$$

shows that the **maximum bits storable in radius $R$** scale as area, not volume.
Trying to pack more bits than $S_{\text{BH}}$ collapses the region into a black hole.
A Schwarzschild horizon therefore *is* the only physical medium that can host Laplace’s infinite ledger – but all information is trapped behind the horizon and only leaks out slowly as near‑thermal Hawking radiation.
So the ledger demon reaches omniscience at the cost of **absolute causal isolation** and maximal entropy in its neighbourhood.

\### 6 Bremermann‑Margolus rate bound

Even if memory were free, *computation* is limited:

$$
   \text{ops s}^{-1} \;\le\; \frac{2E}{\pi\hbar}.
$$

A stellar‑mass black hole delivers \~10⁴⁸ ops s⁻¹, still woefully insufficient to integrate the universal Hamiltonian in real time.  Omniscience is doubly forbidden.

\### 7 What finite agents (brains or CPUs) must do instead

* **Sample only a mesoscopic state** $x_t^{(\text{subset})}$ sufficient for their tasks.
* **Approximate updates** with bounded‑precision filters (population codes, 8‑bit tensor cores).
* **Permanently discard** low‑value hypotheses to limit ledger growth; erasure heat is paid in discrete “garbage‑collection” epochs (sleep replay, data‑centre log rotation).
* **Cache / consolidate** recurring sub‑computations into low‑energy hardware or myelinated tracts to cut the marginal Landauer bill.

The *inner book‑keeper* survives in a **budgeted form**: it writes ledgers only where expected utility per joule is positive.

\### 8 Connection to “mental energy”

* **Subjective effort** ∝ current rate of high‑precision bookkeeping (spike rate, catecholamine up‑regulation).
* **Fatigue** emerges when available metabolic free energy drops and the scheduler must lower the notebook’s resolution (wider priors, mind‑wandering).
* **Flow / insight** is the transient period where ledger updates yield large information gain per joule, justifying sustained gating.

\### 9 Philosophical moral

The ledger demon exemplifies an ultimate tension:

1. **Epistemic hubris** (wish for omniscience) explodes entropy and is self‑extinguishing.
2. **Epistemic asceticism** (selective ignorance) preserves free energy for acting in the world.

All practical intelligences, biological or artificial, live on that
knife‑edge: **record just enough of the cosmic ledger that the saved information exceeds the heat bill of writing it**.
