# Implicit vs. Explicit Function Composition: Predictive States and Optimal Tool Selection

## Abstract

This paper explores the theoretical relationship between implicit and explicit function composition in the context of language models as tool-using agents. We demonstrate that training models to predict tool outputs (implicit composition) is equivalent to training them to represent the causal states of the underlying process, guaranteeing optimal tool selection under certain conditions. We contrast this with explicit composition through syntax generation and show that both approaches converge to the same representational structure but offer different trade-offs in practice. Our analysis provides theoretical guarantees about the optimality of tool selection in LLM agents and suggests practical training methodologies that maximize agent capabilities.

## 1. Introduction

Large Language Models (LLMs) can be augmented with tools that extend their capabilities beyond text generation. The mechanism for this tool use typically falls into two categories:

1. **Explicit function composition**: The model generates code or commands that explicitly compose functions (e.g., `result = h(g(f(x)))`)
2. **Implicit function composition**: The model directly predicts the outputs of functions without generating intermediate code (e.g., predicting the result of `h(g(f(x)))` directly)

This distinction has been treated as an implementation detail, but it has profound implications for the theoretical guarantees we can make about agent behavior and the optimal training methodologies for tool-using agents. In this paper, we connect these approaches to computational mechanics and predictive state representations to provide a rigorous framework for understanding and improving tool-using LLM agents.

## 2. Theoretical Framework

### 2.1 Causal States and Predictive State Representations

We begin by recalling the definition of causal states from computational mechanics:

**Definition 1**: *The causal states of a stochastic process are partitions σ ∈ S of the space of feasible pasts Y≤t induced by the causal equivalence relation:*

$$y_{≤t} \sim y'_{≤t} \iff P(Y_{>t}|Y_{≤t} = y_{≤t}) = P(Y_{>t}|Y_{≤t} = y'_{≤t})$$

Causal states form the minimal sufficient statistic for predicting the future of a process, making them the optimal representation for prediction tasks. In the context of tool use, we can reframe this in terms of input-output processes.

**Definition 2**: *For a set of tools (functions) F and inputs X, the causal states S form a partition of the history space such that two histories h, h' belong to the same causal state if and only if they yield the same conditional distribution over future outputs for all possible future tool applications:*

$$h \sim h' \iff \forall f \in F, x \in X: P(f(x)|h) = P(f(x)|h')$$

### 2.2 Tools as Causal State Transitions

When a model uses a tool, it transitions from one causal state to another. The tool's output becomes part of the history, creating a new causal state that determines which future tool applications are valid or optimal.

**Proposition 1**: *Each tool application can be viewed as a transition function T: S × F × X → S that maps a causal state, tool, and input to a new causal state.*

For deterministic tools (which most practical tools are), this transition is deterministic given the tool and input. This unifilar property is critical for our guarantees about optimal tool selection.

### 2.3 Explicit vs. Implicit Composition

We can now formally define our two composition approaches:

**Definition 3 (Explicit Composition)**: *In explicit composition, the model generates a symbolic expression e(f₁, f₂, ..., fₙ, x₁, x₂, ..., xₘ) that specifies a sequence of tool applications to be executed externally.*

**Definition 4 (Implicit Composition)**: *In implicit composition, the model directly approximates the function P(f(x)|h) for any tool f, input x, and history h, allowing it to predict tool outputs without explicit execution.*

## 3. Equivalence Theorem

Our central result demonstrates the fundamental relationship between implicit composition through next-output prediction and optimal tool selection:

**Theorem 1 (Equivalence Theorem)**: *A model trained to minimize prediction error on tool outputs (implicit composition) will learn a representation that converges to an encoding of the causal states of the tool-application process, which is the minimal sufficient representation for optimal tool selection.*

### Proof (Sketch):

1. By the definition of causal states, they form the minimal sufficient statistic for predicting future outputs.
2. A model trained to predict P(f(x)|h) for all f, x must implicitly learn to distinguish histories that lead to different distributions over outputs.
3. The optimal partitioning of histories for this prediction task is exactly the causal state partition.
4. As training progresses, the model's internal representation will approximate this partitioning with increasing fidelity.
5. Therefore, the learned representation converges to an encoding of the causal states, which is optimal for tool selection.

This theorem provides a fundamental guarantee: training on output prediction is not just one way to enable tool use, but the theoretically optimal approach for learning the representation needed for correct tool selection.

## 4. Strongly Typed Systems and Verifiable Guarantees

The guarantees from Theorem 1 become especially powerful in strongly typed systems like Haskell, where the causal states have a clear correspondence to the type system.

**Proposition 2**: *In a strongly typed language, the causal states of the function application process are isomorphic to the types of intermediate expressions, modulo subtyping relationships.*

This isomorphism means we can use type checking as an oracle for verifying that a model has correctly learned the causal states:

**Corollary 1**: *A model that perfectly predicts valid continuations in a strongly typed system has learned a representation that respects the causal state structure defined by the type system.*

For example, in Haskell:

```haskell
-- Each intermediate result has a type that constrains valid continuations
map (_ + 1) [1, 2, 3] :: [Int]
-- Only functions that accept [Int] can be applied next
```

