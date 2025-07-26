# Formatter Hardcoding Analysis

## 🚨 **Current Hardcoded Issues**

Our formatter is still **hardcoded to the test setup**, not truly generic:

### **1. Hardcoded Event Types**
```python
# ❌ HARDCODED to our test events
if (hist_event.type == "agent.tool_call.start" and
    isinstance(hist_event, AgentToolCallStartEvent) and  # ❌ Specific to test
```

### **2. Hardcoded Event Structure**
```python
# ❌ HARDCODED field expectations
function_name = getattr(start_event, 'function_name', 'unknown')  # ❌ Assumes this field
raw_parameters = getattr(start_event, 'raw_parameters', {})       # ❌ Assumes this field
```

### **3. Hardcoded Event Classes**
```python
# ❌ HARDCODED to our custom event classes
class AgentToolCallStartEvent(ProcessingEvent):     # ❌ Test-specific
class AgentToolCallCompletedEvent(ProcessedEvent): # ❌ Test-specific
```

### **4. Hardcoded Parameter Structure**
```python
# ❌ HARDCODED assumption about parameter format
if isinstance(param_value, str) and param_value.startswith('@'):  # ❌ Assumes string addresses
```

## 🎯 **What "Generic" Should Mean**

A truly generic formatter should work with:
- **Any function execution events** (not just our custom ones)
- **Any parameter format** (not just string addresses)
- **Any event structure** (not assuming specific field names)
- **Any execution pattern** (not just our 9 test patterns)

## 🔧 **Current State Assessment**

### **✅ What IS Generic**
- Entity type extraction from ExecutionResult
- Address resolution through EntityRegistry
- Value resolution through ECSAddressParser

### **❌ What IS Hardcoded**
- Event type matching: `"agent.tool_call.start"`
- Event class checking: `AgentToolCallStartEvent`
- Field name assumptions: `function_name`, `raw_parameters`
- Parameter format assumptions: `@uuid.field` strings
- Event bus usage pattern: Specific to our test setup

## 🏗️ **True Generic Architecture Needed**

### **Option 1: Generic Event-Based Formatter**
Create a formatter that works with **any event structure**:
```python
class GenericExecutionFormatter:
    def format_execution(self, start_event: Event, completion_event: Event) -> str:
        # Extract data generically without assuming field names
        # Use reflection/introspection to find relevant fields
        # Handle any parameter format, not just string addresses
```

### **Option 2: ExecutionResult-Only Formatter**
Create a formatter that works purely from **ExecutionResult data**:
```python
class ExecutionResultFormatter:
    def format_execution(self, result: ExecutionResult, **context) -> str:
        # Work purely from ExecutionResult data
        # No dependency on specific event types or structures
        # Truly generic to any function execution
```

### **Option 3: Registry-Based Formatter**
Create a formatter that uses **CallableRegistry introspection**:
```python
class RegistryExecutionFormatter:
    def format_execution(self, function_name: str, params: Dict, result: Any) -> str:
        # Use CallableRegistry to understand function signature
        # Use EntityRegistry to resolve entity types
        # No dependency on specific event structures
```

## 🚀 **Recommendation**

We should implement **Option 2: ExecutionResult-Only Formatter** because:
1. **Truly Generic**: Works with any ExecutionResult regardless of how it was created
2. **Event Agnostic**: Doesn't depend on specific event types or structures  
3. **Reusable**: Can be used outside of our test environment
4. **Simple**: Clear separation of concerns

The formatter should be extractable and usable in any context where you have:
- Function name
- ExecutionResult
- Access to EntityRegistry (for type resolution)

This would be truly generic and not hardcoded to our test setup.