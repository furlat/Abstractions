# LLM Agents as Goal-Directed Stochastic Approximators of Computational Traces: An Information-Theoretic Framework

## Abstract

This paper presents a unified theoretical framework for understanding large language model (LLM) agents through the lens of goal-directed stochastic processes that approximate computational traces. We emphasize the dual nature of these traces as simultaneously dependent on types (structural constraints) and values (specific data), both directed toward satisfying terminal conditions specified by goal functions. This duality creates distinct forms of uncertainty that agents must navigate with bounded computational resources while optimizing toward goal states. We demonstrate how type-level reasoning enables valid function composition paths, while value-level reasoning determines specific execution branches, all directed toward goal satisfaction. The fundamental tension between agent capacity and the joint entropy of type-value-goal spaces creates an apparent paradox that agents resolve through iterative interaction—collapsing value uncertainty through observation while leveraging learned type knowledge to progress toward goal states. Our framework explains how agents trade off interaction steps against uncertainty reduction in pursuit of goals and how information transfers from training data to model weights, bounded by the KL divergence between predictive states and their realizations. This approach reconciles theoretical bounds on information transfer with the empirical success of goal-directed, tool-using agents, providing new insights into agent design, training methodologies, and fundamental capabilities.

## 1. Introduction: LLM Agents as Goal-Directed Stochastic Approximators

Large Language Model (LLM) agents can be formally characterized as goal-directed stochastic processes that approximate computational traces of function compositions. When an agent interacts with tools, it is effectively attempting to approximate the execution of a program—the composition of multiple functions in sequence to achieve a specified goal. A crucial insight often overlooked is that these traces have a dual nature—they simultaneously depend on types (structural constraints) and values (specific data points), both directed toward a terminal condition.

Consider a simple trace involving a weather API with the goal of providing appropriate clothing recommendations:
```
getWeather("New York") → 72°F
recommendClothing(72°F) → "T-shirt and light pants"
GOAL: Provide weather-appropriate clothing recommendation for New York
```

This trace embodies three parallel threads of information:
- **Type-level information**: `getWeather` returns a temperature (number), which can be input to `recommendClothing`
- **Value-level information**: The specific temperature 72°F leads to the specific recommendation "T-shirt and light pants"
- **Goal-level information**: The recommendation satisfies the terminal condition of being weather-appropriate for New York

Formally, we can define a computational trace as a sequence of steps directed toward a goal:
```
T = [(f₁, x₁, τ₁, y₁), (f₂, x₂, τ₂, y₂), ..., (fₙ, xₙ, τₙ, yₙ)]
G = (τ_goal, E_v)
```

Where:
- fᵢ is the function applied at step i
- xᵢ is the input (with type τᵢ⁻¹)
- τᵢ is the output type
- yᵢ is the specific output value
- G is the goal specification comprising:
  - τ_goal: The required terminal type
  - E_v: An evaluation function mapping values of type τ_goal to a score [0,1]

An LLM agent approximates this goal-directed process as a conditional probability distribution:

$$P_\theta(a_t | h_{<t}, o_{<t}, G)$$

where:
- $a_t$ is the agent's action at time $t$ (text generation or tool call)
- $h_{<t}$ is the history of interactions up to time $t$
- $o_{<t}$ are the observations (including tool outputs) up to time $t$
- $G$ is the goal specification
- $\theta$ are the model parameters

This distribution approximates the "true" distribution of actions in ideal goal-directed computational traces:

$$P^*(a_t | h_{<t}, o_{<t}, G)$$

The quality of this approximation—and the conditions under which it succeeds or fails in achieving the specified goal—is the central focus of this paper.

## 2. The Dual Nature of Goal-Directed Predictive States

The concept of predictive states provides the theoretical foundation for understanding agent behavior. However, we must extend this concept to account for the dual nature of computational traces and their goal-directedness.

**Definition 1 (Goal-Directed Predictive State)**: A predictive state s ∈ S consists of three components:
- sᵗ: The type component, representing structural constraints on valid next functions
- sᵛ: The value component, representing the specific data that determines the exact result of function application
- sᵉ: The evaluation component, representing the estimated goal satisfaction of the current state

This leads to a refined equivalence relation for predictive states:

**Type-Level Equivalence**: 
$$h \sim^t h' \iff \forall f: \text{valid}(f|h) = \text{valid}(f|h')$$

Two histories are type-equivalent if the same set of functions can be validly applied to both.

**Value-Level Equivalence**: 
$$h \sim^v h' \iff \forall f \text{ that is valid}: P(f(h) = y) = P(f(h') = y) \, \forall y$$

