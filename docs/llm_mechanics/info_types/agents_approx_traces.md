# LLM Agents as Stochastic Approximators of Computational Traces: An Information-Theoretic Framework

## Abstract

This paper presents a unified theoretical framework for understanding large language model (LLM) agents through the lens of stochastic processes that approximate computational traces. We explore the fundamental tension between agent representation capacity and tool entropy, demonstrating how this tension creates an apparent paradox that can be resolved through iterative interaction. We prove that agents with perfect predictive states can derive optimal function compositions, while showing how imperfect predictive states can amplify entropy in the joint agent-tool channel. Our framework explains how agents resolve uncertainty through iterative sampling, effectively trading off the number of steps against uncertainty reduction. This approach reconciles theoretical bounds on information transfer with the empirical success of tool-using agents, providing new insights into agent design, training methodologies, and fundamental capabilities.

## 1. Introduction: LLM Agents as Stochastic Approximators

Large Language Model (LLM) agents can be formally characterized as stochastic processes that approximate computational traces of function compositions. When an agent interacts with tools, it is effectively attempting to approximate the execution of a program—the composition of multiple functions in sequence to achieve a goal. The agent's knowledge of this process is imperfect, learned from a finite set of examples, creating a fundamental stochasticity in its behavior.

Formally, we can define an LLM agent as a conditional probability distribution:

$$P_\theta(a_t | h_{<t}, o_{<t})$$

where:
- $a_t$ is the agent's action at time $t$ (text generation or tool call)
- $h_{<t}$ is the history of interactions up to time $t$
- $o_{<t}$ are the observations (including tool outputs) up to time $t$
- $\theta$ are the model parameters

This distribution approximates the "true" distribution of actions in ideal computational traces:

$$P^*(a_t | h_{<t}, o_{<t})$$

The quality of this approximation—and the conditions under which it succeeds or fails—is the central focus of this paper.

## 2. Predictive States and Function Composition

The concept of predictive states provides the theoretical foundation for understanding agent behavior. A predictive state encapsulates the minimal sufficient information needed to predict future behavior of a process.

**Definition 1 (Predictive State)**: A predictive state $s \in S$ is an equivalence class of histories that yield identical conditional distributions over future outcomes:

$$h \sim h' \iff \forall f, x: P(f(x)|h) = P(f(x)|h')$$

In the context of function composition, the predictive states often correspond to the types of intermediate values. For example, after applying a function that returns a `String`, the predictive state encodes that we now have a `String` and can only apply functions that accept a `String` as input.

The optimal function composition path can be represented as a sequence of transitions between predictive states, where each transition is triggered by applying a specific function:

$$s_0 \xrightarrow{f_1} s_1 \xrightarrow{f_2} s_2 \xrightarrow{f_3} \ldots \xrightarrow{f_n} s_n$$

where $s_0$ is the initial state and $s_n$ is the goal state.

## 3. The Entropy Tension: Agent vs. Tool

A fundamental tension exists between the bounded information capacity of the agent and the potentially unbounded entropy of tool outputs. This creates an apparent paradox:

**The Agent-Tool Entropy Paradox**: How can an agent with fixed parameters (bounded information capacity) successfully handle the unbounded space of possible tool outputs and composition paths?

Let's formalize this tension:

1. **Agent Capacity**: The maximum information content of the agent is bounded by its parameter count:
   $$I(Agent) \leq |\theta| \cdot b$$
   where $|\theta|$ is the number of parameters and $b$ is the bits per parameter.

2. **Tool Output Entropy**: The entropy of a tool's output can be much larger:
   $$H(Tool) = \sum_x P(x) \log \frac{1}{P(x)}$$
   For many real-world tools (APIs, calculators, databases), this entropy can be effectively unbounded.

3. **Composition Space**: The entropy of all possible compositions grows exponentially with composition length:
   $$H(Compositions) \approx O(|F|^d)$$
   where $|F|$ is the number of available functions and $d$ is the composition depth.

This creates a situation where:
$$I(Agent) \ll H(Tool) \cdot H(Compositions)$$

The paradox is that despite this inequality, agents successfully compose tools to solve complex tasks. How?

## 4. Perfect Predictive States Enable Optimal Composition

We first examine the idealized case where an agent has perfect knowledge of the predictive states:

**Theorem 1 (Optimal Composition)**: An agent with perfect representation of the predictive states $S$ can derive the optimal function composition path for any solvable task.

**Proof Sketch**:
1. With perfect predictive states, the agent knows exactly which functions can be validly applied at each step
2. The agent can perform graph search in the state space where:
   - Nodes are predictive states
   - Edges are function applications
   - Edge weights are based on function costs
3. Using algorithms like Dijkstra's or A*, the agent can find the minimum-cost path from initial state to goal state
4. This path is precisely the optimal function composition

This theorem explains why agents with strong type awareness and function understanding can perform complex compositions with minimal steps. They have effectively learned an approximation of the predictive state space.

## 5. Entropy Amplification in Imperfect Agents

In practice, agents have imperfect knowledge of predictive states, leading to a phenomenon we call "entropy amplification":

