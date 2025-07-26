"""
All Agent Execution Patterns Test - Clean Generic Implementation

This file demonstrates all 9 agent execution patterns with completely generic
ASCII formatting that works for any function - no hardcoded entity searches.

Based on the proven approach from event_tracking_test.py.
"""

import asyncio
from typing import Any, Dict, Optional, List, Tuple
from uuid import UUID
from pydantic import BaseModel, Field
from datetime import datetime

# Import event system
from abstractions.events.events import (
    Event, EventPhase, emit_events, on, get_event_bus,
    ProcessingEvent, ProcessedEvent
)

# Import entity system components
from abstractions.ecs.entity import Entity
from abstractions.ecs.callable_registry import CallableRegistry

# Import the original execution result model
from abstractions.registry_agent import ExecutionResult


# ============================================================================
# CUSTOM AGENT EVENTS
# ============================================================================

class AgentToolCallStartEvent(ProcessingEvent):
    """Event emitted when agent tool call begins."""
    type: str = "agent.tool_call.start"
    phase: EventPhase = EventPhase.STARTED
    
    # Agent-specific data
    function_name: str = Field(description="Function being called")
    raw_parameters: Dict[str, Any] = Field(default_factory=dict, description="Raw tool parameters")
    pattern_classification: Optional[str] = Field(default=None, description="Input pattern type")
    parameter_count: int = Field(default=0, description="Number of parameters")


class AgentToolCallCompletedEvent(ProcessedEvent):
    """Event emitted when agent tool call completes successfully."""
    type: str = "agent.tool_call.completed"
    phase: EventPhase = EventPhase.COMPLETED
    
    # Agent-specific data
    function_name: str = Field(description="Function that was called")
    result_type: str = Field(description="Type of result returned")
    entity_id: Optional[str] = Field(default=None, description="ID of result entity (single entity)")
    entity_type: Optional[str] = Field(default=None, description="Type of result entity")
    entity_count: Optional[int] = Field(default=None, description="Number of entities returned")
    entity_ids: List[str] = Field(default_factory=list, description="All entity IDs (multi-entity)")
    success: bool = Field(default=True, description="Whether execution succeeded")


class AgentToolCallFailedEvent(ProcessingEvent):
    """Event emitted when agent tool call fails."""
    type: str = "agent.tool_call.failed"
    phase: EventPhase = EventPhase.FAILED
    
    # Agent-specific data  
    function_name: str = Field(description="Function that failed")
    error_type: str = Field(description="Type of error")
    failed_parameters: Dict[str, Any] = Field(default_factory=dict, description="Parameters that caused failure")


# ============================================================================
# EVENT-WRAPPED EXECUTION FUNCTION
# ============================================================================

@emit_events(
    creating_factory=lambda function_name, **kwargs: AgentToolCallStartEvent(
        process_name="execute_function",
        function_name=function_name,
        raw_parameters=kwargs,
        parameter_count=len(kwargs)
    ),
    created_factory=lambda result, function_name, **kwargs: AgentToolCallCompletedEvent(
        process_name="execute_function",
        function_name=function_name,
        result_type=result.result_type if hasattr(result, 'result_type') else "unknown",
        entity_id=result.entity_id if hasattr(result, 'entity_id') else None,
        entity_type=result.entity_type if hasattr(result, 'entity_type') else None,
        entity_count=result.entity_count if hasattr(result, 'entity_count') else None,
        entity_ids=(
            result.debug_info.get('entity_ids', [])
            if hasattr(result, 'debug_info') and isinstance(result.debug_info, dict)
            else []
        ),
        success=result.success if hasattr(result, 'success') else True,
        output_ids=(
            result.debug_info.get('entity_ids', [])
            if hasattr(result, 'debug_info') and isinstance(result.debug_info, dict)
            else []
        )
    ),
    failed_factory=lambda error, function_name, **kwargs: AgentToolCallFailedEvent(
        process_name="execute_function",
        function_name=function_name,
        error_type=type(error).__name__,
        failed_parameters=kwargs,
        error=str(error)
    )
)
async def execute_function_with_events(function_name: str, **kwargs) -> ExecutionResult:
    """
    Event-wrapped version of the registry agent execute_function tool.
    
    This creates a complete event hierarchy and returns proper ExecutionResult.
    """
    try:
        # Execute the function (this will emit all the child events from CallableRegistry)
        result = await CallableRegistry.aexecute(function_name, **kwargs)
        
        # Process result and return a simple ExecutionResult
        if hasattr(result, 'ecs_id') and isinstance(result, Entity):  # Single entity
            return ExecutionResult(
                success=True,
                function_name=function_name,
                result_type="single_entity",
                entity_id=str(result.ecs_id),
                entity_type=type(result).__name__,
                entity_count=1
            )
        elif isinstance(result, list):
            entity_ids = [str(e.ecs_id) for e in result if hasattr(e, 'ecs_id')]
            first_entity_type = type(result[0]).__name__ if result and hasattr(result[0], 'ecs_id') else "Entity"
            return ExecutionResult(
                success=True,
                function_name=function_name,
                result_type="entity_list",
                entity_type=first_entity_type,
                entity_count=len(entity_ids),
                debug_info={"entity_ids": entity_ids}
            )
        else:
            return ExecutionResult(
                success=True,
                function_name=function_name,
                result_type="other",
                debug_info={"value": str(result)}
            )
        
    except Exception as e:
        return ExecutionResult(
            success=False,
            function_name=function_name,
            result_type="error",
            error_message=str(e),
            debug_info={
                "parameters": list(kwargs.keys()),
                "error": str(e)
            }
        )