Two histories are value-equivalent if applying the same function produces the same distribution over output values.

**Evaluation-Level Equivalence**:
$$h \sim^e h' \iff E_v(h) = E_v(h')$$

Two histories are evaluation-equivalent if they satisfy the goal evaluation function to the same degree.

The full predictive state equivalence requires all three:
$$h \sim h' \iff h \sim^t h' \wedge h \sim^v h' \wedge h \sim^e h'$$

In the context of function composition, the type component of predictive states often corresponds to the types of intermediate values. For example, after applying a function that returns a `String`, the type component encodes that we now have a `String` and can only apply functions that accept a `String` as input.

The optimal goal-directed function composition path can be represented as a sequence of transitions between predictive states, where each transition is triggered by applying a specific function, and the final state satisfies the goal condition:

$$s_0 \xrightarrow{f_1} s_1 \xrightarrow{f_2} s_2 \xrightarrow{f_3} \ldots \xrightarrow{f_n} s_n$$

where $s_0$ is the initial state, $s_n$ is the goal state, and $E_v(s_n) \geq \theta$ (where $\theta$ is a threshold).

## 3. Goal Specification and Terminal Conditions

The goal specification G = (τ_goal, E_v) serves as both a guiding heuristic during search and a terminal condition for the stochastic process. In practice, this goal specification is often encoded in the system prompt that controls the agent's behavior.

**Definition 2 (Terminal Condition)**: A state s is terminal if and only if:
1. The type component matches the goal type: sᵗ = τ_goal
2. The evaluation function exceeds a threshold: E_v(sᵛ) ≥ θ

This dual condition ensures that the agent both produces the correct type of output and satisfies the qualitative requirements specified by the goal.

The system prompt functions as a controller for the stochastic process by:
1. Defining the initial state s₀
2. Specifying the goal G = (τ_goal, E_v)
3. Constraining the valid state transitions
4. Establishing terminal conditions

From an information-theoretic perspective, the system prompt reduces entropy in the search space by restricting the set of valid paths and terminal states:

$$H(Paths|G) < H(Paths)$$

The agent's ability to successfully achieve goals depends on its capacity to:
1. Properly interpret the goal specification G from the system prompt
2. Maintain a representation of G during the function composition process
3. Evaluate intermediate states against G to guide search
4. Recognize when a terminal condition has been satisfied

This goal-directed framework explains why agents exhibit emergent planning behavior—they are approximating optimal paths to goal states in the predictive state space.

## 4. The Type-Value-Goal Entropy Tension

A fundamental tension exists between the bounded information capacity of the agent and the potentially unbounded entropy of the type-value-goal space. This creates an apparent paradox:

**The Type-Value-Goal Entropy Paradox**: How can an agent with fixed parameters (bounded information capacity) successfully handle the unbounded space of possible tool outputs, composition paths, and goal specifications?

Let's formalize this tension:

1. **Agent Capacity**: The maximum information content of the agent is bounded by its parameter count:
   $$I(Agent) \leq |\theta| \cdot b$$
   where $|\theta|$ is the number of parameters and $b$ is the bits per parameter.

2. **Type Entropy**: The uncertainty about which functions can be validly applied next:
   $$H(Types) = -\sum_{\tau} P(\tau) \log P(\tau)$$

3. **Value Entropy**: The uncertainty about specific output values given a function:
   $$H(Values|Types) = -\sum_{\tau} P(\tau) \sum_{v} P(v|\tau) \log P(v|\tau)$$

4. **Goal Entropy**: The uncertainty about goal satisfaction for different states:
   $$H(Eval|Types,Values) = -\sum_{\tau} P(\tau) \sum_{v} P(v|\tau) \sum_{e} P(e|\tau,v) \log P(e|\tau,v)$$

5. **Total Entropy**: The joint entropy of the type-value-goal space:
   $$H(Trace) = H(Types) + H(Values|Types) + H(Eval|Types,Values)$$

6. **Composition Space**: The entropy of all possible compositions grows exponentially with composition depth:
   $$H(Compositions) \approx O(|F|^d)$$
   where $|F|$ is the number of available functions and $d$ is the composition depth.

This creates a situation where:
$$I(Agent) \ll H(Types) + H(Values|Types) + H(Eval|Types,Values) \cdot H(Compositions)$$

For many real-world tools and goals, the combined entropy can be enormous. A weather API might return any temperature value, a database might contain millions of records, and goal evaluations can involve complex criteria.

The paradox is that despite this inequality, agents successfully compose tools to achieve complex goals. How?

