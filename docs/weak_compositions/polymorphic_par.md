### Polymorphic Parallel Operator for Branched Compositions
In the process of designing a domain-specific language for the Abstractions framework, we turn our attention to mechanisms that allow functions returning values of a parent type to compose smoothly with transformations specific to subtypes. This polymorphic selector provides a way to examine the runtime instance, determine its concrete subtype through inheritance, and route it to the corresponding path. The approach establishes a connection between parent types and their subtypes on one hand, and union types as explicit disjunctions on the other. Drawing from classical ideas in type theory, such as Hoare's formalizations where a parent type includes its subtypes as refinements, we see the subtype relationship as a particular instance of a set relation—the parent acts as a superset encompassing its specializations. Similarly, a union type constructs a disjunctive set from its components, where any one might be the runtime realization. This duality means that both can be resolved using the same selector logic: whether the return is declared as a parent like Entity or as Union[Student, Teacher], the runtime check verifies if the concrete value fits a handler's input via subtype matching.

To make this concrete, suppose we have a function that processes a raw entity and returns a parent type, but produces subtypes at runtime. The selector inspects this and directs the flow:

```python
@CallableRegistry.register("process_raw")
def process_raw(raw: Entity) -> Entity:  # Parent return
    if "gpa" in raw.fields:
        return Student(name=raw.name, gpa=raw.gpa)
    else:
        return Teacher(name=raw.name, courses=raw.courses)
```

With handlers for subtypes:

```python
@CallableRegistry.register("handle_student")
def handle_student(student: Student) -> str:
    return f"Processed student with GPA {student.gpa}"

@CallableRegistry.register("handle_teacher")
def handle_teacher(teacher: Teacher) -> str:
    return f"Processed teacher with courses {teacher.courses}"
```

The selector could be a function that checks the type and prepares the next step:

```python
@CallableRegistry.register("type_selector")
def type_selector(result: Entity) -> ExecutionSpec:
    if isinstance(result, Student):
        return ExecutionSpec(function="handle_student", args={"student": result})
    elif isinstance(result, Teacher):
        return ExecutionSpec(function="handle_teacher", args={"teacher": result})
```

Execution chains them:

```python
raw = Entity(name="Alice", gpa=3.8)
processed = CallableRegistry.execute("process_raw", raw=raw)
spec = CallableRegistry.execute("type_selector", result=processed)
output = CallableRegistry.execute(spec.function, **spec.args)
```

This resolves the parent return to the subtype path. For an explicit union declaration—Union[Student, Teacher]—the selector works identically, highlighting the duality: the union lists possibilities explicitly, while the parent implies them through inheritance, but both rely on runtime subtype checks for routing.

As hierarchies nest, however, this selector reveals limitations. Introduce a deeper structure, such as ClassRepresentative inheriting from Student, which inherits from Person, all under Entity. A concrete ClassRepresentative would pass isinstance checks for ClassRepresentative, Student, Person, and Entity. If we have handlers for multiple levels:

```python
@CallableRegistry.register("handle_class_rep")
def handle_class_rep(rep: ClassRepresentative) -> str:
    return f"Handled representative role: {rep.role}"

@CallableRegistry.register("handle_student_general")
def handle_student_general(student: Student) -> str:
    return f"Handled general student: GPA {student.gpa}"
```

The selector must decide which to invoke. Prioritizing the most fine-grained (ClassRepresentative) might miss useful general processing, while including both requires explicit logic to avoid arbitrary order in checks. This choice disrupts the selector's simplicity, as it forces assumptions about hierarchy or preferences, complicating what should be a straightforward type-based dispatch.

The way forward with fewest assumptions is to execute all matching paths, defining a polymorphic parallel operator that activates handlers for every level the instance fits. For the ClassRepresentative, this runs the specific role handler and the general student one concurrently, without choosing. In cases with a broad Entity handler, it joins the parallels, producing multiple outputs linked in provenance.

To understand why this parallelism fits, consider that alternatives like ordered resolution demand knowing the hierarchy or adding configurations, which we may not have or want to implement. Parallel execution requires none—it lets the type matches drive the branches naturally, and if only one matches, it behaves as single-path. This makes the polymorphic par a building block for compositions, where forking is the default for overlaps.

