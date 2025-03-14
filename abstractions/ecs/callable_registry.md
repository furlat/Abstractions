# New Features for the ECS + Callable Framework

We’re introducing **two new capabilities** to extend our ECS-based framework and callable registry:

1. **Entity References in Function Arguments**  
2. **Automatic Entity Tracing for All Callables**

Below is a description of each feature and a suggested plan of action.

---

## 1. Entity References in Function Arguments

### Overview

With this feature, users can supply **pointers** to specific fields on version-controlled `Entity` objects when calling any function in our `CallableRegistry`. Instead of always passing raw literals (`42`, `"Bob"`), we can write:

```json
{
  "student_age": "@f65cf3bd-9392-499f-8f57-dba701f5069c.age",
  "bonus_amount": 100.5
}
```

Any JSON field that **starts with `@`** is interpreted as a **reference**. The system will:
1. **Parse** out the UUID (e.g. `f65cf3bd-9392-499f-8f57-dba701f5069c`) and the attribute path (`age`).
2. **Fetch** the corresponding entity from `EntityRegistry`.
3. **Navigate** the attribute path on the entity (e.g. `entity.age`) to retrieve the value.
4. **Replace** the `@…` string with that literal value (e.g. `18`).
5. Finally, perform Pydantic validation on the fully “resolved” input (so if the function wants an `int`, but the entity’s field is a `str`, you’ll get a validation error).

### Rationale

- **Dynamic**: It’s easier to reference an entity’s data without manually passing the raw number.
- **Robust**: Pydantic validation still applies, so type mismatches are caught before execution.
- **Seamless**: Integrates cleanly into the existing `execute_callable` pipeline with minimal changes (just a pre-processing step).

### Proposed Implementation Steps

1. **Update `execute_callable`:**  
   - After retrieving the user’s `input_data`, run a helper function like `resolve_entity_references(data: Any) -> Any`.
   - Recursively scan for any string that starts with `@` and handle them via `_fetch_entity_attribute`.
   - Return a fully “resolved” dictionary, then proceed with Pydantic validation.

2. **Write `_fetch_entity_attribute`:**  
   - Strip the leading `@`.
   - Split off the UUID from the optional attribute path.
   - Retrieve the entity from `EntityRegistry`.
   - If there’s a path, do `getattr` or a small dot-path navigation to get the final field.
   - Return that field as the resolved value (which might be an integer, string, or another nested entity).

3. **Error Handling:**  
   - If an entity is not found, raise a `ValueError`.
   - If the attribute path is missing or invalid, raise a suitable error.
   - Let Pydantic handle final type mismatches.

---

## 2. Automatic Entity Tracing for All Callables

### Overview

Instead of requiring manual `@entity_tracer` decorators, every function registered in `CallableRegistry` is **automatically** wrapped to detect changes in any `Entity` passed into it. This means you no longer need to remember to decorate your functions—**all** of them will:

1. **Check** if their entity arguments have diverged from stored snapshots prior to execution.
2. **Fork** any changed entities as needed.
3. **Perform** the function logic.
4. **Check/fork** again after execution.
5. **Automatically** register newly created entities, if the function returns them.

### Rationale

- **Consistency**: No risk of forgetting to apply `@entity_tracer`.  
- **Convenience**: Every function is guaranteed to have automatic versioning for its entity parameters.
- **Simplicity**: We unify the “callable registration” and “entity tracing” flows.

### Proposed Implementation Steps

1. **Modify `CallableRegistry.register`**  
   - Before storing the function in `_registry`, wrap it with the `entity_tracer`.
   - Something like:
     ```python
     traced_func = entity_tracer(func)
     cls._registry[name] = traced_func
     ```
   - Optionally, check if the function is already traced (by inspecting a custom attribute) to avoid double-wrapping.

2. **Update or remove old references** to `@entity_tracer` if used manually.  
   - That’s optional. It won’t break anything, but it’s redundant.

3. **Maintain Existing Execution Flow**  
   - When we call `execute_callable`, it fetches the stored function, which is already traced. The tracer then does all the pre-/post-call checks/forks.

---

## Overall Plan of Action

1. **Integrate Reference Resolution**  
   1. Write a `_resolve_references` helper in `caregistry.py`.  
   2. Insert it into `execute_callable` and `aexecute_callable` before Pydantic validation.  
   3. Verify that fields like `@uuid.some_attribute` properly map to actual entity fields.

2. **Apply Automatic Entity Tracing**  
   1. Modify `CallableRegistry.register` to wrap the user’s function with `@entity_tracer`.  
   2. Confirm all existing tests and workflows pass when functions are now always traced.  
   3. (Optional) Remove or refactor places where we manually used `@entity_tracer` if we want a single approach going forward.

3. **Testing & Validation**  
   - Write or update test cases:
     - **References**: Provide inputs referencing an entity’s field; confirm correct resolution.  
     - **Tracing**: Confirm that if an entity is mutated in the function body, it forks automatically both before and after.  
     - **Combined**: Tests that pass `@uuid.age` to a function, function modifies that entity, etc.

4. **Documentation**  
   - Update README or docstrings to explain how to pass references (the `@…` syntax).  
   - Clarify that **all** callables in the registry are now “entity-traced” by default.

With these steps in place, the framework will smoothly allow referencing entity attributes **and** ensure version-control checks/forks on every registered callable, all under the same cohesive design.


# Addendum: Function Execution in Isolated Threads with Type-Constrained Returns

## Overview