## 5. Type-Level vs. Value-Level vs. Goal-Level Reasoning

LLM agents employ distinct mechanisms for handling type-level, value-level, and goal-level information:

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

**Theorem 3 (Goal-Level Approximation)**: An agent's estimate of goal satisfaction E_v(sᵛ) for a state s improves as the agent reduces value uncertainty.

**Proof**:
1. The evaluation function E_v maps values to satisfaction scores: E_v: V → [0,1]
2. Uncertainty about values propagates to uncertainty about evaluation: H(E_v(v)) ≤ H(v)
3. As value uncertainty decreases through observation: H(v|o₁,...,oₜ) < H(v|o₁,...,oₜ₋₁)
4. Therefore, goal satisfaction estimates improve with reduced value uncertainty

This threefold distinction explains a common pattern in LLM agent behavior: they can confidently reason about the structure of a solution (which functions to compose), express uncertainty about specific outcomes ("I'll need to check the weather forecast"), and progressively refine their goal trajectory as they gather more information.

## 6. Perfect Predictive States Enable Optimal Goal Achievement

We first examine the idealized case where an agent has perfect knowledge of the predictive states:

**Theorem 4 (Optimal Goal Achievement)**: An agent with perfect representation of the predictive states $S$ and goal specification $G$ can derive the optimal function composition path for any achievable goal.

**Proof Sketch**:
1. With perfect predictive states, the agent knows exactly which functions can be validly applied at each step
2. With perfect goal representation, the agent can evaluate the expected goal satisfaction of each state
3. The agent can perform heuristic search in the state space where:
   - Nodes are predictive states
   - Edges are function applications
   - Edge weights are based on function costs
   - Heuristic values are based on expected goal satisfaction
4. Using algorithms like A*, the agent can find the minimum-cost path from initial state to goal-satisfying state
5. This path is precisely the optimal function composition for goal achievement

This theorem explains why agents with strong type awareness, function understanding, and goal comprehension can perform complex compositions with minimal steps. They have effectively learned an approximation of the goal-directed predictive state space.

Specifically, an agent with perfect type-level knowledge can derive valid function compositions without fully resolving value uncertainty:

**Corollary 1 (Type-Guided Goal Composition)**: An agent with perfect knowledge of the type system can derive all valid function composition paths that potentially satisfy the goal type requirement τ_goal, even with uncertainty about specific values and evaluations.

This explains why type-aware LLM agents can plan multi-step solutions toward goals involving tools they've never used together before, as long as they understand the type signatures and goal structure.

## 7. Entropy Amplification and Goal-Directed Execution Branching

In practice, agents have imperfect knowledge of predictive states and goals, leading to phenomena we call "entropy amplification" and "goal-directed execution branching":

**Definition 3 (Entropy Amplification)**: When an agent with imperfect predictive states attempts function composition, the entropy of the joint agent-tool-goal system increases beyond the sum of their individual entropies:
$$H(Agent, Tool, Goal) > H(Agent) + H(Tool) + H(Goal)$$

This occurs because uncertainty in the agent's representation creates additional possible branches in the interaction, amplifying the overall system uncertainty.

The degree of amplification depends on the KL divergence between the agent's representation and the true predictive states:
$$H_{amplification} \propto D_{KL}(P(S_{agent}) || P(S_{true}))$$

Specifically, when an agent has incorrect or incomplete type knowledge, we observe:

**Definition 4 (Type-Driven Entropy Amplification)**: When an agent has incorrect or incomplete type knowledge, it may consider invalid function compositions to be valid, exponentially increasing the number of execution branches it must consider.

While type-level reasoning enables composition planning, and goal considerations guide direction, value-level uncertainty creates execution branches:

**Definition 5 (Goal-Directed Execution Branch)**: A goal-directed execution branch occurs when a function can return multiple possible values, each leading to a different subsequent execution path with varying degrees of expected goal satisfaction.

The number of potential execution branches grows exponentially with composition depth:

$$|Branches| = \prod_i |Values(f_i)|$$

Where $|Values(f_i)|$ is the number of distinct outputs function $f_i$ might produce.

For real-world tools and complex goals, this creates an explosion of possibilities that cannot be fully represented in the agent's fixed-capacity parameters.

## 8. Iterative Resolution of Type, Value, and Goal Uncertainty

The resolution to the Type-Value-Goal Entropy Paradox lies in how agents handle these three forms of uncertainty differently:

**Type Uncertainty**: Resolved primarily through learning from training data, where the agent internalizes the type system of the domain.

**Value Uncertainty**: Resolved primarily through iterative interaction, where the agent observes specific outputs and uses them to collapse uncertainty about the specific execution branch.