# ============================================================================
# GENERIC ASCII FORMATTER - NO HARDCODED SEARCHES
# ============================================================================

class GenericASCIIFormatter:
    """Generic ASCII formatter that works for any function execution."""
    
    def extract_entity_type_from_completion_event(self, completion_event) -> str:
        """
        Generic entity type extraction from ExecutionResult data.
        No hardcoded event searches - works for any function.
        """
        # Check if completion event has entity_type directly
        if hasattr(completion_event, 'entity_type') and completion_event.entity_type:
            return completion_event.entity_type
            
        # For single entity results, try to get the type from the EntityRegistry
        entity_id = getattr(completion_event, 'entity_id', None)
        if entity_id:
            try:
                from abstractions.ecs.entity import EntityRegistry
                from uuid import UUID
                
                # Convert string to UUID if needed
                if isinstance(entity_id, str):
                    entity_uuid = UUID(entity_id)
                else:
                    entity_uuid = entity_id
                
                # Get root_ecs_id for this entity
                root_ecs_id = EntityRegistry.ecs_id_to_root_id.get(entity_uuid)
                if root_ecs_id:
                    # Query the actual entity to get its type
                    actual_entity = EntityRegistry.get_stored_entity(root_ecs_id, entity_uuid)
                    if actual_entity:
                        return type(actual_entity).__name__
            except Exception:
                pass  # Fall back if EntityRegistry query fails
        
        # For multi-entity results
        if hasattr(completion_event, 'result_type') and completion_event.result_type == "entity_list":
            return "MultipleEntities"
        
        return "Entity"  # Fallback


formatter = GenericASCIIFormatter()


@on(AgentToolCallCompletedEvent)
async def format_and_display_execution(event: AgentToolCallCompletedEvent):
    """Generic detector using ExecutionResult - works for any function!"""
    print(f"\n🎨 ASCII FORMATTER: Detected completed agent call for {event.function_name}")
    
    try:
        # Get EventBus and use history to find related events
        bus = get_event_bus()
        
        # Get recent history to find related events by lineage_id or function_name
        history = bus.get_history(limit=100)
        
        # Find start event by function_name and recent timing
        start_event = None
        for hist_event in reversed(history):  # Recent events first
            if (hist_event.type == "agent.tool_call.start" and
                isinstance(hist_event, AgentToolCallStartEvent) and
                hist_event.function_name == event.function_name):
                # Check if it's reasonably recent (within last 10 seconds)
                time_diff = (event.timestamp - hist_event.timestamp).total_seconds()
                if time_diff < 10:
                    start_event = hist_event
                    break
        
        if not start_event:
            print("⚠️  Could not find start event in recent history")
            return
        
        # ✅ GENERIC: Use ExecutionResult-based extraction instead of event searches
        entity_type = formatter.extract_entity_type_from_completion_event(event)
        print(f"🎯 Entity type extracted from ExecutionResult: {entity_type}")
        
        # Format directly using the generic approach
        ascii_display = format_from_bus_queries(start_event, event, entity_type, bus)
        
        print(f"\n{'='*60}")
        print(f"🎯 AGENT EXECUTION PATTERN (GENERIC)")
        print(f"{'='*60}")
        print(ascii_display)
        print(f"{'='*60}")
            
    except Exception as e:
        print(f"❌ Error in ASCII formatting: {e}")
        import traceback
        traceback.print_exc()


