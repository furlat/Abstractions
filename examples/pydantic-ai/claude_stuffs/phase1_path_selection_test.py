"""
Phase 1: Path Selection Intelligence Tests

Tests the agent's ability to choose different execution paths for the same input 
based on different goals using a cybersecurity incident response scenario.
"""

from typing import Optional, List
from datetime import datetime
from pydantic import Field
from abstractions.ecs.entity import Entity, EntityRegistry
from abstractions.ecs.callable_registry import CallableRegistry
from abstractions.ecs.registry_agent import registry_agent, GoalAchieved
from dataclasses import dataclass
import json


# ================================
# CYBERSECURITY DOMAIN ENTITIES
# ================================

class SecurityAlert(Entity):
    """Raw security alert from monitoring systems - initial ingestion point for all security events"""
    alert_id: str = Field(description="Unique identifier for this security alert, typically from SIEM system")
    source_ip: str = Field(description="IP address that triggered the security alert, may be internal or external")
    target_system: str = Field(description="System, service, or asset that was targeted by the suspicious activity")
    alert_type: str = Field(description="Category of security alert: login_attempt, malware_detection, network_intrusion, etc.")
    severity: str = Field(description="Initial severity level: 'low', 'medium', 'high', or 'critical' based on automated scoring")
    raw_data: dict = Field(description="Complete raw event data from monitoring system for forensic analysis")
    timestamp: datetime = Field(description="When the security event occurred according to monitoring system")


class ThreatAssessment(Entity):
    """Quick threat assessment for routine processing - fast automated analysis for low-risk alerts"""
    alert_id: str = Field(description="Reference to the original SecurityAlert that was analyzed")
    threat_level: int = Field(description="Numeric threat score from 1-5 where 1=benign, 5=critical threat")
    confidence: float = Field(description="Analysis confidence level from 0.0-1.0, typically lower for quick assessments")
    recommended_action: str = Field(description="Suggested next step: automated_containment, manual_review, escalate, etc.")
    assessment_type: str = Field(default="quick", description="Type of analysis performed: 'quick' for automated heuristics")
    processing_time_seconds: float = Field(description="How long the threat assessment took to complete")


class DetailedThreatReport(Entity):
    """Comprehensive analysis for high-priority threats - deep investigation with human-level analysis"""
    alert_id: str = Field(description="Reference to the original SecurityAlert that was analyzed")
    threat_classification: str = Field(description="Detailed threat category: advanced_persistent_threat, ransomware, insider_threat, etc.")
    attack_vectors: List[str] = Field(description="List of attack methods used: network_intrusion, social_engineering, malware, etc.")
    potential_impact: str = Field(description="Assessed business impact if the threat succeeds: data_breach, system_compromise, etc.")
    indicators_of_compromise: List[str] = Field(description="Specific IOCs found: IP addresses, file hashes, domains, etc.")
    recommended_response: str = Field(description="Detailed response strategy: immediate_containment, forensic_analysis, legal_action, etc.")
    analysis_depth: str = Field(default="comprehensive", description="Analysis thoroughness level: 'comprehensive' for full investigation")
    analyst_confidence: float = Field(description="Expert confidence in the analysis from 0.0-1.0, typically higher than quick scans")


class ContainmentAction(Entity):
    """Automated containment response - immediate protective measures taken by security systems"""
    alert_id: str = Field(description="Reference to the SecurityAlert that triggered this containment action")
    action_type: str = Field(description="Type of containment: automated_blocking, system_isolation, account_lockout, etc.")
    containment_status: str = Field(description="Execution status: 'automated', 'manual', or 'failed'")
    affected_systems: List[str] = Field(description="List of systems, IPs, or accounts that were contained or protected")
    mitigation_steps: List[str] = Field(description="Specific technical actions taken: block_ip, isolate_system, update_firewall, etc.")
    response_time_seconds: float = Field(description="How quickly containment was executed after threat detection")


class EscalationTicket(Entity):
    """Manual escalation for complex threats - routes sophisticated threats to human security analysts"""
    alert_id: str = Field(description="Reference to the SecurityAlert that requires human analysis")
    escalation_reason: str = Field(description="Why automated systems couldn't handle this: complexity, impact, uncertainty, etc.")
    assigned_analyst: str = Field(description="Security team member or role assigned to investigate this threat")
    priority: str = Field(description="Escalation priority level: 'low', 'medium', 'high', or 'urgent'")
    human_review_required: bool = Field(default=True, description="Confirms this threat needs human expert analysis")
    estimated_resolution_hours: int = Field(description="Projected time for security analyst to complete investigation")