**Goal Uncertainty**: Resolved through a combination of learning common goal structures during training and refining goal estimates during execution.

**Theorem 5 (Tripartite Uncertainty Resolution)**: An agent resolves type, value, and goal uncertainty through complementary mechanisms:
1. Type uncertainty is minimized by learning the domain's type structure during training
2. Value uncertainty is collapsed through iterative sampling and observation during execution
3. Goal uncertainty is progressively reduced by refining estimates of E_v(sᵛ) based on accumulated observations

Specifically, the agent uses a strategy of:
1. Taking an action (often a tool call) with the highest expected information gain toward the goal
2. Observing the output, which collapses uncertainty about that specific output
3. Using this new information to refine goal satisfaction estimates
4. Selecting the next action to maximize expected goal progress
5. Repeating until a terminal condition is satisfied

This creates a sequential decision process where each step reduces the entropy about the specific goal-satisfying path:
$$H(Path|G,o_1, o_2, ..., o_t) < H(Path|G,o_1, o_2, ..., o_{t-1})$$

Mathematically, each observation particularly reduces value uncertainty:
$$H(Values|Types, G, o_1, o_2, ..., o_t) < H(Values|Types, G, o_1, o_2, ..., o_{t-1})$$

While type knowledge remains relatively stable throughout the interaction, and goal understanding improves through both better value estimates and progressive refinement of the implicit evaluation function.

The iterative approach allows the agent to handle greater complexity than would be possible if it had to encode all possible paths, outputs, and goal evaluations a priori. It effectively "offloads" entropy management to the interaction process.

## 9. Trading Off Steps vs. Uncertainty in Goal Achievement

This iterative goal-directed approach introduces a fundamental trade-off between the number of steps and composition uncertainty:

**Theorem 6 (Step-Uncertainty Trade-off in Goal Achievement)**: An agent can reduce composition uncertainty and improve goal alignment by increasing the number of interaction steps, with the relationship:
$$H(Composition|G) \cdot Steps \approx constant$$

More specifically, the trade-off primarily affects value uncertainty:

**Corollary 2 (Step-Value Uncertainty Trade-off)**: An agent can reduce value uncertainty and improve goal satisfaction estimates by increasing the number of interaction steps, with the relationship:
$$H(Values|Types,G) \times Steps \approx constant$$

This means an agent can either:
1. Take many small steps, each resolving a small amount of value uncertainty and incrementally improving goal alignment
2. Take fewer, larger steps, each involving more value uncertainty and riskier estimates of goal satisfaction

The optimal trade-off depends on:
1. The cost of additional API calls or interactions
2. The risk tolerance for making errors in goal satisfaction
3. The agent's confidence in its predictive state representation
4. The complexity of the value space for relevant functions
5. The sensitivity of the evaluation function E_v to different values

This explains the empirical observation that agents often break complex goal-directed tasks into smaller, more manageable steps when dealing with unfamiliar territory, while taking larger compositional leaps in familiar domains with well-understood goal structures.

## 10. Information Transfer Bounds in Goal-Directed Agents

The dual nature of computational traces and their goal-directedness has profound implications for information transfer from training data to agent parameters:

**Theorem 7 (Goal-Aware Information Transfer Bound)**: The maximum information about a goal-directed tool-using process that can be transferred from a dataset of execution traces $D$ to model weights $\theta$ is bounded by:

$$I(D; \theta) \leq |D| \cdot (H(S,G) - D_{KL}(P(S,G|D) || P(S,G)))$$

where:
- $I(D; \theta)$ is the mutual information between the dataset and model weights
- $|D|$ is the size of the dataset
- $H(S,G)$ is the joint entropy of the predictive states $S$ and goals $G$
- $D_{KL}(P(S,G|D) || P(S,G))$ is the KL divergence between the empirical distribution of states and goals observed in the dataset and the true distribution

However, the information transfers differently for types, values, and goals:

**Type-Level Transfer**: Information about types transfers efficiently because:
1. The type system is generally much smaller than the value space
2. Types follow formal rules that can be compactly represented
3. Type systems tend to be stable across examples

**Value-Level Transfer**: Information about specific values transfers less efficiently because:
1. The value space is often orders of magnitude larger than the type space
2. Value relationships may be complex and domain-specific
3. The training data can only cover a tiny fraction of possible values

**Goal-Level Transfer**: Information about goal structures transfers with intermediate efficiency:
1. Common goal patterns can be learned from multiple examples
2. The space of evaluation functions is vast but exhibits regularities
3. Goal specifications often follow natural language patterns that can be compressed

