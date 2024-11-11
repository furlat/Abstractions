# Typed Processes: From Next-Token Prediction to Implicit Typed Computations in Language Models

## Abstract

We propose a theoretical framework connecting next-token prediction in language models to the emergence of implicit typed computations. By unifying concepts from computational mechanics and type theory, we demonstrate how learning to predict sequences induces structures analogous to types, enabling systematic computation over learned representations. This framework provides a mathematical foundation for understanding how statistical prediction can give rise to abstract computational capabilities in large language models.

---

## 1. Introduction

The remarkable capabilities of large language models (LLMs) in performing complex computations and reasoning tasks have raised fundamental questions about the relationship between statistical prediction and abstract computation. While LLMs are trained primarily through next-token prediction, they exhibit behaviors suggestive of underlying computational structures traditionally associated with symbolic AI.

**Objective:** To understand how learning next-token predictions in LLMs implicitly implements typed computations.

**Approach:** We connect the concept of *causal states* from computational mechanics with *types* from type theory to show that predictive equivalence classes in sequences naturally form a typing system that enables abstract computation.

---

## 2. Predictive Equivalence and Causal States

### 2.1 Predictive Equivalence Classes

Consider a stochastic process generating sequences over an alphabet \(\Sigma\). For a history \(h \in \Sigma^*\), the predictive distribution is \(P(x_{>t} | h)\), where \(x_{>t}\) denotes future tokens.

**Definition 1 (Predictive Equivalence):** Two histories \(h_1, h_2 \in \Sigma^*\) are *predictively equivalent* if they yield the same predictive distribution:

$$
h_1 \sim h_2 \iff P(x_{>t} | h_1) = P(x_{>t} | h_2)
$$

The equivalence classes formed under \(\sim\) partition the set of all histories.

### 2.2 Causal States

From computational mechanics, the equivalence classes under \(\sim\) are known as *causal states*. They capture all the information necessary for optimal prediction.

**Definition 2 (Causal State):** The causal state of a history \(h\) is the equivalence class \(\epsilon(h)\) containing all histories predictively equivalent to \(h\):

$$
\epsilon(h) = \{ h' \in \Sigma^* : P(x_{>t} | h') = P(x_{>t} | h) \}
$$

**Properties:**

