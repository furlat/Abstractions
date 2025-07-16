
## Introduction

In advanced artificial intelligence (AI) systems, especially within the realm of game development and simulation, the intricacies of logical planning play a crucial role in shaping autonomous agent behavior. This detailed exploration focuses on forward and reverse (backward) logical planning methodologies as applied in object-based deterministic automata. The discussion primarily revolves around the intricacies of Goal-Oriented Action Planning (GOAP) systems, a cornerstone in modern AI design for games.

## The Structure of GOAP Systems

[[GOAP]] systems represent a sophisticated approach in AI planning, where the decision-making process is heavily reliant on the concept of affordances - the possible actions or interactions an entity can perform within its environment. In these deterministic systems, both actions (affordances) and their outcomes are not mere predictions but accurate representations derived directly from the simulation's ruleset, thus serving as the ground truth.

### Graph Construction in GOAP

The construction of a [[Graph]] in a GOAP system forms the backbone of its planning mechanism. Here's a more detailed look at its structure:
- **[[Nodes]]**: Each node in this graph represents a distinct state of the world, characterized by a set of statements. These statements are factual descriptions of various conditions or attributes in the game's environment at a given point in time.
- **[[Edges]]**: The edges between nodes symbolize affordances. These are the actions that can transition the game's state from one node to another. Importantly, the direction of each edge is indicative of the causality of actions.
- **[[Goal Node]]**: The graph's construction begins from the goal node. This node is uniquely defined by a set of statements that describe the end state or the desired outcome the AI aims to achieve.
- **Expansion Methodology**: Expanding backward from the goal node, the graph grows by examining each affordance's prerequisites. These prerequisites, or conditions necessary for an action to be feasible, determine the prior state necessary for each affordance to take place.

## Forward vs. Reverse Logical Planning

The dichotomy between forward and reverse planning in GOAP systems presents two fundamentally different approaches to achieving goals.

### Forward Planning

- **Concept**: Forward planning starts from the entity's current state and strategizes towards achieving the goal. It expands the state space step by step, exploring possible actions emanating from the initial state.
- **Relation to Algorithms**: This approach is akin to algorithms like A* and Dijkstra’s, where the focus is on calculating the shortest or most efficient path from the starting point. Additionally, it's similar to Monte Carlo Tree Search (MCTS) used in game AI, where future states are explored through probabilistic models.
- **Advantages**: Intuitive and straightforward, forward planning excels when the goal is clearly defined, and the paths from the current state to the goal can be efficiently estimated.
- **Limitations**: Its efficiency dwindles when goals are ambiguous or when the starting state leads to multiple potential goal states, causing the algorithm to explore many paths that may not be relevant.

### Reverse (Backward) Planning

- **Concept**: Reverse planning, in contrast, initiates from the goal state and traces the path backwards to the current state. It reverses the conventional search direction, posing the question, "What preceding state could lead to this outcome?" at each step.
- **Application in GOAP**: Within the GOAP framework, reverse planning involves starting from the goal and identifying actions (affordances) that could lead to that goal. Subsequently, it traces back to the actions that enable these affordances, continuing until a link to the current state is established.
- **Advantages**: This approach is highly effective when the end goal is well-defined but the starting point varies or is less defined. It can lead to a more focused and goal-oriented search, often resulting in a narrower graph topology that directly aligns with the ultimate objective.
- **Limitations**: Reverse planning might miss out on more creative or non-linear paths that a forward search could uncover. Additionally, it can become complicated if the goal is multifaceted, leading to various branching paths in the reverse direction.
```
class GOAPPlanner:
    initialize with affordances

    function is_goal_achieved(goal, entity):
        Evaluate if the entity's state fulfills the goal conditions using Statements

    function get_filtered_subgoals(goal, entity):
        Determine subgoals of the main goal already satisfied
        Return remaining subgoals using CompositeStatements

    function find_terminal_affordances(goal, entity):
        Identify affordances that hypothetically contribute to the goal
        Use `force_true` to assess potential consequences without actual application
        Categorize as terminal (full match) or partial (partial match) based on hypothetical impact
        Use CompositeStatements to evaluate alignment with goal subgoals

    function find_subgoals_for_affordance(affordance, entity):
        Identify subgoals to hypothetically make an affordance applicable
        Utilize prerequisites in Affordance for missing conditions

    function achieve_goal(goal, entity, depth):
        If goal is achieved, return
        If recursion depth is exceeded, return
        Evaluate terminal and partial affordances for the current state and goal
        For each terminal affordance:
            Hypothetically apply the affordance using `force_true`
            If goal would be achieved, simulate application and return success
        For each partial affordance:
            Hypothetically apply the affordance using `force_true`
            Recursively call achieve_goal for remaining subgoals
        If no affordance fully achieves the goal, consider combinations of partial affordances
        Return the sequence of hypothetical affordances applied

    function log(optional):
        Log steps and decisions for debugging and analysis

    function print_reasoning(optional):
        Print a detailed report of the planning proce
```
## Topological Considerations in Graph-Based Planning

The efficiency of forward or reverse planning is intrinsically linked to the topology of the graph in the GOAP system:
- **In Reverse Planning**: The graph is more streamlined and goal-focused, as it starts from the goal and considers only those affordances that directly contribute to it. This leads to a narrower topology, which is generally more efficient for specific, well-defined goals.
- **In Forward Planning**: The graph can potentially explore a broader range of affordances from the current state, resulting in a more branched and expansive topology. This approach is potentially more efficient in scenarios where the initial state offers multiple viable paths to different goals.
- **Complexity Factors**: The graph's complexity in either approach depends on several factors, including the number and nature of affordances, their interconnections, the graph's depth (number of steps from the goal to the current state or vice versa), and the branching factor (number of affordances available at each state).

## Conclusion

The strategic choice between forward and reverse logical planning in object-based deterministic automata hinges on the specificity of the goal, the nature of affordances, and the overall structure of the state space. Each approach has distinct merits and limitations, and the optimal method depends on the specific demands and constraints of the simulation environment. In the realm of AI planning, particularly in deterministic game environments, understanding these differences is key to developing sophisticated, responsive, and intelligent behaviors in autonomous agents.