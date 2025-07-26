"""
Event Tracking Test - Isolated Example

This file demonstrates wrapping the execute_function tool with @emit_events
to capture the complete event hierarchy without LLM integration.

Based on the actual framework patterns from readme_examples/.
"""

import asyncio
from typing import Any, Dict, Optional, List, Tuple
from uuid import UUID
from pydantic import BaseModel, Field

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
    entity_id: Optional[str] = Field(default=None, description="ID of result entity")
    entity_count: Optional[int] = Field(default=None, description="Number of entities returned")
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
        entity_count=result.entity_count if hasattr(result, 'entity_count') else None,
        success=result.success if hasattr(result, 'success') else True,
        output_ids=[]
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
    
    This creates a complete event hierarchy:
    - AgentToolCallStartEvent (root)
    - All CallableRegistry events become children
    - All Entity events become grandchildren
    - AgentToolCallCompletedEvent (completion)
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
            return ExecutionResult(
                success=True,
                function_name=function_name,
                result_type="entity_list",
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


# Helper functions removed - using simplified approach


# ============================================================================
# ASCII FORMATTER FOR AGENT EXECUTION PATTERNS
# ============================================================================

from datetime import datetime
from dataclasses import dataclass
from typing import Union

@dataclass
class AgentCallInfo:
    """Extracted agent call information"""
    function_name: str
    raw_parameters: Dict[str, Any]
    parameter_count: int
    start_time: datetime
    pattern_classification: Optional[str] = None

@dataclass
class StrategyInfo:
    """Extracted strategy information"""
    detected_strategy: str
    strategy_reasoning: str = ""
    execution_path: str = ""
    confidence_level: str = "unknown"

@dataclass
class ParameterResolution:
    """Individual parameter resolution"""
    param_name: str
    raw_address: str
    resolved_type: str
    resolved_value: Any
    is_borrowing: bool
    entity_short_id: str

@dataclass
class FunctionCallInfo:
    """Function execution information"""
    execution_duration_ms: float
    success: bool
    input_entity_ids: List[str]
    output_entity_ids: List[str]
    created_entity_ids: List[str]
    semantic_results: List[str]

@dataclass
class OutputInfo:
    """Output entity information"""
    entities: List[Dict[str, Any]]
    unpacking_duration_ms: Optional[float] = None
    is_multi_entity: bool = False

@dataclass
class TimingBreakdown:
    """Complete timing breakdown"""
    start_time: datetime
    end_time: datetime
    resolution_ms: float
    execution_ms: float
    unpacking_ms: Optional[float]
    total_ms: float

class ASCIIFormatter:
    """Formats event hierarchies into ASCII agent execution patterns"""
    
    def format_execution_pattern(self, event_tree: Dict[str, Any]) -> str:
        """Generate complete ASCII pattern matching format document"""
        
        # Extract all information using helpers
        agent_info = self._extract_agent_call_info(event_tree)
        strategy_info = self._extract_strategy_info(event_tree)
        resolution_info = self._extract_parameter_resolution(event_tree, agent_info)
        call_info = self._extract_function_call_info(event_tree)
        output_info = self._extract_output_info(event_tree)
        timing_info = self._extract_timing_info(event_tree)
        
        # Detect pattern and format accordingly
        pattern = self._detect_pattern(agent_info, strategy_info, call_info)
        
        return self._build_pattern_display(
            pattern, agent_info, strategy_info, resolution_info, 
            call_info, output_info, timing_info
        )
    
    def _extract_agent_call_info(self, event_tree: Dict[str, Any]) -> AgentCallInfo:
        """Extract agent call information from root event"""
        root_events = event_tree.get("roots", [])
        if not root_events:
            return AgentCallInfo("unknown", {}, 0, datetime.now())
        
        root_event = root_events[0]["event"]
        return AgentCallInfo(
            function_name=getattr(root_event, 'function_name', 'unknown'),
            raw_parameters=getattr(root_event, 'raw_parameters', {}),
            parameter_count=getattr(root_event, 'parameter_count', 0),
            start_time=root_event.timestamp,
            pattern_classification=getattr(root_event, 'pattern_classification', None)
        )
    
    def _extract_strategy_info(self, event_tree: Dict[str, Any]) -> StrategyInfo:
        """Extract strategy information from strategy detection events"""
        strategy_events = self._find_events_by_type(event_tree, "strategy.detected")
        if not strategy_events:
            return StrategyInfo("unknown")
        
        strategy_event = strategy_events[0]
        return StrategyInfo(
            detected_strategy=getattr(strategy_event, 'detected_strategy', 'unknown'),
            strategy_reasoning=getattr(strategy_event, 'strategy_reasoning', ''),
            execution_path=getattr(strategy_event, 'execution_path', ''),
            confidence_level=getattr(strategy_event, 'confidence_level', 'unknown')
        )
    
    def _extract_parameter_resolution(self, event_tree: Dict[str, Any], agent_info: AgentCallInfo) -> List[ParameterResolution]:
        """Extract parameter resolution details"""
        resolutions = []
        
        # For now, create mock resolutions based on raw parameters
        # In real implementation, this would parse InputPreparedEvent data
        for param_name, param_value in agent_info.raw_parameters.items():
            if hasattr(param_value, 'ecs_id'):
                # Direct entity reference
                resolutions.append(ParameterResolution(
                    param_name=param_name,
                    raw_address=f"@{param_value.ecs_id}",
                    resolved_type=type(param_value).__name__,
                    resolved_value=f"{type(param_value).__name__}|{str(param_value.ecs_id)[:8]}",
                    is_borrowing=False,
                    entity_short_id=str(param_value.ecs_id)[:8]
                ))
            else:
                # Primitive value
                resolutions.append(ParameterResolution(
                    param_name=param_name,
                    raw_address=str(param_value),
                    resolved_type=type(param_value).__name__,
                    resolved_value=param_value,
                    is_borrowing=False,
                    entity_short_id=""
                ))
        
        return resolutions
    
    def _extract_function_call_info(self, event_tree: Dict[str, Any]) -> FunctionCallInfo:
        """Extract function execution information"""
        # Look for function execution events - they have "function_execution" as process_name
        execution_events = self._find_events_by_process_name(event_tree, "function_execution")
        if not execution_events:
            return FunctionCallInfo(0.0, True, [], [], [], [])
        
        # Find the "processed" version of the function execution event
        processed_events = [e for e in execution_events if e.phase.value == "completed"]
        if not processed_events:
            processed_events = execution_events
            
        exec_event = processed_events[0]
        
        # Extract entity IDs from the agent completion event which has the actual result
        completion_events = self._find_events_by_type(event_tree, "agent.tool_call.completed")
        entity_id = getattr(completion_events[0], 'entity_id', None) if completion_events else None
        
        return FunctionCallInfo(
            execution_duration_ms=getattr(exec_event, 'duration_ms', 0.0) or 0.0,
            success=True,
            input_entity_ids=[],  # We'll extract this from the agent event
            output_entity_ids=[entity_id] if entity_id else [],
            created_entity_ids=[entity_id] if entity_id else [],
            semantic_results=["creation"]  # Default for now
        )
    
    def _extract_output_info(self, event_tree: Dict[str, Any]) -> OutputInfo:
        """Extract output entity information - FIXED to use ExecutionResult directly"""
        # Find the completion event to get result information
        completion_events = self._find_events_by_type(event_tree, "agent.tool_call.completed")
        if not completion_events:
            return OutputInfo([])
        
        completion_event = completion_events[0]
        result_type = getattr(completion_event, 'result_type', 'unknown')
        entity_id = getattr(completion_event, 'entity_id', None)
        entity_count = getattr(completion_event, 'entity_count', 0)
        
        # ✅ FIXED: Get entity type from ExecutionResult, not hardcoded event search
        entity_type = self._extract_entity_type_from_completion_event(completion_event)
        
        entities = []
        if entity_id:
            entities.append({
                'id': entity_id,
                'type': entity_type,  # ✅ Now actual type from ExecutionResult
                'count': entity_count,
                'result_type': result_type
            })
        
        return OutputInfo(
            entities=entities,
            is_multi_entity=bool(entity_count and entity_count > 1)
        )
    
    def _extract_timing_info(self, event_tree: Dict[str, Any]) -> TimingBreakdown:
        """Extract complete timing breakdown"""
        root_events = event_tree.get("roots", [])
        if not root_events:
            now = datetime.now()
            return TimingBreakdown(now, now, 0.0, 0.0, None, 0.0)
        
        root_event = root_events[0]["event"]
        start_time = root_event.timestamp
        
        # Find completion event
        completion_events = self._find_events_by_type(event_tree, "agent.tool_call.completed")
        end_time = completion_events[0].timestamp if completion_events else start_time
        
        # Calculate total duration
        total_ms = (end_time - start_time).total_seconds() * 1000
        
        # Try to get execution duration from function execution events
        execution_events = self._find_events_by_process_name(event_tree, "function_execution")
        execution_ms = 0.0
        
        if execution_events:
            # Find the completed function execution event
            completed_exec = [e for e in execution_events if e.phase.value == "completed"]
            if completed_exec:
                execution_ms = getattr(completed_exec[0], 'duration_ms', 0.0) or 0.0
        
        if execution_ms == 0.0:
            execution_ms = total_ms * 0.8  # Fallback estimate
        
        resolution_ms = max(0.0, total_ms - execution_ms)
        
        return TimingBreakdown(
            start_time=start_time,
            end_time=end_time,
            resolution_ms=resolution_ms,
            execution_ms=execution_ms,
            unpacking_ms=None,
            total_ms=total_ms
        )
    
    def _detect_pattern(self, agent_info: AgentCallInfo, strategy_info: StrategyInfo, call_info: FunctionCallInfo) -> str:
        """Detect which of the 9 patterns this execution represents"""
        
        # For now, return a simple pattern based on parameter analysis
        # This would be more sophisticated in the full implementation
        param_count = len(agent_info.raw_parameters)
        
        if param_count == 1:
            return "Pattern 3: Direct Entity Reference"
        elif param_count > 1:
            return "Pattern 2: Multi-Entity Field Borrowing"
        else:
            return "Pattern 1: Pure Field Borrowing"
    
    def _build_pattern_display(self, pattern: str, agent_info: AgentCallInfo, strategy_info: StrategyInfo, 
                              resolution_info: List[ParameterResolution], call_info: FunctionCallInfo,
                              output_info: OutputInfo, timing_info: TimingBreakdown) -> str:
        """Build the complete ASCII pattern display"""
        
        lines = []
        
        # Header
        lines.append(f"⏱️  START: {timing_info.start_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]}Z")
        lines.append("")
        
        # Function signature
        param_parts = []
        for resolution in resolution_info:
            param_type = resolution.resolved_type if not resolution.is_borrowing else "str"
            param_parts.append(f"{resolution.param_name}: {param_type}")
        
        signature = f"{agent_info.function_name}({', '.join(param_parts)}) -> Entity"
        lines.append(f"🚀 {signature}")
        lines.append("")
        
        # Raw tool call
        lines.append("📝 RAW TOOL CALL: {")
        for param_name, param_value in agent_info.raw_parameters.items():
            if hasattr(param_value, 'ecs_id'):
                lines.append(f'   "{param_name}": "@{param_value.ecs_id}",')
            else:
                lines.append(f'   "{param_name}": {repr(param_value)},')
        lines.append("}")
        lines.append("")
        
        # Resolution steps
        if resolution_info:
            lines.append("🔍 RESOLVING:")
            for resolution in resolution_info:
                if resolution.is_borrowing:
                    lines.append(f"   {resolution.param_name}: \"{resolution.raw_address}\"")
                    lines.append(f"   → @{resolution.resolved_type}|{resolution.entity_short_id} : {resolution.param_name} = {repr(resolution.resolved_value)}")
                else:
                    lines.append(f"   {resolution.param_name}: \"{resolution.raw_address}\"")
                    lines.append(f"   → @{resolution.resolved_type}|{resolution.entity_short_id} [direct entity reference]")
                lines.append("")
        
        # Function call
        call_params = []
        for resolution in resolution_info:
            if resolution.is_borrowing:
                call_params.append(f"{resolution.param_name}={repr(resolution.resolved_value)}")
            else:
                call_params.append(f"{resolution.param_name}={resolution.resolved_type}|{resolution.entity_short_id}")
        
        call_signature = f"{agent_info.function_name}({', '.join(call_params)})"
        lines.append(f"📥 FUNCTION CALL: {call_signature}")
        lines.append("")
        
        # Output
        if output_info.entities:
            entity = output_info.entities[0]
            entity_id = entity['id']
            entity_type = entity['type']
            
            lines.append(f"📤 OUTPUT: {entity_type}#{entity_id}")
            lines.append(f"   ├─ entity_type: \"{entity_type}\"")
            lines.append(f"   ├─ success: {str(call_info.success).lower()}")
            lines.append("")
        
        # Entity flow - extract from actual parameters and results
        input_entities = []
        for resolution in resolution_info:
            if resolution.entity_short_id:
                input_entities.append(f"{resolution.resolved_type}|{resolution.entity_short_id}")
        
        output_entities = []
        if output_info.entities:
            for entity in output_info.entities:
                entity_id = entity['id']
                entity_type = entity['type']
                short_id = entity_id[:8] if len(entity_id) > 8 else entity_id
                output_entities.append(f"{entity_type}|{short_id}")
        
        if not input_entities:
            input_entities = ["No entities"]
        if not output_entities:
            output_entities = ["No entities"]
        
        exec_id = str(abs(hash(agent_info.function_name)))[:8]
        flow_line = f"[{', '.join(input_entities)}] ---> [{agent_info.function_name}|exec-{exec_id}] ---> [{', '.join(output_entities)}]"
        lines.append(flow_line)
        lines.append("")
        
        # Timing breakdown
        lines.append(f"⏱️  END: {timing_info.end_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]}Z")
        lines.append(f"📥 EXECUTION: {timing_info.execution_ms:.1f}ms")
        lines.append(f"✅ TOTAL: {timing_info.total_ms:.1f}ms")
        
        return "\n".join(lines)
    
    def _find_events_by_type(self, event_tree: Dict[str, Any], event_type: str) -> List[Any]:
        """Find all events of a specific type in the tree"""
        events = []
        
        def traverse(node):
            if node.get("event") and getattr(node["event"], "type", "") == event_type:
                events.append(node["event"])
            for child in node.get("children", []):
                traverse(child)
        
        for root in event_tree.get("roots", []):
            traverse(root)
        
        return events
    
    def _find_events_by_process_name(self, event_tree: Dict[str, Any], process_name: str) -> List[Any]:
        """Find all events with a specific process_name"""
        events = []
        
        def traverse(node):
            event = node.get("event")
            if event and getattr(event, "process_name", "") == process_name:
                events.append(event)
            for child in node.get("children", []):
                traverse(child)
        
        for root in event_tree.get("roots", []):
            traverse(root)
        
        return events
    
    def _traverse_event_tree_depth_first(self, event_tree: Dict[str, Any]):
        """Generate events in depth-first order for traversal."""
        
        def traverse_node(node):
            # Yield current event
            if "event" in node:
                yield node["event"]
            
            # Recursively traverse children
            for child in node.get("children", []):
                yield from traverse_node(child)
        
        # Traverse all root nodes
        for root in event_tree.get("roots", []):
            yield from traverse_node(root)
    
    def _extract_entity_type_from_completion_event(self, completion_event) -> str:
        """
        FIXED: Extract entity type directly from ExecutionResult instead of hardcoded event search.
        
        This method uses the ExecutionResult structure in the completion event to get
        the actual entity type, making it generic to any function call.
        
        Args:
            completion_event: The agent.tool_call.completed event
            
        Returns:
            str: Actual entity type name from ExecutionResult or "Entity" as fallback
        """
        # Check if completion event has entity_type directly (some ExecutionResults include this)
        if hasattr(completion_event, 'entity_type') and completion_event.entity_type:
            return completion_event.entity_type
            
        # For single entity results, try to get the type from the EntityRegistry
        entity_id = getattr(completion_event, 'entity_id', None)
        if entity_id:
            try:
                # Import EntityRegistry here to avoid circular imports
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
        
        # For multi-entity results, get types from debug_info entity_ids
        if hasattr(completion_event, 'result_type') and completion_event.result_type == "entity_list":
            # This would need debug_info access, but for now return generic
            return "MultipleEntities"
        
        return "Entity"  # Fallback



# ============================================================================
# EVENT COLLECTION AND DISPLAY
# ============================================================================

class EventCollector:
    """Collects and displays event hierarchies."""
    
    def __init__(self):
        self.events = []
        self.current_root = None
        
    def start_collecting(self):
        """Start collecting events."""
        self.events.clear()
        
        # Subscribe to all events with debug logging
        @on(Event)
        async def collect_event(event: Event):
            print(f"📨 Collected event: {event.type} | parent_id: {event.parent_id} | id: {str(event.id)[:8]}")
            self.events.append(event)
            
            # Track root events (no parent)
            if event.parent_id is None and event.type.startswith("agent.tool_call.start"):
                self.current_root = event
        
        return self
    
    def get_event_tree(self) -> Dict[str, Any]:
        """Build hierarchical event tree."""
        if not self.events:
            return {}
            
        # Build parent-child map
        events_by_id = {e.id: e for e in self.events}
        children_map = {}
        
        for event in self.events:
            if event.parent_id:
                if event.parent_id not in children_map:
                    children_map[event.parent_id] = []
                children_map[event.parent_id].append(event)
        
        def build_tree(event):
            tree = {
                "event": event,
                "children": []
            }
            
            if event.id in children_map:
                for child in children_map[event.id]:
                    tree["children"].append(build_tree(child))
                    
            return tree
        
        # Find root events
        root_events = [e for e in self.events if e.parent_id is None]
        
        return {
            "roots": [build_tree(root) for root in root_events],
            "total_events": len(self.events)
        }
    
    def print_event_tree(self):
        """Print ASCII representation of event tree."""
        tree = self.get_event_tree()
        
        print(f"\n🌳 EVENT TREE ({tree['total_events']} events)")
        print("=" * 60)
        
        for root_tree in tree["roots"]:
            self._print_node(root_tree, "", True)
        
        print("=" * 60)
    
    def _print_node(self, tree, prefix, is_last):
        """Print a single node in the tree with detailed information."""
        event = tree["event"]
        
        # Choose connector
        connector = "└── " if is_last else "├── "
        
        # Format basic event info
        event_info = f"{event.type}"
        
        # Add function name if available
        if hasattr(event, 'function_name') and event.function_name:
            event_info += f" | {event.function_name}"
        
        # Add process name if available
        if hasattr(event, 'process_name') and event.process_name and event.process_name != event.type:
            event_info += f" | {event.process_name}"
        
        # Add timing info
        if hasattr(event, 'duration_ms') and event.duration_ms:
            event_info += f" | {event.duration_ms:.1f}ms"
        
        # Add phase if not pending
        if event.phase != EventPhase.PENDING:
            event_info += f" | {event.phase}"
        
        print(f"{prefix}{connector}{event_info}")
        
        # Print additional details if available
        details = []
        
        # Add subject info
        if hasattr(event, 'subject_type') and event.subject_type:
            details.append(f"Subject: {event.subject_type.__name__ if hasattr(event.subject_type, '__name__') else event.subject_type}")
        
        # Add raw parameters for agent events (simplified)
        if hasattr(event, 'raw_parameters') and event.raw_parameters:
            param_parts = []
            for k, v in event.raw_parameters.items():
                if hasattr(v, 'name'):  # Entity with name
                    param_parts.append(f"{k}={v.name}")
                elif hasattr(v, 'ecs_id'):  # Entity without name
                    param_parts.append(f"{k}=Entity({str(v.ecs_id)[:8]}...)")
                elif isinstance(v, str) and len(v) > 20:  # Long string
                    param_parts.append(f"{k}={v[:20]}...")
                else:  # Simple value
                    param_parts.append(f"{k}={v}")
            details.append(f"Params: {', '.join(param_parts[:3])}")  # Show max 3 params
        
        # Add result info for completed agent events
        if hasattr(event, 'result_type') and event.result_type:
            details.append(f"Result: {event.result_type}")
        
        # Add error info if failed
        if hasattr(event, 'error') and event.error:
            details.append(f"Error: {event.error}")
        
        # Add metadata info
        if hasattr(event, 'metadata') and event.metadata:
            meta_items = []
            for k, v in list(event.metadata.items())[:2]:  # Show first 2 metadata items
                meta_items.append(f"{k}={v}")
            if meta_items:
                details.append(f"Meta: {', '.join(meta_items)}")
        
        # Print details with proper indentation
        detail_prefix = prefix + ("    " if is_last else "│   ")
        for detail in details:
            print(f"{detail_prefix}  💡 {detail}")
        
        # Print children
        child_prefix = prefix + ("    " if is_last else "│   ")
        for i, child_tree in enumerate(tree["children"]):
            is_last_child = i == len(tree["children"]) - 1
            self._print_node(child_tree, child_prefix, is_last_child)


# ============================================================================
# ASCII FORMATTER INTEGRATION - SINGLE @ON DETECTOR
# ============================================================================

# Global formatter instance - no collector needed!
ascii_formatter = ASCIIFormatter()

@on(AgentToolCallCompletedEvent)
async def format_and_display_execution(event: AgentToolCallCompletedEvent):
    """FIXED: Generic detector using ExecutionResult - no hardcoded searches!"""
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
        
        # ✅ FIXED: Use generic ExecutionResult-based extraction instead of hardcoded search
        formatter = ASCIIFormatter()
        entity_type = formatter._extract_entity_type_from_completion_event(event)
        print(f"🎯 Entity type extracted from ExecutionResult: {entity_type}")
        
        # Format directly using the simplified approach
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


# ============================================================================
# POST-HOC FORMATTING FROM WORKING TREE
# ============================================================================



def format_from_bus_queries(start_event: Event, completion_event: Event, entity_type: str, bus) -> str:
    """
    Simplified formatting using EventBus queries instead of tree traversal.
    
    Args:
        start_event: The agent.tool_call.start event
        completion_event: The agent.tool_call.completed event
        entity_type: Extracted entity type from siblings
        bus: EventBus instance for queries
        
    Returns:
        Formatted ASCII display string
    """
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
    
    # Function signature - build from parameters
    param_parts = []
    for param_name, param_value in raw_parameters.items():
        if hasattr(param_value, 'ecs_id'):
            param_parts.append(f"{param_name}: {type(param_value).__name__}")
        else:
            param_parts.append(f"{param_name}: {type(param_value).__name__}")
    
    signature = f"{function_name}({', '.join(param_parts)}) -> {entity_type}"
    lines.append(f"🚀 {signature}")
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
    
    # Resolution steps
    if raw_parameters:
        lines.append("🔍 RESOLVING:")
        for param_name, param_value in raw_parameters.items():
            if hasattr(param_value, 'ecs_id'):
                entity_type_name = type(param_value).__name__
                full_id = str(param_value.ecs_id)
                lines.append(f"   {param_name}: \"@{param_value.ecs_id}\"")
                lines.append(f"   → @{entity_type_name}|{full_id} [direct entity reference]")
                lines.append("")
    
    # Function call
    call_params = []
    for param_name, param_value in raw_parameters.items():
        if hasattr(param_value, 'ecs_id'):
            entity_type_name = type(param_value).__name__
            full_id = str(param_value.ecs_id)
            call_params.append(f"{param_name}={entity_type_name}|{full_id}")
        else:
            call_params.append(f"{param_name}={repr(param_value)}")
    
    call_signature = f"{function_name}({', '.join(call_params)})"
    lines.append(f"📥 FUNCTION CALL: {call_signature}")
    lines.append("")
    
    # Output
    if entity_id:
        lines.append(f"📤 OUTPUT: {entity_type}#{entity_id}")
        lines.append(f"   ├─ entity_type: \"{entity_type}\"")
        lines.append(f"   ├─ result_type: \"{result_type}\"")
        lines.append(f"   ├─ success: true")
        lines.append("")
    
    # Entity flow
    input_entities = []
    for param_name, param_value in raw_parameters.items():
        if hasattr(param_value, 'ecs_id'):
            entity_type_name = type(param_value).__name__
            full_id = str(param_value.ecs_id)
            input_entities.append(f"{entity_type_name}|{full_id}")
    
    output_entities = []
    if entity_id:
        output_entities.append(f"{entity_type}|{entity_id}")
    
    if not input_entities:
        input_entities = ["No entities"]
    if not output_entities:
        output_entities = ["No entities"]
    
    # Use a proper exec ID from the completion event or generate consistently
    exec_id = f"exec-{str(abs(hash(function_name + str(start_time))))[:8]}"
    flow_line = f"[{', '.join(input_entities)}] ---> [{function_name}|{exec_id}] ---> [{', '.join(output_entities)}]"
    lines.append(flow_line)
    lines.append("")
    
    # Timing breakdown
    lines.append(f"⏱️  END: {end_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]}Z")
    if resolution_ms > 0:
        lines.append(f"🔍 RESOLUTION: {resolution_ms:.1f}ms")
    lines.append(f"📥 EXECUTION: {execution_ms:.1f}ms")
    lines.append(f"✅ TOTAL: {total_ms:.1f}ms")
    
    return "\n".join(lines)


def format_from_working_tree(working_tree: Dict[str, Any]) -> str:
    """Post-hoc formatting from the actual working event tree data"""
    
    # Find the agent tool call start event 
    agent_start_event = None
    agent_completed_event = None
    function_exec_completed_event = None
    
    def find_events(node):
        nonlocal agent_start_event, agent_completed_event, function_exec_completed_event
        event = node.get("event")
        if event:
            if event.type == "agent.tool_call.start":
                agent_start_event = event
            elif event.type == "agent.tool_call.completed":
                agent_completed_event = event
            elif (hasattr(event, 'process_name') and 
                  event.process_name == "function_execution" and 
                  event.phase.value == "completed"):
                function_exec_completed_event = event
        
        for child in node.get("children", []):
            find_events(child)
    
    for root in working_tree.get("roots", []):
        find_events(root)
    
    if not agent_start_event:
        return "❌ Could not find agent.tool_call.start event"
    
    # Extract data from the actual events
    function_name = getattr(agent_start_event, 'function_name', 'unknown')
    raw_parameters = getattr(agent_start_event, 'raw_parameters', {})
    start_time = agent_start_event.timestamp
    
    # Extract timing
    end_time = agent_completed_event.timestamp if agent_completed_event else start_time
    total_ms = (end_time - start_time).total_seconds() * 1000
    
    execution_ms = getattr(function_exec_completed_event, 'duration_ms', 0.0) if function_exec_completed_event else 0.0
    resolution_ms = max(0.0, total_ms - execution_ms)
    
    # Extract result info
    result_type = getattr(agent_completed_event, 'result_type', 'unknown') if agent_completed_event else 'unknown'
    entity_id = getattr(agent_completed_event, 'entity_id', None) if agent_completed_event else None
    
    # ✅ FIXED: Use generic entity type extraction from ExecutionResult
    if agent_completed_event:
        formatter = ASCIIFormatter()
        entity_type = formatter._extract_entity_type_from_completion_event(agent_completed_event)
    else:
        entity_type = "Entity"
    
    # Build the ASCII display
    lines = []
    
    # Header
    lines.append(f"⏱️  START: {start_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]}Z")
    lines.append("")
    
    # Function signature - build from parameters
    param_parts = []
    for param_name, param_value in raw_parameters.items():
        if hasattr(param_value, 'ecs_id'):
            param_parts.append(f"{param_name}: {type(param_value).__name__}")
        else:
            param_parts.append(f"{param_name}: {type(param_value).__name__}")
    
    signature = f"{function_name}({', '.join(param_parts)}) -> {entity_type}"
    lines.append(f"🚀 {signature}")
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
    
    # Resolution steps  
    if raw_parameters:
        lines.append("🔍 RESOLVING:")
        for param_name, param_value in raw_parameters.items():
            if hasattr(param_value, 'ecs_id'):
                entity_type_name = type(param_value).__name__
                full_id = str(param_value.ecs_id)
                lines.append(f"   {param_name}: \"@{param_value.ecs_id}\"")
                lines.append(f"   → @{entity_type_name}|{full_id} [direct entity reference]")
                lines.append("")
    
    # Function call
    call_params = []
    for param_name, param_value in raw_parameters.items():
        if hasattr(param_value, 'ecs_id'):
            entity_type_name = type(param_value).__name__
            full_id = str(param_value.ecs_id)
            call_params.append(f"{param_name}={entity_type_name}|{full_id}")
        else:
            call_params.append(f"{param_name}={repr(param_value)}")
    
    call_signature = f"{function_name}({', '.join(call_params)})"
    lines.append(f"📥 FUNCTION CALL: {call_signature}")
    lines.append("")
    
    # Output
    if entity_id:
        lines.append(f"📤 OUTPUT: {entity_type}#{entity_id}")
        lines.append(f"   ├─ entity_type: \"{entity_type}\"")
        lines.append(f"   ├─ result_type: \"{result_type}\"")
        lines.append(f"   ├─ success: true")
        lines.append("")
    
    # Entity flow
    input_entities = []
    for param_name, param_value in raw_parameters.items():
        if hasattr(param_value, 'ecs_id'):
            entity_type_name = type(param_value).__name__
            full_id = str(param_value.ecs_id)
            input_entities.append(f"{entity_type_name}|{full_id}")
    
    output_entities = []
    if entity_id:
        output_entities.append(f"{entity_type}|{entity_id}")
    
    if not input_entities:
        input_entities = ["No entities"]
    if not output_entities:
        output_entities = ["No entities"]
    
    # Use a proper exec ID from the completion event or generate consistently
    exec_id = f"exec-{str(abs(hash(function_name + str(start_time))))[:8]}"
    flow_line = f"[{', '.join(input_entities)}] ---> [{function_name}|{exec_id}] ---> [{', '.join(output_entities)}]"
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
# TEST EXAMPLE  
# ============================================================================

async def test_event_tracking():
    """Test the event-wrapped execution function."""
    
    print("🚀 Starting Event Tracking Test")
    print("=" * 60)
    
    # No collector needed - EventBus provides all the data!
    
    # Start event bus
    bus = get_event_bus()
    await bus.start()
    
    # Wait a moment for setup
    await asyncio.sleep(0.1)
    
    try:
        # Test 1: Create a simple test entity and function following the actual pattern
        print("\n📝 Test 1: Set up test entities and functions")
        
        # Define test entities (like the examples)
        class Student(Entity):
            name: str = ""
            gpa: float = 0.0
        
        # Register a simple function (following readme_examples pattern)
        # This should match Pattern 6: Same Entity In, Same Entity Out (Mutation)
        @CallableRegistry.register("update_student_gpa")
        async def update_student_gpa(student: Student) -> Student:
            """Update student GPA - test function for event tracking (mutation pattern)."""
            await asyncio.sleep(0.001)  # Simulate async work
            # This simulates a mutation - increase GPA by 0.3 points
            student.gpa = min(4.0, student.gpa + 0.3)
            return student
        
        # Create and promote a test student
        test_student = Student(name="Alice", gpa=3.5)
        test_student.promote_to_root()  # Following the readme pattern
        
        print(f"Created test student: {test_student.name} (GPA: {test_student.gpa})")
        print(f"Student ECS ID: {test_student.ecs_id}")
        
        # Execute the event-wrapped function following Pattern 6 (Single Entity Direct)
        result = await execute_function_with_events(
            "update_student_gpa",
            student=test_student  # Only entity reference, no primitives
        )
        
        print(f"Result: {result}")
        
        # Wait longer for all events to propagate
        print(f"\n⏳ Waiting for events to propagate...")
        await asyncio.sleep(1.0)  # Increased wait time
        
        # Display event statistics from EventBus
        bus = get_event_bus()
        stats = bus.get_statistics()
        print(f"\n📊 EVENT BUS STATISTICS")
        print(f"Total events processed: {stats['total_events']}")
        print(f"Event types: {list(stats['event_counts'].keys())}")
        print("EventBus now provides all data - no collector needed!")
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        
        # Show EventBus statistics on error
        try:
            bus = get_event_bus()
            stats = bus.get_statistics()
            print(f"\n📊 EventBus had {stats['total_events']} events before error")
        except:
            print("Could not get EventBus statistics")
    
    finally:
        await bus.stop()


if __name__ == "__main__":
    asyncio.run(test_event_tracking())