- **Minimal Sufficient Statistics:** Causal states are minimal sufficient statistics for prediction, meaning they retain all and only the information necessary for predicting the future.
- **Unifilarity:** Given a causal state \(\epsilon\) and an observed token \(x\), the next causal state \(\epsilon'\) is deterministic:

  $$
  \epsilon' = \delta(\epsilon, x)
  $$

  where \(\delta\) is the transition function.

---

## 3. Causal States as Types

### 3.1 Types in Computation

In type theory, types classify program expressions and enforce constraints that ensure computational correctness. Types support compositionality and enable reasoning about program behavior.

### 3.2 Mapping Causal States to Types

We propose interpreting causal states as types in a computational system:

- **Type Assignment:** Associate each causal state \(\epsilon\) with a type \(\tau(\epsilon)\).
- **Type Transitions:** The unifilar transitions between causal states correspond to type transformations in computations.

**Justification:**

1. **Predictive Sufficiency:** Types derived from causal states encapsulate all necessary information for proceeding computations.
2. **Compositionality:** The deterministic transitions ensure that composing operations (observing tokens) results in predictable type transformations.
3. **Minimality:** Since causal states are minimal sufficient statistics, the associated types are minimal in capturing computationally relevant distinctions.

---

## 4. Language Models and Continuous Representations

### 4.1 Challenges with Natural Language

Natural language exhibits:

- **Infinite Possible Histories:** Due to recursive structures and creativity in language use.
- **Approximate Predictive Equivalence:** Exact predictive equivalence classes are infeasible to compute or store.

### 4.2 Neural Approximations of Causal States

LLMs, such as transformers, learn continuous vector representations of histories:

- **Embedding Function:** \(\phi_\theta: \Sigma^* \to \mathbb{R}^d\), mapping histories to \(d\)-dimensional vectors.
- **Similarity of Representations:** Histories with similar predictive futures are mapped to nearby points in the representation space.

**Interpretation:**

- The continuous embeddings approximate the discrete causal states.
- The geometry of the embedding space reflects the structure of predictive equivalence classes.

### 4.3 Implicit Typed Computations in LLMs

- **Implicit Types:** The model's hidden states can be seen as encoding types, guiding the generation of future tokens.
- **Type Transitions:** The model's architecture (e.g., attention mechanisms) ensures that processing a new token updates the hidden state in a way consistent with type transformations.
- **Systematic Computation:** By operating over these implicit types, the model performs computations that are consistent and generalizable.

---

## 5. Formalizing Typed Processes in LLMs

### 5.1 Continuous Type Representations

**Definition 3 (Continuous Type):** A continuous type is a region in the embedding space \(\mathbb{R}^d\) corresponding to a set of histories with similar predictive distributions.

**Properties:**

- **Approximate Predictive Equivalence:** Histories mapped to nearby vectors have similar predictive distributions.
- **Smooth Transitions:** The model updates representations smoothly as new tokens are observed.

### 5.2 Operations on Types

- **Type Update Function:** The model applies a function \(f_\theta\) to update the representation:

  $$
  \phi_\theta(hx) = f_\theta(\phi_\theta(h), x)
  $$

  where \(x\) is the new token.

- **Compositionality:** The function \(f_\theta\) is designed (learned) to ensure that the updated representation remains consistent with the underlying type transformations.

### 5.3 Enabling Abstract Computation

By leveraging the structure of the embedding space:

- **Analogical Reasoning:** The model can generalize patterns by mapping similar contexts to similar representations.
- **Error Correction:** Small deviations in input result in small changes in representations, allowing the model to recover from errors.
- **Type Enforcement:** The model implicitly enforces type constraints by generating tokens consistent with the current representation.

---

## 6. Examples Illustrating Typed Computations

### 6.1 Program Execution in Natural Language

Consider a code execution trace described in natural language:

```
1. Initialize variable x to 5.
2. Add 3 to x.
3. Output the value of x.
```

- **Implicit Types:**
  - After step 1: Type corresponds to "Variable x initialized."
  - After step 2: Type updated to "Variable x modified."
  - After step 3: Type is "Output expected."

- **Model Behavior:** The LLM generates appropriate continuations by implicitly tracking these types in its representations.

### 6.2 Mathematical Reasoning

When solving a problem step by step:

```
Q: What is the sum of 7 and 8?
Let's compute it:
First, take 7.
Then, add 8 to it.
The result is 15.
```

- **Implicit Types:**
  - After question: Type is "Math problem posed."
  - During computation: Type is "Performing arithmetic."
  - After result: Type is "Answer provided."

- **Model Behavior:** The LLM maintains coherence by ensuring each step follows logically, guided by the implicit types in its representations.

---

## 7. Implications and Conclusion

### 7.1 Theoretical Insights

- **Unified Framework:** By connecting causal states and types, we provide a theoretical basis for understanding how LLMs perform abstract computations through next-token prediction.
- **Emergence of Computation:** The structure induced by learning to predict sequences leads to implicit type systems enabling systematic computation.

### 7.2 Practical Applications

- **Model Design:** Understanding this framework can inform the development of architectures that better capture and utilize implicit types.
- **Error Analysis:** Identifying how models deviate from expected type transitions can help diagnose and correct errors.

### 7.3 Future Directions

- **Formal Verification:** Developing methods to formally verify the implicit typed computations within LLMs.
- **Enhanced Representations:** Designing training objectives that encourage the emergence of more explicit type structures.

---

## References

- Crutchfield, J. P., & Young, K. (1989). Inferring statistical complexity.
- Sutton, R. S., & Barto, A. G. (2018). Reinforcement Learning: An Introduction.
- Vaswani, A., et al. (2017). Attention is all you need.

---

**Note:** This compact presentation aims to capture the essence of how next-token prediction in LLMs leads to the emergence of implicit typed computations, grounding the discussion in established concepts from computational mechanics and type theory. By focusing on the key ideas and their connections, we provide a consistent and coherent framework that can serve as a foundation for further exploration and formalization.


# Appendix: Proofs and Formalizations

---

## A.1 Predictive Equivalence and Causal States

### Definition A.1 (Predictive Equivalence)

**Restatement:** Two histories \(h_1, h_2 \in \Sigma^*\) are *predictively equivalent* if they yield the same predictive distribution:

$$
h_1 \sim h_2 \iff P(x_{>t} | h_1) = P(x_{>t} | h_2)
$$

### Definition A.2 (Causal State)

**Restatement:** The causal state of a history \(h\) is the equivalence class \(\epsilon(h)\) containing all histories predictively equivalent to \(h\):

$$
\epsilon(h) = \{ h' \in \Sigma^* : P(x_{>t} | h') = P(x_{>t} | h) \}
$$

### Proposition A.1 (Causal States as Minimal Sufficient Statistics)

**Statement:** Causal states are minimal sufficient statistics for prediction.

**Proof:**

