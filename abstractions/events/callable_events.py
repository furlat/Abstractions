"""
Callable Registry-Specific Events

This module provides specialized event types for callable registry operations that work
with the automatic nesting system. These events are designed specifically for
function execution, strategy detection, input processing, and result handling.

All events inherit from base event classes and work seamlessly with the
automatic nesting context management system.
"""

from typing import Optional, Dict, Any, List
from uuid import UUID
from pydantic import Field

# Import base events from events.py
from abstractions.events.events import (
    ProcessingEvent, ProcessedEvent
)

# =============================================================================
# FUNCTION EXECUTION EVENTS
# =============================================================================

class FunctionExecutionEvent(ProcessingEvent):
    """Event emitted when function execution starts."""
    function_name: str
    execution_strategy: Optional[str] = None  # Will be determined during execution
    
    # ✅ UUID TRACKING - Input entities
    input_entity_ids: List[UUID] = Field(default_factory=list)
    input_entity_types: List[str] = Field(default_factory=list)
    
    # Input context
    input_parameter_count: int
    input_entity_count: int
    input_primitive_count: int
    
    # Function metadata
    is_async: bool
    uses_config_entity: bool
    expected_output_count: int
    
    # Execution context
    execution_pattern: str  # "single_entity", "multi_entity", "config_entity", "transactional"
    execution_id: Optional[UUID] = None  # Generated during execution

class FunctionExecutedEvent(ProcessedEvent):
    """Event emitted when function execution completes."""
    function_name: str
    execution_successful: bool
    
    # ✅ UUID TRACKING - Complete entity lifecycle
    input_entity_ids: List[UUID] = Field(default_factory=list)
    output_entity_ids: List[UUID] = Field(default_factory=list)
    created_entity_ids: List[UUID] = Field(default_factory=list)
    modified_entity_ids: List[UUID] = Field(default_factory=list)
    config_entity_ids: List[UUID] = Field(default_factory=list)
    execution_record_id: Optional[UUID] = None
    
    # Execution results
    execution_strategy: str
    output_entity_count: int
    semantic_results: List[str]  # ["creation", "mutation", "detachment"]
    
    # Performance metrics
    execution_duration_ms: float
    total_events_generated: int
    execution_id: Optional[UUID] = None
    
    # Error context
    error_message: Optional[str] = None
    error_type: Optional[str] = None

# =============================================================================
# STRATEGY DETECTION EVENTS
# =============================================================================

class StrategyDetectionEvent(ProcessingEvent):
    """Event emitted when execution strategy detection starts."""
    function_name: str
    
    # ✅ UUID TRACKING - Strategy detection
    input_entity_ids: List[UUID] = Field(default_factory=list)
    input_entity_types: List[str] = Field(default_factory=list)
    config_entity_ids: List[UUID] = Field(default_factory=list)
    entity_type_mapping: Dict[str, str] = Field(default_factory=dict)  # UUID -> type mapping
    
    # Input analysis
    input_types: Dict[str, str]  # param_name -> type_name
    entity_count: int
    config_entity_count: int
    primitive_count: int
    
    # Detection context
    has_metadata: bool
    detection_method: str  # "signature_analysis", "runtime_analysis"

class StrategyDetectedEvent(ProcessedEvent):
    """Event emitted when execution strategy detection completes."""
    function_name: str
    detection_successful: bool
    
    # ✅ UUID TRACKING - Strategy results
    input_entity_ids: List[UUID] = Field(default_factory=list)
    config_entity_ids: List[UUID] = Field(default_factory=list)
    entity_type_mapping: Dict[str, str] = Field(default_factory=dict)
    
    # Strategy results
    detected_strategy: str  # "single_entity_with_config", "multi_entity_composite", etc.
    strategy_reasoning: str
    execution_path: str  # "transactional", "borrowing", "partial"
    
    # Decision factors
    decision_factors: List[str]
    confidence_level: str  # "high", "medium", "low"

# =============================================================================
# INPUT PROCESSING EVENTS
# =============================================================================

class InputPreparationEvent(ProcessingEvent):
    """Event emitted when input preparation starts."""
    function_name: str
    preparation_type: str  # "entity_creation", "borrowing", "isolation", "config_creation"
    
    # ✅ UUID TRACKING - Input preparation
    input_entity_ids: List[UUID] = Field(default_factory=list)
    
    # Input context
    entity_count: int
    requires_isolation: bool
    requires_config_entity: bool
    
    # Preparation metadata
    pattern_classification: Optional[str] = None
    borrowing_operations_needed: int = 0

