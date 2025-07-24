# Messages and Chat History Research

## Message History Overview

Pydantic AI supports continuing conversations across multiple agent runs by passing message history between runs.

## Basic Message History Pattern

### Continuing Conversations

```python
# First run
result1 = agent.run_sync('Tell me about Einstein')

# Second run, passing previous messages  
result2 = agent.run_sync(
    'What was his most famous equation?',
    message_history=result1.new_messages(),  # Pass history
)
print(result2.output)
#> Albert Einstein's most famous equation is (E = mc^2).
```

## Message Access Methods

### Result Message Methods

Both `RunResult` and `StreamedRunResult` provide message access:

```python
# Get new messages from this run
new_messages = result.new_messages()

# Use in subsequent runs
next_result = agent.run_sync(
    'Follow up question',
    message_history=new_messages
)
```

## Message Types and Events

```python
from pydantic_ai.messages import (
    FinalResultEvent,
    FunctionToolCallEvent,
    ModelMessagesTypeAdapter,  # For message serialization
)
```

## Conversation vs Run Concepts

### Runs vs Conversations

- **Run**: A single interaction that can contain multiple message exchanges
- **Conversation**: Can span multiple runs, maintaining state between separate API calls

> An agent **run** might represent an entire conversation — there's no limit to how many messages can be exchanged in a single run. However, a **conversation** might also be composed of multiple runs, especially if you need to maintain state between separate interactions or API calls.

## Context Window Management

```python
# Context window handling options:
# - `disabled` (default): Request fails with 400 error if exceeding context window
# - `auto`: Model truncates response by dropping middle conversation items
```

## Message Serialization

```python
from pydantic_ai.messages import ModelMessagesTypeAdapter

agent = Agent('openai:gpt-4o', system_prompt='Be a helpful assistant.')

# ModelMessagesTypeAdapter enables message serialization/deserialization
# for persistent conversation storage
```

## Streaming and Messages

```python
from pydantic_ai import Agent
from pydantic_ai.messages import (
    FinalResultEvent,
    FunctionToolCallEvent,
    # Other message event types...
)

# Streaming runs also support message access
async with agent.run_stream('Query') as stream:
    # Access messages during streaming
    pass
```

## Key Findings for Integration

1. **Message Continuity**: `result.new_messages()` enables conversation continuation
2. **Cross-Run State**: Message history maintains context across separate agent runs  
3. **Flexible Architecture**: Runs can be single interactions or full conversations
4. **Context Management**: Automatic truncation options for long conversations
5. **Message Events**: Rich event system for different message types
6. **Serialization Support**: `ModelMessagesTypeAdapter` for persistent storage
7. **Streaming Compatible**: Message history works with both sync and streaming runs

For our registry integration:
- Use message history to maintain context across multiple registry operations
- Enable multi-step entity manipulation workflows
- Support conversational debugging of entity states
- Persist conversation state for complex data analysis sessions