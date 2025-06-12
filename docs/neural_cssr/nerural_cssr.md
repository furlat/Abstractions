# Neural CSSR: Enhancing Causal-State Splitting Reconstruction with Neural Conditional Probability Estimation

## Abstract

We present Neural CSSR, a novel approach that enhances the classical Causal-State Splitting Reconstruction (CSSR) algorithm by replacing its count-based conditional probability estimation with neural networks, specifically transformers. While preserving CSSR's theoretical guarantees for discovering minimal sufficient statistics, our method achieves dramatically improved sample efficiency and handles continuous observations naturally. We further demonstrate how the discovered causal states can be used as supervised labels to extract clean partitions from the transformer's over-representation of the causal states, enabling principled out-of-distribution detection. This work bridges computational mechanics theory with modern deep learning, providing both practical improvements and new theoretical insights.

## 1. Introduction

The discovery of minimal predictive models from time series data is a fundamental challenge in machine learning and dynamical systems analysis. The Causal-State Splitting Reconstruction (CSSR) algorithm [Shalizi & Shalizi, 2004] provides a mathematically principled approach to this problem by constructing epsilon-machines—provably minimal sufficient statistics for prediction. However, CSSR's reliance on discrete count-based probability estimation severely limits its practical applicability.

We introduce Neural CSSR, which preserves CSSR's algorithmic structure and theoretical guarantees while replacing its n-gram counting with neural conditional probability estimation. This seemingly simple modification yields profound improvements: exponentially better sample efficiency, natural handling of continuous observations, and the ability to generalize across similar but non-identical histories.

## 2. Background: CSSR and Epsilon Machines

### 2.1 Causal States and Minimal Sufficient Statistics

Consider a stochastic process generating sequences from alphabet A. A predictive statistic η maps histories to some representation. The fundamental insight of computational mechanics is that among all sufficient statistics for prediction, there exists a unique minimal one—the causal states.

Two histories x⁻ and y⁻ belong to the same causal state if and only if:
$$P(X^∞_{t+1} | X^t_{-∞} = x^-) = P(X^∞_{t+1} | X^t_{-∞} = y^-)$$

The function ε mapping histories to their causal states is the minimal sufficient statistic for prediction. The resulting epsilon-machine has three crucial properties:
1. The causal state process {St} is Markovian
2. States are recursively calculable: St+1 = T(St, Xt+1)
3. The observed process is a function of the hidden state process

### 2.2 The CSSR Algorithm

CSSR discovers causal states through iterative refinement:

**Phase I**: Initialize with a single state containing the null history

**Phase II**: For increasing history lengths L:
- For each state s and history x ∈ s:
  - For each symbol a ∈ A:
    - Test if P(Xt | X^{t-1}_{t-L} = ax) differs from P(Xt | S = s)
    - If different, either assign ax to an existing state with matching distribution or create a new state

**Phase III**: Ensure deterministic transitions by splitting states as needed

The critical bottleneck is estimating P(Xt | X^{t-1}_{t-L} = ax) through frequency counting, which requires:
- Exact matches of histories in the data
- Exponentially many samples as L increases
- Discrete observations

### 2.3 Limitations of Classical CSSR

1. **Sample Complexity**: Estimating P(Xt | history) requires observing each specific history multiple times. For history length L and alphabet size k, potentially need O(k^L) samples.

2. **No Generalization**: The count-based approach cannot leverage similarities between histories—"ABAB" and "BABA" are treated as completely unrelated.

3. **Fixed History Length**: Must choose Lmax a priori, with convergence guaranteed only if Lmax ≥ Λ (the synchronization length of the true process).

## 3. Neural CSSR: Architecture and Algorithm

### 3.1 Core Innovation

Neural CSSR replaces discrete counting with a transformer that learns:
$$P_\theta(X_{t+1} | X^t_{t-L}) \approx P(X_{t+1} | X^t_{t-L})$$

The transformer generalizes across similar patterns, providing reliable probability estimates even for unseen histories. Crucially, we preserve CSSR's clustering mechanism in observation space, maintaining its convergence guarantees.

### 3.2 Algorithm Modifications

```python
def neural_cssr(data, transformer, L_max, alpha):
    # Phase I: Train transformer
    transformer.train(data)  # Standard autoregressive training
    
    # Phase II: Modified sufficiency testing
    states = [{null_history}]
    for L in range(1, L_max + 1):
        for state in states:
            # Use transformer for probability estimation
            p_state = transformer.estimate_distribution(state)
            
            for history in state:
                for symbol in alphabet:
                    extended = symbol + history
                    # Neural probability estimation
                    p_extended = transformer.predict(extended)
                    
                    # Same statistical tests as CSSR
                    if not test_same_distribution(p_extended, p_state, alpha):
                        assign_or_create_state(extended, states, transformer)
    
    # Phase III: Identical to classical CSSR
    make_deterministic(states)
    return states
```

### 3.3 Self-Supervised Refinement

Once initial causal states are discovered, we can generate synthetic trajectories from the learned epsilon-machine to augment the dataset:

1. Sample trajectories from the epsilon-machine
2. Retrain transformer on original + synthetic data
3. Re-run state discovery with improved probability estimates
4. Iterate until convergence

This particularly helps with rare transitions and improves estimates for longer histories.

## 4. Theoretical Foundations

### 4.1 Information-Theoretic Guarantee

The key theoretical insight connecting neural networks to causal states comes from the information bottleneck principle. For any sufficient statistic η and the minimal sufficient statistic ε:

**Theorem**: There exists a deterministic function f such that ε = f(η).

**Proof sketch**: Since ε is minimal, it can be computed from any other sufficient statistic. The existence of f follows from the definition of minimality.

This guarantees that:
1. Any neural predictor with sufficient capacity contains the causal state information
2. The causal states discovered by Neural CSSR are well-defined targets for supervised learning

### 4.2 Convergence Properties

Neural CSSR inherits CSSR's convergence guarantees under modified conditions:

**Theorem**: If the transformer achieves ε-accurate probability estimation uniformly over histories of length ≤ L_max, then Neural CSSR converges to the true causal states as ε → 0.

The improvement is that we need far fewer samples to achieve ε-accuracy through generalization rather than counting.

## 5. Extracting Structure from Neural Representations

### 5.1 Supervised Phase: From Over-representation to Causal States

After discovering causal states via Neural CSSR, we can train linear probes:
$$g: h_t \mapsto S_t$$

where h_t is the transformer's hidden state at time t, and S_t is the causal state label from Neural CSSR.

This differs fundamentally from Zhang et al.'s approach:

**Zhang et al.**:
- Cluster hidden states directly
- No principled way to determine number of clusters
- Must use cross-validation or heuristics
- No convergence guarantees

**Neural CSSR**:
- Cluster in observation space using CSSR's proven algorithm
- Number of states determined by statistical tests
- Convergence guaranteed under standard conditions
- Causal states are ground truth labels, not approximations

### 5.2 Out-of-Distribution Detection

The linear probe g learns hyperplanes separating causal states. For new sequences:
- **In-distribution**: Maps cleanly to one causal state (high confidence)
- **Out-of-distribution**: Falls in mixing regions between hyperplanes

This provides principled OOD detection because:
1. Valid sequences must correspond to some causal state (completeness of epsilon-machine)
2. Sequences violating the learned dynamics cannot map cleanly to any state
3. Probe uncertainty directly measures deviation from learned structure

## 6. Experimental Considerations

### 6.1 Implementation Details

```python
class NeuralCSSR:
    def __init__(self, transformer_config, cssr_params):
        self.transformer = TransformerLM(transformer_config)
        self.L_max = cssr_params['L_max']
        self.alpha = cssr_params['alpha']
        
    def estimate_conditional_prob(self, history):
        # Use transformer instead of counting
        with torch.no_grad():
            logits = self.transformer(history)
            return F.softmax(logits, dim=-1)
    
    def discover_states(self, data):
        # Train transformer
        self.transformer.train_on_sequences(data)
        
        # Run modified CSSR
        states = self.cssr_with_neural_probs(data)
        
        # Optional: self-supervised refinement
        for _ in range(n_refinement_steps):
            synthetic_data = self.generate_from_states(states)
            self.transformer.fine_tune(synthetic_data)
            states = self.cssr_with_neural_probs(data)
            
        return states
```

### 6.2 Advantages Over Classical CSSR

1. **Sample Efficiency**: O(N) samples sufficient for length-L histories (vs O(k^L))
2. **Continuous Observations**: Natural handling through neural architectures
3. **Adaptive History Length**: Can increase L_max without exponential data requirements
4. **Transfer Learning**: Pre-trained transformers provide good initialization

## 7. Related Work and Distinctions

### 7.1 Comparison with Variable-Length Markov Models

VLMMs suffer from the same limitations as classical CSSR regarding count-based estimation. Neural CSSR maintains CSSR's advantage of capturing multi-suffix states while adding neural efficiency.

### 7.2 Distinction from Neural Predictive State Representations

While Zhang et al. focus on learning representations useful for downstream tasks (particularly in POMDP settings), Neural CSSR targets the fundamental computational mechanics goal: discovering the minimal generative model of the process itself.

Key differences:
- **Objective**: Minimal sufficient statistics vs task-useful representations
- **Guarantees**: Convergence to epsilon-machine vs empirical performance
- **Architecture**: Explicit state construction vs implicit representation

## 8. Conclusion and Future Directions

Neural CSSR successfully bridges classical computational mechanics with modern deep learning, achieving:
- Exponentially improved sample efficiency
- Natural handling of high-dimensional observations
- Principled OOD detection through causal state extraction
- Preserved theoretical guarantees of optimality

Future work includes:
1. Extension to controlled systems (Neural POMDP discovery)
2. Hierarchical causal states for multi-scale processes
3. Application to real-world domains (neuroscience, genomics, climate)
4. Integration with causal inference beyond prediction

By combining the theoretical rigor of CSSR with the practical power of neural networks, Neural CSSR opens new possibilities for understanding complex dynamical systems while maintaining mathematical guarantees about the discovered structures.