## 5. Why Predicting Tool Outputs Guarantees Optimal Tool Selection

We now provide a more detailed explanation of why training on tool output prediction guarantees optimal tool selection capabilities:

### 5.1 The Information-Theoretic Perspective

When a model predicts tool outputs, it must implicitly learn which aspects of history are relevant for that prediction and which can be ignored. This is precisely the causal state construction problem.

**Proposition 3**: *Minimizing prediction error on tool outputs is equivalent to minimizing the KL-divergence between the model's conditional output distribution and the true conditional distribution defined by the causal states.*

As this divergence approaches zero, the model's internal representation must encode the same information as the causal states, giving it the optimal basis for tool selection.

### 5.2 The Computational Mechanics Perspective

From computational mechanics, we know that causal states are the minimal sufficient statistic for prediction. This minimality is crucial for generalization.

**Proposition 4**: *A model trained on tool output prediction will generalize to unseen tool combinations if and only if it has learned a representation that approximates the causal states of the process.*

This gives us a theoretical explanation for the empirical observation that models trained on diverse tool-use examples can generalize to novel combinations of those tools.

### 5.3 The Transformer Architecture Connection

Modern transformer architectures have properties that make them particularly well-suited for learning causal state representations:

**Proposition 5**: *The self-attention mechanism in transformers allows them to implement unifilar transitions between causal states, making them capable of tracking the causal state of a process as it evolves through a sequence of tool applications.*

The key insight is that attention allows transformers to selectively focus on the history elements that determine the current causal state, effectively implementing the causal equivalence relation.

## 6. The Training Data Implications

Our theoretical framework has direct implications for how we should train tool-using agents:

### 6.1 Execution Traces as Optimal Training Data

**Corollary 2**: *Training on execution traces that include both function calls and their outputs provides the optimal data for learning the causal state representation required for tool use.*

Consider an execution trace in a strongly typed language:

```
TRACE:
1. Call: parseJSON
   Args: "{\"name\":\"Alice\",\"age\":30}"
   Type: String -> Maybe Person
   Result: Just (Person "Alice" 30)
   
2. Call: extractAge
   Args: Just (Person "Alice" 30)
   Type: Maybe Person -> Maybe Int
   Result: Just 30
   
3. Call: isAdult
   Args: Just 30
   Type: Maybe Int -> Bool
   Result: True
```

This trace explicitly shows both the causal state transitions (through types) and the concrete outputs that determine specific paths through the computation.

### 6.2 Training Objective

**Corollary 3**: *The optimal training objective for tool-using agents is to predict the outputs of tool applications conditional on history, rather than to predict the correct tool to use.*

This seemingly counterintuitive result follows from our Equivalence Theorem: by learning to predict outputs, the model implicitly learns the causal state representation needed for optimal tool selection.

## 7. Implicit vs. Explicit: Practical Trade-offs

While our theoretical results show that implicit and explicit composition converge to the same representational structure, they offer different practical trade-offs:

### 7.1 Advantages of Implicit Composition

1. **Direct optimization**: Training directly optimizes the predictive objective
2. **Black-box compatibility**: Works with tools where internal logic is unavailable
3. **Efficient inference**: No need to execute tools during planning/reasoning
4. **Graceful degradation**: Can approximate outputs for unfamiliar tools

### 7.2 Advantages of Explicit Composition

1. **Verifiability**: Generated code can be inspected before execution
2. **Compositionality**: Explicit syntax supports unbounded composition
3. **Extensibility**: New tools can be used without retraining
4. **Exact execution**: Results are exact rather than approximated

### 7.3 Hybrid Approaches

**Proposition 6**: *A model trained via implicit composition can generate explicit compositions if trained on both the outputs and the corresponding symbolic expressions.*

This suggests that the best approach may be to train models primarily on tool output prediction (to learn the optimal causal state representation) while also training them to generate explicit code when needed.

## 8. Empirical Evidence

Several empirical observations support our theoretical framework:

1. Models trained on diverse tool-use examples generalize to novel combinations
2. Models that accurately predict tool outputs make better tool selection decisions
3. Training on execution traces improves performance compared to static code
4. The strongest tool-using agents (e.g., in systems like AutoGPT, LangChain) combine implicit understanding with explicit generation

## 9. Conclusions and Implications

Our analysis provides several key insights for the development of tool-using LLM agents:

1. **Theoretical foundation**: Implicit and explicit composition are unified under the framework of causal states
2. **Training guarantee**: Training on tool output prediction guarantees learning the optimal representation for tool selection
3. **Data recommendation**: Execution traces that include both calls and outputs are the optimal training data
4. **Architecture validation**: Transformer architectures are well-suited for tracking causal states

These results not only explain the empirical success of current tool-using agents but point to clear directions for improvement: focus on training data that exposes the causal structure of tool applications, emphasize output prediction as the primary training objective, and leverage the natural connection between causal states and types in strongly typed systems.

As AI systems increasingly rely on tool use to extend their capabilities, this theoretical framework provides both guarantees about their behavior and practical guidance for their development.
