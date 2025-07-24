### The Many-to-Many Challenge

Traditional composition expects one-to-one type matching:
```
f: A → B
g: B → C
compose: f ∘ g  // Works because output of f matches input of g
```

Union returns create a many-to-many problem:
```
f: A → Union[B₁, B₂, B₃]
g₁: B₁ → C₁
g₂: B₂ → C₂
g₃: B₃ → C₃

// How to compose f with g₁, g₂, and g₃?
```

Weak composition with discrimination nodes solves this by creating conditional routing based on the actual runtime type.# Polymorphic Discriminator Pattern for Sparse Runtime Type Checking

## Overview

This document describes a pattern for handling functions that return union types in functional data processing systems. The pattern introduces two key concepts:

1. **Weak composition** - A composition rule that allows connecting functions returning union types to functions expecting specific types from that union
2. **Discrimination nodes** - Runtime elements that resolve which concrete type was actually returned

Together, these concepts enable type-safe processing while minimizing runtime overhead.

## Terminology Note

- **Weak composition**: A composition rule (design-time concept)
- **Weak connector**: The runtime implementation of weak composition  
- **Discrimination node**: The specific point where type checking occurs
- **Many-to-many**: One function returning a union connecting to many type-specific functions

## Core Problem

The challenge arises when functions return union types:

```
analyze_entity: Entity → Union[Student, Teacher, Course]
```

This creates uncertainty - we don't know which specific type we have. Traditional solutions either:
- Require all downstream functions to accept the full union (inflexible)
- Force immediate type checking everywhere (expensive)
- Use complex inheritance hierarchies (rigid)

The discriminator pattern allows functions returning unions to compose with functions expecting specific types, using discrimination nodes only where needed.

## Basic Concepts

### The Union Return Problem

When functions return union types, they create type uncertainty:

```
// This function returns one of three possible types
classify_entity: Entity → Union[Student, Teacher, Course]

// But downstream functions expect specific types
process_student: Student → StudentReport
process_teacher: Teacher → TeacherReport
process_course: Course → CourseReport
```

The type system prevents direct composition because the output type doesn't match any single input type.

### Weak Composition (Composition Rule)

A weak composition is a rule that allows connecting:
- A function returning `Union[A, B, C]` 
- To functions expecting specific types `A`, `B`, or `C`

```
f: X → Union[Student, Teacher, Course]
g: Student → StudentReport

// Weak composition allows: f ∘ g
// The composition is "weak" because it's partial
// It only defines behavior when f returns Student
```

### Discrimination Nodes (Runtime Resolution)

When executing a weak composition, discrimination nodes resolve which type was actually returned:

```
discrimination_node(value: Union[A, B, C]) → (ConcreteType, ExecutionPath)
```

The discrimination node:
1. Inspects the actual runtime value
2. Determines its concrete type
3. Routes to the appropriate type-specific function

### Many-to-Many Pattern

The general case handles many-to-many mappings:

```
// Function returns union
f: Entity → Union[Student, Teacher, Course]

// Multiple possible downstream functions
g1: Student → StudentReport
g2: Teacher → TeacherReport  
g3: Course → CourseReport

// Discrimination node creates branches for all possibilities
Entity → f → Union[S,T,C] → discrimination → ├─ S → g1 → StudentReport
                                              ├─ T → g2 → TeacherReport
                                              └─ C → g3 → CourseReport
```

### The Many-to-Many Challenge

Traditional composition expects one-to-one type matching:
```
f: A → B
g: B → C
compose: f ∘ g  // Works because output of f matches input of g
```

Union returns create a many-to-many problem:
```
f: A → Union[B₁, B₂, B₃]
g₁: B₁ → C₁
g₂: B₂ → C₂
g₃: B₃ → C₃

// How to compose f with g₁, g₂, and g₃?
```

Weak composition with discrimination nodes solves this by creating conditional routing based on the actual runtime type.

### Discriminator Functions

A discriminator function inspects a value of union type and returns an execution specification:

```
discriminator: Union[A, B, C] → (ConcreteType, ExecutionSpec)

where ExecutionSpec contains:
  - function_name: string
  - args: map of arguments
  - expected_output_type: Type
```

### Execution Specifications

Instead of immediately executing code, discriminators return data describing what should be executed for each resolved type. This separation allows:
- Type validation before execution  
- Composition of execution paths
- Complete provenance tracking