class InputPreparedEvent(ProcessedEvent):
    """Event emitted when input preparation completes."""
    function_name: str
    preparation_successful: bool
    
    # ✅ UUID TRACKING - Input preparation results
    input_entity_ids: List[UUID] = Field(default_factory=list)
    created_entities: List[UUID] = Field(default_factory=list)
    config_entities_created: List[UUID] = Field(default_factory=list)
    execution_copy_ids: List[UUID] = Field(default_factory=list)
    borrowed_from_entities: List[UUID] = Field(default_factory=list)
    
    # Preparation results
    object_identity_map_size: int
    
    # Operation metrics
    isolation_successful: bool
    borrowing_operations_completed: int
    preparation_duration_ms: Optional[float] = None

# =============================================================================
# SEMANTIC ANALYSIS EVENTS
# =============================================================================

class SemanticAnalysisEvent(ProcessingEvent):
    """Event emitted when semantic analysis starts."""
    function_name: str
    
    # ✅ UUID TRACKING - Semantic analysis
    input_entity_ids: List[UUID] = Field(default_factory=list)
    result_entity_ids: List[UUID] = Field(default_factory=list)
    
    # Analysis context
    result_type: str
    analysis_method: str  # "object_identity", "ecs_id_comparison", "tree_analysis"
    
    # Analysis input
    has_object_identity_map: bool
    input_entity_count: int
    result_entity_count: int

class SemanticAnalyzedEvent(ProcessedEvent):
    """Event emitted when semantic analysis completes."""
    function_name: str
    analysis_successful: bool
    
    # ✅ UUID TRACKING - Semantic analysis results
    input_entity_ids: List[UUID] = Field(default_factory=list)
    result_entity_ids: List[UUID] = Field(default_factory=list)
    analyzed_entity_ids: List[UUID] = Field(default_factory=list)
    original_entity_id: Optional[UUID] = None
    
    # Analysis results
    semantic_type: str  # "creation", "mutation", "detachment"
    confidence_level: str  # "high", "medium", "low"
    
    # Analysis metrics
    analysis_duration_ms: float
    entities_analyzed: int

# =============================================================================
# OUTPUT PROCESSING EVENTS
# =============================================================================

class UnpackingEvent(ProcessingEvent):
    """Event emitted when result unpacking starts."""
    function_name: str
    
    # ✅ UUID TRACKING - Unpacking sources
    source_entity_ids: List[UUID] = Field(default_factory=list)
    
    # Unpacking context
    unpacking_pattern: str  # "list_return", "tuple_return", "dict_return", "single_return"
    expected_entity_count: int
    container_type: str
    
    # Unpacking metadata
    supports_unpacking: bool
    requires_container_entity: bool

class UnpackedEvent(ProcessedEvent):
    """Event emitted when result unpacking completes."""
    function_name: str
    unpacking_successful: bool
    
    # ✅ UUID TRACKING - Unpacking results
    source_entity_ids: List[UUID] = Field(default_factory=list)
    unpacked_entity_ids: List[UUID] = Field(default_factory=list)
    container_entity_id: Optional[UUID] = None
    sibling_entity_ids: List[UUID] = Field(default_factory=list)
    
    # Unpacking results
    unpacked_entity_count: int
    sibling_relationships_created: bool
    
    # Performance metrics
    unpacking_duration_ms: Optional[float] = None

class ResultFinalizationEvent(ProcessingEvent):
    """Event emitted when result finalization starts."""
    function_name: str
    
    # ✅ UUID TRACKING - Result finalization
    result_entity_ids: List[UUID] = Field(default_factory=list)
    
    # Finalization context
    result_count: int
    finalization_type: str  # "single_entity", "multi_entity", "with_siblings"
    
    # Finalization metadata
    requires_sibling_setup: bool
    requires_provenance_tracking: bool

class ResultFinalizedEvent(ProcessedEvent):
    """Event emitted when result finalization completes."""
    function_name: str
    finalization_successful: bool
    
    # ✅ UUID TRACKING - Finalization results
    final_entity_ids: List[UUID] = Field(default_factory=list)
    sibling_entity_ids: List[UUID] = Field(default_factory=list)
    
    # Finalization results
    final_entity_count: int
    sibling_groups_created: int
    provenance_records_created: int
    
    # Performance metrics
    finalization_duration_ms: Optional[float] = None

# =============================================================================
# CONFIGURATION EVENTS
# =============================================================================

class ConfigEntityCreationEvent(ProcessingEvent):
    """Event emitted when config entity creation starts."""
    function_name: str
    
    # ✅ UUID TRACKING - Config entity creation
    source_entity_ids: List[UUID] = Field(default_factory=list)  # If created from entities
    
    # Creation context
    config_type: str  # "explicit", "dynamic", "from_primitives"
    expected_config_class: Optional[str] = None
    
    # Creation metadata
    primitive_params_count: int
    has_expected_type: bool

