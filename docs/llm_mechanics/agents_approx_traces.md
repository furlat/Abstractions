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


# The Dual Nature of Computational Traces: Types, Values, and Uncertainty in LLM Agents

## Abstract

This paper presents a unified theoretical framework for understanding LLM agents through the lens of stochastic processes that approximate computational traces. We emphasize the dual nature of these traces as simultaneously dependent on types (structural constraints) and values (specific data). This duality creates distinct forms of uncertainty that agents must manage through different mechanisms. We demonstrate how type-level reasoning enables valid function composition paths, while value-level reasoning determines the specific execution branch taken. The tension between agent capacity and the joint entropy of type-value spaces creates an apparent paradox that agents resolve through iterative interaction—collapsing value uncertainty through observation while maintaining type awareness. Our framework explains how agents balance these two levels of information, trading off the number of interaction steps against composition uncertainty. This approach reconciles theoretical bounds on information transfer with the empirical success of tool-using agents, providing insights into fundamental capabilities and limitations of LLM agents.

## 1. Introduction: The Dual Nature of Computational Traces

Large Language Model (LLM) agents can be understood as stochastic processes that approximate computational traces of function compositions. A crucial insight often overlooked is that these traces have a dual nature—they simultaneously depend on types (structural constraints) and values (specific data points).

Consider a simple trace involving a weather API:
```
getWeather("New York") → 72°F
recommendClothing(72°F) → "T-shirt and light pants"
```

This trace embodies two parallel threads of information:
- **Type-level information**: `getWeather` returns a temperature (number), which can be input to `recommendClothing`
- **Value-level information**: The specific temperature 72°F leads to the specific recommendation "T-shirt and light pants"

Formally, we can define a computational trace as a sequence of steps:
```
T = [(f₁, x₁, τ₁, y₁), (f₂, x₂, τ₂, y₂), ..., (fₙ, xₙ, τₙ, yₙ)]
```

Where:
- fᵢ is the function applied at step i
- xᵢ is the input (with type τᵢ⁻¹)
- τᵢ is the output type
- yᵢ is the specific output value

An LLM agent approximates this process as a conditional probability distribution:
```
P_θ(a_t | h_{<t}, o_{<t})
```

Where the history h and observations o contain both type-level and value-level information from previous steps.

This dual nature creates distinct challenges and opportunities for LLM agents, which form the focus of this paper.

## 2. Types and Values in Predictive States

The concept of predictive states must be extended to account for this duality. A predictive state encompasses information about both the types and values of intermediate results in a computation.

**Definition 1 (Dual Predictive State)**: A predictive state s ∈ S consists of two components:
- sᵗ: The type component, representing structural constraints on valid next functions
- sᵛ: The value component, representing the specific data that determines the exact result of function application

This leads to a refined equivalence relation for predictive states:

**Type-Level Equivalence**: 
```
h ~ᵗ h' ⟺ ∀f: valid(f|h) = valid(f|h')
```
Two histories are type-equivalent if the same set of functions can be validly applied to both.

**Value-Level Equivalence**: 
```
h ~ᵛ h' ⟺ ∀f that is valid: P(f(h) = y) = P(f(h') = y) ∀y
```
Two histories are value-equivalent if applying the same function produces the same distribution over output values.

The full predictive state equivalence requires both:
```
h ~ h' ⟺ h ~ᵗ h' ∧ h ~ᵛ h'
```

This distinction is crucial because LLM agents often learn type-level equivalence more readily than value-level equivalence, leading to situations where they know which functions can be applied but have uncertainty about specific outcomes.

## 3. The Type-Value Entropy Tension

The entropy of computational traces comes from both type and value uncertainty:

**Type Entropy**: The uncertainty about which functions can be validly applied next:
```
H(Types) = -∑_τ P(τ) log P(τ)
```

**Value Entropy**: The uncertainty about specific output values given a function:
```
H(Values|Types) = -∑_τ P(τ) ∑_v P(v|τ) log P(v|τ)
```

**Total Entropy**: The joint entropy of the type-value space:
```
H(Trace) = H(Types) + H(Values|Types)
```