To further enhance our callable framework and entity versioning system, we propose executing registered callables in isolated threads with type-constrained return values. This approach creates powerful guarantees around entity manipulation while maintaining developer flexibility.

## Core Mechanism

1. **Process Isolation**
   - Each callable executes in a forked process with its own copy of the EntityRegistry
   - The callable has complete freedom to manipulate entities within its process boundary
   - Side effects are naturally contained within the forked process
   - Using `.fork()` provides faster execution than threading

2. **Type-Constrained Returns**
   - Only entities that match the function's return type hints can cross the thread boundary
   - The system automatically validates return values against these type constraints
   - Non-conforming entities remain isolated in the forked thread and are garbage collected

3. **Versioning Semantics**
   - Root entities are passed as inputs to preserve proper versioning
   - Multi-input scenarios use a container entity to maintain a single DAG
   - The tracer focuses only on comparing DAG state before and after execution
   - Lineage is preserved for pure functions and intentionally broken for transformative ones

## Implementation Strategy

This approach uses process forking rather than threading for complete isolation and faster execution:

1. **Process Forking**
   ```python
   def execute_callable_forked(func_name: str, input_data: Dict[str, Any]) -> Any:
       """Execute a callable in a forked process with its own registry branch."""
       # Resolve any entity references in input_data
       resolved_input = resolve_entity_references(input_data)
       
       # Get the function from registry
       func = CallableRegistry.get(func_name)
       return_type = get_return_type_hint(func)
       
       # Fork the process
       pid = os.fork()
       
       if pid == 0:
           # Child process - execute function and exit
           try:
               # Execute function with resolved inputs
               result = func(**resolved_input)
               
               # Serialize result to be picked up by parent
               with open('/tmp/func_result.pickle', 'wb') as f:
                   pickle.dump(result, f)
               
               os._exit(0)  # Exit child process successfully
           except Exception as e:
               # Log error and exit with non-zero code
               with open('/tmp/func_error.pickle', 'wb') as f:
                   pickle.dump(e, f)
               os._exit(1)
       else:
           # Parent process - wait for child to complete
           _, status = os.waitpid(pid, 0)
           
           if status == 0:
               # Child succeeded, get result
               with open('/tmp/func_result.pickle', 'rb') as f:
                   result = pickle.load(f)
                   
               # Type checking and validation
               if not type_matches(result, return_type):
                   raise TypeError(f"Function {func_name} returned {type(result)}, expected {return_type}")
                   
               # If successful, merge relevant entities back to main registry
               if isinstance(result, Entity):
                   EntityRegistry.merge_entity(result)
                   
               return result
           else:
               # Child failed, get error
               with open('/tmp/func_error.pickle', 'rb') as f:
                   error = pickle.load(f)
               raise error
   ```

2. **Registry Branching**
   ```python
   @classmethod
   def create_branch(cls) -> 'EntityRegistry':
       """Create a branch of the registry for isolated execution."""
       branch = cls()
       
       # Copy the minimal necessary state
       # We don't need to copy all entities, just the ones that will be used
       # Most implementations would use copy-on-write semantics
       
       return branch
   ```

3. **Type Enforcement**
   ```python
   def type_matches(value: Any, type_hint: Type) -> bool:
       """Check if a value matches the expected type hint."""
       # Handle Union, Optional, etc.
       if hasattr(type_hint, "__origin__") and type_hint.__origin__ is Union:
           return any(type_matches(value, arg) for arg in type_hint.__args__)
           
       # Handle generic containers
       if hasattr(type_hint, "__origin__"):
           if not isinstance(value, type_hint.__origin__):
               return False
           # Check container item types...
           
       # Handle direct type check
       return isinstance(value, type_hint)
   ```

## Benefits

1. **Transactional Semantics**
   - Functions operate like database transactions - all or nothing
   - Changes only propagate if they match the expected return type
   - Protects the main entity registry from invalid states

2. **Developer Experience**
   - Developers can write pragmatic, mutable code within functions
   - No need to manually track entity versions during implementation
   - Clear, type-based contract for what functions can return

3. **Clean Versioning Model**
   - Entity versioning happens at well-defined boundaries
   - No need to track intermediate versions during function execution
   - Automatic detachment/reattachment based on function signature

4. **Performance Benefits**
   - Using OS-level forking provides faster execution than threading
   - Complete memory isolation prevents accidental sharing
   - Registry operations can be optimized for the specific function context
   - Parallel execution becomes more feasible with true process isolation

## Practical Example

```python
@CallableRegistry.register("transform_student")
def transform_student(student: Student) -> GraduateStudent:
    """Transform a Student entity into a GraduateStudent entity."""
    # Inside this function, we're free to:
    # 1. Create temporary entities
    # 2. Modify the student entity
    # 3. Create and manipulate other entities
    
    # Create a new graduate student from the input student
    grad_student = GraduateStudent(
        name=student.name,
        age=student.age,
        undergraduate_degree=student.major
    )
    
    # This will be returned and type-validated against GraduateStudent
    return grad_student
```

When called:
1. The function executes in a forked thread with its own registry branch
2. It's free to manipulate entities however needed internally
3. Only the returned `GraduateStudent` entity crosses the thread boundary
4. The entity is validated against the return type hint
5. If valid, it's merged into the main registry with proper versioning

## Conclusion

Executing callables in isolated threads with type-constrained returns provides a powerful balance between developer flexibility and system integrity. This approach maintains the elegant versioning model of our entity system while allowing pragmatic, readable function implementations. The thread boundary acts as a natural versioning boundary, simplifying both the implementation and the mental model for developers.