class SecurityIncident(Entity):
    """Formal security incident for critical threats - official incident response activation"""
    alert_id: str = Field(description="Reference to the SecurityAlert that triggered formal incident response")
    incident_id: str = Field(description="Official incident tracking number for legal, compliance, and audit purposes")
    severity: str = Field(description="Incident severity: 'critical', 'high', 'medium' - determines response team size")
    incident_status: str = Field(description="Current incident state: active_response, contained, investigating, resolved")
    response_team_assigned: bool = Field(description="Whether full incident response team has been activated")
    estimated_business_impact: str = Field(description="Projected business consequences: data_breach, downtime, reputation_damage, etc.")
    requires_executive_notification: bool = Field(default=False, description="Whether C-level executives must be immediately notified")


# ================================
# FUNCTION REGISTRY SETUP
# ================================

def setup_phase1_functions():
    """Register all functions for Phase 1 testing"""
    
    # Clear any existing functions
    CallableRegistry._functions.clear()
    
    @CallableRegistry.register("ingest_alert")
    def ingest_alert(raw_alert: str) -> SecurityAlert:
        """
        Parse and structure raw security alert data from monitoring systems.
        
        Takes raw JSON alert data from SIEM systems and converts it into a structured
        SecurityAlert entity for further processing. This is the entry point for all
        security event processing workflows.
        
        Args:
            raw_alert: JSON string containing raw security event data with fields like
                      alert_id, source_ip, target_system, type, severity, timestamp
        
        Returns:
            SecurityAlert: Structured entity ready for threat analysis and response
        """
        # Parse the JSON alert data
        alert_data = json.loads(raw_alert)
        
        return SecurityAlert(
            alert_id=alert_data.get("alert_id", "unknown"),
            source_ip=alert_data.get("source_ip", "0.0.0.0"),
            target_system=alert_data.get("target_system", "unknown"),
            alert_type=alert_data.get("type", "unknown"),
            severity=alert_data.get("severity", "medium"),
            raw_data=alert_data,
            timestamp=datetime.now()
        )

    @CallableRegistry.register("quick_scan")
    def quick_scan(alert: SecurityAlert) -> ThreatAssessment:
        """
        Perform fast automated threat assessment for routine security alerts.
        
        Uses heuristic-based analysis for rapid threat scoring. Suitable for low to 
        medium severity alerts that don't require deep investigation. Provides quick
        risk assessment to determine if automated containment is appropriate.
        
        Args:
            alert: SecurityAlert entity to analyze for threat indicators
        
        Returns:
            ThreatAssessment: Quick risk evaluation with threat level and recommended action
        """
        # Quick heuristic-based assessment
        threat_level = 2 if alert.severity == "low" else 3
        confidence = 0.7  # Lower confidence for quick scan
        
        return ThreatAssessment(
            alert_id=alert.alert_id,
            threat_level=threat_level,
            confidence=confidence,
            recommended_action="automated_containment",
            processing_time_seconds=1.2
        )

    @CallableRegistry.register("deep_analysis")  
    def deep_analysis(alert: SecurityAlert) -> DetailedThreatReport:
        """
        Conduct comprehensive threat analysis for high-priority security alerts.
        
        Performs thorough investigation including attack vector analysis, impact assessment,
        and IOC extraction. Used for high/critical severity alerts or when human-level
        analysis is required. Provides detailed intelligence for incident response.
        
        Args:
            alert: SecurityAlert entity requiring comprehensive investigation
        
        Returns:
            DetailedThreatReport: Complete threat analysis with IOCs and response recommendations
        """
        # Detailed analysis based on alert type and severity
        attack_vectors = ["network_intrusion"] if "network" in alert.alert_type.lower() else ["malware"]
        
        return DetailedThreatReport(
            alert_id=alert.alert_id,
            threat_classification=f"advanced_{alert.alert_type}",
            attack_vectors=attack_vectors,
            potential_impact=f"{alert.severity}_impact_to_{alert.target_system}",
            indicators_of_compromise=[alert.source_ip, alert.target_system],
            recommended_response="immediate_containment" if alert.severity == "critical" else "manual_review",
            analyst_confidence=0.95
        )

    @CallableRegistry.register("auto_contain")
    def auto_contain(assessment: ThreatAssessment) -> ContainmentAction:
        """
        Execute automated containment measures for routine security threats.
        
        Implements immediate protective actions based on threat assessment results.
        Suitable for well-understood threats that can be safely contained without
        human intervention. Provides rapid response to limit threat impact.
        
        Args:
            assessment: ThreatAssessment indicating threat level and recommended actions
        
        Returns:
            ContainmentAction: Record of automated protective measures taken
        """
        return ContainmentAction(
            alert_id=assessment.alert_id,
            action_type="automated_blocking",
            containment_status="automated",
            affected_systems=[f"system_{assessment.alert_id}"],
            mitigation_steps=["block_ip", "isolate_system", "update_firewall"],
            response_time_seconds=0.8
        )

    @CallableRegistry.register("manual_escalation")
    def manual_escalation(report: DetailedThreatReport) -> EscalationTicket:
        """
        Escalate complex threats to human security analysts for expert review.
        
        Routes sophisticated or uncertain threats to skilled security professionals
        when automated systems cannot provide adequate response. Creates formal
        escalation ticket with priority assignment and analyst allocation.
        
        Args:
            report: DetailedThreatReport requiring human expert analysis and decision-making
        
        Returns:
            EscalationTicket: Formal assignment of threat to human security analyst
        """
        return EscalationTicket(
            alert_id=report.alert_id,
            escalation_reason="complex_threat_requires_human_analysis",
            assigned_analyst="security_team_lead",
            priority="high" if report.analyst_confidence > 0.8 else "medium",
            estimated_resolution_hours=4
        )

    @CallableRegistry.register("create_incident")
    def create_incident(report: DetailedThreatReport) -> SecurityIncident:
        """
        Activate formal incident response for critical security threats.
        
        Creates official security incident with full incident response team activation.
        Used for critical threats that pose significant business risk and require
        coordinated response, executive notification, and formal documentation.
        
        Args:
            report: DetailedThreatReport indicating critical threat requiring incident response
        
        Returns:
            SecurityIncident: Official incident record with response team assignment
        """
        return SecurityIncident(
            alert_id=report.alert_id,
            incident_id=f"INC_{report.alert_id}_{datetime.now().strftime('%Y%m%d')}",
            severity="critical",
            incident_status="active_response",
            response_team_assigned=True,
            estimated_business_impact="high_potential_data_breach",
            requires_executive_notification=True
        )

    print(f"✅ Registered {len(CallableRegistry.list_functions())} functions for Phase 1")
    return True