The polymorphic par operator emerges as a way to apply handlers in parallel where subtype matches occur, effectively a simplified parallel composition with pattern matching based on the type hierarchy. It processes the output by checking against declared handlers, executing all that fit the concrete type, and collecting the results. The operator's behavior is driven by the event system in the framework, where events are emitted for the output, and handlers respond to those events by triggering executions.

To see this in action, let's first consider how the framework's event system enables it. When a function completes, it emits a CreatedEvent carrying the output's type and ID. @on decorators then listen for specific types, fetching the entity and executing the next step. For hierarchical outputs, multiple @on decorators match because of inheritance, leading to parallel firing as the event system dispatches asynchronously to all listeners:

```python
@on(Student)
async def student_path(event: CreatedEvent[Student]):
    # The event carries the subject_type and subject_id; since the concrete type is ClassRepresentative, it matches Student via inheritance
    student = get(f"@{event.subject_id}")
    # Execute the general handler for Student
    await CallableRegistry.aexecute("handle_student_general", student=student)
    # This path runs, producing its output

@on(ClassRepresentative)
async def rep_path(event: CreatedEvent[ClassRepresentative]):
    rep = get(f"@{event.subject_id}")
    # Execute the specific handler for ClassRepresentative
    await CallableRegistry.aexecute("handle_class_rep", rep=rep)
    # This path also runs, in parallel with the Student one
```

The emission happens after the initial function:

```python
classified = CallableRegistry.execute("process_hierarchical", raw=raw)
# The framework could auto-emit, or we do it manually for clarity
emit(CreatedEvent(subject_type=type(classified), subject_id=classified.ecs_id))
# The event broadcasts, and both handlers activate for a ClassRepresentative output, running concurrently due to the async nature of the event dispatch
# Provenance records the fork: "Event matched 2 handlers due to subtype overlap; executed in parallel"
```

This parallel firing is automatic—the event system doesn't prevent multiple matches; it embraces them, allowing the hierarchy to drive the number of branches. If the output was a plain Student without further specialization, only the Student handler would fire, reducing to a single path. The connection here is that the operator leverages the event system's broadcast to achieve parallelism without additional orchestration; the @on decorators act as the pattern matchers, and the subtype checks are implicit in how the event matching works with type inheritance.

To declare this in the DSL, we use a syntax that lists the handlers with their expected types, which under the hood generates the @on handlers:

```python
composition = "process_hierarchical" ∘par (
    "handle_student_general": Student |
    "handle_class_rep": ClassRepresentative
)
# This DSL compiles to the @on definitions shown above, registering them dynamically for this composition
# At runtime, the par operator ensures the emission and collects outputs from the fired paths
results = CallableRegistry.execute_par(composition, raw=some_raw)
```

The generated handlers are scoped to the composition's context, perhaps by adding a unique step ID to the event:

```python
emit(CreatedEvent(subject_type=type(classified), subject_id=classified.ecs_id, composition_id=composition.id))
# Handlers include predicate=lambda e: e.composition_id == current_id
```

This prevents cross-composition interference. The outputs form a tuple of results from non-muted paths, with provenance noting any forks, such as "Forked to 2 branches for single input due to hierarchy match."

The operator's static signature is Tuple[OutputType1, OutputType2, ...], where each position corresponds to a declared branch's output if not muted. For over-representation—multiple branches for one input—the tuple nests sub-tuples, e.g., Tuple[Tuple[GeneralOutput, SpecificOutput]] if two handlers match. This signature captures branching as multiplicity in the return type, propagating uncertainty or parallelism downstream—callers expect a container holding all completed paths, which they can unpack or process further.

```
Static Signature for par with 2 branches:
Input -> process_hierarchical -> Entity (hierarchical)
     -> par -> Tuple[GeneralStr, SpecificStr]  # If fork, Tuple[Tuple[Str, Str]]

+---------------+     +---------------------+     +---------------------+
| process_hier  |     | par Operator        |     | Output Tuple        |
| returns Entity| --> | Emit event          | --> | (general_result,    |
+---------------+     | Match @on subtypes  |     |  specific_result)   |
                      | Fire parallel if    |     | If no fork: (result)|
                      | multiple match      |     +---------------------+
                      +---------------------+
```

This models the return as a container of non-muted results, connecting the parallel execution to a structured output that reflects the branches taken.

