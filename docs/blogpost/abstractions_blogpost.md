# LLM Agents as Policies in Typed Program Space
### tags: @vision @abstractions

## Introduction
This year was supposed to be the year of the agents, yet they stumble. There have been remarkable improvements in coding agents, but the definitely not sporadic mistakes stand out even more against their skillful successes.

I believe this has mostly to do with our lack of understanding, or better, a lack of framing for what LLM agents actually are. As a result, many doubts arise about what they should do and how they should do it. This is not surprising, given the wide range of theories that tempt us while navigating such a complex problem. It is not an easy task to lift the autoregression of symbolic sequences into a coherent theory of agency.

Moreover, agency is only half of the story: if they are agents, what is their environment?

The goal of this post, and of this blog in general, is to contribute a clearer vision of what we are building, in a way that remains consistent across the entire theoretical stack. We will start from the top, by formalizing in what sense a function-calling LLM can be considered a goal-directed agent.

We will focus on the general setup of a function-calling agent equipped with a finite set of functions, a computing engine to execute them, and a clear terminal reward signal. Think of one of the default LangChain or PydanticAI agents interacting with a Python REPL.

First, we want to properly characterize the interaction between the LLM and the computing environment as a potentially partially observable Markov Decision Process. This will require a clear separation between the environment’s state, its afferents, the resulting state update rules, and how these elements appear as the agent’s observations and actions.

Second, we want to formalize the structure of the computing environment in a way that helps us better understand LLM agents. To do so, we will draw on ideas from pure functional programming and model the computing environment as a category of object types whose morphisms are the typed functions that the agent can execute.

Under a first, simplified approximation where the problem semantics are fully modeled by the type system, we can define rewards or goals as a partition function over the set of types. In this view, the objective of the agent is to compose a sequence of functions into a program that leads to a terminal type maximizing reward. Alternatively, given a set of initial objects, the task becomes finding a path through a typed category that reaches a reward partition. 
 

We will see that in this relatively simplistic setting, we can initially enumerate the complete state space of programs and navigate it using traditional algorithms such as A* or BFS. However, as we include more realistic compositional patterns, the state space explodes, pushing us back toward a reinforcement learning framework in the hope of discovering more efficient navigation policies. 

In the conclusion, we will further emphasize the fundamental role of the language modeling aspect of the agent by exploring the scenario where the given base types are not sufficient to model the goal condition. From a categorical perspective, this requires further refinements, or fibrations, of the base category of types, typically expressed as exhaustive predicates over typed records. From the classical search perspective, this represents not only a combinatorial explosion but also a significant increase in modeling cost, since the minimal set of predicates that fully recovers the maximally coarse fibration sufficient for successful navigation must be known in advance by the researcher designing the environment. Still, LLMs often appear to navigate the fibration implicitly, for instance when they must identify the relevant subrecord to process among several of the same type, suggesting that an approximate encoding of the fibration is already embedded within their learned representations.

## The Reinforcement Learning Perspective on Function-Calling Agents

We will now build our empirical setup in Python, followed by the corresponding mathematical formulation in terms of a partially observable Markov Decision Process. More formally, we study the **joint stochastic process** emerging from the interaction between a function calling LLM agent and its computing environment.

### From Next-Token Prediction to Decision-Making

As mentioned earlier, it is not straightforward to lift next-token prediction into a decision-making framework composed of actions, observations, and consequences, each of which may involve multiple steps of generation.

We start from the basic autoregressive formulation for multistep generation of a language model, which defines a probability distribution over generated token sequences of length $T$ conditional on the semi-infinite prefix of previously generated tokens:

$$
P_\theta(\tau_{1:T}) = \prod_{t=1}^{T} P_\theta(\tau_t \mid \tau_{<t})
$$

where $\tau_t$ denotes the token generated at position $t$, and $\tau_{<t}$ represents the prefix of previously generated tokens.  
In this view, the model defines a left-to-right stochastic process that sequentially samples the next symbol conditioned on its textual history.

To move from this token-level process to a **decision-making** framework, we segment the token stream into **turns** using special control tokens inserted during assistant post-training. These artificial tokens define syntactical boundaries between:

1. the agent’s generations (e.g. tool calls or textual reasoning),
2. the environment’s responses, and  
3. the user’s requests.

A single **turn** thus corresponds to the subsequence of tokens between a *start-of-turn* and an *end-of-turn* token.  
The autoregressive process can equivalently be expressed as a stochastic process over these turns:

$$
P_\theta(\text{turn}_{1:N}) = \prod_{t=1}^{N} P_\theta(\text{turn}_t \mid \text{turn}_{<t})
$$

Each conditional distribution $P_\theta(\text{turn}_t \mid \text{turn}_{<t})$ captures the model’s behavior at the turn level and serves as the **behavioral policy** governing the agent’s generation.

During inference, the transformer recursively generates tokens until the *end-of-turn* token is reached.  
The resulting string is then parsed into a structured object (typically JSON) that can be passed to the computing environment. The environment executes the corresponding call and returns a stringifiable response, which is appended to the agent’s context as part of the next observation.

For this blog post, we will stop at this level of abstraction and define our sequential decision-making problem at the turn level. In future work, we will attempt to define the problem at the token level using the language of options, modeling each turn as a temporally extended action. This would resemble how local continuous control policies are applied to robotic systems to chain symbolic behaviors into coherent trajectories.




### Observation Space and Behavioral Policies

Let there be an agent interacting with a computing environment through a discrete sequence of function calls.  
At each step $t$, the agent selects a function $f_t$ from a finite set of callable functions and provides an input $x_t$ drawn from the corresponding input space.  
The environment executes the call $(f_t, x_t)$ and returns an observable output $y_t$, which is appended to the ongoing context available to the agent.

At this point, the agent observes a history $h_t$ consisting of all previous function calls and their responses:

$$
h_t = ((y_i, (f_i, x_i)))_{i < t}
$$

where each pair $(f_i, x_i)$ represents a function selected by the agent together with its input, and $y_i$ is the corresponding response returned by the environment (i.e. the computing engine).

The agent policy defines the probability of selecting the next function and its input given this interaction history:

$$
P(f_t, x_t \mid h_t, s_0)
$$

where $s_0$ is the initial state of the environment.

---

### Environment Response and State Evolution

The environment maintains an internal state $s_t$, which may correspond, for example, to the current memory of a Python REPL session, a running kernel, or any in-memory data structure that evolves as function calls are executed.  
Given the initial state $s_0$, the environment defines two stochastic processes: the **state transition** and the **response generation**.

The **state transition** updates the internal state after each function call:

$$
s_{t+1} \sim P(s_{t+1} \mid s_t, f_t, x_t)
$$

and the **response generation** produces an observable output based on the current state and the function execution:

$$
y_t \sim P(y_t \mid s_t, f_t, x_t)
$$

Together, these define the environment kernel that mediates the agent’s interaction with the computing system.

---

### Stateful Functions and Non-Degenerate Side Effects

In the general case, functions may have **non-degenerate side effects**, meaning they can modify the internal state of the environment without changing the definition of the functions themselves.  
For example, executing a function that writes a variable in a Python kernel alters the REPL state even though the function’s interface remains the same.

Under this assumption, the environment’s state is a deterministic or stochastic function of the initial state $s_0$ and the complete history of interactions:

$$
s_t = g(s_0, ((y_i, (f_i, x_i)))_{i < t})
$$

The environment’s response distribution can therefore be written as:

$$
P(y_t \mid f_t, x_t, h_t, s_0)
$$

which generalizes the previous formulation to include the underlying state evolution.



### The Pure (Stateless) Case

In the most well-behaved setting, we consider **pure functions**, where function calls have no side effects and do not alter or depend on the environment’s internal state other than through the observable output.  
This property is naturally guaranteed in **immutable environments**, which treat every function input and output as distinct and non-overlapping data.  
Each call produces a new object rather than updating an existing one, effectively creating a functional copy of the system at each step.  
In such cases, the *observable outputs* are **conditionally independent** of the internal state given the function and its input:

$$
P(y_t \mid f_t, x_t, s_t) = P(y_t \mid f_t, x_t)
$$

This describes a purely functional interaction model where the environment behaves as a deterministic or stochastic function evaluator, and all side effects are eliminated at the level of observable behavior.

In contrast, **mutable environments** such as a Python REPL modify in-memory objects directly. Each function call may overwrite variables or data structures, which means that even if individual functions are pure in isolation, the system as a whole becomes stateful because subsequent calls can observe those mutations.  
This situation must be carefully managed in the way functions are written and composed, often increasing the **modeling cost** for the environment designer, who must explicitly control how and when state is preserved or reset.