# ================================
# TEST CASES
# ================================

@dataclass 
class TestCase:
    name: str
    input_message: str
    expected_path: List[str]
    expected_final_entity_type: type
    expected_entity_attributes: dict
    description: str


def create_test_alert_data():
    """Create test alert data"""
    return json.dumps({
        "alert_id": "ALT_001_SUSPICIOUS_LOGIN", 
        "source_ip": "203.0.113.42",
        "target_system": "web_server_01",
        "type": "suspicious_login_attempt",
        "severity": "medium",
        "description": "Multiple failed login attempts from foreign IP",
        "timestamp": "2024-01-15T14:30:00Z"
    })


def get_phase1_test_cases():
    """Define all Phase 1 test cases"""
    alert_data = create_test_alert_data()
    
    return [
        TestCase(
            name="1A_Routine_Processing",
            input_message=f"Process this network alert for routine handling: {alert_data}",
            expected_path=["ingest_alert", "quick_scan", "auto_contain"],
            expected_final_entity_type=ContainmentAction,
            expected_entity_attributes={"containment_status": "automated"},
            description="Same input should trigger quick processing path for routine handling"
        ),
        
        TestCase(
            name="1B_Critical_Incident",
            input_message=f"Process this network alert for critical incident response: {alert_data}",
            expected_path=["ingest_alert", "deep_analysis", "create_incident"],
            expected_final_entity_type=SecurityIncident,
            expected_entity_attributes={"severity": "critical", "requires_executive_notification": True},
            description="Same input should trigger comprehensive analysis path for critical response"
        ),
        
        TestCase(
            name="1C_Human_Review",
            input_message=f"Process this network alert but I need human review: {alert_data}",
            expected_path=["ingest_alert", "deep_analysis", "manual_escalation"], 
            expected_final_entity_type=EscalationTicket,
            expected_entity_attributes={"human_review_required": True},
            description="Same input should trigger escalation path when human review is requested"
        )
    ]