To build on this, consider tuples of types as explicit outputs—fixed collections of mixed entities, where the par operator processes each position independently, connecting to the idea that tuples provide a natural structure for parallel branches:

```python
@CallableRegistry.register("multi_output")
def multi_output(input: Entity) -> Tuple[Student, Teacher]:
    # Produce mixed subtypes
    return Student(name="Alice", gpa=3.8), Teacher(name="Bob", courses=["Math"])
```

The DSL declares the par with handlers for each expected type:

```python
composition = "multi_output" ∘par (
    "handle_student": Student |
    "handle_teacher": Teacher
)
# Generates @on for Student and Teacher
```

To handle the tuple, the execution emits separate events for each element:

```python
student, teacher = multi_output(input)
emit(CreatedEvent(subject_type=type(student), subject_id=student.ecs_id))
emit(CreatedEvent(subject_type=type(teacher), subject_id=teacher.ecs_id))
# The generated @on handlers fire in parallel: student_path for first, teacher_path for second
# Outputs collected as Tuple[str, str], with provenance "Parallel branches for tuple positions 0 and 1"
```

If a hierarchy overlap occurs on one element—say the first is ClassRepresentative—the event for that position matches multiple @on, forking for that slot, and the output tuple becomes Tuple[Tuple[general_str, specific_str], teacher_str], nesting to capture the multiplicity. The connection is that the tuple's positions define the base structure for branches, while the par operator adds forks within positions if inheritance allows, ensuring the return signature reflects both the fixed multiplicity and any additional parallelism.

```
Tuple Flow with par:
Tuple[Student, Teacher] -> Emit per element -> Match @on -> Execute parallel

+---------------+     +---------------------+     +---------------------+
| multi_output  |     | Emit events per pos |     | Tuple Outputs:      |
| returns tuple | --> | Pos0: Student event | --> | Pos0: student_res   |
+---------------+     | Pos1: Teacher event |     | Pos1: teacher_res   |
                      | Match & fire par    |     | If fork on Pos0:    |
                      +---------------------+     |   (gen_res, spec_res)|
                                                  +---------------------+
```

For optionals in tuples—Tuple[Optional[Student], Optional[Teacher]]—the par propagates uncertainty by muting branches for None or unmatched subtypes. The function might produce partial results:

```python
@CallableRegistry.register("optional_multi")
def optional_multi(input: Entity) -> Tuple[Optional[Student], Optional[Teacher]]:
    student = Student(...) if "gpa" in input.fields else None
    teacher = Teacher(...) if "courses" in input.fields else None
    return student, teacher
```

The DSL remains the same, but generated handlers include checks for None:

```python
@on(Student)
async def student_path(event: CreatedEvent[Student]):
    if event.subject_id is None:
        return None  # Mute the branch, no execution
    student = get(f"@{event.subject_id}")
    return await CallableRegistry.aexecute("handle_student", student=student)

# Similar for Teacher
```

Emission handles None by emitting with subject_id=None or skipping, but to propagate:

```python
student, teacher = optional_multi(input)
if student is not None:
    emit(CreatedEvent(subject_type=type(student), subject_id=student.ecs_id))
else:
    emit(CreatedEvent(subject_type=Student, subject_id=None))  # Signal optional mute
# Handlers detect None and return None
```

The static signature is Tuple[Optional[str], Optional[str]], with outputs like (student_result, None) if second muted. Guaranteed branches (always non-None) remain non-optional in the signature, while uncertain ones introduce optionality. This monadic-like propagation connects to the idea that the par operator treats absences as silenced paths, keeping the tuple structure but allowing sparsity, which models uncertainty without halting the flow.

```
Optional Tuple Flow:
Tuple[Opt[Student], Opt[Teacher]] -> Emit (with None signal) -> Match & mute if None

+---------------+     +---------------------+     +---------------------+
| optional_multi|     | Emit per pos,       |     | Tuple Outputs:      |
| returns opt   | --> | signal None if abs  | --> | (student_res, None) |
| tuple         |     | Match @on, mute None|     | If both: (res1, res2)|
+---------------+     +---------------------+     | If none: (None, None)|
                                                  +---------------------+
```

