# From Next Token Prediction to Agency

### tags: @vision @abstractions

Building LLM agents has never been easier, with API providers directly exposing tool calls as a first-class primitive and a myriad of opinionated frameworks each harnessing the API in a slightly different way. This fertile ground has led to such a proliferation of open-source projects and startups that it is now common to conflate agents with LLMs interacting with some external system. Yes, we are finally able to write adaptive workflows, or even goal-oriented programs and sophisticated coding assistants, but the result often feels stitched together. There seems to be a disconnect between the way we conceptualize and train LLMs and the way we expect intelligent agents to behave. We generally understand agency as a high-level cognitive process involving abstractions like observations, states, actions, and rewards. On the other hand, we understand underlying language models through the lens of transformers approximating a finer-grained token-level stochastic process. Throughout this post, we will refer to these two different yet coexisting perspectives as the macro-level (agentic) and micro-level (autoregressive) views.


Thankfully, both perspectives are amenable to mathematical formalization and have been explored by greater minds. Encouraged by the empirical certainty that LLM agents exist, we will formalize how an LLM can become an agent. We will draw on existing abstractions and known equivalences to construct a narrative that lifts the autoregression of symbolic sequences into a coherent theory of agentic decision-making. Without claiming any secret LLM training sauce, I hope to shed light on esoteric properties of LLM agents that follow from their mathematical nature. 


We then relax the exact-tokenization assumption and consider agentic traces where each action and observation is composed of a sequence of symbols. We show how the original next-token formulation of the transformer, together with special turn-delimiting tokens, can express the probability of these sequences as a function of turns rather than raw token history. This gives us a clear view of two distinct problems and their connection. At the macro level, we have a turn-based POMDP with its own action, observation, and hidden state spaces. The agent observes the history of actions and observations and emits a new action; if valid, the environment updates its hidden state, emits a new observation that is appended to the history, and the process repeats. At the token level, the LLM observes a serialized representation of this history where each turn is separated by a special token and generates a new sequence of tokens; if valid, the environment emits a new sequence that is appended to the model context, and the process repeats. The connection is now evident: the macro process exists when the micro process generates sequences recognized as valid actions by the environment. We can think of the LLM as an optimizing agent when its micro-level token choices induce high-level actions that lead toward high-reward states.

While this picture is getting complicated, this sort of problem is not novel in reinforcement learning. Think of a robotic arm controlled by a continuous controller that needs to play a video game using a keyboard. The high-level problem is the video game, while the low-level problem is the motor control of the arm. This setup is often interpreted as hierarchical reinforcement learning, where local policies generate temporally extended actions modeled as temporal options, while the high-level policy chooses which option to execute.

By the end of this post, I hope to have persuaded you that we can interpret an LLM interacting with an environment as a hierarchical POMDP, where the transformer implements micro-level controllers at the level of options that compose into a coherent high-level policy. 


### From Next-Token Prediction to Decision-Making

In the previous section we derived the macro-level decision-making problem as a decomposition of the resulting stochastic process connecting the observable autoregressive dynamics to the underlying agent–environment relationship. The one caveat is that we were reasoning directly in terms of autoregression over high-level symbols, implicitly assuming that the transformer’s token space coincides with the union of the alphabets $\mathcal{A}$ and $\mathcal{O}$, together with their Cartesian product $\mathcal{A} \times \mathcal{O}$. In this section we relax that assumption. The underlying process operates on a much finer-grained alphabet $\Sigma$ whose only algebraic structure is right-side concatenation, and the coarser alphabet of turns $\mathcal{Z}$ is induced as a quotient space defined by special delimiter tokens. This construction allows the next-token process to realize an effective agent–environment interface where each completed segment of tokens corresponds to a full turn $(a_t, o_t)$ in the macro POMDP. Crucially, this turn-level view aligns with the **unifilar** structure of the environment, where each emitted observation $o_{t+1}$ simultaneously marks the completion of a turn and determines the unique causal branch of the environment’s latent transition.

We start from the basic autoregressive formulation of a language model, which defines a probability distribution over token sequences of length $T$ conditional on the semi-infinite prefix of previously generated tokens:

$$
P_\theta(\tau_{1:T}) = \prod_{t=1}^{T} P_\theta(\tau_t \mid \tau_{< t})
$$

where $\tau_t$ denotes the token generated at position $t$, and $\tau_{< t}$ represents the prefix of previously generated tokens.
This defines a left-to-right stochastic process that samples each token sequentially, conditioned on the textual history.
In POMDP terms, this autoregressive process defines the *micro-dynamics* of the agent’s internal policy $\pi$, acting within the observation space defined by its evolving textual context.

### From Tokens to Turns to Actions and Observations

