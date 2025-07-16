# Pydantic `create_model`: A Deep Dive

This document provides a comprehensive guide to the `create_model` function in Pydantic, a powerful tool for dynamically generating Pydantic models at runtime. We will explore its use cases, parameters, advanced features, performance considerations, and delve into its source code to understand its inner workings.

## 1. Introduction: What is `create_model`?

The `create_model` function is a utility provided by Pydantic to dynamically create new Pydantic `BaseModel` classes. This is particularly useful in scenarios where the structure of a data model is not known at development time but is determined at runtime.

Common situations where `create_model` is invaluable include:

*   **Adapting to External Data:** When consuming data from external APIs or databases with schemas that may change, `create_model` allows you to build models that match the incoming data structure on the fly.
*   **User-Defined Schemas:** In applications where users can define their own data structures, `create_model` can be used to generate the corresponding Pydantic models for validation and data handling.
*   **Flexible API Endpoints:** For frameworks like FastAPI, you can use `create_model` to create dynamic request or response models, making your API endpoints more adaptable.
*   **Interfacing with LLMs:** When working with Large Language Models (LLMs), you can use `create_model` to enforce a specific, dynamically-defined output structure.

## 2. Basic Usage

The fundamental usage of `create_model` involves providing a model name and field definitions as keyword arguments.

```python
from pydantic import BaseModel, create_model

# Dynamically create a model
DynamicFoobarModel = create_model(
    'DynamicFoobarModel',
    foo=(str, ...),  # Required field of type str
    bar=(int, 123)   # Optional field of type int with a default value
)

# The above is equivalent to this static definition:
class StaticFoobarModel(BaseModel):
    foo: str
    bar: int = 123

# Instantiate the dynamic model
instance = DynamicFoobarModel(foo='hello')
print(instance)
# > foo='hello' bar=123
```

Field definitions can be provided in two ways:
1.  A tuple of `(type, default_value)`. For required fields, use `...` (Ellipsis) as the default value.
2.  Just a default value (the type will be inferred).

## 3. Parameters of `create_model`

The `create_model` function has the following signature:

```python
def create_model(
    model_name: str,
    *,
    __config__: ConfigDict | None = None,
    __base__: type[BaseModel] | tuple[type[BaseModel], ...] | None = None,
    __module__: str = __name__,
    __validators__: dict[str, classmethod] | None = None,
    __cls_kwargs__: dict[str, Any] | None = None,
    **field_definitions: Any,
) -> type[BaseModel]:
```

