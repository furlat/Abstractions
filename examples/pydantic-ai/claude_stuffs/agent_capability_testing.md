# Agent Capability Testing: Progressive Multi-Step Reasoning

## Overview

This document outlines a comprehensive testing framework for evaluating the pydantic-ai agent's ability to use the Abstractions Entity Framework for complex, multi-step problem solving. We test the agent's capacity for logical sequencing, path selection, composition patterns, and goal-oriented reasoning.

## Testing Philosophy

### Core Capabilities Being Tested

1. **Path Selection Intelligence**: Can the agent choose different execution paths for the same input based on different goals?
2. **Multi-Step Composition**: Can the agent chain functions together using address patterns?
3. **Distractor Resistance**: Can the agent ignore irrelevant functions and focus on goal-relevant operations?
4. **Goal Validation**: Can we automatically verify that the agent achieved the intended goal?
5. **Context Awareness**: Does the agent understand when to use direct execution vs. complex composition?

### Interesting Domain: Cybersecurity Incident Response

Instead of boring student/course examples, we'll use a cybersecurity incident response scenario that requires:
- **Intelligence gathering** (scanning, analysis)
- **Threat assessment** (scoring, classification) 
- **Response planning** (containment, remediation)
- **Evidence collection** (forensics, reporting)

This domain naturally requires multi-step reasoning and has clear success/failure criteria.

## Test Suite Architecture

### Phase 1: Basic Path Selection
**Goal**: Test if agent can choose different execution sequences for same input

### Phase 2: Complex Composition
**Goal**: Test if agent can use address patterns to compose results from multiple functions

### Phase 3: Distractor Handling
**Goal**: Test if agent can ignore irrelevant functions and focus on goal-relevant operations

### Phase 4: Automatic Goal Validation
**Goal**: Test if we can programmatically verify goal achievement

---

## Phase 1: Basic Path Selection Tests

### Scenario: Network Security Alert Processing

**Domain Setup**: We have a network security alert that needs to be processed. Depending on the urgency/goal, we need different processing paths.

#### Function Registry:
```python
# Raw data ingestion
@register("ingest_alert")
def ingest_alert(raw_alert: str) -> SecurityAlert:
    """Convert raw alert string into structured SecurityAlert entity"""

# Analysis paths
@register("quick_scan") 
def quick_scan(alert: SecurityAlert) -> ThreatAssessment:
    """Fast threat assessment for low-priority alerts"""

@register("deep_analysis")
def deep_analysis(alert: SecurityAlert) -> DetailedThreatReport:
    """Comprehensive analysis for high-priority alerts"""

# Response paths  
@register("auto_contain")
def auto_contain(assessment: ThreatAssessment) -> ContainmentAction:
    """Automated containment for routine threats"""

@register("manual_escalation")
def manual_escalation(report: DetailedThreatReport) -> EscalationTicket:
    """Manual escalation for complex threats"""

@register("create_incident")
def create_incident(report: DetailedThreatReport) -> SecurityIncident:
    """Create formal incident for critical threats"""
```

#### Test Case 1A: Routine Threat Processing
**Input**: `"Process this network alert: suspicious_login_attempt.json for routine handling"`
**Expected Path**: `ingest_alert → quick_scan → auto_contain`
**Goal Validation**: ContainmentAction entity created with status="automated"

#### Test Case 1B: Critical Threat Processing  
**Input**: `"Process this network alert: suspicious_login_attempt.json for critical incident response"`
**Expected Path**: `ingest_alert → deep_analysis → create_incident`
**Goal Validation**: SecurityIncident entity created with severity="critical"

#### Test Case 1C: Escalation Processing
**Input**: `"Process this network alert: suspicious_login_attempt.json but I need human review"`
**Expected Path**: `ingest_alert → deep_analysis → manual_escalation`
**Goal Validation**: EscalationTicket entity created with human_review_required=true

### What This Tests:
- **Context Understanding**: Same input, different processing goals
- **Function Selection**: Choosing appropriate analysis depth
- **Goal Interpretation**: Understanding "routine", "critical", "human review" implications
- **Path Planning**: Multi-step sequence planning

---

## Phase 2: Complex Composition Tests

### Scenario: Threat Intelligence Fusion

**Domain Setup**: Agent must gather intelligence from multiple sources and compose them into a unified threat profile.

#### Function Registry:
```python
# Intelligence gathering
@register("scan_network_logs")
def scan_network_logs(target_ip: str) -> NetworkIntelligence:
    """Analyze network traffic for IP address"""

@register("query_threat_db")
def query_threat_db(target_ip: str) -> ThreatDatabaseRecord:
    """Look up IP in threat intelligence database"""

@register("analyze_geolocation")
def analyze_geolocation(target_ip: str) -> GeolocationData:
    """Get geographic and ISP information for IP"""

# Composition functions (use address patterns)
@register("create_threat_profile")
def create_threat_profile(
    network_intel_ref: str,  # @uuid.field reference
    threat_db_ref: str,      # @uuid.field reference  
    geo_data_ref: str        # @uuid.field reference
) -> ComprehensiveThreatProfile:
    """Compose multiple intelligence sources into unified profile"""

@register("calculate_risk_score")
def calculate_risk_score(
    threat_profile_ref: str  # @uuid.comprehensive_score
) -> RiskAssessment:
    """Calculate composite risk score from threat profile"""
```