This creates a fundamental tension:

**The Type-Value Entropy Paradox**: An agent with fixed parameters (bounded information capacity) must handle both:
1. The type space entropy, which constrains valid function compositions
2. The value space entropy, which determines specific execution paths

Formally, this tension manifests as:
```
I(Agent) ≪ H(Types) + H(Values|Types)
```

For many real-world tools, H(Values|Types) can be enormous. A weather API might return any temperature value, a database might contain millions of records, and a calculator can produce a vast range of numeric outputs.

## 4. Type-Level vs. Value-Level Reasoning

LLM agents employ distinct mechanisms for handling type-level and value-level information:

**Theorem 1 (Type-Level Determinism)**: With perfect type-level information, an agent can determine with certainty whether a function composition path is valid, without needing to know specific values.

**Proof**: 
1. Types form a formal system where composition validity follows from type rules: f: σ → τ, g: τ → ρ ⟹ g ∘ f: σ → ρ
2. These rules are deterministic: given input and output types, the validity of applying a function is binary
3. Therefore, type-level validity can be determined with certainty without value information

**Theorem 2 (Value-Level Stochasticity)**: Even with perfect type-level information, value-level outcomes remain stochastic from the agent's perspective until observed.

**Proof**:
1. The specific value returned by a function depends on its input value and internal implementation
2. The agent has uncertainty about exact function implementations (especially for external APIs, databases, etc.)
3. Therefore, the agent must model value-level outcomes as stochastic until observed

This distinction explains a common pattern in LLM agent behavior: they can confidently reason about the structure of a solution (which functions to compose) while expressing uncertainty about specific outcomes ("I'll need to check the weather forecast to determine what clothing to recommend").

## 5. Perfect Type Knowledge Enables Valid Composition

An agent with perfect type-level knowledge can derive valid function compositions without fully resolving value uncertainty:

**Theorem 3 (Type-Guided Composition)**: An agent with perfect knowledge of the type system can derive all valid function composition paths, even with uncertainty about specific values.

**Proof**:
1. The validity of applying function f after function g depends only on whether the output type of g matches the input type of f
2. With perfect type knowledge, the agent knows all input and output types of available functions
3. Therefore, the agent can construct a graph where:
   - Nodes are types
   - Edges are functions that map between types
4. Valid composition paths are paths through this graph
5. This construction requires no value-level information

This explains why type-aware LLM agents can plan multi-step solutions involving tools they've never used together before, as long as they understand the type signatures.

## 6. Value Uncertainty and Execution Branching

While type-level reasoning enables composition planning, value-level uncertainty creates execution branches:

**Definition 2 (Execution Branch)**: An execution branch occurs when a function can return multiple possible values, each leading to a different subsequent execution path.

The number of potential execution branches grows exponentially with composition depth:

```
|Branches| = ∏_i |Values(f_i)|
```

Where |Values(f_i)| is the number of distinct outputs function f_i might produce.

For real-world tools, this creates an explosion of possibilities that cannot be fully represented in the agent's fixed-capacity parameters.

## 7. Iterative Resolution of Type and Value Uncertainty

The resolution to the Type-Value Entropy Paradox lies in how agents handle these two forms of uncertainty differently:

**Type Uncertainty**: Resolved primarily through learning from training data, where the agent internalizes the type system of the domain.

**Value Uncertainty**: Resolved primarily through iterative interaction, where the agent observes specific outputs and uses them to collapse uncertainty about the specific execution branch.

**Theorem 4 (Dual Uncertainty Resolution)**: An agent resolves type and value uncertainty through complementary mechanisms:
1. Type uncertainty is minimized by learning the domain's type structure during training
2. Value uncertainty is collapsed through iterative sampling and observation during execution

This creates a process where:
1. Type-level reasoning constrains the space of valid function compositions
2. Initial actions are taken based on expected information gain about values
3. Observed values collapse uncertainty about the specific execution branch
4. This reduced uncertainty informs the next action
5. The process repeats until the task is completed

Mathematically, each observation reduces value uncertainty:
```
H(Values|Types, o_1, o_2, ..., o_t) < H(Values|Types, o_1, o_2, ..., o_{t-1})
```