-   `model_name`: The name for the new model class.
-   `**field_definitions`: The fields of the model, provided as keyword arguments.
-   `__config__`: A `ConfigDict` (or a regular dictionary) to set the [model configuration](https://docs.pydantic.dev/latest/concepts/config/).
-   `__base__`: A single base class or a tuple of base classes from which the new model should inherit. This allows you to extend existing models.
-   `__module__`: The name of the module where the model is created. It defaults to the caller's module.
-   `__validators__`: A dictionary to add [functional validators](https://docs.pydantic.dev/latest/concepts/validators/#functional-validators) to the model.
-   `__cls_kwargs__`: A dictionary of keyword arguments to be passed to the metaclass during class creation (e.g., `metaclass=...`).

## 4. Advanced Usage

### 4.1. Dynamic Validators and Computed Fields

You can add `validators` and `computed_fields` dynamically.

```python
from pydantic import (
    create_model,
    field_validator,
    computed_field,
    ValidationError,
)
from typing import Any

# Define a validator function
@field_validator("name")
def validate_name_length(cls, v: str) -> str:
    """Ensures the name has at least 3 characters."""
    if len(v) < 3:
        raise ValueError("Name must be at least 3 characters long")
    return v.capitalize()

# Define a function for a computed field
@computed_field
@property
def info(self) -> str:
    """Computes a string from other fields."""
    return f"{self.name} is {self.age} years old."

# Create the dynamic model
DynamicModel = create_model(
    "DynamicModel",
    name=(str, ...),
    age=(int, ...),
    __validators__={"name_validator": validate_name_length},
    __computed_fields__={"info": info},
)

# Instantiate and use the model
try:
    instance = DynamicModel(name="alice", age=30)
    print(instance.model_dump())
    # > {'name': 'Alice', 'age': 30, 'info': 'Alice is 30 years old.'}
except ValidationError as e:
    print(e)
```

### 4.2. Custom Configuration with `__config__`

Model behavior can be customized using the `__config__` argument, which accepts a `ConfigDict`.

```python
from pydantic import create_model, ConfigDict, ValidationError

DynamicModelWithConfig = create_model(
    'DynamicModelWithConfig',
    field1=(str, ...),
    __config__=ConfigDict(extra='forbid') # Forbid extra fields
)

# This will raise a validation error
try:
    DynamicModelWithConfig(field1='value1', extra_field='value2')
except ValidationError as e:
    print(e)
```

### 4.3. Inheriting from a Base Model with `__base__`

You can extend existing models using the `__base__` argument.

```python
from pydantic import BaseModel, create_model

class BaseUser(BaseModel):
    id: int

AdminUser = create_model(
    'AdminUser',
    username=(str, ...),
    permissions=(list[str], []),
    __base__=BaseUser
)

admin = AdminUser(id=1, username='superadmin')
print(admin)
# > id=1 username='superadmin' permissions=[]
```

### 4.4. Achieving Generic-like Behavior

While you cannot create a truly generic model with `create_model`, you can use a factory function to generate concrete models for different types, achieving a similar result.

```python
from typing import List, Type, TypeVar
from pydantic import BaseModel, create_model

T = TypeVar('T')

def create_paged_response_model(item_type: Type[T]) -> Type[BaseModel]:
    """
    A factory that dynamically creates a Pydantic model for a
    paginated response containing a specific item type.
    """
    model_name = f"PagedResponse[{item_type.__name__}]"
    return create_model(
        model_name,
        page=(int, ...),
        size=(int, ...),
        total=(int, ...),
        items=(List[item_type], ...),
    )

class User(BaseModel):
    id: int
    name: str

# Generate a specific paged response model for the User type
UserPagedResponse = create_paged_response_model(User)

# Use the generated model
users_data = {
    "page": 1, "size": 1, "total": 1,
    "items": [{"id": 1, "name": "Alice"}]
}
user_page = UserPagedResponse.model_validate(users_data)
print(user_page.model_dump_json(indent=2))
```

## 5. Performance Considerations

-   **Creation Overhead:** The initial call to `create_model` for a unique set of parameters has a performance cost. Pydantic needs to build the model's schema, validators, and serializers. This can be noticeable for very complex models.
-   **Caching:** Pydantic internally caches the classes created by `create_model`. If you call it with the exact same arguments multiple times, subsequent calls are extremely fast as they retrieve the cached model.
-   **`create_model` vs. `BaseModel`:** For static models, defining a class that inherits from `BaseModel` is more performant as the model is constructed when the module is imported. `create_model` is for when the model structure is truly dynamic.
-   **`model_construct`:** If you have data that you already trust and want to bypass validation for performance, `model_construct()` can be significantly faster than a standard model instantiation (`MyModel(...)`).

## 6. Limitations and Pitfalls

-   **Complex Validators:** Passing arguments to dynamically applied validators can be complex, often requiring workarounds like `functools.partial`.
-   **Cyclic Relationships:** Models that reference each other (cyclic relationships) are a general challenge in Pydantic and this extends to dynamically created models.
-   **Naming Collisions:** Be careful not to have field names that collide with type names (e.g., a field named `int` of type `Optional[int]`).
-   **`__init_subclass__` Conflicts:** The mechanism `create_model` uses can sometimes clash with `__init_subclass__`, as keyword arguments might be interpreted as fields instead of being passed to `__init_subclass__`.
-   **Type Inference:** While Pydantic can infer types from default values, it is best practice to be explicit with type annotations to avoid ambiguity.

## 7. Source Code Explained

The `create_model` function is located in the `pydantic/main.py` file. Here is a simplified breakdown of its operation:

```python
# Simplified for explanation
def create_model(
    model_name: str,
    *,
    __config__: ConfigDict | None = None,
    __base__: type[BaseModel] | None = None,
    # ... other args
    **field_definitions: Any,
) -> type[BaseModel]:

    # 1. Handle the base class
    if __base__ is None:
        __base__ = (BaseModel,)
    # ...

    # 2. Process field definitions
    fields = {}
    annotations = {}
    for f_name, f_def in field_definitions.items():
        if isinstance(f_def, tuple):
            annotations[f_name] = f_def[0]
            fields[f_name] = f_def[1]
        else:
            annotations[f_name] = f_def

    # 3. Build the class namespace
    namespace = {
        '__annotations__': annotations,
        '__module__': # ... determines caller's module
    }
    namespace.update(fields)
    if __config__:
        namespace['model_config'] = __config__
    # ... add validators, etc.

    # 4. Create the class using the metaclass
    # This is conceptually similar to:
    # return type(model_name, __base__, namespace)
    # but uses Pydantic's metaclass for full functionality.
    resolved_bases = types.resolve_bases(__base__)
    meta = resolved_bases[0].__class__ # Get the metaclass
    
    return meta(model_name, resolved_bases, namespace)
```

**Step-by-step breakdown:**

1.  **Base Class Handling:** It ensures `__base__` is a tuple, defaulting to `(BaseModel,)`.
2.  **Field and Annotation Processing:** It iterates through keyword arguments, separating them into type `annotations` and `fields` with default values.
3.  **Namespace Creation:** It constructs a `namespace` dictionary, which acts as the body of the new class, populating it with annotations, fields, the config, and validators.
4.  **Class Creation:** It uses Python's underlying machinery (`type` or a metaclass) to dynamically create a new class with the specified name, base classes, and namespace. Pydantic's `ModelMetaclass` intercepts this creation to build the core schema, serializers, and validation logic.