This setup now enables analyzing union returns by reframing Union[Student, Teacher] as Tuple[Optional[Student], Optional[Teacher]], applying par virtually. Statically, the operator enumerates branches as if parallel over optionals: one for potential Student, one for Teacher, with matches to handlers. The hypothesis space is this virtual tuple's paths, where each optional represents a possible activation.

At runtime, the concrete output—say Student—activates the Student branch, mutes the Teacher one by treating it as None, collapsing to a single path. The return signature becomes Tuple[Optional[str], Optional[str]], but in practice, the non-muted result is in the first position, None in the second, which callers can unpack knowing the sparsity.

```python
# DSL for union as virtual optional tuple
composition = "classify_union" ∘par (
    "handle_student": Optional[Student] |
    "handle_teacher": Optional[Teacher]
)
# Static enumeration: virtual pos0 for Student, pos1 for Teacher
# Runtime: concrete Student -> execute pos0, mute pos1 with None
```

Diagram:

```
Union as Virtual Opt Tuple: Union[S, T] -> Tuple[Opt[S], Opt[T]]

+---------------+     +---------------------+     +---------------------+
| classify_union|     | Virtual par:        |     | Collapsed Output:   |
| returns Union | --> | Pos0: Opt[S] match  | --> | (student_res, None) |
+---------------+     | Pos1: Opt[T] match  |     | Or (None, teach_res)|
                      | Runtime concrete S: |     | Single path via mute|
                      |   activate pos0     |     +---------------------+
                      |   mute pos1         |
                      +---------------------+
```

Single execution emerges as a particular instance within this broader model, where the muting of non-matching branches prunes the virtual structure down to a solitary path. This connects directly back to the original intent of the polymorphic selector—to resolve ambiguity through type-based routing—but now generalized under the umbrella of the par operator. In the simpler selector approach, we aimed for a single, determined continuation based on the concrete subtype; with par, that outcome becomes one possible realization of a multipath setup, achieved when the runtime value activates only one branch in the virtual optional tuple, silencing the rest. The framework doesn't need to distinguish this case specially; it follows from the same enumeration and muting logic, ensuring that what appears as a linear flow is merely the sparse result of a parallel enumeration that collapses efficiently.

To see how this works in practice, recall the reframing of a union return like Union[Student, Teacher] as Tuple[Optional[Student], Optional[Teacher]]. The par operator treats this virtually as two parallel branches: one attempting to match and process the Student optional, the other the Teacher. Statically, the DSL declaration:

```python
composition = "classify_union" ∘par (
    "handle_student": Optional[Student] |
    "handle_teacher": Optional[Teacher]
)
```

generates @on handlers that account for the optionality, such as:

```python
@on(Student)
async def student_branch(event: CreatedEvent[Student]):
    if event.subject_id is None:  # Representing the optional None
        return None  # Mute this virtual position
    student = get(f"@{event.subject_id}")
    return await CallableRegistry.aexecute("handle_student", student=student)

# Similar for Teacher branch
```