#### Test Case 2A: Parallel Intelligence Gathering + Composition
**Input**: `"Create comprehensive threat analysis for IP 192.168.1.100"`

**Expected Sequence**:
1. **Parallel Execution**: 
   - `scan_network_logs(target_ip="192.168.1.100")` → NetworkIntelligence entity
   - `query_threat_db(target_ip="192.168.1.100")` → ThreatDatabaseRecord entity  
   - `analyze_geolocation(target_ip="192.168.1.100")` → GeolocationData entity

2. **Address-Pattern Composition**:
   - `create_threat_profile(network_intel_ref="@{net_uuid}.traffic_patterns", threat_db_ref="@{threat_uuid}.reputation_score", geo_data_ref="@{geo_uuid}.location_risk")`

3. **Final Analysis**:
   - `calculate_risk_score(threat_profile_ref="@{profile_uuid}.comprehensive_score")`

**Goal Validation**: RiskAssessment entity with composite_score > 0

#### Test Case 2B: Conditional Composition Based on Results
**Input**: `"Analyze IP 10.0.0.50 and if high risk, create incident response plan"`

**Expected Logic**:
1. Gather intelligence (parallel)
2. Create threat profile  
3. Calculate risk score
4. **Conditional**: If risk_score > 7.0, execute `create_response_plan(@{risk_uuid}.threat_indicators)`

**Goal Validation**: Either RiskAssessment (if low risk) OR ResponsePlan (if high risk)

### What This Tests:
- **Parallel Execution**: Running multiple functions simultaneously
- **Address Pattern Usage**: Using @uuid.field syntax for composition
- **Data Flow Understanding**: How outputs become inputs in next step
- **Conditional Logic**: Making decisions based on intermediate results

---

## Phase 3: Distractor Handling Tests

### Scenario: Incident Response with Noise

**Domain Setup**: Registry contains both relevant and irrelevant functions. Agent must ignore distractors.

#### Function Registry (Relevant + Distractors):
```python
# RELEVANT: Incident response functions
@register("analyze_malware")
def analyze_malware(sample: str) -> MalwareReport:
    """Analyze malware sample for incident response"""

@register("contain_threat") 
def contain_threat(malware_report: MalwareReport) -> ContainmentStatus:
    """Contain identified threat"""

@register("collect_evidence")
def collect_evidence(malware_report: MalwareReport) -> ForensicEvidence:
    """Collect forensic evidence for legal proceedings"""

# DISTRACTORS: Unrelated functions
@register("update_employee_database")  # HR function
@register("process_purchase_order")    # Finance function  
@register("schedule_maintenance")      # IT ops function
@register("send_marketing_email")      # Marketing function
@register("backup_database")          # Backup function
@register("generate_payroll")         # Payroll function
```

#### Test Case 3A: Signal vs Noise (6 Distractors)
**Input**: `"We found malware sample 'trojan.exe' - analyze it and contain the threat"`
**Expected Path**: `analyze_malware → contain_threat` (ignore all 6 distractors)
**Goal Validation**: ContainmentStatus entity created, no irrelevant entities

#### Test Case 3B: Legal Evidence Collection (6 Distractors)  
**Input**: `"Analyze malware 'ransomware.bin' and prepare evidence for legal action"`
**Expected Path**: `analyze_malware → collect_evidence` (ignore distractors)
**Goal Validation**: ForensicEvidence entity with legal_admissible=true

#### Test Case 3C: Complete Investigation (12 Distractors)
**Input**: `"Full investigation of malware 'apt.dll' - analyze, contain, and collect evidence"`
**Expected Path**: `analyze_malware → contain_threat → collect_evidence(@{malware_uuid}.indicators)`
**Goal Validation**: All three entities created, no distractor functions called

### What This Tests:
- **Focus Under Noise**: Ignoring irrelevant functions
- **Goal-Function Alignment**: Understanding which functions serve the goal
- **Semantic Understanding**: Distinguishing cybersecurity from HR/finance/etc.
- **Distractor Scaling**: Performance with increasing noise levels

---

## Phase 4: Automatic Goal Validation

### Validation Strategy Framework

#### Level 1: Entity Existence Validation
```python
def validate_entity_exists(entity_type: Type[Entity], required_fields: Dict[str, Any]) -> bool:
    """Verify entity of correct type exists with required field values"""
```

#### Level 2: Execution Path Validation  
```python
def validate_execution_path(expected_functions: List[str], actual_functions: List[str]) -> bool:
    """Verify correct functions were called in right sequence"""
```