To lift this token-level process into a decision-making framework compatible with the POMDP perspective, we segment the token stream into turns using special control tokens inserted during assistant post-training.
These tokens provide explicit syntactical boundaries between:

1. the agent’s generations (tool calls or textual reasoning),
2. the environment’s responses, and
3. the user’s requests.

Each turn thus corresponds to a higher-level event in the stochastic process, marking a complete interaction step between the agent and the environment.
This segmentation allows us to reinterpret the autoregressive process in terms of turn-level sequences, which naturally play the role of actions and observations within the POMDP framework.

Let each turn be the contiguous block of tokens

$$
\text{turn}_t = (\tau_{k_t}, \ldots, \tau_{k_{t+1}-1})
$$

ending with a distinguished delimiter token $\text{EOT}$.
We can then define the induced distribution over turns as

$$
P_\theta(\text{turn}_{1:N}) = \prod_{t=1}^{N} P_\theta(\text{turn}_t \mid \text{turn}_{< t})
$$

Each conditional distribution represents the behavioral policy of the agent at the turn level. It describes how the model generates the next complete action sequence—its next decision—conditioned on its full observation history.

### Stopping times and measurability

Let $(\mathcal{F}_k)_{k \ge 0}$ be the natural filtration generated by the token sequence, where $\mathcal{F}_k = \sigma(\tau_{1:k})$.
Fix the distinguished delimiter $\text{EOT} \in \Sigma$.
Define the stopping times for turn boundaries by

$$
\kappa_1 = \inf\{\, k \ge 1 : \tau_k = \text{EOT} \,\},
\qquad
\kappa_{t+1} = \inf\{\, k > \kappa_t : \tau_k = \text{EOT} \,\},
\qquad
\kappa_0 := 0.
$$

Each $\kappa_t$ is an $(\mathcal{F}_k)$-stopping time, and the $t$-th completed turn block is

$$
\text{turn}_t = (\tau_{\kappa_{t-1}+1}, \ldots, \tau_{\kappa_t}).
$$

The mapping from a token path to its corresponding finite sequence of completed turns is therefore measurable with respect to the filtration.
This formalizes that the end of a turn is determined by information available at the stopping time $\kappa_t$.
Under the unifilar formulation of the environment, the realized observation $o_t$ that closes turn $t$ uniquely determines the next environment branch, implying that the latent generator of the observable turn process can be taken to be the environment state $s_t$ itself. This property guarantees **synchronizability**: the macro process over turns is informationally equivalent to the hidden-state process $(s_t)$.

### Quotient mapping by independent parsers

Let $\Sigma$ be the token alphabet and $\Sigma^*$ the set of finite token strings.
Define two token-level parsers

$$
\rho_{\mathcal{A}} : \Sigma^* \to \mathcal{A},
\qquad
\rho_{\mathcal{O}} : \Sigma^* \to \mathcal{O}
$$

that independently extract the action and the observation components from a completed turn string.
Define the joint parser

$$
\rho_{\mathcal{Z}}(x) = \big(\rho_{\mathcal{A}}(x), \rho_{\mathcal{O}}(x)\big) \in \mathcal{A} \times \mathcal{O}.
$$

Introduce the equivalence relation on $\Sigma^*$

$$
x \sim y
\quad\Longleftrightarrow\quad
\rho_{\mathcal{Z}}(x) = \rho_{\mathcal{Z}}(y).
$$

The quotient space of turn semantics is then

$$
\mathcal{Z} = \Sigma^* / \sim,
\qquad
[z] = \{\, x \in \Sigma^* : \rho_{\mathcal{Z}}(x) = z \,\},
\qquad
z = (a_t,o_t) \in \mathcal{A} \times \mathcal{O}.
$$

For any completed turn block $x = \text{turn}_t$ we write $z_t = \rho_{\mathcal{Z}}(x)$ and $x \in [z_t]$.

### Class-marginalization from tokens to turns

The token model induces a turn-level distribution by marginalizing over all token realizations in the equivalence class of the parsed turn.
We restrict this marginalization to **prefix-free** token strings that contain exactly one delimiter at the end and none internally. Let $L_{z_t} \subseteq [z_t]$ denote this parser-recognized language of completed turns. Then

$$
P_\theta(z_t \mid \text{turn}_{< t})
=
\sum_{x \in L_{z_t}}
P_\theta\big(x \mid \text{turn}_{< t}\big),
$$

where for any $x = (\tau_{m}, \ldots, \tau_{n})$ ending with the delimiter,

$$
P_\theta\big(x \mid \text{turn}_{< t}\big)
=
\prod_{k=m}^{n}
P_\theta\big(\tau_k \mid \tau_{< k}\big).
$$

This recovers the desired turn-level process from the micro-level autoregression while ensuring that each turn is counted exactly once and ends at the first valid delimiter.

### Concatenation compatibility and class projection