class ConfigEntityCreatedEvent(ProcessedEvent):
    """Event emitted when config entity creation completes."""
    function_name: str
    creation_successful: bool
    
    # ✅ UUID TRACKING - Config entity creation results
    config_entity_id: UUID
    source_entity_ids: List[UUID] = Field(default_factory=list)  # If created from entities
    
    # Creation results
    config_entity_type: str
    fields_populated: int
    
    # Registration results
    registered_in_ecs: bool
    creation_duration_ms: Optional[float] = None

# =============================================================================
# EXECUTION PATTERN EVENTS
# =============================================================================

class PartialExecutionEvent(ProcessingEvent):
    """Event emitted when partial execution starts."""
    function_name: str
    
    # ✅ UUID TRACKING - Partial execution
    input_entity_ids: List[UUID] = Field(default_factory=list)
    config_entity_ids: List[UUID] = Field(default_factory=list)
    
    # Partial context
    partial_type: str  # "config_partial", "entity_partial", "mixed_partial"
    bound_parameters: List[str]
    
    # Execution metadata
    has_entity_params: bool
    has_config_params: bool

class PartialExecutedEvent(ProcessedEvent):
    """Event emitted when partial execution completes."""
    function_name: str
    execution_successful: bool
    
    # ✅ UUID TRACKING - Partial execution results
    input_entity_ids: List[UUID] = Field(default_factory=list)
    output_entity_ids: List[UUID] = Field(default_factory=list)
    config_entity_ids: List[UUID] = Field(default_factory=list)
    
    # Execution results
    result_entity_count: int
    partial_function_created: bool
    
    # Performance metrics
    execution_duration_ms: float

class TransactionalExecutionEvent(ProcessingEvent):
    """Event emitted when transactional execution starts."""
    function_name: str
    
    # ✅ UUID TRACKING - Transactional execution
    isolated_entity_ids: List[UUID] = Field(default_factory=list)
    execution_copy_ids: List[UUID] = Field(default_factory=list)
    
    # Transaction context
    isolated_entities_count: int
    has_object_identity_map: bool
    
    # Transaction metadata
    isolation_successful: bool
    transaction_id: UUID

class TransactionalExecutedEvent(ProcessedEvent):
    """Event emitted when transactional execution completes."""
    function_name: str
    execution_successful: bool
    
    # ✅ UUID TRACKING - Transactional execution results
    isolated_entity_ids: List[UUID] = Field(default_factory=list)
    output_entity_ids: List[UUID] = Field(default_factory=list)
    execution_copy_ids: List[UUID] = Field(default_factory=list)
    
    # Transaction results
    output_entities_count: int
    semantic_analysis_completed: bool
    
    # Performance metrics
    transaction_duration_ms: float
    transaction_id: UUID

# =============================================================================
# VALIDATION EVENTS
# =============================================================================

class ValidationEvent(ProcessingEvent):
    """Event emitted when function validation starts."""
    function_name: str
    
    # ✅ UUID TRACKING - Validation
    validated_entity_ids: List[UUID] = Field(default_factory=list)
    
    # Validation context
    validation_type: str  # "signature", "input_types", "constraints"
    items_to_validate: int
    
    # Validation metadata
    has_type_hints: bool
    has_constraints: bool

class ValidatedEvent(ProcessedEvent):
    """Event emitted when function validation completes."""
    function_name: str
    validation_successful: bool
    
    # ✅ UUID TRACKING - Validation results
    validated_entity_ids: List[UUID] = Field(default_factory=list)
    
    # Validation results
    validation_errors: List[str]
    warnings: List[str]
    
    # Performance metrics
    validation_duration_ms: Optional[float] = None

# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Function execution events
    'FunctionExecutionEvent',
    'FunctionExecutedEvent',
    
    # Strategy detection events
    'StrategyDetectionEvent',
    'StrategyDetectedEvent',
    
    # Input processing events
    'InputPreparationEvent',
    'InputPreparedEvent',
    
    # Semantic analysis events
    'SemanticAnalysisEvent',
    'SemanticAnalyzedEvent',
    
    # Output processing events
    'UnpackingEvent',
    'UnpackedEvent',
    'ResultFinalizationEvent',
    'ResultFinalizedEvent',
    
    # Configuration events
    'ConfigEntityCreationEvent',
    'ConfigEntityCreatedEvent',
    
    # Execution pattern events
    'PartialExecutionEvent',
    'PartialExecutedEvent',
    'TransactionalExecutionEvent',
    'TransactionalExecutedEvent',
    
    # Validation events
    'ValidationEvent',
    'ValidatedEvent',
]