#### Level 3: Data Flow Validation
```python  
def validate_data_flow(entity_graph: EntityGraph, expected_references: Dict[str, str]) -> bool:
    """Verify address patterns were used correctly for data composition"""
```

#### Level 4: Goal State Validation
```python
def validate_goal_achieved(goal_criteria: Dict[str, Any], final_entities: List[Entity]) -> bool:
    """Verify the ultimate goal state was achieved"""
```

### Comprehensive Test Cases

#### Test Case 4A: Multi-Step Validation
**Scenario**: Critical incident response
**Goal**: `"Respond to zero-day exploit targeting our web servers"`

**Expected Execution**:
1. `analyze_exploit(target="web_servers")` → ExploitAnalysis
2. `assess_impact(exploit_ref="@{analysis_uuid}.vulnerability_details")` → ImpactAssessment  
3. `deploy_patches(impact_ref="@{impact_uuid}.affected_systems")` → PatchDeployment
4. `create_incident(patch_ref="@{patch_uuid}.deployment_status")` → SecurityIncident

**Validation Layers**:
- **L1**: SecurityIncident exists with status="resolved"
- **L2**: Functions called in correct order [analyze→assess→deploy→create]  
- **L3**: Address references used correctly between steps
- **L4**: All affected systems patched AND incident documented

#### Test Case 4B: Parallel + Sequential Validation
**Scenario**: Advanced persistent threat (APT) investigation
**Goal**: `"Investigate APT group infiltration across multiple attack vectors"`

**Expected Execution**:
1. **Parallel**: 
   - `analyze_network_traffic()` → NetworkAnalysis
   - `examine_email_headers()` → EmailAnalysis
   - `investigate_file_system()` → FileSystemAnalysis

2. **Sequential**:
   - `correlate_indicators(net_ref="@{net_uuid}.iocs", email_ref="@{email_uuid}.iocs", fs_ref="@{fs_uuid}.iocs")` → CorrelatedIOCs
   - `attribute_attack(iocs_ref="@{corr_uuid}.attack_patterns")` → AttackAttribution
   - `generate_report(attribution_ref="@{attr_uuid}.threat_actor")` → APTReport

**Validation Layers**:
- **L1**: APTReport exists with threat_actor identified
- **L2**: Parallel execution confirmed, then sequential composition
- **L3**: All address patterns resolve correctly  
- **L4**: Attack attribution confidence > 85%

---

## Test Execution Framework

### Automated Test Runner
```python
class AgentCapabilityTestSuite:
    def __init__(self, agent: Agent, registry: CallableRegistry):
        self.agent = agent
        self.registry = registry
        self.test_results = []
    
    def run_phase_1_tests(self) -> List[TestResult]:
        """Path selection tests"""
        
    def run_phase_2_tests(self) -> List[TestResult]:
        """Composition tests"""
        
    def run_phase_3_tests(self) -> List[TestResult]:
        """Distractor handling tests"""
    
    def run_phase_4_tests(self) -> List[TestResult]:
        """Full validation tests"""
    
    def generate_capability_report(self) -> CapabilityReport:
        """Comprehensive analysis of agent capabilities"""
```

### Success Metrics

#### Quantitative Metrics:
- **Path Accuracy**: % of tests where agent chose correct execution path
- **Function Precision**: % of relevant functions called / total functions called  
- **Goal Achievement**: % of tests where final goal state was achieved
- **Distractor Resistance**: % of irrelevant functions avoided
- **Composition Correctness**: % of address patterns used correctly

#### Qualitative Analysis:
- **Reasoning Quality**: Does agent explain its path selection?
- **Error Recovery**: How does agent handle intermediate failures?
- **Adaptability**: Can agent adjust strategy based on intermediate results?

---

## Expected Outcomes

### Agent Capability Levels

#### Level 1: Basic Sequencing
- ✅ Can execute single-step functions
- ✅ Can choose between 2-3 function options
- ❌ Limited multi-step planning

#### Level 2: Path Selection  
- ✅ Can choose different paths for different goals
- ✅ Basic multi-step sequences (2-3 steps)
- ❌ Complex composition patterns

#### Level 3: Advanced Composition
- ✅ Uses address patterns for data flow
- ✅ Parallel + sequential execution
- ✅ Conditional logic based on results
- ❌ Complex conditional branching

#### Level 4: Expert System
- ✅ Complex multi-step planning (5+ steps)
- ✅ Dynamic strategy adjustment
- ✅ High distractor resistance
- ✅ Near-perfect goal achievement

### Research Questions Answered

1. **Can LLM agents effectively use sophisticated entity frameworks for complex reasoning?**
2. **How does function registry size affect agent performance?**
3. **What types of composition patterns are learnable vs. require explicit instruction?**
4. **How can we measure and improve agent "focus" in noisy environments?**

This testing framework will provide deep insights into the practical capabilities of AI agents when paired with sophisticated functional data processing systems like the Abstractions Entity Framework.