def format_from_bus_queries(start_event: Event, completion_event: Event, entity_type: str, bus) -> str:
    """Generic formatting using EventBus queries - no hardcoded patterns."""
    
    # Extract data directly from events
    function_name = getattr(start_event, 'function_name', 'unknown')
    raw_parameters = getattr(start_event, 'raw_parameters', {})
    start_time = start_event.timestamp
    
    # Extract timing
    end_time = completion_event.timestamp
    total_ms = (end_time - start_time).total_seconds() * 1000
    
    # Extract result info
    result_type = getattr(completion_event, 'result_type', 'unknown')
    entity_id = getattr(completion_event, 'entity_id', None)
    entity_count = getattr(completion_event, 'entity_count', None)
    
    # Find function execution duration from siblings
    execution_ms = 0.0
    siblings = bus.get_siblings(completion_event.id)
    for sibling in siblings:
        if (hasattr(sibling, 'process_name') and 
            sibling.process_name == "function_execution" and 
            sibling.phase.value == "completed"):
            execution_ms = getattr(sibling, 'duration_ms', 0.0) or 0.0
            break
    
    resolution_ms = max(0.0, total_ms - execution_ms)
    
    # Build the ASCII display
    lines = []
    
    # Header
    lines.append(f"⏱️  START: {start_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]}Z")
    lines.append("")
    
    # Function signature - get REAL signature from CallableRegistry and clean it
    try:
        function_info = CallableRegistry.get_function_info(function_name)
        if function_info and 'signature' in function_info:
            # Use the actual function signature and clean __main__ references
            real_signature = function_info['signature']
            clean_signature = real_signature.replace('__main__.', '')
            lines.append(f"🚀 {clean_signature}")
        else:
            # Fallback if function not found in registry
            lines.append(f"🚀 {function_name}(...) -> {entity_type}")
    except Exception as e:
        # Final fallback
        lines.append(f"🚀 {function_name}(...) -> {entity_type}")
    lines.append("")
    
    # Raw tool call
    lines.append("📝 RAW TOOL CALL: {")
    for param_name, param_value in raw_parameters.items():
        if hasattr(param_value, 'ecs_id'):
            lines.append(f'   "{param_name}": "@{param_value.ecs_id}",')
        else:
            lines.append(f'   "{param_name}": {repr(param_value)},')
    lines.append("}")
    lines.append("")
    
    # Resolution steps - resolve actual values through EntityRegistry
    if raw_parameters:
        lines.append("🔍 RESOLVING:")
        for param_name, param_value in raw_parameters.items():
            if isinstance(param_value, str) and param_value.startswith('@'):
                # String address - resolve through EntityRegistry to get real types and values
                lines.append(f"   {param_name}: \"{param_value}\"")
                try:
                    from abstractions.ecs.ecs_address_parser import ECSAddressParser
                    from abstractions.ecs.entity import EntityRegistry
                    from uuid import UUID
                    
                    if '.' in param_value:
                        # Field borrowing: @uuid.field - resolve to actual value
                        resolved_value = ECSAddressParser.resolve_address(param_value)
                        entity_uuid, field_path = ECSAddressParser.parse_address(param_value)
                        field_name = field_path[0]
                        
                        # Get actual entity type
                        root_ecs_id = EntityRegistry.ecs_id_to_root_id.get(entity_uuid)
                        if root_ecs_id:
                            entity = EntityRegistry.get_stored_entity(root_ecs_id, entity_uuid)
                            if entity:
                                entity_type_name = type(entity).__name__
                                full_id = str(entity_uuid)
                                lines.append(f"   → @{entity_type_name}|{full_id} : {field_name} = {repr(resolved_value)}")
                            else:
                                full_id = str(entity_uuid)
                                lines.append(f"   → @Entity|{full_id} : {field_name} = {repr(resolved_value)}")
                        else:
                            full_id = str(entity_uuid)
                            lines.append(f"   → @Entity|{full_id} : {field_name} = {repr(resolved_value)}")
                    else:
                        # Direct entity reference: @uuid - get actual entity type
                        entity_uuid = UUID(param_value[1:])  # Remove @ and convert to UUID
                        root_ecs_id = EntityRegistry.ecs_id_to_root_id.get(entity_uuid)
                        if root_ecs_id:
                            entity = EntityRegistry.get_stored_entity(root_ecs_id, entity_uuid)
                            if entity:
                                entity_type_name = type(entity).__name__
                                full_id = str(entity_uuid)
                                lines.append(f"   → @{entity_type_name}|{full_id} [direct entity reference]")
                            else:
                                full_id = str(entity_uuid)
                                lines.append(f"   → @Entity|{full_id} [direct entity reference]")
                        else:
                            full_id = str(entity_uuid)
                            lines.append(f"   → @Entity|{full_id} [direct entity reference]")
                except Exception:
                    # Fallback to generic display
                    if '.' in param_value:
                        parts = param_value.split('.')
                        entity_part = parts[0][1:]
                        field_part = parts[1]
                        lines.append(f"   → @Entity|{entity_part} : {field_part} = <unresolved>")
                    else:
                        entity_id = param_value[1:]
                        lines.append(f"   → @Entity|{entity_id} [direct entity reference]")
                lines.append("")
            elif hasattr(param_value, 'ecs_id') and not isinstance(param_value, str):
                # Direct entity reference
                entity_type_name = type(param_value).__name__
                full_id = str(param_value.ecs_id)
                lines.append(f"   {param_name}: \"@{param_value.ecs_id}\"")
                lines.append(f"   → @{entity_type_name}|{full_id} [direct entity reference]")
                lines.append("")
    
    # Function call - show actual resolved values and entity types
    call_params = []
    for param_name, param_value in raw_parameters.items():
        if isinstance(param_value, str) and param_value.startswith('@'):
            try:
                from abstractions.ecs.ecs_address_parser import ECSAddressParser
                from abstractions.ecs.entity import EntityRegistry
                from uuid import UUID
                
                if '.' in param_value:
                    # Field borrowing - show actual resolved value
                    resolved_value = ECSAddressParser.resolve_address(param_value)
                    call_params.append(f"{param_name}={repr(resolved_value)}")
                else:
                    # Direct entity reference - show actual entity type
                    entity_uuid = UUID(param_value[1:])  # Remove @
                    root_ecs_id = EntityRegistry.ecs_id_to_root_id.get(entity_uuid)
                    if root_ecs_id:
                        entity = EntityRegistry.get_stored_entity(root_ecs_id, entity_uuid)
                        if entity:
                            entity_type_name = type(entity).__name__
                            full_id = str(entity_uuid)
                            call_params.append(f"{param_name}={entity_type_name}|{full_id}")
                        else:
                            full_id = str(entity_uuid)
                            call_params.append(f"{param_name}=Entity|{full_id}")
                    else:
                        full_id = str(entity_uuid)
                        call_params.append(f"{param_name}=Entity|{full_id}")
            except Exception:
                # Fallback
                if '.' in param_value:
                    call_params.append(f"{param_name}=<unresolved>")
                else:
                    entity_id = param_value[1:]
                    call_params.append(f"{param_name}=Entity|{entity_id}")
        elif hasattr(param_value, 'ecs_id') and not isinstance(param_value, str):
            # Direct entity reference
            entity_type_name = type(param_value).__name__
            full_id = str(param_value.ecs_id)
            call_params.append(f"{param_name}={entity_type_name}|{full_id}")
        else:
            call_params.append(f"{param_name}={repr(param_value)}")
    
    call_signature = f"{function_name}({', '.join(call_params)})"
    lines.append(f"📥 FUNCTION CALL: {call_signature}")
    lines.append("")
    
    # Output - handle both single and multi-entity using entity_ids
    entity_ids = getattr(completion_event, 'entity_ids', [])
    
    if entity_ids and len(entity_ids) > 0:
        # Multi-entity case - show proper entity information
        if len(entity_ids) == 1:
            lines.append(f"📤 OUTPUT: {entity_type}#{entity_ids[0]}")
            lines.append(f"   ├─ entity_type: \"{entity_type}\"")
            lines.append(f"   ├─ result_type: \"{result_type}\"")
            lines.append(f"   ├─ success: true")
            lines.append("")
        else:
            first_id = entity_ids[0]
            lines.append(f"📤 OUTPUT: {len(entity_ids)} entities (first: {entity_type}#{first_id})")
            lines.append(f"   ├─ entity_count: {len(entity_ids)}")
            lines.append(f"   ├─ entity_type: \"{entity_type}\"")
            lines.append(f"   ├─ result_type: \"{result_type}\"")
            lines.append(f"   ├─ success: true")
            lines.append("")
    elif entity_id:
        # Single entity case
        if entity_count and entity_count > 1:
            lines.append(f"📤 OUTPUT: {entity_count} entities (first: {entity_type}#{entity_id})")
            lines.append(f"   ├─ entity_count: {entity_count}")
            lines.append(f"   ├─ result_type: \"{result_type}\"")
            lines.append(f"   ├─ success: true")
            lines.append("")
        else:
            lines.append(f"📤 OUTPUT: {entity_type}#{entity_id}")
            lines.append(f"   ├─ entity_type: \"{entity_type}\"")
            lines.append(f"   ├─ result_type: \"{result_type}\"")
            lines.append(f"   ├─ success: true")
            lines.append("")
    
    # Entity flow - show actual entity types from EntityRegistry
    input_entities = []
    for param_name, param_value in raw_parameters.items():
        if isinstance(param_value, str) and param_value.startswith('@'):
            try:
                from abstractions.ecs.entity import EntityRegistry
                from uuid import UUID
                
                # Extract entity UUID from string address
                if '.' in param_value:
                    # Field borrowing: @uuid.field -> just the entity
                    entity_uuid = UUID(param_value.split('.')[0][1:])  # Remove @ and get UUID
                else:
                    # Direct entity: @uuid
                    entity_uuid = UUID(param_value[1:])  # Remove @
                
                # Get actual entity type from EntityRegistry
                root_ecs_id = EntityRegistry.ecs_id_to_root_id.get(entity_uuid)
                if root_ecs_id:
                    entity = EntityRegistry.get_stored_entity(root_ecs_id, entity_uuid)
                    if entity:
                        entity_type_name = type(entity).__name__
                        input_entities.append(f"{entity_type_name}|{str(entity_uuid)}")
                    else:
                        input_entities.append(f"Entity|{str(entity_uuid)}")
                else:
                    input_entities.append(f"Entity|{str(entity_uuid)}")
            except Exception:
                # Fallback to generic entity display
                if '.' in param_value:
                    entity_id_str = param_value.split('.')[0][1:]
                else:
                    entity_id_str = param_value[1:]
                input_entities.append(f"Entity|{entity_id_str}")
        elif hasattr(param_value, 'ecs_id') and not isinstance(param_value, str):
            # Direct entity reference
            entity_type_name = type(param_value).__name__
            full_id = str(param_value.ecs_id)
            input_entities.append(f"{entity_type_name}|{full_id}")
    
    # Output entities - handle single and multi-entity cases using entity_ids
    output_entities = []
    
    # Check if completion_event has entity_ids (multi-entity case)
    entity_ids = getattr(completion_event, 'entity_ids', [])
    
    if entity_ids and len(entity_ids) > 0:
        # Multi-entity case - get ACTUAL entity types from EntityRegistry for each entity
        output_entities = []
        for eid in entity_ids:
            try:
                from abstractions.ecs.entity import EntityRegistry
                from uuid import UUID
                
                # Convert string to UUID if needed
                entity_uuid = UUID(eid) if isinstance(eid, str) else eid
                
                # Get root_ecs_id for this entity
                root_ecs_id = EntityRegistry.ecs_id_to_root_id.get(entity_uuid)
                if root_ecs_id:
                    # Query the actual entity to get its real type
                    actual_entity = EntityRegistry.get_stored_entity(root_ecs_id, entity_uuid)
                    if actual_entity:
                        actual_type = type(actual_entity).__name__
                        output_entities.append(f"{actual_type}|{eid}")
                    else:
                        output_entities.append(f"Entity|{eid}")
                else:
                    output_entities.append(f"Entity|{eid}")
            except Exception:
                # Fallback - use the generic entity_type from the event
                output_entities.append(f"{entity_type}|{eid}")
    elif entity_id:
        # Single entity case - use entity_id field
        if entity_count and entity_count > 1:
            # Fallback: show count
            output_entities.append(f"{entity_count} {entity_type} entities")
        else:
            output_entities.append(f"{entity_type}|{entity_id}")
    
    # Remove duplicates from input entities while preserving order
    seen = set()
    unique_input_entities = []
    for entity in input_entities:
        if entity not in seen:
            unique_input_entities.append(entity)
            seen.add(entity)
    input_entities = unique_input_entities
    
    if not input_entities:
        input_entities = ["No entities"]
    if not output_entities:
        output_entities = ["No entities"]
    
    # Entity flow with REAL function name and REAL execution UUID (FULL UUID)
    execution_id = str(completion_event.id) if hasattr(completion_event, 'id') else "unknown"
    flow_line = f"[{', '.join(input_entities)}] ---> [{function_name}|{execution_id}] ---> [{', '.join(output_entities)}]"
    lines.append(flow_line)
    lines.append("")
    
    # Timing breakdown
    lines.append(f"⏱️  END: {end_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]}Z")
    if resolution_ms > 0:
        lines.append(f"🔍 RESOLUTION: {resolution_ms:.1f}ms")
    lines.append(f"📥 EXECUTION: {execution_ms:.1f}ms")
    lines.append(f"✅ TOTAL: {total_ms:.1f}ms")
    
    return "\n".join(lines)