# ================================
# VALIDATION FRAMEWORK
# ================================

@dataclass
class TestResult:
    test_case: TestCase
    agent_response: Optional[GoalAchieved]
    validation_results: dict
    passed: bool
    failure_reasons: List[str]


class Phase1Validator:
    """Validation framework for Phase 1 tests"""
    
    @staticmethod
    def validate_execution_path(expected_functions: List[str], agent_response: Optional[GoalAchieved]) -> tuple[bool, List[str]]:
        """Validate that the agent used the expected function sequence"""
        errors = []
        
        if agent_response is None:
            errors.append("No agent response available for validation")
            return False, errors
        
        actual_functions = agent_response.functions_used
        
        # Check if all expected functions were used
        for expected_func in expected_functions:
            if expected_func not in actual_functions:
                errors.append(f"Missing expected function: {expected_func}")
        
        # Check for unexpected functions
        for actual_func in actual_functions:
            if actual_func not in expected_functions:
                errors.append(f"Unexpected function used: {actual_func}")
        
        # Check sequence order (if agent provides sequence info)
        if len(actual_functions) == len(expected_functions):
            for i, expected in enumerate(expected_functions):
                if i < len(actual_functions) and actual_functions[i] != expected:
                    errors.append(f"Function sequence mismatch at position {i}: expected {expected}, got {actual_functions[i]}")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_final_entity(expected_type: type, expected_attrs: dict, agent_response: Optional[GoalAchieved]) -> tuple[bool, List[str]]:
        """Validate that the correct final entity was created with expected attributes"""
        errors = []
        
        if agent_response is None:
            errors.append("No agent response available for validation")
            return False, errors
        
        # Check if goal was completed
        if not agent_response.goal_completed:
            errors.append("Agent reported goal not completed")
            return False, errors
        
        # Check if we have entity references
        if not agent_response.entity_ids_referenced:
            errors.append("No entity IDs referenced in response")
            return False, errors
        
        # For this test, we'll check the agent's data field and summary
        # In a full implementation, we'd query the EntityRegistry for the actual entities
        
        # Check if expected entity type is mentioned in summary or data
        entity_type_name = expected_type.__name__
        summary_lower = agent_response.summary.lower()
        
        if entity_type_name.lower() not in summary_lower:
            errors.append(f"Expected entity type {entity_type_name} not mentioned in summary")
        
        # Check for expected attributes in the response data
        if agent_response.data:
            for attr_name, expected_value in expected_attrs.items():
                # This is a simplified check - in reality we'd query the actual entities
                attr_found = any(
                    attr_name in str(value) or str(expected_value) in str(value)
                    for value in agent_response.data.values()
                )
                if not attr_found:
                    errors.append(f"Expected attribute {attr_name}={expected_value} not found in response data")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_goal_interpretation(test_case: TestCase, agent_response: Optional[GoalAchieved]) -> tuple[bool, List[str]]:
        """Validate that the agent correctly interpreted the goal from the input message"""
        errors = []
        
        if agent_response is None:
            errors.append("No agent response available for validation")
            return False, errors
        
        # Check primary action alignment
        expected_actions = {
            "routine": ["data_retrieval", "function_execution"],
            "critical": ["function_execution", "incident_response"],
            "human review": ["function_execution", "escalation"]
        }
        
        # Determine expected action type from test case
        if "routine" in test_case.input_message.lower():
            valid_actions = expected_actions["routine"]
        elif "critical" in test_case.input_message.lower():
            valid_actions = expected_actions["critical"]  
        elif "human review" in test_case.input_message.lower():
            valid_actions = expected_actions["human review"]
        else:
            valid_actions = ["function_execution"]  # Default
        
        if agent_response.primary_action not in valid_actions:
            errors.append(f"Primary action '{agent_response.primary_action}' doesn't match expected actions for goal: {valid_actions}")
        
        return len(errors) == 0, errors


# ================================
# TEST RUNNER
# ================================

