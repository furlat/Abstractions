"""
Multi-Step Workflow with Distractor Functions

This demonstrates a complex 3-4 step workflow where the agent must:
1. Validate user credentials and permissions
2. Process data transformation with multiple similar functions (distractors)
3. Generate and send notifications
4. Create final audit report

Includes distractor functions with similar signatures but different semantics.
"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from pydantic import Field

from abstractions.registry_agent import (
    TypedAgentFactory, GoalFactory
)
from abstractions.ecs.entity import Entity, ConfigEntity
from abstractions.ecs.callable_registry import CallableRegistry


# Result entity for function execution operations
class FunctionExecutionResult(Entity):
    """
    Result entity for function execution operations.
    
    This entity captures the outcome of executing registered functions including
    success status, function identification, and the returned data.
    
    Fields:
    - function_name: Name of the function that was executed
    - success: Boolean indicating if the function executed successfully
    - result_data: The actual data/results returned by the function execution
    """
    function_name: str
    success: bool
    result_data: Dict[str, Any]


# Domain entities for the workflow
class UserCredentials(Entity):
    """User authentication and authorization entity."""
    user_id: str = Field(description="Unique user identifier")
    username: str = Field(description="User login name")
    role: str = Field(description="User role: admin, manager, user")
    permissions: List[str] = Field(default_factory=list, description="List of granted permissions")
    session_token: str = Field(description="Current session authentication token")

class DataTransformConfig(Entity):
    """Configuration for data transformation operations."""
    source_format: str = Field(description="Input data format: json, csv, xml")
    target_format: str = Field(description="Output data format: json, csv, xml")
    transformation_rules: List[str] = Field(default_factory=list, description="Applied transformation rules")
    batch_size: int = Field(default=100, description="Number of records to process per batch")

class NotificationSettings(Entity):
    """Settings for notification delivery."""
    recipient_email: str = Field(description="Email address to receive notifications")
    notification_type: str = Field(description="Type of notification: success, warning, error")
    include_details: bool = Field(default=True, description="Whether to include detailed information")
    priority_level: str = Field(default="normal", description="Priority level: low, normal, high, urgent")

class AuditConfig(Entity):
    """Configuration for audit report generation."""
    report_type: str = Field(description="Type of audit report: summary, detailed, compliance")
    include_user_actions: bool = Field(default=True, description="Include user action logs")
    include_system_events: bool = Field(default=False, description="Include system event logs")
    retention_days: int = Field(default=90, description="How long to retain audit data")

# Result entities for each workflow step
class AuthValidationResult(Entity):
    """Result of user authentication and authorization validation."""
    user_id: str
    is_authenticated: bool
    is_authorized: bool
    granted_permissions: List[str]
    session_valid: bool
    validation_timestamp: datetime

class DataProcessingResult(Entity):
    """Result of data transformation processing."""
    process_id: str
    records_processed: int
    records_successful: int
    records_failed: int
    output_location: str
    processing_duration_seconds: float
    transformation_applied: str

class NotificationResult(Entity):
    """Result of notification delivery."""
    notification_id: str
    recipient: str
    delivery_status: str  # sent, failed, pending
    delivery_timestamp: Optional[datetime]
    retry_count: int
    error_message: Optional[str]

class AuditReportResult(Entity):
    """Result of audit report generation."""
    report_id: str
    report_type: str
    total_events_captured: int
    report_file_path: str
    generation_timestamp: datetime
    report_size_bytes: int

# STEP 1: Authentication and Authorization Functions
@CallableRegistry.register("validate_user_credentials")
async def validate_user_credentials(credentials: UserCredentials) -> AuthValidationResult:
    """Validate user authentication and check authorization permissions."""
    # Simulate authentication check
    is_authenticated = len(credentials.session_token) > 10
    is_authorized = credentials.role in ["admin", "manager"]
    
    result = AuthValidationResult(
        user_id=credentials.user_id,
        is_authenticated=is_authenticated,
        is_authorized=is_authorized,
        granted_permissions=credentials.permissions if is_authorized else [],
        session_valid=is_authenticated,
        validation_timestamp=datetime.now(timezone.utc)
    )
    
    return result

# DISTRACTOR: Similar signature but different purpose
@CallableRegistry.register("validate_user_profile")
async def validate_user_profile(credentials: UserCredentials) -> AuthValidationResult:
    """Validate user profile completeness (DISTRACTOR - wrong function for auth)."""
    # This looks similar but validates profile, not permissions!
    result = AuthValidationResult(
        user_id=credentials.user_id,
        is_authenticated=True,  # Profile validation doesn't check auth
        is_authorized=False,    # Profile validation doesn't grant permissions
        granted_permissions=[],
        session_valid=False,
        validation_timestamp=datetime.now(timezone.utc)
    )
    
    return result

# STEP 2: Data Processing Functions  
@CallableRegistry.register("transform_data_batch")
async def transform_data_batch(config: DataTransformConfig) -> DataProcessingResult:
    """Transform data according to specified configuration (CORRECT for data processing)."""
    # Simulate data processing
    records_to_process = config.batch_size
    success_rate = 0.95 if config.source_format == config.target_format else 0.85
    
    successful = int(records_to_process * success_rate)
    failed = records_to_process - successful
    
    result = DataProcessingResult(
        process_id=f"BATCH_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        records_processed=records_to_process,
        records_successful=successful,
        records_failed=failed,
        output_location=f"/data/processed/{config.target_format}/output.{config.target_format}",
        processing_duration_seconds=2.5,
        transformation_applied=f"{config.source_format}_to_{config.target_format}"
    )
    
    return result

# DISTRACTOR: Similar signature but different semantics
@CallableRegistry.register("validate_data_batch") 
async def validate_data_batch(config: DataTransformConfig) -> DataProcessingResult:
    """Validate data integrity (DISTRACTOR - validates but doesn't transform)."""
    # This validates data but doesn't actually transform it!
    result = DataProcessingResult(
        process_id=f"VALIDATION_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        records_processed=config.batch_size,
        records_successful=config.batch_size,  # Validation always "succeeds"
        records_failed=0,
        output_location="",  # No output for validation
        processing_duration_seconds=0.5,
        transformation_applied="validation_only"  # No actual transformation
    )
    
    return result

# DISTRACTOR: Another similar function
@CallableRegistry.register("archive_data_batch")
async def archive_data_batch(config: DataTransformConfig) -> DataProcessingResult:
    """Archive data batch (DISTRACTOR - archives but doesn't transform for current use)."""
    result = DataProcessingResult(
        process_id=f"ARCHIVE_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        records_processed=config.batch_size,
        records_successful=config.batch_size,
        records_failed=0,
        output_location=f"/archive/{config.source_format}/archived.{config.source_format}",
        processing_duration_seconds=1.0,
        transformation_applied="archival_copy"  # Not what we want for processing
    )
    
    return result

# STEP 3: Notification Functions
@CallableRegistry.register("send_process_notification")
async def send_process_notification(settings: NotificationSettings, process_details: str) -> NotificationResult:
    """Send notification about process completion (CORRECT for workflow notifications)."""
    # Simulate notification sending
    delivery_success = settings.priority_level in ["normal", "high", "urgent"]
    
    result = NotificationResult(
        notification_id=f"NOTIF_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        recipient=settings.recipient_email,
        delivery_status="sent" if delivery_success else "failed",
        delivery_timestamp=datetime.now(timezone.utc) if delivery_success else None,
        retry_count=0 if delivery_success else 1,
        error_message=None if delivery_success else "Invalid priority level"
    )
    
    return result

# DISTRACTOR: Similar signature but different purpose
@CallableRegistry.register("send_marketing_notification")
async def send_marketing_notification(settings: NotificationSettings, process_details: str) -> NotificationResult:
    """Send marketing notification (DISTRACTOR - wrong type of notification)."""
    # This sends marketing emails, not process notifications!
    result = NotificationResult(
        notification_id=f"MARKETING_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        recipient=settings.recipient_email,
        delivery_status="sent",
        delivery_timestamp=datetime.now(timezone.utc),
        retry_count=0,
        error_message=None
    )
    
    return result

# STEP 4: Audit Report Functions
@CallableRegistry.register("generate_compliance_audit")
async def generate_compliance_audit(audit_config: AuditConfig, user_id: str, process_id: str) -> AuditReportResult:
    """Generate compliance audit report (CORRECT for audit trail)."""
    # Simulate audit report generation
    event_count = 150 if audit_config.include_user_actions else 50
    
    result = AuditReportResult(
        report_id=f"AUDIT_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        report_type=audit_config.report_type,
        total_events_captured=event_count,
        report_file_path=f"/reports/audit/{audit_config.report_type}_report.pdf",
        generation_timestamp=datetime.now(timezone.utc),
        report_size_bytes=2048 * event_count
    )
    
    return result

# DISTRACTOR: Similar signature but different report type
@CallableRegistry.register("generate_performance_audit")
async def generate_performance_audit(audit_config: AuditConfig, user_id: str, process_id: str) -> AuditReportResult:
    """Generate performance audit report (DISTRACTOR - wrong audit type)."""
    # This generates performance reports, not compliance audits!
    result = AuditReportResult(
        report_id=f"PERF_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        report_type="performance",  # Wrong type!
        total_events_captured=25,   # Much fewer events
        report_file_path=f"/reports/performance/perf_report.pdf",
        generation_timestamp=datetime.now(timezone.utc),
        report_size_bytes=1024 * 25
    )
    
    return result

def create_workflow_entities():
    """Create entities needed for the multi-step workflow."""
    
    # User credentials for authentication
    user_creds = UserCredentials(
        user_id="USR_12345",
        username="john.manager",
        role="manager",
        permissions=["data_processing", "audit_access", "notification_send"],
        session_token="SESSION_TOKEN_ABCDEF123456789"
    )
    user_creds.promote_to_root()
    
    # Data transformation configuration
    transform_config = DataTransformConfig(
        source_format="csv",
        target_format="json",
        transformation_rules=["normalize_dates", "validate_emails", "remove_duplicates"],
        batch_size=500
    )
    transform_config.promote_to_root()
    
    # Notification settings
    notification_settings = NotificationSettings(
        recipient_email="admin@company.com",
        notification_type="success",
        include_details=True,
        priority_level="high"
    )
    notification_settings.promote_to_root()
    
    # Audit configuration
    audit_config = AuditConfig(
        report_type="compliance",
        include_user_actions=True,
        include_system_events=True,
        retention_days=365
    )
    audit_config.promote_to_root()
    
    return user_creds, transform_config, notification_settings, audit_config

async def test_multi_step_workflow():
    """Test the complete multi-step workflow with distractors."""
    print("🔄 Testing Multi-Step Workflow with Distractors...")
    
    # Create entities for the workflow
    user_creds, transform_config, notification_settings, audit_config = create_workflow_entities()
    
    # Create a function execution agent
    workflow_agent = TypedAgentFactory.create_agent(FunctionExecutionResult)
    
    # Complex multi-step request with potential for confusion
    request = f"""
    Execute a complete data processing workflow with the following 4 steps:
    
    STEP 1 - User Authentication:
    Use entity @{user_creds.ecs_id} to validate user credentials and permissions.
    CRITICAL: Use validate_user_credentials (NOT validate_user_profile) to check authorization.
    
    STEP 2 - Data Processing:
    Use entity @{transform_config.ecs_id} to transform data from CSV to JSON format.
    CRITICAL: Use transform_data_batch (NOT validate_data_batch or archive_data_batch) for actual transformation.
    
    STEP 3 - Send Notification:
    Use entity @{notification_settings.ecs_id} with process details from step 2.
    CRITICAL: Use send_process_notification (NOT send_marketing_notification) for workflow updates.
    Include the process_id from step 2 as the process_details parameter.
    
    STEP 4 - Generate Audit Report:
    Use entity @{audit_config.ecs_id} with user_id from step 1 and process_id from step 2.
    CRITICAL: Use generate_compliance_audit (NOT generate_performance_audit) for regulatory compliance.
    
    Each step depends on results from previous steps. Create a FunctionExecutionResult tracking the final audit report generation.
    """
    
    try:
        run_result = await workflow_agent.run(request)
        result = run_result.output
        
        print(f"✅ Multi-step workflow completed!")
        print(f"   Goal type: {result.goal_type}")
        print(f"   Completed: {result.goal_completed}")
        print(f"   Summary: {result.summary}")
        
        if result.typed_result and isinstance(result.typed_result, FunctionExecutionResult):
            print(f"   Result type: {type(result.typed_result).__name__}")
            print(f"   Function: {result.typed_result.function_name}")
            print(f"   Success: {result.typed_result.success}")
            print(f"   Result data: {result.typed_result.result_data}")
        
        if result.error:
            print(f"   Error: {result.error.error_message}")
        
        print(f"\nall messages: {run_result.all_messages()}")
            
    except Exception as e:
        print(f"❌ Multi-step workflow failed: {e}")

async def main():
    """Run the multi-step workflow test."""
    print("🚀 Multi-Step Workflow with Distractors Test")
    print("=" * 60)
    print("Testing agent's ability to:")
    print("1. Execute 4 sequential function calls")
    print("2. Use results from previous steps")
    print("3. Avoid distractor functions with similar signatures")
    print("4. Maintain context across the entire workflow")
    print()
    
    await test_multi_step_workflow()

if __name__ == "__main__":
    asyncio.run(main())