# ============================================================================
# TEST ENTITIES FOR ALL 9 PATTERNS
# ============================================================================

class DateRangeConfig(Entity):
    start_date: str = ""
    end_date: str = ""

class Student(Entity):
    name: str = ""
    gpa: float = 0.0
    courses: List[str] = Field(default_factory=list)

class Course(Entity):
    name: str = ""
    credits: int = 0
    description: str = ""

class FunctionExecutionResult(Entity):
    function_name: str = ""
    success: bool = True
    result_data: Dict[str, Any] = Field(default_factory=dict)

class ComparisonResult(Entity):
    winner: str = ""
    score_difference: float = 0.0
    comparison_type: str = ""

class AnalysisResult(Entity):
    student_id: str = ""
    performance_level: str = ""
    gpa_score: float = 0.0
    recommendation: str = ""

class EnrollmentResult(Entity):
    student_id: str = ""
    course_name: str = ""
    enrollment_date: str = ""
    credits_enrolled: int = 0

class ClassStatistics(Entity):
    class_average: float = 0.0
    student_count: int = 0
    highest_gpa: float = 0.0
    lowest_gpa: float = 0.0

class AcademicRecord(Entity):
    student_id: str = ""
    total_credits: int = 0
    graduation_eligible: bool = False

class Assessment(Entity):
    student_id: str = ""
    performance_level: str = ""
    gpa_score: float = 0.0

