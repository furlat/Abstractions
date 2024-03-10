My objective is creating a fully deterministic object oriented discrete space discrete time simulation engine that is natively able to generate goal oriented plans for any implemented entity. The engine must be simultaneously powerful enough to create engaging video-games and and have enough mathematical rigour such that multiple theoretical presentations are always avaiable. 
## Multi-representations
The formal representations we want to achieve are:
* Discrete Finite State Automation
* 2D grid with LOS and MOVE information for spatial planning
* Logical STRIPS like representation
* WorldStates graph with action labelled edges
* Multi-Agent Markov Decision Process
* Partially Observable Markov Decision Process
* Autoregressive Stochastic Process

Each representation allows us to derive different classes of optimal algorithm and either take an objective deterministc view of the system, similar to that of an idealized scientist, or the subjective view of an entity acting as a embedded observer with intrinsic perceptual, computational and efferential bottlenecks.

The most stringent requirement on the engine design is imposed by the logical STRIPS like representation which is based on inherently discrete truth tables. InfiniPL manages continuous variable via discretization, and currently the only use of this approach is in the implementation of 2d spatial reasoning over a closed set of (x,y) tuples. 

### Spatial Primitives


Our framweork implements under the hood the following systems and automatially prepares their output for logical reasoning:
* pathfinding
* raycasting
* L1,L2 and manhattan distance

The combination of the pathfinding, raycasting and distance primitives over spatial tuples and their automatic discretization space to entity propagation allows to derive a logical representation for each source entity of:
* `What is their position`
* `Are they lightened?`
* `What entities do they see`
* `What entities can they path too`
* `What entities are above or below a particular distance thresold.`


As well as how changes in the source position would update each of the above logical statements for all entities in the system. This can lead to statements like 
* `What entities would the source see along a path?`
* `Which entities would see the source moving along a path?`

This sort of consequential derivations is not limited to movement updates but to any other action modifying a state variable that interacts with the spatial system namely `position`, `blocks_los`, `blocks_move`,`stored_in` and `can_move`.

## Entities
The core of the simulation is given by a set of entites, each with a dictionary of state-variables, or attributes, that fully summarize them. We strictly employ boolean atributes to facilitate planning except for a few more complicated state variables that are connected to ad-hoc subsystem. 

The core state variables that define a InfinipyPL entity are:
* `Name`
* `Id`
* `Position`
* `Stored_in`
* `Light_Source`
* `Lightened`
* `Vision_range`
* `Movement_speed`
* `Light_Range`
* `Blocks_Move`
* `Blocks_Los`
* `Can_Move`
* `Can_See`
* `Can_Store`
* `Can_Stored`
* `Can_Act`

This resitricted list of variables allows the simulation of exstensive grid-based environments with multiple light sources, where entities have constrained perceptual and navigation abilities controlled by the pathfinding, raycasting and distance primitives and can "own each other" through an inventory system which binds to the spatial primitives by connecting stored items to their owner position as well ass connecting with the planning engine by allowing sources to use the entities they own.

### Atomic Statements, Composite Statements and Propositions

`AtomicStatements` are logical representation associated to entities attribute. They are composed by a tuple `(attribute,truth_value)` and are used to associate am attribute to a specific truth value. Continuous and structured attributes are converted to a set of bools to enable a statement representation by the underlying primitves. 

`CompositeStatement` are hash maps or dictionaries of statements `{attribute: truth_value}` and are used to define conditions across multiple attributes that must be `ALL` valid simultaneously.

`Propositions` ground statements to entities and they are composed by dictionary `{entity,CompositeStatement}`.

## Turn-based Causality
Causality is implemented in a sequential manner, where state updates are always locally induced by the action of `source` entity over a `target` entity, potentially itself. 

### Actions and Affordances

The way in which entities can interact is defined by the concept of `Affordance` which specifies the attirubtes that `source` and the `target` must posses, the subset of atomic truth values required to apply the affordance, and the subset of atomic truth values causally induced by the application of the affordance. Beyond the attribute check the `Affordance` is summarized by the prequistes and consequences both of the form `{source: CompositeStatement, target: CompositeStatement}` .

An `Action` binds an `Affordance` to a specific `source` and `target` which have the necessary attributes by constructing a prerequsite and consequence `Proposition`. 
If an affordance modifies any attribute associated to the spatial or inventory system of either `source` or `target` the spatial causal consequencesa are propagated to any other involved entity and the action consequence `Proposition` is enriched with the spatially propagated consequences. E.g. the application of the open affordance to a closed door, currently blocking movement and vision, will accumulate the causal consequence of being able to path  to or see new entities due to the door not blocking the way anymore. 
An `Action` is fully characterized by the precondition and consequence `Proposition` which include both the `Affordance` propositions and the spatial and inventory consequences computed by the dedicated systems.


### Temporal Options or Actions Sequences
A `Option` is an ordered collection of feasible `Action` objects. It is characterized by the prerequisite and consequence `Proposition` which respectively state the atomic statements sub-configuration required for the action sequence to start and the sub-configuration that will true at the end of the sequence.

The temporal consistency of the actions is ensured using either a forward or backward logical propagation algorithm allowing actions to be inserted ad the beginning or end of the sequence. 

The `forward algorithm ` only allows to append actions whose prerequsite is not violated by the current option consequence, and accordingly update the option prerequisite with the action prerequisite not already satifisfeid by the option consequence and the global consequences by right merging the current consequence and new consequences.  

The `backward algorithm` instead only allows actions whose prerequisites and consequences are not in conflict with the option prerequisite. The option consequences are updated by left merging with the pre-appended consequences. The option prerequsiste are updated with those of the new action and by removing those satisfied by the new consequences.

### Goal Oriented Action Planning
In this framework we can specify both the state of the world and desired objectives with a `Proposition` object.  `Goap` is achieved with a search process over options that starts from the current proposition and lead to a world where the goal propostion is satisfied. This can be achieved either by deriving a `Proposition` of the current world state and either set it as starting consequence and append new actions until the option consequence contains the goal proposition, or set the current world state to the goal proposition and 
pre-append actions until the option prerequisite are validated by the current proposition.
