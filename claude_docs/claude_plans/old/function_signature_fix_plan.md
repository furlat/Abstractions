# Function Signature Fix Plan

## 🎯 **Problem**
The formatter is showing wrong function signatures like:
- `🚀 analyze_performance(student: str) -> Assessment` 
- `🚀 split_student_record(student: str) -> Entity`

When it should show the **actual function signatures**:
- `🚀 analyze_performance(student: Student) -> Tuple[Assessment, Recommendation]`
- `🚀 split_student_record(student: Student) -> Tuple[Student, AcademicRecord]`

## 🏗️ **Root Cause**
I'm trying to reverse-engineer the signature from string addresses, which is stupid. The **actual function signature** is available in CallableRegistry when the event is created.

## ✅ **Clean Solution**

### 1. **Add `function_signature` to AgentToolCallStartEvent**
```python
class AgentToolCallStartEvent(ProcessingEvent):
    """Event emitted when agent tool call begins."""
    type: str = "agent.tool_call.start"
    phase: EventPhase = EventPhase.STARTED
    
    # Agent-specific data
    function_name: str = Field(description="Function being called")
    function_signature: str = Field(default="", description="Actual function signature")  # ✅ NEW
    raw_parameters: Dict[str, Any] = Field(default_factory=dict, description="Raw tool parameters")
    pattern_classification: Optional[str] = Field(default=None, description="Input pattern type")
    parameter_count: int = Field(default=0, description="Number of parameters")
```

### 2. **Extract signature in event creation factory**
```python
creating_factory=lambda function_name, **kwargs: AgentToolCallStartEvent(
    process_name="execute_function",
    function_name=function_name,
    function_signature=CallableRegistry.get_function_signature(function_name),  # ✅ NEW
    raw_parameters=kwargs,
    parameter_count=len(kwargs)
),
```

### 3. **Use signature directly in formatter**
```python
# Function signature - use REAL signature from event
function_signature = getattr(start_event, 'function_signature', '')
if function_signature:
    lines.append(f"🚀 {function_signature}")
else:
    # Fallback
    lines.append(f"🚀 {function_name}(...) -> {entity_type}")
```

## 🎉 **Benefits**
1. **Accurate signatures**: Shows exactly what's defined in the code
2. **No reverse engineering**: Uses the actual signature, not guesswork
3. **Clean architecture**: Capture information when available, not reconstruct later
4. **Reliable**: Won't break with complex type hints or tuples

This is the right way - **capture the signature when we have access to it** (during event creation), not try to rebuild it later from parameters.