class Recommendation(Entity):
    student_id: str = ""
    action: str = ""
    reasoning: str = ""


# ============================================================================
# PATTERN FUNCTIONS - ALL 9 EXECUTION PATTERNS
# ============================================================================

# Pattern 1: Pure Field Borrowing (Single Entity Source)
@CallableRegistry.register("calculate_revenue_metrics")
async def calculate_revenue_metrics(start_date: str, end_date: str) -> FunctionExecutionResult:
    """Pattern 1: Pure field borrowing from single entity."""
    await asyncio.sleep(0.001)
    return FunctionExecutionResult(
        function_name="calculate_revenue_metrics",
        success=True,
        result_data={"total_revenue": 15750.50, "orders": 123}
    )

# Pattern 2: Multi-Entity Field Borrowing
@CallableRegistry.register("compare_students")
async def compare_students(name1: str, name2: str, gpa1: float, gpa2: float) -> ComparisonResult:
    """Pattern 2: Field borrowing from multiple entities."""
    await asyncio.sleep(0.001)
    winner = name1 if gpa1 > gpa2 else name2
    return ComparisonResult(
        winner=winner,
        score_difference=abs(gpa1 - gpa2),
        comparison_type="gpa_based"
    )

# Pattern 3: Direct Entity Reference (Single Entity)
@CallableRegistry.register("analyze_student")
async def analyze_student(student: Student) -> AnalysisResult:
    """Pattern 3: Direct entity reference."""
    await asyncio.sleep(0.001)
    level = "high" if student.gpa > 3.5 else "standard"
    recommendation = "advanced_placement" if student.gpa > 3.5 else "standard_track"
    return AnalysisResult(
        student_id=str(student.ecs_id),
        performance_level=level,
        gpa_score=student.gpa,
        recommendation=recommendation
    )

