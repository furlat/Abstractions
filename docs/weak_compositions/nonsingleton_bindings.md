# Abstractions Extension: Polymorphic Binding and Hypothesis Navigation in Functional Compositions

This document extends the core Abstractions framework by addressing the binding problem in functional compositions, particularly when dealing with union types, subsets, and ambiguous mappings. Drawing inspiration from parallel operators like `par` (parallel composition) and `map` (transformation over collections), we generalize these to handle non-singleton intersections. Traditional systems require exact type matches or singleton intersections for composition, treating unions atomically and negating weak or partial bindings. Here, we model compositions as navigable hypothesis spaces, enabling under-represented (partial coverage leading to selection) and over-represented (ambiguous many-to-many leading to enumeration or optimization) scenarios.

The extension builds on Abstractions' entity-native model, functional registry, and distributed execution, introducing weak connectors for polymorphic routing. It reduces complex binding to inspired operators: starting from `map/par` as convolutions over types, extending to exhaustive weak mappings for under-representation, polymorphic parallel routing for over-representation, and finally recasting as goal-directed optimization over hypothesis spaces.

## The Binding Problem in Functional Data Processing

In Abstractions, functions are registered with type signatures, and compositions rely on matching outputs to inputs. Traditional binding requires a singleton intersection: \( O_f \cap I_g = \{T\} \) (exact match on type \( T \)). Unions complicate this—e.g., \( f: Entity \to Union[A, B, C] \) has \( O_f = \{A, B, C\} \), and composing with \( g: A \to X \) yields non-singleton or empty intersections, blocking direct binding.

This "binding problem" manifests in two forms:
- **Under-representation**: Partial coverage where not all output types have handlers (e.g., \( |O_f \cap I_g| < |O_f| \)), leading to uncertainty and potential errors.
- **Over-representation**: Ambiguous overlaps where multiple functions can handle the same output (e.g., multiple \( g, h \) for type A), creating many-to-many possibilities.

Inspired by `map` (sequential transformation over collections) and `par` (parallel execution), we treat binding as a convolution: convolving output sets with input sets to generate branched paths. This allows compositions without singleton constraints, modeling uncertainty as degrees of freedom (|O_f| as potential branches).

## Extending Map/Par with Concrete Type Polymorphic Map (Exhaustive Weak Connectors)

We begin by extending `map/par` to a "concrete type polymorphic map" concept. In functional programming, `map` applies a function to each element of a collection, implicitly handling polymorphism via type classes or subtypes. Here, we generalize to unions: treat \( Union[A, B, C] \) as a virtual collection, and `map` as polymorphic dispatching over concrete types.

This introduces **exhaustive weak connectors**: bindings where intersections are non-singleton but exhaustive (covering all outputs via subsets or subtypes). Under-representation (partial intersections) leads to **selection**: fewer branches than the full degrees of freedom (|O_f|), with uncovered types muted or errored.

### Theoretical Foundation: Set-Theoretic Binding as Convolution

Define binding as a relation \( \beta(f, g) \subseteq O_f \times I_g \), where pairs (o, i) exist if o ≼ i (subtype/subset match). Composition is a convolution: for each o, convolve with matching i's, generating paths.

- For under-representation: If \( |\beta| < |O_f| \), select the covered subset (weak binding), muting others. Degrees of freedom reduce from |O_f| to |β|.
- Exhaustive if no mutes; otherwise, selection prunes.

Example in Abstractions:
```python
from abstractions.ecs.callable_registry import CallableRegistry
from typing import Union

class A(Entity): pass
class B(Entity): pass
class C(Entity): pass

@CallableRegistry.register("produce_union")
def produce_union(input: Entity) -> Union[A, B, C]:
    # Runtime logic determines concrete type
    return A()  # Example

@CallableRegistry.register("handle_a")
def handle_a(a: A) -> str:
    return "Handled A"

# Weak polymorphic map: Bind only to matching, select under-represented
# Hypothetical extension: execute_weak with exhaustive=False for selection
result = CallableRegistry.execute_weak("produce_union", input=some_entity,
    branches={"handle_a": A}  # Under-represented: only A covered
)
# If output is A, selects handle_a; else mutes (fewer branches than 3)
```