**Definition 2 (Entropy Amplification)**: When an agent with imperfect predictive states attempts function composition, the entropy of the joint agent-tool system increases beyond the sum of their individual entropies:
$$H(Agent, Tool) > H(Agent) + H(Tool)$$

This occurs because uncertainty in the agent's representation creates additional possible branches in the interaction, amplifying the overall system uncertainty.

The degree of amplification depends on the KL divergence between the agent's representation and the true predictive states:
$$H_{amplification} \propto D_{KL}(P(S_{agent}) || P(S_{true}))$$

This explains why agents sometimes make errors that compound over multiple steps of reasoning, particularly when dealing with unfamiliar tool combinations or edge cases not well-represented in training data.

## 6. Iterative Uncertainty Resolution

The resolution to the Agent-Tool Entropy Paradox lies in iterative uncertainty resolution:

**Theorem 2 (Iterative Resolution)**: An agent can resolve uncertainty through iterative sampling from tools, effectively trading off the number of interaction steps for reduced composition uncertainty.

Specifically, the agent uses a strategy of:
1. Taking an action (often a tool call) with the highest expected information gain
2. Observing the output, which collapses the uncertainty about that specific output
3. Using this new information to reduce uncertainty about the next optimal action
4. Repeating until the task is completed

This creates a sequential decision process where each step reduces the entropy about the specific execution path:
$$H(Path|o_1, o_2, ..., o_t) < H(Path|o_1, o_2, ..., o_{t-1})$$

The iterative approach allows the agent to handle greater complexity than would be possible if it had to encode all possible paths and outputs a priori. It effectively "offloads" entropy management to the interaction process.

## 7. Trading Off Steps vs. Uncertainty

This iterative approach introduces a fundamental trade-off between the number of steps and composition uncertainty:

**Proposition 1 (Step-Uncertainty Trade-off)**: An agent can reduce composition uncertainty by increasing the number of interaction steps, with the relationship:
$$H(Composition) \cdot Steps \approx constant$$

This means an agent can either:
1. Take many small, certain steps (high number of steps, low uncertainty per step)
2. Take fewer, more uncertain leaps (low number of steps, high uncertainty per step)

The optimal trade-off depends on:
1. The cost of additional steps
2. The risk tolerance for potential errors
3. The agent's confidence in its predictive state representation

This explains the empirical observation that agents often break complex tasks into smaller, more manageable steps when dealing with unfamiliar territory, while taking larger compositional leaps in familiar domains.

## 8. Information Transfer Bounds Revisited

With the step-uncertainty trade-off in mind, we can revisit our understanding of information transfer from training data to agent parameters:

**Theorem 3 (Information Transfer with Iteration)**: The effective information content of an iterative agent exceeds the static information bound of its parameters through the process of interactive sampling:
$$I_{effective}(Agent) = I(Agent) + \sum_{t=1}^T I(o_t; Path|o_{<t})$$

where $I(o_t; Path|o_{<t})$ is the information gain about the correct path from each observation.

This theorem explains why even relatively small models can solve complex compositional tasks through iterative approaches—they're effectively augmenting their fixed parameter information with dynamic information acquired through interaction.

## 9. Practical Implications

Our theoretical framework has several practical implications for agent design:

1. **Trace Diversity vs. Depth**: Training data should balance diverse examples (covering the predictive state space) with deep examples (showing extended compositions)

2. **Explicit Uncertainty Handling**: Agents should be designed to recognize and manage their uncertainty, taking smaller steps when uncertain

3. **Type-Aware Architectures**: Model architectures that explicitly represent and track types can more efficiently encode predictive states

4. **Hybrid Approaches**: Combining implicit prediction with explicit reasoning allows agents to leverage the benefits of both approaches

5. **Tool Design for Uncertainty Reduction**: Tools should be designed to provide informative outputs that efficiently reduce uncertainty

## 10. Conclusion and Final Thoughts

This paper has presented a unified theoretical framework for understanding LLM agents as stochastic approximators of computational traces. We've shown how the apparent paradox between bounded agent capacity and unbounded tool entropy is resolved through iterative interaction and uncertainty reduction.

The key insights are:

1. LLM agents approximate the stochastic process of function composition through learned predictive states
2. Perfect predictive states enable optimal composition, while imperfect states can amplify entropy
3. Iterative interaction allows agents to trade off steps against uncertainty, resolving the capacity paradox
4. This framework unifies implicit and explicit approaches to tool use under a single theoretical umbrella

Looking forward, I believe this theoretical framework opens new directions for agent design. By explicitly modeling the information flow between agents and tools, we can develop more efficient training methodologies, better architectures for capturing predictive states, and improved strategies for handling uncertainty.

The most promising avenue may be hybrid systems that combine the strengths of neural approximation with symbolic reasoning, using each where it excels. Neural components can learn the predictive state structure from data, while symbolic components can perform exact computation when needed. Together, they can navigate the vast space of possible compositions more effectively than either approach alone.

Ultimately, this framework suggests that the key to more capable agents lies not in simply scaling parameters, but in better aligning model representations with the underlying predictive state structure of the computational processes they aim to approximate. By focusing on this alignment, we can develop agents that more efficiently leverage tools to extend their capabilities beyond what their static parameters would otherwise allow.