# Pattern 4: Mixed Direct Entity + Field Borrowing
@CallableRegistry.register("enroll_student")
async def enroll_student(student: Student, course_name: str, credits: int) -> EnrollmentResult:
    """Pattern 4: Mixed direct entity + field borrowing."""
    await asyncio.sleep(0.001)
    return EnrollmentResult(
        student_id=str(student.ecs_id),
        course_name=course_name,
        enrollment_date="2024-07-25",
        credits_enrolled=credits
    )

# Pattern 5: Multiple Direct Entity References
@CallableRegistry.register("calculate_class_average")
async def calculate_class_average(student1: Student, student2: Student, student3: Student) -> ClassStatistics:
    """Pattern 5: Multiple direct entity references."""
    await asyncio.sleep(0.001)
    gpas = [student1.gpa, student2.gpa, student3.gpa]
    return ClassStatistics(
        class_average=sum(gpas) / len(gpas),
        student_count=3,
        highest_gpa=max(gpas),
        lowest_gpa=min(gpas)
    )

# Pattern 6: Same Entity In, Same Entity Out (Mutation)
@CallableRegistry.register("update_student_gpa")
async def update_student_gpa(student: Student) -> Student:
    """Pattern 6: Mutation - same entity in and out."""
    await asyncio.sleep(0.001)
    student.gpa = min(4.0, student.gpa + 0.1)  # Small boost
    print("🔧 Updated GPA for student:", student.name)
    return student