This models under-representation as selective branching: weak connectors probe concrete types (isinstance), exhausting covered paths but reducing to actual matches.

## Handling Over-Representation: Extending Par to Polymorphic Routing

Over-representation occurs when intersections are over-full: multiple inputs match an output (|β| > |O_f|), or many-to-many (unions of lists). Traditional `par` models parallelism but assumes deterministic dispatch. We extend to **polymorphic routing**: `par` over polymorphic bindings, routing outputs to all valid functions, defaulting to combinatorial enumeration.

For unions of lists (e.g., List[Union[A,B]]), this is extensive many-to-many: convolve each union element with multiple handlers. Default: Enumerate all combinations in β, forking parallel executions.

- Under many-to-many, model as par extension: Fork branches for each (o, i), producing multi-outputs (siblings in Abstractions).
- Bounding: If combinatorial explosion, use uncertainty measures (μ) for greedy selection, but default to full enum.

Example:
```python
@CallableRegistry.register("produce_list_union")
def produce_list_union() -> List[Union[A, B]]:
    return [A(), B()]

@CallableRegistry.register("handle_a_or_b")
def handle_a_or_b(input: Union[A, B]) -> str:
    return "Handled"

@CallableRegistry.register("handle_b_specific")
def handle_b_specific(b: B) -> str:
    return "Handled B specifically"

# Over-represented: Multiple handlers for B (ambiguous)
# Extend par: Enumerate combinatorial (A -> handle_a_or_b; B -> [handle_a_or_b, handle_b_specific])
results = CallableRegistry.execute_par("produce_list_union",
    branches=[("handle_a_or_b", Union[A, B]), ("handle_b_specific", B)]
)
# Forks: 3 branches total (many-to-many routing)
```

This extends par to polymorphic: route via concrete types, enumerating over-represented paths as parallel convolutions.

## Recasting Over-Representation as Composition Hypothesis Space

Over-represented bindings model a **hypothesis space**: the full β as a graph of possible compositions, where each path is a hypothesis (e.g., "if output is B, try handle_b_specific"). Enumeration explores the space exhaustively, but over-representation (large |β|) turns it into a search problem.

- Hypothesis space: Nodes are types/functions; edges are bindings with μ (utility/probability).
- Under-representation prunes space (selection); over selects all viable hypotheses.

## Goal-Directed Choice: Casting to RL/Search/Non-Convex Optimization

To navigate large hypothesis spaces, recast choice as maximizing a loss function: select paths maximizing utility (e.g., accuracy, speed from provenance). This reduces to:
- **RL**: Policies as Q-values over edges; navigate greedily (argmax Q).
- **Search**: Greedy/beam search bounding enumeration.
- **Non-Convex Optimization**: Maximize ∑μ over subsets, subject to bounds (non-convex due to dependencies).

In Abstractions, integrate as navigated execution: Policies bound enum, learning from lineage (rewards = successful outputs).

Example:
```python
# Hypothesis navigation with RL policy
policy = learn_policy_from_provenance()  # Maximize loss (e.g., -reward)
results = CallableRegistry.execute_navigated("produce_union",
    branches={...}, navigator=policy  # Greedy max over hypothesis space
)
```

This unifies: Start with polymorphic map/par for binding, enumerate hypotheses, optimize navigation.

## Implementation in Abstractions

Extend CallableRegistry with `execute_weak`, `execute_par`, `execute_navigated`. Preserves immutability, provenance tracks hypotheses.

## Why This Scales

Reduces binding rigidity, enables adaptive distributed pipelines via hypothesis optimization.