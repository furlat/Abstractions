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