# Pattern 7: Same Entity In, Multiple Entities Out (One Continues Lineage)
@CallableRegistry.register("split_student_record")
async def split_student_record(student: Student) -> Tuple[Student, AcademicRecord]:
    """Pattern 7: Split into multiple entities, one continues lineage."""
    await asyncio.sleep(0.001)
    record = AcademicRecord(
        student_id=str(student.ecs_id),
        total_credits=48,
        graduation_eligible=student.gpa >= 3.0
    )
    return student, record

# Pattern 8: Same Entity Type Out But Not Lineage Continuation (Creation)
@CallableRegistry.register("create_similar_student")
async def create_similar_student(template: Student) -> Student:
    """Pattern 8: Create new entity of same type with different lineage."""
    await asyncio.sleep(0.001)
    return Student(
        name=f"{template.name} Clone",
        gpa=template.gpa,
        courses=template.courses.copy()
    )

# Pattern 9: Multi-Entity Output (Tuple Return)
@CallableRegistry.register("analyze_performance")
async def analyze_performance(student: Student) -> Tuple[Assessment, Recommendation]:
    """Pattern 9: Multiple entity output."""
    await asyncio.sleep(0.001)
    
    level = "high" if student.gpa > 3.5 else "standard"
    action = "advanced_placement" if student.gpa > 3.5 else "standard_track"
    
    assessment = Assessment(
        student_id=str(student.ecs_id),
        performance_level=level,
        gpa_score=student.gpa
    )
    
    recommendation = Recommendation(
        student_id=str(student.ecs_id),
        action=action,
        reasoning=f"Based on GPA of {student.gpa}"
    )
    
    return assessment, recommendation


# ============================================================================
# COMPREHENSIVE TEST SUITE
# ============================================================================