Define the projection
$$
q : \Sigma^* \to \mathcal{Z},
\qquad
q(x) = [\,\rho_{\mathcal{Z}}(x)\,].
$$

Let $\mathbin{\smallfrown}$ denote token concatenation and let $x \Vert y$ denote concatenation along turn boundaries, that is, $x$ ends at a delimiter and $y$ begins immediately after.
Then concatenation followed by class projection is compatible with turn concatenation modulo delimiters:

$$
q(x \Vert y) = q(x) \odot q(y),
$$

where $\odot$ is the induced concatenation of equivalence classes at the turn level.
In particular, if $x \in [z_t]$ and $y \in [z_{t+1}]$ with both ending at delimiters, then $x \Vert y \in [z_t] \odot [z_{t+1}]$.
This factorization justifies composing probabilities turn by turn, since the projection $q$ respects the segmentation defined by the stopping times $\kappa_t$.

### Admissibility and semantic support

The parser-induced turn space interacts with the environment through admissibility constraints.
For each environment state $s_t$, define the admissible class set

$$
\mathcal{Z}_{\mathrm{env}}(s_t) \subseteq \mathcal{Z},
$$

and the corresponding semantic indicator

$$
\mathbb{I}_{\mathrm{env}}(x, s_t) = \mathbb{I}\!\big[q(x) \in \mathcal{Z}_{\mathrm{env}}(s_t)\big].
$$

In practice, $\mathcal{Z}_{\mathrm{env}}(s_t)$ is realized by a state-conditioned recognizer $\mathcal{G}(s_t)$ defining the language of admissible token sequences for that environment state. The recognizer constrains the micro policy during decoding, ensuring that only syntactically valid and executable actions are produced. The induced set of admissible high-level actions is then

$$
\mathcal{A}_{\mathrm{env}}(s_t) = \{\, a : \exists\, o \text{ s.t. } (a,o) \in \mathcal{Z}_{\mathrm{env}}(s_t) \,\},
$$

which aligns the grammar-constrained token policy with the reinforcement learning action space.

### Induced macro kernels from micro dynamics

We now return to the parameterization $\theta = (\theta_\pi, \theta_{\mathcal{M}})$ introduced in the POMDP formulation.
At the token level, the autoregressive model defines a generator

$$
\sigma_\theta(\tau_k \mid \tau_{< k})
=
P_\theta(\tau_k \mid \tau_{< k}),
$$

whose path probability for a completed turn block $x = (\tau_m, \ldots, \tau_n)$ ending at the delimiter is

$$
P_\theta(x \mid \text{turn}_{< t}) = \prod_{k=m}^{n} \sigma_\theta(\tau_k \mid \tau_{< k}).
$$

Through the equivalence relation $x \sim y$ induced by the joint parser $\rho_{\mathcal{Z}}$, we recover the class-marginal turn distribution

$$
P_\theta(z_t \mid \text{turn}_{< t}, s_t)
=
\sum_{x \in L_{z_t}}
P_\theta(x \mid \text{turn}_{< t}) \,
\mathbb{I}_{\mathrm{env}}(x, s_t).
$$

The induced process over turns then defines the macro-level transition kernel

$$
P_\theta(z_{t+1}, s_{t+1}, \hat{s}_{t+1} \mid s_t, \hat{s}_t)
=
P_\theta(z_{t+1} \mid s_t, \hat{s}_t)
\cdot
P(s_{t+1}, \hat{s}_{t+1} \mid s_t, \hat{s}_t, z_{t+1}),
$$

where under the emission-conditioned (unifilar) factorization we have

$$
P_\theta(z_{t+1} \mid s_t, \hat{s}_t)
=
\pi_\theta(a_{t+1} \mid \hat{s}_t; \theta_\pi)
\cdot
P(o_{t+1} \mid s_t, a_{t+1}),
$$

and equivalently, when marginalizing over the agent’s belief state,

$$
P_\theta(z_{t+1} \mid b_t, \hat{s}_t)
=
\pi_\theta(a_{t+1} \mid \hat{s}_t; \theta_\pi)
\sum_{s_t} b_t(s_t)\, P(o_{t+1} \mid s_t, a_{t+1}).
$$

This expression mirrors the emission decomposition of the macro POMDP but now explicitly under the unifilar transition structure.
Each factor arises directly from the token-level generator $\sigma_\theta$ through the quotient mapping, meaning that the same parameters $\theta$ induce both the **macro policy** $\pi_\theta$ and the **macro world model** $\mathcal{M}_\theta$.
This identification closes the loop between the micro and macro views:
the low-level token generator $\sigma_\theta$ produces a synchronized, unifilar process whose class-marginals implement the high-level policy $\pi_\theta$ and transition model $\mathcal{M}_\theta$.