This creates a natural prioritization where agents learn type-level information most thoroughly, goal structures with moderate fidelity, and value-level information least completely, explaining why they can reason accurately about composition validity and goal direction even when uncertain about specific outcomes.

With the step-uncertainty trade-off in mind, we can expand our understanding:

**Theorem 8 (Information Transfer with Goal-Directed Iteration)**: The effective information content of a goal-directed iterative agent exceeds the static information bound of its parameters through the process of interactive sampling:
$$I_{effective}(Agent) = I(Agent) + \sum_{t=1}^T I(o_t; Path|G,o_{<t})$$

where $I(o_t; Path|G,o_{<t})$ is the information gain about the correct goal-satisfying path from each observation.

This theorem explains why even relatively small models can solve complex goal-directed compositional tasks through iterative approaches—they're effectively augmenting their fixed parameter information with dynamic information acquired through goal-directed interaction.

## 11. Practical Implications

Our goal-directed theoretical framework has several practical implications for agent design:

1. **Goal-Explicit Training**: Training should include explicit goal specifications paired with traces that satisfy those goals

2. **Type-Goal-Value Hierarchy**: Training should emphasize comprehensive coverage of the type space, moderate coverage of goal structures, while accepting that the value space can only be sparsely sampled

3. **Goal Specification Design**: System prompts should clearly specify both the structural (type) and qualitative (evaluation) components of goals

4. **Trace Diversity vs. Depth**: Training data should balance diverse examples (covering the predictive state space) with deep examples (showing extended goal-directed compositions)

5. **Explicit Uncertainty Handling**: Agents should be designed to recognize and manage their uncertainty about goal satisfaction, taking smaller steps when uncertain

6. **Goal-Aware Architectures**: Model architectures that explicitly represent and track goals alongside types can more efficiently encode predictive states

7. **Tool Design**: Tools should provide clear type signatures and structured outputs that help agents distinguish type-level from value-level information relevant to goals

8. **Interaction Protocols**: Interaction protocols should support iterative refinement, allowing agents to resolve value uncertainty progressively while maintaining goal focus

9. **Error Handling**: Error handling should distinguish between type errors (invalid compositions), value errors (unexpected outputs), and goal errors (solutions that fail to satisfy requirements), with different recovery strategies for each

10. **Hybrid Approaches**: Combining implicit prediction with explicit goal-directed reasoning allows agents to leverage the benefits of both approaches

## 12. Conclusion: A Unified Theory of Goal-Directed LLM Agents

This paper has presented a unified theoretical framework for understanding LLM agents as goal-directed stochastic approximators of computational traces, emphasizing their tripolar nature as dependent on types, values, and goals.

The key insights are:

1. Computational traces contain three parallel threads of information: types (structural constraints), values (specific data), and goals (terminal conditions and evaluation criteria)

2. Type-level reasoning enables agents to determine valid function compositions, value-level reasoning determines specific execution branches, and goal-level reasoning guides search and terminal decisions

3. Agents resolve type uncertainty primarily through training, value uncertainty primarily through iterative interaction, and goal uncertainty through a combination of both

4. The information transfer from training data to model weights is bounded by the KL divergence between predictive states, goals, and their realizations

5. Agents trade off interaction steps against uncertainty reduction and goal satisfaction, allowing them to handle complexity beyond their parameter capacity

This tripartite approach explains how agents overcome the apparent paradox between bounded parameter capacity and unbounded execution spaces, reconciling theoretical bounds with empirical success in goal achievement.

Looking forward, we believe this unified perspective offers new directions for agent design. Rather than treating types, values, and goals as interchangeable forms of information, we should design systems that explicitly separate and specialize in these distinct aspects of computation.

The most promising approach may be hybrid systems that combine neural type inference with iterative value resolution and explicit goal tracking. Such systems would leverage the strengths of each mechanism where it excels: neural components learning the type structure and goal patterns of the domain, and interactive components resolving value uncertainty through targeted sampling.

By explicitly modeling the information flow between agents, tools, and goals, and recognizing the tripartite nature of computational traces, we can develop more efficient training methodologies, better architectures for capturing predictive states, and improved strategies for handling uncertainty.

Ultimately, this framework suggests that the key to more capable goal-directed agents lies not in simply scaling parameters, but in better aligning model representations with the underlying tripartite structure of computational traces they aim to approximate. By focusing on this alignment, we can develop agents that more efficiently leverage tools to extend their capabilities beyond what their static parameters would otherwise allow, guided by well-specified goals that define terminal conditions for their stochastic processes.