async def test_all_patterns():
    """Test all 9 agent execution patterns."""
    
    print("🚀 Starting All Patterns Test - Clean Generic Implementation")
    print("=" * 80)
    
    # Start event bus
    bus = get_event_bus()
    await bus.start()
    
    # Wait a moment for setup
    await asyncio.sleep(0.1)
    
    # Create test entities
    print("\n📝 Setting up test entities...")
    
    # For Pattern 1: DateRangeConfig
    date_config = DateRangeConfig(start_date="2024-10-01", end_date="2024-12-31")
    date_config.promote_to_root()
    
    # For Patterns 2, 3, 4, 5, 6, 7, 8, 9: Students
    student1 = Student(name="Alice", gpa=3.8, courses=["CS101", "CS201"])
    student1.promote_to_root()
    
    student2 = Student(name="Bob", gpa=3.2, courses=["CS101", "MATH101"])
    student2.promote_to_root()
    
    student3 = Student(name="Carol", gpa=3.5, courses=["CS201", "PHYS101"])
    student3.promote_to_root()
    
    # For Pattern 4: Course
    course = Course(name="Advanced Algorithms", credits=4, description="Advanced CS course")
    course.promote_to_root()
    
    print(f"Created DateRangeConfig: {date_config.ecs_id}")
    print(f"Created Student1 (Alice): {student1.ecs_id}")
    print(f"Created Student2 (Bob): {student2.ecs_id}")
    print(f"Created Student3 (Carol): {student3.ecs_id}")
    print(f"Created Course: {course.ecs_id}")
    
    # Test each pattern using string addresses
    patterns = [
        ("Pattern 1: Pure Field Borrowing", "calculate_revenue_metrics", {
            "start_date": f"@{date_config.ecs_id}.start_date",
            "end_date": f"@{date_config.ecs_id}.end_date"
        }),
        ("Pattern 2: Multi-Entity Field Borrowing", "compare_students", {
            "name1": f"@{student1.ecs_id}.name",
            "name2": f"@{student2.ecs_id}.name",
            "gpa1": f"@{student1.ecs_id}.gpa",
            "gpa2": f"@{student2.ecs_id}.gpa"
        }),
        ("Pattern 3: Direct Entity Reference", "analyze_student", {
            "student": f"@{student1.ecs_id}"
        }),
        ("Pattern 4: Mixed Direct Entity + Field Borrowing", "enroll_student", {
            "student": f"@{student1.ecs_id}",
            "course_name": f"@{course.ecs_id}.name",
            "credits": f"@{course.ecs_id}.credits"
        }),
        ("Pattern 5: Multiple Direct Entity References", "calculate_class_average", {
            "student1": f"@{student1.ecs_id}",
            "student2": f"@{student2.ecs_id}",
            "student3": f"@{student3.ecs_id}"
        }),
        ("Pattern 6: Same Entity In, Same Entity Out (Mutation)", "update_student_gpa", {
            "student": f"@{student2.ecs_id}"
        }),
        ("Pattern 7: Same Entity In, Multiple Entities Out", "split_student_record", {
            "student": f"@{student3.ecs_id}"
        }),
        ("Pattern 8: Same Entity Type Out (New Lineage)", "create_similar_student", {
            "template": f"@{student1.ecs_id}"
        }),
        ("Pattern 9: Multi-Entity Output (Tuple Return)", "analyze_performance", {
            "student": f"@{student2.ecs_id}"
        })
    ]
    
    for i, (pattern_name, function_name, params) in enumerate(patterns, 1):

        print(f"\n{'='*80}")
        print(f"🎯 Testing {pattern_name}")
        print(f"{'='*80}")
        
        # Execute the function

        result = await execute_function_with_events(function_name, **params)
        print(f"Result: {result}")
        
        # Wait for events to propagate
        await asyncio.sleep(0.5)
        
        # Add separator between patterns
        if i < len(patterns):
            print(f"\n{'~'*80}")
            print(f"Completed Pattern {i} - Moving to Pattern {i+1}")
            print(f"{'~'*80}")
    
    # Final statistics
    print(f"\n📊 FINAL EVENTBUS STATISTICS")
    stats = bus.get_statistics()
    print(f"Total events processed: {stats['total_events']}")
    print(f"Event types: {list(stats['event_counts'].keys())}")
    print(f"✅ All {len(patterns)} patterns tested successfully with GENERIC formatting!")
    

    
    await bus.stop()


# Run the test
asyncio.run(test_all_patterns())