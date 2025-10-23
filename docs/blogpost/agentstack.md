

###  From Mutable Environments to the Agent Stack
We have established that mutable environments such as a Python REPL create a fundamental challenge: even pure functions become entangled with state through their interaction with shared memory. Let us now complete the POMDP formulation by examining how this complexity manifests mathematically, and then demonstrate how the pure functional case leads to a remarkable simplification—one where the agent can maintain perfect tracking of the environment through what we call the agent stack.
State Space in Mutable Environments
The environment state st∈Ss_t \in \mathcal{S}
st​∈S represents the complete computational state at time tt
t. For a Python REPL, this includes:


Memory state: Mt={(vi,oi)}M_t = \{(v_i, o_i)\}
Mt​={(vi​,oi​)} where viv_i
vi​ are variable names and oio_i
oi​ are objects

Function definitions: F={f1,...,fn}F = \{f_1, ..., f_n\}
F={f1​,...,fn​} (typically static)

Type assignments: τ:Mt→T\tau: M_t \to \mathcal{T}
τ:Mt​→T mapping objects to types


The crucial observation is that in mutable environments, the cardinality of MtM_t
Mt​ can vary dynamically, and objects oio_i
oi​ can be modified in place. This creates a state space whose structure evolves:

∣S∣=∏i=1∣V∣∣Oi∣ki|\mathcal{S}| = \prod_{i=1}^{|V|} |\mathcal{O}_i|^{k_i}∣S∣=i=1∏∣V∣​∣Oi​∣ki​
where VV
V is the set of possible variable names, Oi\mathcal{O}_i
Oi​ represents possible object values for type ii
i, and kik_i
ki​ counts active variables of that type.

Action Space and Execution
An action at=(ft,xt)a_t = (f_t, x_t)
at​=(ft​,xt​) consists of:


Function selection: ft∈Ff_t \in F
ft​∈F
Input specification: xt∈Dom(ft)x_t \in \text{Dom}(f_t)
xt​∈Dom(ft​)

The action space is thus: A=⋃f∈F{f}×Dom(f)\mathcal{A} = \bigcup_{f \in F} \{f\} \times \text{Dom}(f)
A=⋃f∈F​{f}×Dom(f)
In the mutable case, the input xtx_t
xt​ often contains
references to objects in MtM_t
Mt​, creating implicit dependencies:

xt=ρ(Mt,θt)x_t = \rho(M_t, \theta_t)xt​=ρ(Mt​,θt​)
where ρ\rho
ρ is a reference resolution function and θt\theta_t
θt​ are the symbolic parameters provided by the agent.

Observation Function and Partial Observability
The observation function maps states and actions to observable outputs:

O:S×A→Y\mathcal{O}: \mathcal{S} \times \mathcal{A} \to YO:S×A→Y
For stateful functions in mutable environments:

O(st,(ft,xt))=g(st,ft,xt)\mathcal{O}(s_t, (f_t, x_t)) = g(s_t, f_t, x_t)O(st​,(ft​,xt​))=g(st​,ft​,xt​)
where gg
g captures both the computed result and any side effects that modify sts_t
st​.

The agent observes only the output yty_t
yt​, not the full state change, creating genuine partial observability. The agent must infer changes to MtM_t
Mt​ from the sequence of outputs.

Belief State and Uncertainty
Since the agent doesn't directly observe sts_t
st​, it maintains a belief state:

bt(s)=P(st=s∣ht,s0)b_t(s) = P(s_t = s \mid h_t, s_0)bt​(s)=P(st​=s∣ht​,s0​)
This can be updated recursively using Bayes' rule:

bt+1(s′)=P(yt∣s′,at)∑sP(s′∣s,at)bt(s)P(yt∣ht,at)b_{t+1}(s') = \frac{P(y_t \mid s', a_t) \sum_s P(s' \mid s, a_t) b_t(s)}{P(y_t \mid h_t, a_t)}bt+1​(s′)=P(yt​∣ht​,at​)P(yt​∣s′,at​)∑s​P(s′∣s,at​)bt​(s)​
In practice, maintaining this belief exactly is intractable due to the combinatorial explosion of possible memory configurations.
The Pure Functional Simplification
Eliminating State Entanglement
In the pure functional case, we eliminate side effects entirely. Every function call produces a new object without modifying existing ones:
P(yt∣ft,xt,st)=P(yt∣ft,xt)P(y_t \mid f_t, x_t, s_t) = P(y_t \mid f_t, x_t)P(yt​∣ft​,xt​,st​)=P(yt​∣ft​,xt​)
This conditional independence has profound implications. The state transition becomes deterministic and append-only:
Mt+1=Mt∪{(vnew,ft(xt))}M_{t+1} = M_t \cup \{(v_{new}, f_t(x_t))\}Mt+1​=Mt​∪{(vnew​,ft​(xt​))}
where vnewv_{new}
vnew​ is a fresh variable name (or implicit reference).

The Markov Property Recovery
With pure functions, the history hth_t
ht​ becomes a
sufficient statistic for the state:
st=s0⊕⨁i=1t−1(fi,xi,yi)s_t = s_0 \oplus \bigoplus_{i=1}^{t-1} (f_i, x_i, y_i)st​=s0​⊕i=1⨁t−1​(fi​,xi​,yi​)
where ⊕\oplus
⊕ denotes the deterministic state construction operator. This means:

P(st∣ht,s0)=1[st=construct(ht,s0)]P(s_t \mid h_t, s_0) = \mathbb{1}[s_t = \text{construct}(h_t, s_0)]P(st​∣ht​,s0​)=1[st​=construct(ht​,s0​)]
The belief state collapses to a point mass—there is no uncertainty about the environment state given the history.
The Agent Stack: Optimal State Compression
In pure functional environments, we can introduce the concept of the agent stack, a compressed representation that maintains only the unique (vi,oi)(v_i, o_i)
(vi​,oi​) pairs needed for future computation.

Define the equivalence relation:

(vi,oi)∼(vj,oj)  ⟺  oi=oj∧τ(oi)=τ(oj)(v_i, o_i) \sim (v_j, o_j) \iff o_i = o_j \land \tau(o_i) = \tau(o_j)(vi​,oi​)∼(vj​,oj​)⟺oi​=oj​∧τ(oi​)=τ(oj​)
The agent stack is then:

Stackt=Mt/∼={[(vi,oi)]∼}\text{Stack}_t = M_t / \sim = \{[(v_i, o_i)]_\sim\}Stackt​=Mt​/∼={[(vi​,oi​)]∼​}
This represents the minimal sufficient memory for perfect state tracking.
Stack Evolution Dynamics
The stack evolution follows simple rules:

**Push**: When yt=ft(xt)y_t = f_t(x_t)
yt​=ft​(xt​) is computed:

 $$\text{Stack}_{t+1} = \text{Stack}_t \cup \{[(v_{new}, y_t)]_\sim\}

Deduplication: If yty_t
yt​ already exists in the stack:

 $$\text{Stack}_{t+1} = \text{Stack}_t
   The agent simply maintains a reference to the existing object.

**Garbage Collection**: Objects unreachable from current computation can be removed:

 $$\text{Stack}_{t+1} = \{[(v, o)]_\sim \in \text{Stack}_t : \text{reachable}(o, \text{current\_context})\}


Information-Theoretic Properties
The compression ratio achieved by the agent stack is:

ρ=∣Mt∣∣Stackt∣\rho = \frac{|M_t|}{|\text{Stack}_t|}ρ=∣Stackt​∣∣Mt​∣​
In typical execution patterns with significant reuse, ρ\rho
ρ grows linearly with tt
t, while ∣Stackt∣|\text{Stack}_t|
∣Stackt​∣ grows logarithmically:

∣Stackt∣=O(log⁡t)|\text{Stack}_t| = O(\log t)∣Stackt​∣=O(logt)
This is because many computations reference the same objects repeatedly.
Perfect Observability Through History
In the pure case, the agent achieves perfect observability through history alone:
H(st∣ht)=0H(s_t \mid h_t) = 0H(st​∣ht​)=0
This transforms the POMDP into an MDP with a particular structure where the state is perfectly reconstructible from observations.