class Phase1TestRunner:
    """Test runner for Phase 1: Path Selection Intelligence"""
    
    def __init__(self):
        self.results: List[TestResult] = []
    
    def run_all_tests(self) -> List[TestResult]:
        """Run all Phase 1 tests"""
        print("🚀 Starting Phase 1: Path Selection Intelligence Tests")
        print("=" * 60)
        
        # Setup function registry
        setup_success = setup_phase1_functions()
        if not setup_success:
            print("❌ Failed to setup function registry")
            return []
        
        # Get test cases
        test_cases = get_phase1_test_cases()
        print(f"📋 Running {len(test_cases)} test cases...")
        
        # Run each test case
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n🧪 Test {i}/{len(test_cases)}: {test_case.name}")
            print(f"Description: {test_case.description}")
            
            result = self._run_single_test(test_case)
            self.results.append(result)
            
            # Print immediate result
            status = "✅ PASSED" if result.passed else "❌ FAILED"
            print(f"Result: {status}")
            
            if not result.passed:
                print("Failure reasons:")
                for reason in result.failure_reasons:
                    print(f"  - {reason}")
        
        # Print summary
        self._print_summary()
        
        return self.results
    
    def _run_single_test(self, test_case: TestCase) -> TestResult:
        """Run a single test case"""
        try:
            # Execute agent
            print(f"Input: {test_case.input_message[:100]}...")
            agent_response = registry_agent.run_sync(test_case.input_message)
            
            # Validate results
            validation_results = {}
            all_errors = []
            
            # Validate execution path
            path_valid, path_errors = Phase1Validator.validate_execution_path(
                test_case.expected_path, agent_response.output
            )
            validation_results["execution_path"] = {"valid": path_valid, "errors": path_errors}
            all_errors.extend(path_errors)
            
            # Validate final entity
            entity_valid, entity_errors = Phase1Validator.validate_final_entity(
                test_case.expected_final_entity_type, test_case.expected_entity_attributes, agent_response.output
            )
            validation_results["final_entity"] = {"valid": entity_valid, "errors": entity_errors}
            all_errors.extend(entity_errors)
            
            # Validate goal interpretation
            goal_valid, goal_errors = Phase1Validator.validate_goal_interpretation(
                test_case, agent_response.output
            )
            validation_results["goal_interpretation"] = {"valid": goal_valid, "errors": goal_errors}
            all_errors.extend(goal_errors)
            
            # Overall pass/fail
            passed = path_valid and entity_valid and goal_valid
            
            return TestResult(
                test_case=test_case,
                agent_response=agent_response.output,
                validation_results=validation_results,
                passed=passed,
                failure_reasons=all_errors
            )
            
        except Exception as e:
            return TestResult(
                test_case=test_case,
                agent_response=None,
                validation_results={"error": str(e)},
                passed=False,
                failure_reasons=[f"Test execution failed: {str(e)}"]
            )
    
    def _print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 60)
        print("📊 PHASE 1 TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for r in self.results if r.passed)
        total = len(self.results)
        
        print(f"Tests Passed: {passed}/{total} ({passed/total*100:.1f}%)")
        
        if passed < total:
            print("\n❌ Failed Tests:")
            for result in self.results:
                if not result.passed:
                    print(f"  - {result.test_case.name}: {result.failure_reasons[0] if result.failure_reasons else 'Unknown error'}")
        
        print(f"\n🎯 Path Selection Intelligence: {'PASSED' if passed == total else 'NEEDS IMPROVEMENT'}")


# ================================
# MAIN EXECUTION
# ================================

if __name__ == "__main__":
    runner = Phase1TestRunner()
    results = runner.run_all_tests()
    
    # Optional: Print detailed results for debugging
    print("\n" + "=" * 60)
    print("🔍 DETAILED RESULTS (for debugging)")
    print("=" * 60)
    
    for result in results:
        print(f"\n{result.test_case.name}:")
        if result.agent_response:
            print(f"  Goal Completed: {result.agent_response.goal_completed}")
            print(f"  Primary Action: {result.agent_response.primary_action}")
            print(f"  Functions Used: {result.agent_response.functions_used}")
            print(f"  Entity IDs: {result.agent_response.entity_ids_referenced}")
            print(f"  Summary: {result.agent_response.summary[:150]}...")
        else:
            print(f"  ERROR: No agent response (test execution failed)")
            print(f"  Failure Reasons: {result.failure_reasons}")