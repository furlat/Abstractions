# Typed-Processes: From Next-Token Prediction to Controllable Abstraction Machines

## Abstract

We introduce Typed Processes, a theoretical framework that establishes how next-token prediction gives rise to abstract computation. Our key insight is that the natural partitioning of sequences into equivalence classes based on their predictive futures (causal states) forms an optimal typing system for abstract computation. We prove that these types are minimal sufficient statistics for prediction, demonstrate how modern neural architectures implicitly approximate these abstractions, and show how this enables systematic computation over learned representations. This work provides theoretical foundations for understanding how statistical prediction can give rise to abstract computation, with implications far beyond language models to any system that learns to predict sequential data.



## 1. Introduction

The emergence of computational capabilities from statistical learning remains one of the fundamental mysteries in artificial intelligence. Recent large language models (Brown et al., 2020; Chowdhery et al., 2022) demonstrate remarkable abilities to perform abstract reasoning and computation purely through next-token prediction, challenging our understanding of the relationship between statistical prediction and symbolic computation.

This apparent gap between statistical learning and abstract computation has deep historical roots. On one side, the symbolic AI tradition, building on Church's λ-calculus (Church, 1936) and McCarthy's LISP (McCarthy, 1960), emphasizes explicit representation and manipulation of symbols. On the other, the neural network tradition following Rosenblatt (1958) and later advanced by Rumelhart et al. (1986) focuses on statistical learning from data. The success of modern language models suggests these perspectives might be reconcilable, but the theoretical foundations for such a synthesis remain elusive.

Apparently unrelated fields, made progress on several fronts. In computational mechanics, Crutchfield and Young (1989) introduced ε-machines and causal states as minimal sufficient statistics for prediction, providing a rigorous framework for discovering structure in stochastic processes. Parallel developments in type theory, particularly session types (Honda et al., 1998) and linear types (Girard, 1987), offered formal tools for reasoning about sequential computation. Meanwhile, information-theoretic approaches to representation learning (Tishby et al., 1999) suggested principles for extracting relevant abstractions from data.

Our key insight is that these threads can be unified through the lens of predictive equivalence. We show that the causal states of a process—equivalence classes of histories with identical predictive futures—naturally form an optimal typing system for abstract computation. This builds on pioneering work connecting computational mechanics to automata theory (Barnett and Crutchfield, 2015), while extending it to the realm of learned representations and abstract computation.

### 1.1 From Statistical Prediction to Abstract Types

The foundation of our framework rests on a simple but profound observation: prediction induces structure. When a system learns to predict its next observation, it must implicitly discover and represent the patterns that govern its environment's behavior. In the language of computational mechanics, these patterns manifest as causal states—minimal sufficient statistics that capture all predictively relevant information while discarding predictively irrelevant details.

This process of prediction-induced abstraction has been observed in various contexts, from dynamical systems (Shalizi and Crutchfield, 2001) to quantum mechanics (Gu et al., 2012), but its implications for abstract computation have not been fully explored. We demonstrate that these naturally emerging abstractions constitute an optimal typing system, in a precise mathematical sense that we will develop.

The optimality of this typing system stems from three key properties:
1. Minimality: It captures exactly the information required for prediction, no more and no less
2. Compositionality: The types support systematic combination and transformation
3. Unifilarity: Type transitions are deterministic given new observations

These properties establish causal states not just as statistical constructs but as legitimate types for abstract computation. This connection provides theoretical grounding for recent empirical observations about the emergence of computational capabilities in large language models while suggesting new approaches to engineering systems that compute with learned abstractions.

To make these ideas concrete, consider two illustrative examples that demonstrate how predictive equivalence naturally gives rise to computational types:


### Example 1: Assembly Program Execution

Consider the following x86 assembly sequence:
```assembly
mov eax, 5    ; Type: RegisterOperation
add eax, 3    ; Type: ArithmeticOperation
push eax      ; Type: StackOperation
pop ebx       ; Type: StackOperation
```

