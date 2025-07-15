# README Example Mapping

This document maps the working examples in this directory to sections in the main README.md file.

## Current Examples → README Sections

### ✅ **Fully Implemented & Tested Examples**

| Example File | README Section | Line Range | Status | Notes |
|-------------|----------------|------------|--------|-------|
| `01_basic_entity_transformation.py` | "First steps" | 19-40 | ✅ MATCHES | Core minimal pattern |
| `01_basic_entity_transformation_async.py` | "Async and concurrent execution" | 262-292 | ✅ MATCHES | Async version of basic pattern |
| `02_distributed_addressing.py` | "String-based distributed addressing" | 51-60, 127-149 | ✅ MATCHES | Entity addressing with `@uuid.field` |
| `02_distributed_addressing_async.py` | "Distributed execution patterns" | 232-255 | ✅ MATCHES | Async distributed addressing |
| `03_multi_entity_transformations.py` | "Multi-entity transformations" | 204-224 | ✅ MATCHES | Tuple unpacking and sibling relationships |
| `03_multi_entity_transformations_async.py` | "Async and concurrent execution" | 262-292 | ✅ MATCHES | Async tuple unpacking |
| `04_distributed_grade_processing.py` | "Real-world example: Grade processing" | 424-509 | ✅ MATCHES | Complex distributed workflow |
| `05_async_workflow_orchestration.py` | "Multi-step async processing workflows" | 299-355 | ✅ MATCHES | Async workflow coordination |

### ❌ **Missing Examples (README shows code but no working example)**

| Missing Example | README Section | Line Range | Priority | Description |
|----------------|----------------|------------|----------|-------------|
| `05_reactive_cascades.py` | "Multi-step reactive cascades" | 295-362 | 🔴 HIGH | Event-driven reactive pattern with `@on` decorators |
| `06_entity_versioning_lineage.py` | "Automatic provenance and lineage tracking" | 154-178 | 🟡 MEDIUM | Entity lineage and versioning examples |
| `07_event_driven_observation.py` | "Event-driven observation" | 181-197 | 🟡 MEDIUM | Event bus and observation patterns |
| `08_complex_addressing_patterns.py` | "String-based distributed addressing" | 127-149 | 🟠 LOW | Advanced addressing scenarios |
| `09_performance_optimization.py` | Various performance claims | Multiple | 🟠 LOW | Performance patterns and optimization |
| `10_error_handling_patterns.py` | Error handling claims | Multiple | 🟠 LOW | Graceful degradation examples |

### 🔄 **Partially Implemented (needs enhancement)**

| Example File | README Section | Issue | Fix Needed |
|-------------|----------------|-------|------------|
| `04_distributed_grade_processing.py` | "Real-world example: Grade processing" | Missing event handler example | Add `@on` decorator example for grade reports |

## README Sections Analysis

### **Well-Covered Sections** ✅
- ✅ Basic entity transformation (lines 19-40)
- ✅ Distributed addressing (lines 51-60, 127-149)
- ✅ Multi-entity transformations (lines 204-224)
- ✅ Async execution patterns (lines 262-292)
- ✅ Complex distributed workflows (lines 424-509)

### **Missing Implementation** ❌
- ❌ **Event-driven reactive cascades** - The README shows event-driven patterns with `@on` decorators, but we don't have a working example
- ❌ **Entity versioning and lineage** - README shows lineage tracking but no dedicated example
- ❌ **Event system observation** - README mentions events but no comprehensive example

### **Inconsistencies to Fix** 🔄
- 🔄 **Line 175**: `EntityRegistry.get_function_execution()` doesn't exist - already fixed
- 🔄 **Line 428**: Missing imports in grade processing example - already fixed
- 🔄 **Line 313**: Event handling in grade processing needs example

## Next Steps

### **Priority 1: Create Missing Event-Driven Example**
Create `05_reactive_cascades.py` that demonstrates:
- `@on` decorator usage for event handling
- Automatic batching based on events
- Emergent workflow coordination
- Map-reduce pattern through events

### **Priority 2: Create Entity Versioning Example**
Create `06_entity_versioning_lineage.py` that shows:
- Entity lineage tracking
- Version history management
- Provenance querying
- Audit trails

### **Priority 3: Create Event System Example**
Create `07_event_driven_observation.py` that demonstrates:
- Event bus usage
- Event filtering and routing
- Performance monitoring through events
- System observability patterns

### **Priority 4: Sync README with Examples**
Update README to:
- Link directly to example files
- Use exact code from working examples
- Remove any non-working code patterns
- Add file references for each code block

## File Naming Convention

```
NN_descriptive_name.py - Core functionality example
NN_descriptive_name_async.py - Async version of core functionality
```

Where `NN` is the sequential number matching the order of concepts in the README.

## Example Template Structure

Each example should follow this structure:
```python
"""
Example NN: Descriptive Title

This example demonstrates:
- Feature 1
- Feature 2
- Feature 3

Features showcased:
- Technical detail 1
- Technical detail 2
"""

# Imports and setup
# Entity definitions
# Function registrations
# Test/validation code
# Main execution with comprehensive output
```

## Testing Requirements

Each example must:
- ✅ Run without errors
- ✅ Include comprehensive validation
- ✅ Show clear output demonstrating features
- ✅ Include both success and edge case handling
- ✅ Provide performance metrics where relevant
- ✅ Match the exact patterns shown in README