While type knowledge remains relatively stable throughout the interaction.

## 8. Information Transfer in the Dual Framework

The dual nature of computational traces has profound implications for information transfer from training data to agent parameters:

**Type-Level Transfer**: Information about types transfers efficiently because:
1. The type system is generally much smaller than the value space
2. Types follow formal rules that can be compactly represented
3. Type systems tend to be stable across examples

**Value-Level Transfer**: Information about specific values transfers less efficiently because:
1. The value space is often orders of magnitude larger than the type space
2. Value relationships may be complex and domain-specific
3. The training data can only cover a tiny fraction of possible values

This creates a natural prioritization where agents learn type-level information more thoroughly than value-level information, explaining why they can reason accurately about composition validity even when uncertain about specific outcomes.

## 9. Trading Steps for Value Uncertainty

The dual framework reveals a fundamental trade-off between the number of interaction steps and value uncertainty:

**Theorem 5 (Step-Value Uncertainty Trade-off)**: An agent can reduce value uncertainty by increasing the number of interaction steps, with the relationship:
```
H(Values|Types) × Steps ≈ constant
```

This means an agent can either:
1. Take many small steps, each resolving a small amount of value uncertainty
2. Take fewer, larger steps, each involving more value uncertainty

The optimal trade-off depends on:
1. The cost of additional API calls or interactions
2. The risk tolerance for making errors due to value uncertainty
3. The complexity of the value space for relevant functions

Importantly, this trade-off primarily affects value uncertainty; type uncertainty remains largely determined by the agent's training.

## 10. Entropy Amplification in the Dual Framework

When an agent has imperfect understanding of the type system, a phenomenon we call "entropy amplification" occurs:

**Definition 3 (Type-Driven Entropy Amplification)**: When an agent has incorrect or incomplete type knowledge, it may consider invalid function compositions to be valid, exponentially increasing the number of execution branches it must consider.

The degree of amplification scales with the agent's type confusion:
```
H_amplification ∝ D_{KL}(P(Types_agent) || P(Types_true))
```

This explains why type errors are particularly costly in agent reasoning—they don't just cause individual mistakes but can derail entire solution paths.

## 11. Practical Implications of the Dual Framework

Our theoretical framework has several practical implications:

1. **Training Focus**: Training should emphasize comprehensive coverage of the type space, while accepting that the value space can only be sparsely sampled

2. **Architecture Design**: Models should represent type information and value information differently, potentially with specialized components for type tracking

3. **Tool Design**: Tools should provide clear type signatures and structured outputs that help agents distinguish type-level from value-level information

4. **Interaction Protocols**: Interaction protocols should support iterative refinement, allowing agents to resolve value uncertainty progressively

5. **Error Handling**: Error handling should distinguish between type errors (invalid compositions) and value errors (unexpected outputs), with different recovery strategies for each

## 12. Conclusion: The Dual Path Forward

This paper has presented a unified theoretical framework for understanding LLM agents as stochastic approximators of computational traces, emphasizing the dual nature of these traces as dependent on both types and values.

The key insights are:

1. Computational traces contain two parallel threads of information: types (structural constraints) and values (specific data)

2. Type-level reasoning enables agents to determine valid function compositions, while value-level reasoning determines specific execution branches

3. Agents resolve type uncertainty primarily through training and value uncertainty primarily through iterative interaction

4. This dual approach allows agents to handle the apparent paradox between bounded parameter capacity and unbounded execution spaces

Looking forward, I believe this dual perspective offers new directions for agent design. Rather than treating types and values as interchangeable forms of information, we should design systems that explicitly separate and specialize in these distinct aspects of computation.

The most promising approach may be hybrid systems that combine neural type inference with iterative value resolution. Such systems would leverage the strengths of each mechanism where it excels: neural components learning the type structure of the domain, and interactive components resolving value uncertainty through targeted sampling.

By recognizing and embracing the dual nature of computational traces, we can develop agents that more efficiently navigate the vast space of possible computations, combining the formal precision of type systems with the pragmatic adaptability of iterative value resolution.