The execution happens after type resolution, ensuring type safety.

## Simple Example: Handling Union Returns

Consider a function that returns different types based on runtime analysis:

```
@register("analyze_data")
function analyze_data(raw_data: Data) → Union[Student, Teacher, Course]:
    // Runtime analysis determines the actual type
    // But return type is a union
```

To compose this with type-specific processors:

```
@register("analyze_discriminator")
function analyze_discriminator(result: Union[Student, Teacher, Course]) → ExecutionSpec:
    // Inspect the actual value returned
    if result is Student:
        return ExecutionSpec(
            function: "process_student",
            args: {student: result, include_gpa: true}
        )
    elif result is Teacher:
        return ExecutionSpec(
            function: "process_teacher",
            args: {teacher: result, include_courses: true}
        )
    elif result is Course:
        return ExecutionSpec(
            function: "process_course",
            args: {course: result, include_enrollment: true}
        )
```

The composition would be:
```
raw_data → analyze_data → Union[S,T,C] → analyze_discriminator → type-specific processing
```

The discriminator node resolves which type was actually returned and routes to the appropriate processor.

## Weak Connectors: Handling Many-to-Many Compositions

A weak connector implements the runtime mechanism for weak compositions. When a function returns a union type, the connector handles routing to type-specific functions:

```
connector: Union[A, B, C] → routing based on actual type
```

The connector handles the many-to-many case: one function returning a union needs to connect to many possible type-specific functions.

### Basic Weak Connector

A weak connector examines the actual type of a union value and routes accordingly:

```
@register("weak_connector")
function weak_connector(
    input: Union[A, B, C],
    type_filter: Type,
    on_match: string,     // Function to call if type matches
    on_mismatch: string   // "pass_through" or "mute" or function name
) → Any:
    if input matches type_filter:
        return execute(on_match, input)
    else:
        if on_mismatch == "pass_through":
            return input  // Continue with original value
        elif on_mismatch == "mute":
            return null   // Filter out this path
        else:
            return execute(on_mismatch, input)
```

### Composition Example

```
// Function returns union type
result: Union[Student, Teacher, Course] = analyze_data(raw_data)

// First connector - handles Students only
result1 = weak_connector(
    input: result,
    type_filter: Student,
    on_match: "enrich_student_data",    // Applied only if Student
    on_mismatch: "pass_through"         // Others continue unchanged
)

// Second connector - handles Teachers only  
result2 = weak_connector(
    input: result1,
    type_filter: Teacher,
    on_match: "enrich_teacher_data",    // Applied only if Teacher
    on_mismatch: "pass_through"         // Others continue unchanged
)
```

Each connector handles one possible type from the union, creating a many-to-many routing pattern.

## Multi-Stage Branching

When functions return unions at multiple stages, discrimination nodes throughout the graph resolve type uncertainty:

```
raw_data → classify() → Union[Student, Teacher, Course]
              |
              ├─[if Student]→ analyze_student() → Union[HighPerformer, Regular]
              │                    |
              │                    ├─[if HighPerformer]→ honors_report()
              │                    └─[if Regular]→ standard_report()
              │
              ├─[if Teacher]→ analyze_teacher() → Union[Tenured, Adjunct]
              │                    |
              │                    ├─[if Tenured]→ full_evaluation()
              │                    └─[if Adjunct]→ basic_evaluation()
              │
              └─[if Course]→ analyze_course() → CourseReport
```

Each function that returns a union creates new branches. Discrimination nodes resolve the uncertainty at each branching point.

### Multi-Stage Example

```
@register("progressive_analysis")
function progressive_analysis(data: Data) → Report:
    // Stage 1: Initial classification returns union
    classified: Union[Student, Teacher, Course] = classify(data)
    
    // Stage 2: Type-specific analysis (may return unions)
    stage2_result = discriminate_and_analyze(classified)
    // where discriminate_and_analyze routes to:
    // - analyze_student: Student → Union[HighPerformer, Regular]
    // - analyze_teacher: Teacher → Union[Tenured, Adjunct]  
    // - analyze_course: Course → CourseReport
    
    // Stage 3: Further discrimination if needed
    final_result = discriminate_and_format(stage2_result)
    
    return final_result
```

Each stage that returns a union requires discrimination to route to appropriate downstream functions.

## Type Flow Analysis

The discriminator pattern allows static analysis of all possible type flows through a composition:

```
function analyze_type_flow(composition: string) → TypeFlowGraph:
    union_returns = find_union_returning_functions(composition)
    discrimination_points = find_discrimination_nodes(composition)
    
    type_paths = {}
    for each union_return in union_returns:
        for each possible_type in union_return.types:
            path = trace_path_from_type(possible_type, discrimination_points)
            type_paths[possible_type] = path
    
    return TypeFlowGraph(paths: type_paths)
```

For any composition, we can determine:
- Where functions return union types
- All possible execution paths from each union
- Which discrimination nodes handle which unions

Since all functions in the registry are typed, type safety is guaranteed by construction - compositions with incompatible types cannot be created.

## Practical Benefits

### 1. Minimal Runtime Checking
Type checks occur only at discrimination nodes - specifically when handling values of union type. Once a discrimination node resolves the actual type and routes to a type-specific function, no further runtime type checking is needed until another function returns a union type.

### 2. Composability
Functions returning union types can be composed with functions expecting specific types. Weak connectors implement the many-to-many routing, connecting each possible output type to its appropriate processor.

### 3. Static Analysis
Despite union returns creating runtime uncertainty, all possible paths can be analyzed statically:

```
// Analyze what happens when classify returns each possible type
paths = analyze_composition("@{classify(data)} → @{discriminate} → @{process}")
// Returns: [
//   classify→Student → discriminate → process_student → StudentReport,
//   classify→Teacher → discriminate → process_teacher → TeacherReport,
//   classify→Course → discriminate → process_course → CourseReport
// ]
```

The framework can verify that handlers exist for all possible types in each union return.

### 4. Clear Execution Flow
The branching structure makes the computation flow explicit and traceable.

## Advanced Patterns

### Filtering with Mute

Weak connectors can filter out specific types from a union return:

```
// Function returns Union[Student, Teacher, Course]
result = classify_entity(data)

// Remove Courses from the flow
filtered = weak_connector(
    input: result,
    type_filter: Course,
    on_match: "mute",           // Remove Courses from downstream processing
    on_mismatch: "pass_through" // Students and Teachers continue
)
// Downstream only needs to handle Students and Teachers
```

### Nested Compositions

Discriminators can return composition strings that handle nested union returns:

```
@register("nested_discriminator")
function nested_discriminator(result: Union[Student, Teacher, Course]) → ExecutionSpec:
    if result is Student:
        return ExecutionSpec(
            function: "compose",
            args: {
                // fetch_grades might return Union[Grades, NoGrades]
                pipeline: "@{fetch_grades} → @{discriminate_grades} → @{calculate_gpa}"
            }
        )
    // Other cases...
```

This creates nested discrimination - the outer discriminator handles the Student/Teacher/Course union, while inner discriminators handle any unions returned by the nested functions.

## Summary

The polymorphic discriminator pattern addresses the challenge of composing functions that return union types with functions that expect specific types. 

The pattern provides:
- **Weak composition rules** that allow connecting union-returning functions to type-specific functions
- **Discrimination nodes** that resolve actual types at runtime and route execution accordingly
- **Minimal runtime overhead** by checking types only at discrimination points

The pattern is particularly useful when:
- Functions must return different types based on runtime analysis
- Type-specific downstream processing is required
- Multiple stages of processing may each introduce type uncertainty
- Static analysis of all possible execution paths is valuable

Through weak connectors and discrimination nodes, the pattern enables building type-safe processing pipelines that handle the many-to-many nature of union type composition.

## Related Pattern: Conditional Branching Within Types

While the main discriminator pattern handles functions returning union types (many-to-many), a related pattern handles conditional logic within a single type:

```
@register("performance_analyzer")
function performance_analyzer(student: Student) → Union[HighPerformer, Regular, Probation]:
    // Returns different subtypes based on attributes
    if student.gpa > 3.5 and student.credits > 60:
        return HighPerformer(student_data)
    elif student.gpa > 2.0:
        return Regular(student_data)
    else:
        return Probation(student_data)
```

This creates union returns based on data analysis rather than type discovery. The same discrimination node approach handles the routing:

```
student → performance_analyzer → Union[H,R,P] → discriminate → ├─ H → honors_track
                                                                ├─ R → regular_track
                                                                └─ P → probation_track
```

This shows how the pattern extends beyond simple type checking to data-driven branching.