# LLM Agents as Policies in Typed Program Space
### tags: @vision @abstractions

## Introduction
This year was supposed to be the year of the agents, yet they stumble. There have been remarkable improvements in coding agents, but the definitely not sporadic mistakes stand out even more against their skillful successes.

I believe this has mostly to do with our lack of understanding, or better, a lack of framing for what LLM agents actually are. As a result, many doubts arise about what they should do and how they should do it. This is not surprising, given the wide range of theories that tempt us while navigating such a complex problem. It is not an easy task to lift the autoregression of symbolic sequences into a coherent theory of agency. Moreover, agency is only half of the story: if they are agents, what is their environment?

The goal of this post, and of this blog in general, is to contribute a clearer vision of what we are building, in a way that attempts consistency across the entire theoretical stack. We will start from the top, by formalizing in what sense a function-calling LLM can be considered a goal-directed agent. We will focus on the general setup of a function-calling agent equipped with a finite set of functions, a computing engine to execute them, and a clear terminal reward signal. Think of one of the default LangChain or PydanticAI agents interacting with a Python REPL.

First, we want to properly characterize the interaction between the LLM and the computing environment as a potentially partially observable Markov Decision Process. This will require a clear separation between the environment’s state, its afferents, the resulting state update rules, and how these elements appear as the agent’s observations and actions.

Second, we want to formalize the structure of the computing environment in a way that helps us better understand LLM agents. To do so, we will draw on ideas from pure functional programming and model the computing environment as a category of object types whose morphisms are the typed functions that the agent can execute. Under a first, simplified approximation where the problem semantics are fully modeled by the type system, we can define rewards or goals as a partition function over the set of types. In this view, the objective of the agent is to compose a sequence of functions into a program that leads to a terminal type maximizing reward. Alternatively, given a set of initial objects, the task becomes finding a path through a typed category that reaches a reward partition. 
 

We will see that in this relatively simplistic setting, we can initially enumerate the complete state space of programs and navigate it using traditional algorithms such as A* or BFS. However, as we include more realistic compositional patterns, the state space explodes, pushing us back toward a reinforcement learning framework in the hope of discovering more efficient navigation policies. 

In the conclusion, we will further emphasize the fundamental role of the language modeling aspect of the agent by exploring the scenario where the given base types are not sufficient to model the goal condition. From a categorical perspective, this requires further refinements, or fibrations, of the base category of types, typically expressed as exhaustive predicates over typed records. From the classical search perspective, this represents not only a combinatorial explosion but also a significant increase in modeling cost, since the minimal set of predicates that fully recovers the maximally coarse fibration sufficient for successful navigation must be known in advance by the researcher designing the environment. Still, LLMs often appear to navigate the fibration implicitly, for instance when they must identify the relevant subrecord to process among several of the same type, suggesting that an approximate encoding of the fibration is already embedded within their learned representations.

## The Reinforcement Learning Perspective on Function-Calling Agents

We will now build our mathematical formulation in terms of a **Partially Observable Markov Decision Process (POMDP)**.  
More formally, we study the **joint stochastic process** emerging from the interaction between a function-calling LLM agent and its computing environment.  
Our objective is to build an intuition for how the practical implementation of this system shapes crucial properties of the process, such as stochasticity and observability.  
This understanding will then guide us toward a more coherent and synergistic design of learning agents and their computing environments.



#### The POMDP Frame

To make our discussion concrete, we start from the general language of POMDPs.  
We define a process composed of a set of possible **environment states** $\mathcal{S}$, **actions** $\mathcal{A}$ available to the agent, and **observations** $\mathcal{O}$ emitted by the environment.  
The evolution of the system is governed by the following stochastic kernels:

- $P(s' \mid s, a)$ — the **transition kernel**, describing how the environment evolves after an action;  
- $\Omega(o \mid s', a)$ — the **observation kernel**, specifying what part of the new state is revealed to the agent;  
- and $R(s, a)$ — the **reward function**, evaluating the desirability of transitions.

Because the environment is only *partially observable*, the agent cannot condition its decisions directly on the true state $s_t$.  
Instead, it maintains an **internal state estimate** or **belief representation** $b_t$, summarizing all past interactions:

$$
b_t = P(s_t \mid h_t, s_0),
$$

where $h_t$ is the full visible history of actions and observations.  
The agent’s policy is then a distribution over actions conditioned on this belief:

$$
\pi(a_t \mid b_t),
$$

which in practice may be implemented through a **predictive state representation** (PSR), a recurrent neural hidden state, or—as in our case—the evolving hidden activations of a transformer model processing its own context.

We can also introduce an explicit **goal specification** $\mathcal{G}$, representing a family of desired outcomes or equivalently a partition over the state space.  
In this **goal-conditioned** formulation, both policy and reward may depend on a goal variable $g \in \mathcal{G}$:

$$
\pi(a_t \mid b_t, g), \qquad R(s_t, a_t, g).
$$

This view is particularly relevant for our setting, as function-calling agents operate under explicit user-specified tasks that naturally act as goal conditions.





Our objective is to understand how **actions**, **observations**, **state transitions**, and **goals** materialize in such a system, and how the architectural or representational choices we make affect the stochastic and observable structure of the process. Starting in the next section to the connecting individual tokens to the concepts of actions and observations.



### From Next-Token Prediction to Decision-Making

Having introduced the POMDP frame, we now return to the base mechanics of language modeling to identify how its components emerge in practice.  
As mentioned earlier, it is not straightforward to lift next-token prediction into a decision-making framework composed of actions, observations, and consequences, each of which may involve multiple steps of generation.  
Fortunately, modern assistant post-training already addresses this challenge through the introduction of artificial tokens that segment symbolic sequences into turns.

We start from the basic autoregressive formulation of a language model, which defines a probability distribution over token sequences of length $T$ conditional on the semi-infinite prefix of previously generated tokens:

$$
P_\theta(\tau_{1:T}) = \prod_{t=1}^{T} P_\theta(\tau_t \mid \tau_{\lt t})
$$

where $\tau_t$ denotes the token generated at position $t$, and $\tau_{\lt t}$ represents the prefix of previously generated tokens.  
This defines a left-to-right stochastic process that samples each token sequentially, conditioned on the textual history.  
In POMDP terms, this autoregressive process defines the *micro-dynamics* of the agent’s internal policy $\pi$, acting within the observation space defined by its evolving textual context.



### From Tokens to Turns to Actions and Observations

To lift this token-level process into a **decision-making** framework compatible with the POMDP perspective, we segment the token stream into **turns** using special control tokens inserted during assistant post-training.  
These tokens provide explicit syntactical boundaries between:

1. the agent’s generations (tool calls or textual reasoning),
2. the environment’s responses, and  
3. the user’s requests.

Each **turn** thus corresponds to a higher-level event in the stochastic process, marking a complete *interaction step* between the agent and the environment.  
This segmentation allows us to reinterpret the autoregressive process in terms of **turn-level sequences**, which naturally play the role of *actions* and *observations* within the POMDP framework.

Let each turn be the contiguous block of tokens

$$
\text{turn}_t = (\tau_{k_t}, \ldots, \tau_{k_{t+1}-1})
$$

beginning with a *start-of-turn* token and ending with an *end-of-turn* token.

We can then define the induced distribution over turns as:

$$
P_\theta(\text{turn}_{1:N}) = \prod_{t=1}^{N} P_\theta(\text{turn}_t \mid \text{turn}_{\lt t})
$$

Each conditional distribution represents the **behavioral policy** of the agent at the turn level. It describes how the model generates the next complete action sequence—its next *decision*—conditioned on its full observation history.

$$
P_\theta(\text{turn}_t \mid \text{turn}_{\lt t})
$$

### Building Turn Probabilities from Token Probabilities

The turn-level distribution can be constructed directly from the base autoregressive model.  
Given the token-level probability $P_\theta(\tau_t \mid \tau_{\lt t})$, the probability of generating a specific subsequence of length $L$ is:

$$
P_\theta(\tau_{t:t+L}) = \prod_{k=0}^{L-1} P_\theta(\tau_{t+k} \mid \tau_{\lt t+k})
$$

The probability of producing a complete **turn** corresponds to summing over all possible subsequences that terminate with an *end-of-turn* token:

$$
P_\theta(\text{turn}_t) = \sum_{L} P_\theta(\tau_{t:t+L}) \cdot \mathbb{I}[\tau_{t+L} = \text{EOT}]
$$

This formulation bridges the low-level token process with the higher-level policy governing full turns.  
Each completed turn becomes a well-defined *action* in the decision process, while the textual and functional context that follows it constitutes the *observation* for the next step.



### Turns as Temporally Extended Actions

From the reinforcement learning perspective, we can interpret each **turn** as a **temporally extended action**, analogous to an *option* in hierarchical RL.  
Each option corresponds to an internal autoregressive policy over tokens that terminates upon producing an *end-of-turn* token.  
The higher-level decision process then operates over these options, selecting which structured action (for instance, a reasoning segment or function call) to generate next.

For this blog post, we will remain at this level of abstraction and define our sequential decision-making problem at the turn level.  
In future work, we will attempt a formulation at the token level using the full language of options, where token-level autoregressive policies compose into structured behaviors that define the agent’s turns.

### Mapping the Turn-Level Process to the POMDP Frame

Having lifted the autoregressive process to the turn level, we can now connect it to the POMDP structure introduced earlier.  
Our goal is to identify what corresponds to *actions*, *observations*, *state transitions*, and *goals* in the empirical case of a function-calling LLM interacting with a computing environment.



### Observation Space, Valid Actions, and Behavioral Policies

Let there be an agent interacting with a computing environment through a discrete sequence of function calls.  
At each step $t$, the agent selects a function $f_t$ from a finite set of callable functions and provides an input $x_t$ drawn from its corresponding input space.  
The environment executes the call $(f_t, x_t)$ and returns an observable output $y_t$, which is appended to the ongoing context available to the agent.

The agent’s **observation space** therefore consists of all visible results of past interactions, summarized by the interaction history:

$$
h_t = ((y_i, (f_i, x_i)))_{i \lt t}.
$$

Each $y_i$ is an emitted observation (e.g., a JSON result), while each $(f_i, x_i)$ represents the function invoked and its input at that step.  
Together, they define the entire visible trajectory from which the agent must infer the current computational state.  
The LLM’s hidden state or context window serves as an implicit **belief representation** $b_t = \Phi(h_t)$, a compressed, internal estimate of the relevant environment state derived from this history.

---

#### Valid actions and compositionality

Not all token sequences the LLM can produce correspond to executable actions in the environment.  
Each turn must define a **valid function call**, and its input must be **semantically grounded** in the current environment state.  
Formally, we require that

$$
x_t \in \mathcal{X}(s_t),
$$

where $\mathcal{X}(s_t)$ is the set of admissible inputs given the current environment state $s_t$.  
In practice, this means that inputs can only reference objects that are already present in the environment —
either those that were part of the **initial state** $s_0$ or those **produced by previous function calls**.  

This compositionality constraint ensures that the action sequence defines a **well-typed function composition**:

$$
(f_t, x_t): \quad x_t \mapsto y_t = f_t(x_t), \qquad x_t \in \{ y_i \mid i \lt t \} \cup s_0.
$$

It enforces that each new computation depends only on known quantities rather than on arbitrary strings generated by the language model.  
By construction, this keeps the overall process grounded in the environment’s evolving state and prevents the model from “inventing” data out of thin air.

---

#### Behavioral policy

Given this structure, the agent’s **behavioral policy** defines the probability of selecting the next valid function and its corresponding input, conditioned on its internal belief derived from the visible history and the initial environment state:

$$
P(f_t, x_t \mid b_t, s_0),
\qquad b_t = \Phi(h_t).
$$

subject to the validity constraint $x_t \in \mathcal{X}(s_t)$ described above.  
This is the turn-level analogue of the policy $\pi(a_t \mid b_t)$ in the general POMDP formulation, where $b_t$ denotes the agent’s internal estimate of the state rather than an instantaneous observation.

In future work, we will also consider the **open-world case**, where the agent is allowed to generate novel inputs not derived from prior state — for instance, creating new constants, text, or objects dynamically.  
While such capabilities are crucial for creative reasoning and generative synthesis, they break strict compositionality and require a richer definition of admissible actions, which we defer to a dedicated discussion.

---

### Environment Response and State Evolution

The **state space** $\mathcal{S}$ of the environment captures everything relevant to how function calls are executed and how outputs are produced.  
In a computing setting, this state can correspond to the current memory of a Python REPL, a running kernel, or any in-memory data structure that evolves as function calls are executed.

Given the initial state $s_0$, the environment defines two stochastic processes: one for **state transitions** and one for **response generation**.

The **state transition kernel** updates the environment after each function call:

$$
s_{t+1} \sim P(s_{t+1} \mid s_t, f_t, x_t)
$$

The **observation kernel** produces the output seen by the agent based on the current state and executed function:

$$
y_t \sim P(y_t \mid s_t, f_t, x_t)
$$

In the general case, the environment is **stateful**.  
Functions may have **non-degenerate side effects**, meaning that while their input–output mapping remains constant, they can modify the internal state of the system.  
For instance, executing a function that writes a variable in a Python kernel changes the REPL state even though the function interface itself is unchanged.

Under this assumption, the environment’s state at time $t$ can be expressed as a deterministic or stochastic function of the initial state and the entire interaction history:

$$
s_t = g(s_0, ((y_i, (f_i, x_i)))_{i \lt t})
$$

The environment’s response distribution then becomes:

$$
P(y_t \mid f_t, x_t, h_t, s_0)
$$

This generalizes the observation kernel to account for implicit dependencies on the environment’s evolving state.

Together, these form the environment kernel that mediates the agent’s interaction with the computing system.  
In POMDP terms, $P(s_{t+1} \mid s_t, f_t, x_t)$ corresponds to the **transition kernel**, and $P(y_t \mid s_t, f_t, x_t)$ to the **observation kernel** $\Omega(o_t \mid s_t, a_t)$.

---

### The POMDP Correspondence

We can now summarize the correspondence between our empirical formulation and the general POMDP structure introduced earlier.  
At the turn level, the process aligns with the standard components of a POMDP, while the underlying token dynamics provide the fine-grained implementation of each stochastic kernel.

| POMDP Component | Function-Calling LLM Analogue |
|--|--|
| **State** $s_t$ | The internal memory of the computing environment (e.g., REPL, kernel, variable bindings) |
| **Observation** $y_t$ | The environment’s emitted response (e.g., tool output, JSON object) |
| **Belief / internal state** $b_t = \Phi(h_t)$ | The LLM’s hidden representation of the accumulated history (context window, KV cache, or neural state) |
| **Action** $a_t$ | The generation of a complete turn: a structured function call or reasoning segment produced by the LLM |
| **Policy** $\pi(a_t \mid b_t)$ | The LLM’s autoregressive generation process conditioned on its internal belief (compressed history) and constrained by valid-action support |
| **Transition** $P(s_{t+1} \mid s_t, a_t)$ | The update of the environment’s internal state following a function execution |
| **Observation kernel** $\Omega(y_t \mid s_t, a_t)$ | The process by which the environment produces the next visible output |
| **Reward / Goal** $R(s_t, a_t, g)$ | A task- or user-conditioned objective that defines success in terms of terminal or intermediate states |

---

The **policy** of the model begins at the token level, where the transformer defines a conditional distribution over the next token:

$$
P_\theta(\tau_t \mid \tau_{\lt t})
$$

Aggregating these local conditionals yields the probability of producing a complete turn: an entire segment between *start-of-turn* and *end-of-turn* tokens:

$$
P_\theta(\text{turn}_t \mid \text{turn}_{\lt t}) =
\sum_L
\left(
\prod_{k=0}^{L-1} P_\theta(\tau_{k_t+k} \mid \tau_{\lt k_t+k})
\right)
\mathbb{I}[\tau_{k_t+L} = \text{EOT}]
$$

However, not every sequence that ends with an EOT token corresponds to a valid action for the environment.  
The **action kernel** and **observation kernel** of the environment restrict this support to the subset of turns that are *semantically valid*—those that can be parsed, executed, and yield a well-formed response.  
The effective behavioral policy of the function-calling agent is therefore the restriction of the autoregressive process to this joint support:

$$
\pi(a_t \mid b_t) \propto
P_\theta(\text{turn}_t \mid \text{turn}_{\lt t}) \,
\mathbb{I}[\text{turn}_t \in \mathcal{A}_{env}]
$$

where $\mathcal{A}_{env}$ denotes the set of admissible actions defined by the environment’s interface.  
This is precisely where the **option perspective** becomes essential: each valid subsequence defines a temporally extended policy fragment whose termination condition (*end-of-turn*) must align with an action boundary meaningful to the environment.

Once a valid action $(f_t, x_t)$ is generated, the **transition kernel** governs how the environment evolves:

$$
s_{t+1} \sim P(s_{t+1} \mid s_t, f_t, x_t)
$$

The **observation kernel** then determines the response visible to the agent:

$$
y_t \sim P(y_t \mid s_t, f_t, x_t)
$$

which is appended to the ongoing context forming the next history:

$$
h_{t+1} = ((y_i, (f_i, x_i)))_{i \leq t}
$$

Finally, the process is guided by a **goal specification** $g \in \mathcal{G}$ and a corresponding reward function $R(s_t, a_t, g)$ that evaluates whether the trajectory has reached a desired terminal or intermediate condition.  
In practice, these correspond to user-defined success criteria—such as producing a correct answer, generating valid code, or completing a function chain that satisfies a constraint.

Seen this way, the function-calling LLM forms a complete POMDP loop whose **action space** is defined jointly by the model’s language distribution and the environment’s executable semantics.  
The **token-level autoregression** specifies a continuous generative policy, while the **environment kernels** discretize it into admissible options that carry meaning and consequence.  
This layered view exposes how the structure of the environment and the model’s own representational limits jointly determine the observability, stochasticity, and effective agency of the system.

---

## Can We Make It an MDP?

In our current setup, the agent never observes the true environment state $s_t$ directly, either because functions may cause unobserved side effects or because the memory context is shared with other asynchronous processes.  
The system is therefore **partially observable by construction**: the LLM only sees the *observable history* of previous interactions, not the full memory of the computing environment.

### The agent stack as a parsing of history

The key question is whether this visible history can be **parsed** into a sufficient state representation.  
Let the observable history at time $t$ be

$$
h_t = ((y_i, (f_i, x_i)))_{i \lt t},
$$

where each $y_i$ is the environment’s emitted observation at step $i$.  
We introduce a parsing function

$$
\Phi: \mathcal{H} \to \mathcal{S}_{\text{eff}}, \qquad \text{Stack}_t = \Phi(h_t),
$$

which extracts from the history a compact **agent stack**, a structured representation containing exactly the typed objects and references required for future computation.

The process behaves like an **MDP** if this parser makes the environment’s future depend only on the parsed state and current action:

$$
P(s_{t+1} \mid h_{\le t}, a_t) = P(s_{t+1} \mid \text{Stack}_t, a_t),
\qquad
P(y_{t+1} \mid h_{\le t}, a_t) = P(y_{t+1} \mid \text{Stack}_t, a_t).
$$

Equivalently, $\text{Stack}_t$ is a **sufficient statistic** of the history and the history is a sufficient statistic of the memory state.  
Intuitively, the agent stack acts as a *parser over the LLM’s context window*, turning the textual record of the past into a canonical computational state.

### When does such a parser exist?

A natural sufficient condition is the **pure functional** regime, where the environment is immutable and functions have no side effects beyond their return values.  
Then, the output is conditionally independent of hidden state:

$$
P(y_t \mid f_t, x_t, s_t) = P(y_t \mid f_t, x_t),
$$

and the state is reconstructible from the initial state and visible history:

$$
s_t = \text{construct}(s_0, h_t),
\quad
P(s_t \mid h_t, s_0) = \mathbb{I}[s_t = \text{construct}(s_0, h_t)].
$$

Under these conditions, we can define the parsing function $\Phi$ explicitly as the construction of a minimal stack of unique, typed objects sufficient for all future actions:

$$
\text{Stack}_t = M_t / \sim,
$$

where $M_t$ collects the bindings and outputs induced by $h_t$ and $\sim$ identifies equivalent objects of the same type.  
The stack evolves through simple operations: pushing new outputs, deduplicating repeated ones, and optionally removing unreachable entries.  
With such a parser, the history $h_t$ is enough — the process **collapses to an MDP** on $\text{Stack}_t$.

### What breaks the parser

In **mutable environments** (e.g., a Python REPL), in-place updates create hidden dependencies that are not guaranteed to appear in $h_t$.  
Even if individual functions are pure, the overall system becomes stateful because later calls can read mutated memory that was never revealed in the prior observations.  
No fixed parser $\Phi$ can make $h_t$ sufficient without explicit logging or serialization of side effects.  
In this case, the agent must maintain a belief distribution over hidden states:

$$
b_t(s) = P(s_t = s \mid h_t, s_0),
$$

and the process remains a true **POMDP**.

### What Makes an Environment Desirable

Under immutability, each function call is a morphism between typed objects, and $\Phi$ behaves as a **functor** mapping the trace of turns (the LLM’s context) into the corresponding object graph of typed values.  
The reconstructed stack represents the composed morphisms applied to the initial state.  
With mutability, hidden morphisms act outside this functorial image, and the mapping from histories to states is no longer unique, hence partial observability re-emerges.

To make $\Phi(h_t)$ a valid and sufficient state representation in practice:

1. **Immutability**: each function call produces fresh outputs, never in-place mutations.  
2. **Explicit references**: inputs must refer to prior outputs by stable identifiers or serialized content.  
3. **Complete serialization**: all side effects relevant to future behavior must appear in the observation $y_t$.  
4. **Action validity**: constrain the policy to the environment’s admissible actions so parsed turns remain executable.

When these conditions hold, the **agent stack** is a faithful parse of the LLM’s context, and the system behaves like an **MDP** whose state is explicitly recoverable from history.