At runtime, the concrete output—suppose a Student instance—leads to an event emission that matches only the Student branch, with the Teacher branch receiving a virtual None signal (or simply not firing if the event type doesn't match), resulting in muting. The output tuple becomes (student_result, None), which can be unpacked or pattern-matched downstream to ignore the muted slot, effectively yielding the single result. This pruning happens without explicit intervention; the optional structure models the disjunctive uncertainty inherent in the union—the "or" between Student and Teacher translates to parallel optionals, where runtime sparsity resolves to one active path and one silenced.

The connection to the selector's original goal is that this generalization preserves the type-driven resolution while accommodating more complex scenarios. The selector was a sequential dispatcher; par extends it to a parallel one where muting enforces sequential-like behavior when appropriate. This sparsity is "lucky" in the sense that unions often resolve to exactly one subtype, making the virtual tuple's branches mutually exclusive in practice, even though statically they are enumerated as independent. The framework benefits from this by allowing static validation to explore the full hypothesis space—the set of all possible branch activations—while runtime execution remains lightweight, only pursuing the non-muted paths.

```
Virtual Optional Tuple for Union[S, T]: Tuple[Opt[S], Opt[T]]

Static Enumeration:
+---------------+     +---------------------+     +---------------------+
| classify_union|     | par over virtual    |     | Hypothesis Space:   |
| returns Union | --> | tuple positions:    | --> | Pos0: Opt[S] -> h_s |
+---------------+     | Pos0 for Opt[S]     |     | Pos1: Opt[T] -> h_t |
                      | Pos1 for Opt[T]     |     | All branches listed  |
                      | Enumerate matches   |     | for validation      |
                      +---------------------+     +---------------------+

Runtime with concrete S:
Emit event for S -> Match Pos0 (activate h_s), Pos1 gets virtual None (mute)
Output: (result_s, None)  # Collapses to single effective path
```

The optional tuple thus serves as a model for disjunctive uncertainty: each position represents a potential realization of the union, with the par operator enumerating them statically to build the hypothesis space—a graph of all conceivable executions based on which optionals might activate. At runtime, the concrete value determines the sparsity pattern, resolving the space by muting non-applicable positions and producing a tuple that captures only the active results. This resolution is deterministic and tied to the subtype, ensuring no arbitrary choices; the framework's event system handles the dispatch, and provenance logs the muting, such as "Virtual position 1 muted due to type mismatch; only position 0 executed."

Expanding on this, the par operator's handling of sparsity connects to how it manages cases where the hypothesis space has more potential branches than the runtime needs. In under-represented scenarios, where a union component has no matching handler, the corresponding optional position mutes statically as well as at runtime, flagging potential gaps during analysis without runtime cost. The tuple signature reflects this uncertainty upfront—Tuple[Optional[Output1], Optional[Output2]]—guiding callers to handle possibles, while guaranteed matches (if a branch always activates) remain non-optional, tightening the type.

In over-represented cases, where multiple matches occur per virtual position—such as a hierarchy fork on Student, with handlers for both Student and a supertype like Person—the pruning of the hypothesis space can incorporate goal-conditioned learning to select or limit branches. Here, the space grows with the overlaps: for a single position in the virtual tuple, multiple handlers might activate, leading to nested tuples in the output, like Tuple[Tuple[student_result, person_result], None]. To manage this expansion, we can model an LLM agent tasked with navigating the space toward a goal defined as reaching a target subtype of Entity. The agent operates within the finite hierarchical type system deriving from Entity and draws from the registry's finite set of typed functions as tools.

The enumeration of the space starts from the starting type (the input to the composition) and the goal type, generating chains of function applications that transform step by step, with each step a potential fork if multiple functions match the current type. The LLM acts as an adaptive selector at each juncture, choosing which function to call and with which input (perhaps addressing entities via strings), evaluating based on how the choice advances toward the target subtype. For example, if the goal is a Report subtype, and the current state is a Student entity, the LLM might select a grading function that outputs Report, pruning alternatives like scheduling that lead elsewhere.

Over iterations, outcomes from executions—success in reaching the goal, efficiency in steps, or accuracy in results—feed back to refine the agent's choices, pruning inefficient paths by favoring those with higher learned utility. This extends the par's multipath nature into a learnable framework: the hypothesis space, initially enumerated fully for analysis, becomes navigable, with the LLM's decisions acting as a dynamic reducer that collapses branches based on goals. In the framework, this could integrate with provenance to log traversals, allowing the agent to learn from past chains, ultimately optimizing compositions for specific objectives like minimizing latency while achieving the desired output type.

```
Over-Represented Hypothesis Space with Pruning:

Static Space for Union[S, T] with multiple handlers per:
Tuple[Opt[S], Opt[T]] -> par -> Nested Tuple possibilities
  Pos0 Opt[S]: fork to h_student and h_person if overlap
  Pos1 Opt[T]: single h_teacher

+---------------+     +---------------------+     +---------------------+
| Union return  |     | par Enumeration     |     | Pruned by LLM:      |
| reframed opt  | --> | Pos0: fork if over  | --> | Choose h_student    |
| tuple         |     | Pos1: single        |     | over h_person if    |
+---------------+     | Full space generated|     | goal favors detail  |
                      +---------------------+     | Runtime: sparse res |
                                                  +---------------------+
```

This goal-conditioned pruning transforms the static enumeration into a dynamic process, where the par operator's branches are not just executed but selected adaptively, refining the hypothesis space over time to focus on paths that efficiently reach the target subtype. The connection back to the initial selector is that learning elevates the type-based routing to a purposeful navigation, where the framework's event system and async execution support the parallelism, but the agent's choices ensure sparsity aligns with intentions.