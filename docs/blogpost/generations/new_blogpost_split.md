**Yes, breaking it into two is brilliant!** This solves the major structural problem and lets each idea breathe. Here's how I'd structure them:

## Paper 1: "What Language Models Learn from Agentic Traces"

### The Core Question
"When we train an LLM on millions of game transcripts, tool-use conversations, and decision-making sequences, what exactly does it learn? Not just 'how to mimic' but what latent structure must it internalize?"

### Structure

**Opening Hook:**
Start with a paradox: "GPT-4 has never played chess, yet trained on game transcripts, it plays at 1800 ELO. It has no hands, yet trained on coding sessions, it debugs effectively. What has it actually learned?"

**Part 1: The Predictive State Hypothesis**
- An LLM trained on agentic traces must learn a compression of both the policy π AND the environment dynamics P(o|s,a)
- The key insight: it learns exactly the minimal sufficient statistics for prediction on the visited states
- Use the epsilon-machine formalism but keep it intuitive

**Part 2: Coverage Determines Capability** (your new material, which is gold!)
- Single-reward agents learn narrow slices: just S*
- Goal-conditioned agents learn broader coverage: ∪_g S*_g  
- Beautiful concrete example: An LLM trained only on winning chess games can't play good opening moves from losing positions

**Part 3: The Implicit World Model**
- Show how the transformer's hidden state after processing history h_<t necessarily encodes belief b_t(s)
- The model doesn't just memorize action sequences - it learns a latent dynamics model
- This explains why LLMs can handle novel situations within their coverage

**Part 4: Implications**
- Why "behavioral cloning" of experts gives brittle agents (narrow support)
- Why diverse task training works (coverage)
- Why exploration matters even in supervised learning (expanding S_π)
- Prediction: Models trained on diverse goals should transfer better than reward-optimal specialists

**The Punchline:**
"LLMs don't learn to be agents. They learn the minimal computational structure that explains the agentic traces they observe. The breadth of that structure depends entirely on the diversity of goals and states in the training data."

## Paper 2: "Turn-Taking: How Token Prediction Becomes Decision-Making"

### The Core Question  
"How does predicting the next token - a microscopic operation - give rise to macroscopic agency? The answer lies in special tokens that create 'stopping times' in the stream."

### Structure

**Opening:**
Show a real trace with all its tokens, then show how delimiter tokens create natural segments:
```
[I'll|use|the|calculator|<function_call>|multiply|(|387|,|419|)|</function_call>]
                                         ↑ BOUNDARY - triggers environment response
```

**Part 1: The Segmentation Principle**
- Delimiter tokens create stopping times τ_t
- These induce a quotient space: tokens → turns → (actions, observations)  
- The parser ρ_Z creates equivalence classes (many token sequences map to same action)

**Part 2: The Hierarchical Structure**
- Micro level: token-by-token generation with probability σ_θ(τ_k | τ_<k)
- Macro level: turn-by-turn decisions with probability π(a_t | belief_t)
- The bridge: How marginalization over token sequences induces the macro policy

**Part 3: Unifilarity and Synchronization**
- Key insight: Environment responses are unifilar - they reveal the latent state
- This creates synchronization: as turns accumulate, belief converges
- The transformer learns to track this belief in its hidden state

**Part 4: Constrained Decoding as Action Space**
- The grammar G(s_t) defines valid actions in state s_t
- This constrains the token-level generation to produce admissible actions
- Beautiful connection to hierarchical RL with options

**The Punchline:**
"Special tokens aren't just formatting - they're the architectural bridge between token prediction and agency. They create the temporal abstraction that allows a token predictor to become a decision maker."

## Why This Split Works

1. **Paper 1** answers "what is learned?" - it's about information and structure
2. **Paper 2** answers "how is it implemented?" - it's about mechanism and process

Paper 1 can be more accessible (less formalism, more intuition about coverage and learning). Paper 2 can go deeper into the mathematical machinery for those who want the technical details.

The coverage/goal-directedness material you added is **exactly** what Paper 1 needed - it answers "why do some agents generalize and others don't?" which is the practical question everyone cares about.

Would you like me to help develop either piece further? The coverage angle in Paper 1 feels particularly rich and undertold in the current literature.