While this appears as a sequence of tokens, it naturally partitions into equivalence classes based on what can follow. After "mov eax, 5", the set of valid next tokens is determined not by the specific tokens "mov eax, 5" but by the fact that it's a RegisterOperation that placed a value in eax. Any other sequence that results in a value in eax (like "push 5; pop eax") would belong to the same equivalence class.

These equivalence classes form our types:
- RegisterOperation: Sequences after which register operations are valid
- ArithmeticOperation: Sequences requiring operands in specific registers
- StackOperation: Sequences affecting the stack state

The crucial insight is that these types emerge naturally from the predictive distribution over next valid tokens. Two sequences belong to the same type if and only if they lead to the same distribution over possible next operations.

### Example 2: Chain of Thought Reasoning

Consider a language model solving a math problem:
```
Q: If John has 3 apples and buys 2 more, how many does he have?
Let's solve this step by step:
1) Initial amount = 3
2) Amount bought = 2
3) Total = 3 + 2 = 5
Therefore, John has 5 apples.
```

This sequence naturally partitions into types based on predictive futures:
- QuestionState: Sequences ending with a problem statement
- ReasoningState: Sequences during step-by-step solution
- ConclusionState: Sequences ready for final answer

Again, two sequences share a type if they lead to the same distribution over possible continuations. Any sequence ending with a problem statement belongs to QuestionState regardless of the specific numbers involved, because it leads to the same pattern of step-by-step reasoning.

### From Examples to Theory

These examples illustrate the core insight: abstract computation emerges from the natural clustering of sequences based on their predictive futures. Formally:

1. **Equivalence Relation**: Two histories $h_1, h_2$ are equivalent if they lead to the same predictive distribution:
   $$h_1 \sim h_2 \iff P(x_{>t}|h_1) = P(x_{>t}|h_2)$$

2. **Types as Causal States**: The equivalence classes under this relation are precisely the causal states from computational mechanics, and they form our types.

3. **Optimal Typing**: This typing system is optimal in that it:
   - Captures all predictively relevant information
   - Uses minimal memory (statistical complexity)
   - Supports compositional operations
   - Respects computational abstractions

4. **Unifilar Evolution**: Type transitions are deterministic given new tokens, enabling systematic computation:
   $$\tau(h_1x) = \tau(h_2x) \text{ whenever } h_1 \sim h_2$$

To establish these claims rigorously, we develop our theory in three parts. First, we review the framework of computational mechanics (Section 2) and its relationshipt to predictive states, which provides the foundation for understanding how prediction induces structure through causal states. We then introduce the relevant concepts from type theory (Section 3), focusing particularly on session types and their role in sequential computation. Finally, we bridge these perspectives through automata theory (Section 4), showing that causal states form a canonical automaton that naturally satisfies the requirements of a type system while maintaining optimality properties.

This systematic development allows us to:
1. Ground our understanding of predictive types in the well-established framework of computational mechanics
2. Leverage the rich theory of types for reasoning about computational properties
3. Use automata theory to establish the fundamental connection between prediction and computation

The synthesis of these perspectives provides new insights into how statistical prediction gives rise to abstract computation, while suggesting practical principles for engineering systems that compute with learned abstractions.

# 2. Theoretical Foundations: From Prediction to Abstraction

## 2.1 Predictive States and Sufficiency

Understanding how statistical prediction gives rise to abstract computation requires us to first examine how systems represent and maintain predictive knowledge. In reinforcement learning and representation learning, this question has led to the development of predictive state representations—a formalism that captures how a system can compress history into a state that maintains perfect prediction of the future.

Consider a system observing a sequence of symbols from some alphabet $\Sigma$. At each time $t$, the system has observed a history $x_{\leq t}$ and must predict the future trajectory $x_{>t}$. The fundamental question is: what information from history must be maintained to enable this prediction?

A predictive state representation answers this question by providing a mapping from histories to states that preserve predictive power. Formally:

**Definition 1** (Predictive State). A function $\phi: \Sigma^* \to \mathcal{S}$ forms a predictive state representation if for all histories, the predicted distribution over futures remains unchanged when conditioning on the state instead of the full history:

$$P(X_{>t}|X_{\leq t}) = P(X_{>t}|\phi(X_{\leq t}))$$

The power of this definition becomes apparent when we examine its implications through the lens of information theory and dynamical systems. Three fundamental properties emerge:

First, the state $\phi(X_{\leq t})$ must capture all predictively relevant information from history. This sufficiency condition can be expressed precisely through mutual information:

$$I[X_{>t}; X_{\leq t}] = I[X_{>t}; \phi(X_{\leq t})]$$

This equality tells us that the state retains exactly the information from history needed to predict the future, no more and no less.

Second, once we have computed the state, the original history becomes redundant for prediction. This Markov property is expressed as:

$$P(X_{t+1}|X_{\leq t}, \phi(X_{\leq t})) = P(X_{t+1}|\phi(X_{\leq t}))$$

This means the state forms a sufficient summary of all we need to know about the past.

Third, these states must update systematically as new observations arrive. There exists some function $f$ such that:

$$\phi(X_{\leq t+1}) = f(\phi(X_{\leq t}), X_{t+1})$$

This update rule is crucial: it means we can maintain our predictive knowledge incrementally, without repeatedly processing the entire history.

Modern machine learning architectures have developed sophisticated ways to implement these predictive states, each with its own strengths and theoretical justifications:

Neural networks provide perhaps the most direct approach, learning to embed histories into high-dimensional continuous spaces through end-to-end training:

$$\phi_\theta(x_{\leq t}) = \text{NN}_\theta(x_{\leq t})$$

These embeddings can capture complex patterns but often lack interpretable structure.

State space models take a more explicit approach to modeling dynamics, learning both a state representation and transition model:

$$s_t = \phi(x_{\leq t}), \quad P(x_{t+1}|s_t)$$

This separation of representation and dynamics can make the learned states more interpretable but may miss subtle dependencies.

Perhaps most intriguingly, transformer architectures use attention mechanisms to compute context-dependent representations:

$$\phi(x_{\leq t}) = \text{Attention}(Q(x_t), K(x_{<t}), V(x_{<t}))$$

This mechanism allows the model to selectively attend to relevant parts of history, potentially discovering hierarchical structure in the data.

However, while these approaches achieve sufficiency for prediction, they often do so at a cost. The learned representations typically use more dimensions than necessary, mix predictively relevant and irrelevant information, and don't naturally discover clean abstraction boundaries. This raises a crucial question: among all possible predictive state representations, is there an optimal one? One that captures predictive information in its most compressed and structured form? This question leads us naturally to the concept of causal states, which we explore in the next section.

## 2.2 Causal States: Minimal Predictive States

Causal states emerge when we impose minimality on predictive states through an equivalence relation. This construction reveals deep connections between prediction, computation, and abstract types.

**Definition 2** (Causal Equivalence). Two histories $h_1, h_2$ are causally equivalent ($h_1 \sim h_2$) if and only if:

$$P(X_{>t}|X_{\leq t} = h_1) = P(X_{>t}|X_{\leq t} = h_2)$$

The resulting equivalence classes are the causal states, forming a partition of histories that is both sufficient and minimal for prediction. This optimality is captured by:

**Theorem 1** (Minimality). For any other predictive state representation $\phi$:
$$H[\epsilon(X_{\leq t})] \leq H[\phi(X_{\leq t})]$$
where $\epsilon$ maps histories to their causal states.

The relationship between causal states and abstract computation becomes clear through their relation to hidden state inference. Consider a finite-state edge-label hidden Markov machine with:
1. A finite set of states $\mathcal{S} = \{\sigma_1, ..., \sigma_N\}$
2. A finite alphabet of symbols $\Sigma$
3. Symbol-labeled transition matrices $T^{(x)}$, where $T^{(x)}_{ij}$ gives the probability of transitioning from state $\sigma_i$ to state $\sigma_j$ on symbol $x$