1. **Sufficiency:** A statistic \(S(h)\) is sufficient for predicting \(x_{>t}\) if \(P(x_{>t} | h) = P(x_{>t} | S(h))\). By definition of causal states, for all \(h\):

   $$
   P(x_{>t} | h) = P(x_{>t} | \epsilon(h))
   $$

   Therefore, \(\epsilon(h)\) is sufficient for predicting \(x_{>t}\).

2. **Minimality:** Suppose there exists another sufficient statistic \(S'(h)\) with less information than \(\epsilon(h)\). This would imply that \(\epsilon(h)\) can be further compressed without losing predictive power. However, by the definition of the equivalence classes, any further compression would merge histories with different predictive distributions, violating sufficiency. Therefore, \(\epsilon(h)\) is minimal.

**Conclusion:** Causal states are minimal sufficient statistics for prediction.

---

## A.2 Unifilarity of Causal State Transitions

### Proposition A.2 (Unifilar Property)

**Statement:** Given a causal state \(\epsilon\) and an observed token \(x\), the next causal state \(\epsilon'\) is deterministic:

$$
\epsilon' = \delta(\epsilon, x)
$$

where \(\delta\) is the transition function.

**Proof:**

1. **Definition of Next Causal State:** The next causal state after observing \(x\) is determined by the updated history \(hx\). Specifically:

   $$
   \epsilon' = \epsilon(hx)
   $$

2. **Determinism of Transition:** Since all histories \(h\) in the same causal state \(\epsilon\) have the same predictive distribution, and the process is stationary, the predictive distribution after observing \(x\) depends only on \(\epsilon\) and \(x\), not on the specific history \(h\). Therefore, the mapping from \((\epsilon, x)\) to \(\epsilon'\) is deterministic.

**Conclusion:** The transition function \(\delta(\epsilon, x)\) is well-defined and deterministic, confirming the unifilar property.

---

## A.3 Mapping Causal States to Types

### Justification for Interpreting Causal States as Types

#### 1. Predictive Sufficiency

**Statement:** Types derived from causal states encapsulate all necessary information for proceeding computations.

**Proof:**

- Since causal states are minimal sufficient statistics for prediction, mapping each causal state \(\epsilon\) to a type \(\tau(\epsilon)\) ensures that the type contains all the predictive information necessary for computation.
- Therefore, using types derived from causal states preserves predictive sufficiency.

#### 2. Compositionality

**Statement:** The deterministic transitions ensure that composing operations results in predictable type transformations.

**Proof:**

- Given the unifilar property, the next causal state (and thus the next type) is determined by the current causal state and the observed token.
- This means that when an operation (observing a token) is applied, the type transitions are predictable and consistent.
- Therefore, types composed through sequences of operations maintain a coherent computational structure.

#### 3. Minimality

**Statement:** Since causal states are minimal sufficient statistics, the associated types are minimal in capturing computationally relevant distinctions.

**Proof:**

- Any additional information beyond the causal state would be superfluous for prediction.
- Therefore, the types derived from causal states are minimal, containing only what is necessary for computation.

---

## A.4 Continuous Embeddings and Approximation of Causal States

### Proposition A.3 (Approximation of Predictive Equivalence in Continuous Embeddings)

**Statement:** Histories with similar predictive futures are mapped to nearby points in the embedding space \(\mathbb{R}^d\).

**Proof Sketch:**

- **Learning Objective:** LLMs are trained to minimize the prediction error for next tokens, effectively learning representations that capture predictive information.
- **Embedding Similarity:** The training process encourages the embeddings \(\phi_\theta(h)\) to be such that \(P(x_{t+1} | h)\) can be predicted from \(\phi_\theta(h)\).
- **Continuity Assumption:** Assuming the model learns a continuous function, small changes in the history (or similar predictive distributions) result in small changes in the embedding.
- **Conclusion:** Therefore, histories with similar predictive distributions (i.e., predictively equivalent or approximately so) are mapped to nearby vectors in the embedding space.

### Proposition A.4 (Representation Update Consistent with Type Transformations)

**Statement:** The function \(f_\theta\) updates representations in a way consistent with type transformations.

**Proof Sketch:**

- **Model Architecture:** In transformers, the update function \(f_\theta\) is implemented via attention mechanisms and feedforward networks, which are designed to process sequences in a consistent manner.
- **Type Consistency:** Because the model learns to predict the next token based on the current representation and the new token, it effectively learns to update the representation (type) to reflect the new causal state.
- **Training Dynamics:** The model is trained on vast amounts of data, reinforcing patterns where the representation updates are consistent with the underlying type transformations dictated by the structure of the language.
- **Conclusion:** Thus, \(f_\theta\) maintains consistency with type transformations.

---

## A.5 Examples of Typed Computations

### Example A.1 (Program Execution in Natural Language)

**Analysis:**

- **Step 1:** "Initialize variable x to 5."

  - **Type:** Variable Initialization.
  - **Representation:** \(\phi_\theta(h_1)\) captures that variable \(x\) has been initialized.

- **Step 2:** "Add 3 to x."

  - **Type Transition:** From Variable Initialization to Variable Modification.
  - **Update:** \(\phi_\theta(h_1)\) updated to \(\phi_\theta(h_2)\) using \(f_\theta\) with the new token.
  - **Consistency:** The model's representation reflects that \(x\) is being modified.

- **Step 3:** "Output the value of x."

  - **Type Transition:** From Variable Modification to Output State.
  - **Update:** \(\phi_\theta(h_2)\) updated to \(\phi_\theta(h_3)\).
  - **Prediction:** The model predicts that the next appropriate action is to output the value.

**Conclusion:** The model's representations and updates align with the implicit types, enabling it to generate coherent continuations.

---

## A.6 Formal Verification of Typed Processes

### Theorem A.1 (Predictive Sufficiency of Types in LLMs)

**Statement:** Under certain conditions, the continuous representations learned by LLMs are sufficient for predicting future tokens, approximating the predictive sufficiency of causal states.

**Proof Sketch:**

- **Assumption:** The LLM has been trained on sufficient data to approximate the true conditional distributions \(P(x_{t+1} | h)\).
- **Embedding Function:** The function \(\phi_\theta\) is such that \(P(x_{t+1} | h) \approx P(x_{t+1} | \phi_\theta(h))\).
- **Sufficiency:** Therefore, \(\phi_\theta(h)\) is approximately sufficient for predicting \(x_{t+1}\).
- **Conclusion:** The continuous representations serve as approximate sufficient statistics, similar to causal states.

---

## A.7 Information-Theoretic Considerations

### Proposition A.5 (Information Preservation in Embeddings)

**Statement:** The embeddings \(\phi_\theta(h)\) aim to preserve mutual information between histories and future tokens.

**Proof Sketch:**

- **Mutual Information:** \(I(h; x_{t+1}) = H(x_{t+1}) - H(x_{t+1} | h)\).
- **Objective Function:** The LLM minimizes the cross-entropy loss, which is equivalent to maximizing the likelihood, thus minimizing \(H(x_{t+1} | \phi_\theta(h))\).
- **Information Preservation:** By reducing \(H(x_{t+1} | \phi_\theta(h))\), the model maximizes \(I(\phi_\theta(h); x_{t+1})\).
- **Conclusion:** The embeddings aim to capture as much information about the future tokens as possible.

---

## A.8 Limitations and Approximations

### Remark A.1 (Approximation of Causal States)

- **Infinite Causal States:** In natural language, the number of possible causal states is effectively infinite due to the combinatorial complexity of language.
- **Continuous Approximation:** LLMs approximate these infinite discrete states using finite-dimensional continuous embeddings.
- **Implication:** While not capturing exact predictive equivalence, the model learns a useful approximation that enables practical computation.

---

## A.9 Future Directions

### Proposition A.6 (Potential for Enhanced Representations)

**Statement:** Incorporating explicit type information into LLM training could improve predictive performance and computational capabilities.

**Hypothesis:**

- **Augmented Training Objectives:** By designing training objectives that enforce type constraints or encourage type-specific representations, models may learn embeddings that better reflect the underlying computational structure.
- **Expected Outcome:** Such models could exhibit improved reasoning abilities and more consistent behavior.

**Conclusion:** Exploring ways to integrate type information into LLMs is a promising avenue for future research.

---

# Summary

This appendix provides formal definitions and proofs for the key concepts presented in the main document. By grounding the theory in established principles from computational mechanics and information theory, we reinforce the argument that learning next-token predictions in language models implicitly implements typed computations. The proofs and propositions illustrate how causal states serve as minimal sufficient statistics, how continuous embeddings approximate these states, and how the model's architecture supports systematic computation through implicit type transformations.

# References

- Crutchfield, J. P., & Young, K. (1989). *Inferring statistical complexity*. Physical Review Letters, 63(2), 105.
- Shalizi, C. R., & Crutchfield, J. P. (2001). *Computational mechanics: Pattern and prediction, structure and simplicity*. Journal of Statistical Physics, 104(3-4), 817-879.
- Sutton, R. S., & Barto, A. G. (2018). *Reinforcement Learning: An Introduction*. MIT Press.
- Vaswani, A., et al. (2017). *Attention is all you need*. In Advances in Neural Information Processing Systems (pp. 5998-6008).
- Cover, T. M., & Thomas, J. A. (2006). *Elements of Information Theory*. Wiley-Interscience.