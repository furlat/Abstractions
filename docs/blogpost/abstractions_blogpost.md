# LLM Agents as Policies in Typed Program Space
### tags: @vision @abstractions

## Introduction
This year was supposed to be the year of the agents, yet they stumble. There have been remarkable improvements in coding agents, but the definitely not sporadic mistakes stand out even more against their skillful successes.

I believe this has mostly to do with our lack of understanding, or better, a lack of framing for what LLM agents actually are. As a result, many doubts arise about what they should do and how they should do it. This is not surprising, given the wide range of theories that tempt us while navigating such a complex problem. It is not an easy task to lift the autoregression of symbolic sequences into a coherent theory of agency.

Moreover, agency is only half of the story: if they are agents, what is their environment?

The goal of this post, and of this blog in general, is to contribute a clearer vision of what we are building, in a way that remains consistent across the entire theoretical stack. We will start from the top, by formalizing in what sense a function-calling LLM can be considered a goal-directed agent.

We will focus on the general setup of a function-calling agent equipped with a finite set of functions, a computing engine to execute them, and a clear terminal reward signal.Our objective is twofold.

    First, we want to properly characterize the interaction between the LLM and the computing environment as a potentially partially observable Markov Decision Process. This will require a clear separation between the environment’s state, its afferents, the resulting state update rules, and how these elements appear as the agent’s observations and actions.

    Second, we want to formalize the structure of the computing environment in a way that helps us better understand LLM agents. To do so, we will draw on ideas from pure functional programming and model the computing environment as a category of object types whose morphisms are the typed functions that the agent can execute.

Under a first, simplified approximation where the problem semantics are fully modeled by the type system, we can define rewards or goals as a partition function over the set of types. In this view, the objective of the agent is to compose a sequence of functions into a program that leads to a terminal type maximizing reward. Alternatively, given a set of initial objects, the task becomes finding a path through a typed category that reaches a reward partition. 
 

We will see that in this relatively simplistic setting, we can initially enumerate the complete state space of programs and navigate it using traditional algorithms such as A* or BFS. However, as we include more realistic compositional patterns, the state space explodes, pushing us back toward a reinforcement learning framework in the hope of discovering more efficient navigation policies. 

In the conclusion, we will further emphasize the fundamental role of the language modeling aspect of the agent by exploring the scenario where the given base types are not sufficient to model the goal condition. From a categorical perspective, this requires further refinements, or fibrations, of the base category of types, typically expressed as exhaustive predicates over typed records. From the classical search perspective, this represents not only a combinatorial explosion but also a significant increase in modeling cost, since the minimal set of predicates that fully recovers the maximally coarse fibration sufficient for successful navigation must be known in advance by the researcher designing the environment.