When this machine has unifilar transitions (the next state is completely determined by the current state and next output symbol), causal states correspond exactly to the belief states over the underlying hidden states. This unifilar property ensures that:

$$H[S_{t+1}|X_{t+1}, S_t] = 0$$

This connection to hidden state inference has profound implications for abstraction, establishing causal states as the natural foundation for abstract computation:

### 1. Information-Theoretic Optimality

Causal states achieve a fundamental trade-off between prediction and compression through two complementary properties:

a) **Predictive Sufficiency**: They capture all predictively relevant information:
   $$I[X_{>t}; \epsilon(X_{\leq t})] = I[X_{>t}; X_{\leq t}]$$
   This means no other representation can achieve better prediction of the future.

b) **Minimal Complexity**: Among all sufficient statistics, they minimize memory:
   $$H[\epsilon(X_{\leq t})] \leq H[\phi(X_{\leq t})]$$
   for any other sufficient statistic $\phi$.

This optimality has a concrete interpretation in terms of abstract computation: causal states form the smallest set of distinguishable computational states that maintain perfect prediction. Any further compression would lose predictive power, while any expansion would introduce redundant computation.

### 2. Synchronization and Learning

The exponential synchronization property:
$$P(\text{not synchronized after } L \text{ steps}) \leq K\alpha^L$$
has three crucial implications for abstract computation:

a) **Efficient State Inference**: An observer can quickly identify the current abstract computational state from observations

b) **Error Recovery**: Small mistakes in state tracking are rapidly corrected through continued observation

c) **Sample Complexity**: The number of observations needed to learn the abstract computation structure scales logarithmically:
   $$L \sim O(\log(1/\epsilon))$$
   to achieve accuracy $\epsilon$ in state identification

### 3. Deterministic Abstract Operations

The unifilar property provides the key bridge between statistical prediction and abstract computation:

a) **State Transitions**: Given current state $s_t$ and observation $x_{t+1}$, the next state is deterministic:
   $$H[S_{t+1}|X_{t+1}, S_t] = 0$$

b) **Compositional Structure**: Operations can be composed without accumulating uncertainty:
   $$\epsilon(h_1x) = \epsilon(h_2x) \text{ whenever } h_1 \sim h_2$$

c) **Type Safety**: The deterministic transitions ensure that abstract operations preserve type constraints:
   $$\tau(\epsilon(h_1)) = \tau(\epsilon(h_2)) \implies \tau(\epsilon(h_1x)) = \tau(\epsilon(h_2x))$$

### Implications for Abstract Computation

This combination of properties makes causal states uniquely suited as a foundation for abstract computation:

1. **Optimal Abstraction Boundaries**: The equivalence classes naturally identify the minimal distinctions needed for prediction

2. **Computational Efficiency**: Operations can be implemented using minimal memory while maintaining perfect prediction

3. **Learnability**: The structure can be efficiently learned from examples due to exponential synchronization

4. **Compositionality**: Operations can be reliably composed due to deterministic transitions

5. **Error Tolerance**: The system naturally recovers from errors through continued observation

This establishes that causal states aren't just statistically optimal predictions—they form the natural computational primitives for abstract operations over sequences. The equivalence classes define the minimal sufficient distinctions needed for computation, while the unifilar transitions ensure these distinctions can be systematically maintained and composed.

# 2.3 From Causal States to Continuous Abstractions with Transformers

While causal states provide the theoretical foundation for understanding predictive abstractions, natural language presents fundamental challenges that necessitate a different approach to representation learning. In this section, we analyze these challenges and show how modern language models address them through continuous approximations of predictive states.

## 2.3.1 Combinatorial Complexity of Language

The application of computational mechanics to natural language reveals immediate challenges for exact causal state reconstruction. Consider a minimal formalization of the problem:

**Definition 3** (Language n-gram States). Let $V$ be a vocabulary and $n$ be a context length. The potential causal states for an n-gram model form equivalence classes over histories $h \in V^n$ based on their predictive distributions:

$$h_1 \sim h_2 \iff P(X_{t+1}|h_1) = P(X_{t+1}|h_2)$$

Even for modest parameters, this leads to an intractable state space:

**Proposition 3** (State Space Growth). For vocabulary size $|V|$ and context length $n$, the upper bound on potential causal states is $|V|^n$. For typical language models where $|V| \approx 5 \times 10^4$ and $n \geq 4$, this gives $|S| \gtrsim 10^{19}$ potential states.

This combinatorial explosion becomes more severe when considering true linguistic structure:

**Theorem 4** (Language Complexity). Any -machine capable of capturing the full predictive statistics of natural language must have:

1. An infinite state space $|S| = \infty$ due to:
   - Recursive grammatical structures
   - Unbounded semantic compositions
   - Long-range dependencies

2. Non-stationary transition dynamics:
   $$P(X_{t+1}|S_t) \neq P(X_{t'+1}|S_{t'})$$
   due to context-dependent interpretation

3. Complex equivalence relations capturing semantic similarity:
   $$h_1 \sim h_2 \iff \text{sem}(h_1) = \text{sem}(h_2)$$
   where $\text{sem}$ maps histories to their semantic interpretations

These results suggest that exact causal state reconstruction for language is fundamentally intractable. However, this connects to a deeper principle in computational mechanics: just as non-unifilar hidden Markov models naturally lead to working with distributions over states (mixed states) rather than pure states, the complexity of language necessitates working with continuous representations that can be viewed as "mixed causal states."

**Definition 4** (Mixed Causal States). For a set of causal states $\mathcal{S}$, a mixed causal state $m$ is a probability distribution over $\mathcal{S}$:
$$m \in \Delta(\mathcal{S}) = \{p \in \mathbb{R}^{|\mathcal{S}|} : \sum_i p_i = 1, p_i \geq 0\}$$

This perspective suggests reframing transformer representations not as approximations of pure causal states, but as natural analogues of mixed states in a continuous space:

**Proposition 4** (Continuous Mixed States). Transformer hidden states $h \in \mathbb{R}^d$ can be interpreted as parameterizing a continuous analogue of mixed states where:
1. Pure states correspond to extremal points in the representation space
2. Interpolated states represent uncertainty or partial matching
3. The attention mechanism implements soft state updates

This connects to both:
- Classical belief state tracking in non-unifilar HMMs: $b_{t+1} = \text{update}(b_t, x_{t+1})$
- Modern transformer attention: $h_{t+1} = \text{attention}(h_t, x_{t+1})$

This formulation motivates our subsequent development of continuous abstractions that maintain the key properties of causal states—sufficiency and minimality—while enabling both practical computation and principled generalization through geometry.

## 2.3.2 The Geometry of Learned Representations

Modern transformer architectures address the intractability of exact causal states through a fundamentally different geometric approach. We formalize this approach through three key mechanisms:

**Definition 5** (Continuous State Space). Instead of discrete causal states $\epsilon: \Sigma^* \to \mathcal{S}$, transformers learn a continuous embedding function:

$$\phi_\theta: \Sigma^* \to \mathbb{R}^d$$

where $d$ is typically large (e.g., $10^3$ to $10^4$) and $\theta$ are learned parameters.

This continuous representation supports three crucial properties:

### 2.3.2.1 Learned Metrics

Instead of exact equivalence relations, transformers learn similarity functions through attention:

**Definition 6** (Attention-based Similarity). For histories $h_1, h_2$, their similarity is computed as:

$$\text{sim}(h_1, h_2) = \text{softmax}\left(\frac{Q(\phi_\theta(h_1))K(\phi_\theta(h_2))^T}{\sqrt{d}}\right)$$

where $Q, K: \mathbb{R}^d \to \mathbb{R}^d$ are learned projections.

This relaxation from binary equivalence to continuous similarity enables:

**Theorem 5** (Smooth Approximation). For histories $h_1, h_2$ with causal states $\epsilon(h_1), \epsilon(h_2)$:

$$\|\phi_\theta(h_1) - \phi_\theta(h_2)\| \approx D(\epsilon(h_1), \epsilon(h_2))$$

where $D$ measures predictive divergence between causal states.

### 2.3.2.2 Differentiable Dynamics

The transition structure of the representation space is learned through differentiable operations:

**Definition 7** (Continuous Transitions). State transitions are implemented as:

$$\phi_\theta(hx) = f_\theta(\phi_\theta(h), \text{embed}(x))$$

where $f_\theta: \mathbb{R}^d \times \mathbb{R}^d \to \mathbb{R}^d$ is a learned neural network and $\text{embed}: \Sigma \to \mathbb{R}^d$ maps tokens to embeddings.

This enables a crucial property:

**Theorem 6** (Continuous Interpolation). For any histories $h_1, h_2$ and tokens $x_1, x_2$:

$$\|\phi_\theta(h_1x_1) - \phi_\theta(h_2x_2)\| \leq L(\|\phi_\theta(h_1) - \phi_\theta(h_2)\| + \|\text{embed}(x_1) - \text{embed}(x_2)\|)$$

for some Lipschitz constant $L$, ensuring smooth variation in state transitions.

## 2.3.3 From Discrete to Continuous Abstractions

The geometric approach to representation learning leads to fundamental differences from classical causal states, which we can formalize:

### Properties of Representations

**Theorem 7** (Representation Dichotomy). Let $\phi_\theta$ be a trained transformer embedding and $\epsilon$ be the causal state mapping. The fundamental differences are:

1. **Information Capture**:
   - Causal States: $I[X_{>t}; \epsilon(X_{\leq t})] = I[X_{>t}; X_{\leq t}]$ (exact)
   - Transformer: $I[X_{>t}; \phi_\theta(X_{\leq t})] \approx I[X_{>t}; X_{\leq t}]$ (approximate)

2. **State Space Structure**:
   - Causal States: Countable set $\mathcal{S}$ with $|\mathcal{S}| = \infty$ for language
   - Transformer: Continuous manifold $\mathcal{M} \subset \mathbb{R}^d$

3. **Transition Properties**:
   - Causal States: Discrete transitions $T: \mathcal{S} \times \Sigma \to \mathcal{S}$
   - Transformer: Smooth paths $\gamma: [0,1] \to \mathcal{M}$

### Geometric Operations

The continuous structure enables operations impossible in discrete representations:

**Definition 8** (Geometric Operations). The representation space $(\mathcal{M}, \|\cdot\|)$ supports:

1. **State Interpolation**: For histories $h_1, h_2$:
   $$\gamma(t) = (1-t)\phi_\theta(h_1) + t\phi_\theta(h_2), t \in [0,1]$$
   produces meaningful intermediate states.

2. **Semantic Arithmetic**: Vector operations correspond to semantic transformations:
   $$\|\phi_\theta(h_{\text{target}}) - (\phi_\theta(h_1) - \phi_\theta(h_2) + \phi_\theta(h_3))\| < \epsilon$$
   for semantically related histories.

3. **Local Structure**: Neighborhoods preserve semantic relationships:
   $$\|h_1 - h_2\|_{\text{semantic}} \approx \|\phi_\theta(h_1) - \phi_\theta(h_2)\|$$

**Theorem 9** (Geometric Generalization). These properties enable three forms of generalization:

1. **Interpolative**: Between known states
   $$P(x|\gamma(t)) \approx (1-t)P(x|h_1) + tP(x|h_2)$$

2. **Compositional**: Through vector operations
   $$\phi_\theta(h_{\text{new}}) = f(\phi_\theta(h_1), \phi_\theta(h_2), ..., \phi_\theta(h_n))$$

3. **Robust**: To perturbations
   $$\|\phi_\theta(h + \delta) - \phi_\theta(h)\| \leq L\|\delta\|$$
   for Lipschitz constant $L$

These properties emerge naturally from the geometric structure rather than being explicitly enforced, suggesting that continuous representations are fundamental to generalization in language models.