# Output Handling Research

## Output Type Declaration

Agents specify their expected output type at creation:

### Basic Output Types

```python
# Boolean output
roulette_agent = Agent(
    'openai:gpt-4o',
    deps_type=int,
    output_type=bool,  # Agent produces boolean
    system_prompt='...'
)

# String output  
weather_agent = Agent(
    'openai:gpt-4o',
    output_type=str,  # Agent produces string
    system_prompt='...'
)
```

### Special Output Types

```python
# Never output type (for infinite retry scenarios)
class NeverOutputType(TypedDict):
    """Never ever coerce data to this type."""
    pass

agent = Agent(
    'anthropic:claude-3-5-sonnet-latest',
    retries=3,
    output_type=NeverOutputType,  # Special case
    system_prompt='...'
)
```

## Output Validation

### Output Validator Functions

```python
@agent.output_validator
async def validate_output(ctx: RunContext[MyDeps], output: str) -> str:
    response = await ctx.deps.http_client.post(
        'https://example.com#validate',
        headers={'Authorization': f'Bearer {ctx.deps.api_key}'},
        params={'query': output},
    )
    response.raise_for_status()
    return output  # Return validated output

@agent.output_validator
async def output_validator_deps(ctx: RunContext[str], data: str) -> str:
    if ctx.deps in data:
        raise ModelRetry('wrong response')  # Trigger retry
    return data
```

## Output Access

### Result Structure

```python
# Run agent and access output
result = roulette_agent.run_sync('Put my money on square eighteen', deps=success_number)
print(result.output)  # Access the typed output
#> True

result = roulette_agent.run_sync('I bet five is the winner', deps=success_number)  
print(result.output)
#> False
```

## Structured Output

The documentation mentions **structured output validation** which suggests support for complex types beyond primitives.

### Error Handling and Retries

```python
# Validation errors trigger model retries
# Both function tool parameter validation and structured output validation
# can be passed back to the model with a request to retry

# ModelRetry can be raised from tools or output validators
raise ModelRetry('wrong response')  # Forces model to retry
```

## Output Type Generics

```python
# Agents are generic over output type
Agent[DependencyType, OutputType]

# Example with specific types
roulette_agent: Agent[int, bool] = Agent(
    'openai:gpt-4o',
    deps_type=int,
    output_type=bool,
)
```

## Key Findings for Integration

1. **Type Safety**: Output types are declared at agent creation and enforced
2. **Validation**: `@agent.output_validator` decorators for custom validation
3. **Retry Logic**: `ModelRetry` exception triggers automatic retries
4. **Access Pattern**: `result.output` provides typed access to output
5. **Structured Output**: Support for complex output types beyond primitives
6. **Generic Types**: Agents are parameterized by both dependency and output types
7. **Error Propagation**: Validation errors can be fed back to the model for correction

For our registry integration, we can use:
- `str` output type for most tool responses
- Custom Pydantic models for structured data
- Output validators for entity validation
- `ModelRetry` for error handling