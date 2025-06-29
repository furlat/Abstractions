"""
Phase 4 Integration Example: Multi-Entity Returns with Enhanced Callable Registry

This demonstrates the complete Phase 4 integration featuring:

- Phase 2 return analysis and multi-entity unpacking
- Phase 3 ConfigEntity patterns with functools.partial execution
- Advanced sibling relationship tracking
- Enhanced execution metadata and audit trails
- Complete semantic detection for all output patterns
- Performance tracking and analysis
"""

import sys
sys.path.append('..')

from typing import List, Tuple
from pydantic import BaseModel
from uuid import uuid4
import time

# Import our enhanced entity system
from abstractions.ecs.entity import Entity, EntityRegistry, ConfigEntity, FunctionExecution
from abstractions.ecs.callable_registry import CallableRegistry

print("🚀 Phase 4 Integration: Multi-Entity Returns Demo")
print("=" * 60)

# Define entities for comprehensive testing
class StudentProfile(Entity):
    """Enhanced student entity."""
    name: str = ""
    major: str = ""
    gpa: float = 0.0
    credits: int = 0

class AcademicAnalysis(Entity):
    """Analysis result entity."""
    overall_score: float = 0.0
    strengths: List[str] = []
    weaknesses: List[str] = []
    predicted_graduation: bool = True

class Recommendation(Entity):
    """Recommendation entity."""
    action: str = ""
    priority: int = 1
    description: str = ""
    estimated_impact: float = 0.0

class PerformanceMetrics(Entity):
    """Performance tracking entity."""
    trend: str = "stable"  # "improving", "stable", "declining"
    velocity: float = 0.0
    confidence: float = 0.5

# ConfigEntity for advanced analysis
class AdvancedAnalysisConfig(ConfigEntity):
    """Configuration for advanced analysis."""
    depth: str = "standard"  # "basic", "standard", "deep"
    include_recommendations: bool = True
    threshold: float = 3.0
    max_recommendations: int = 3

# Multi-entity return functions showcasing Phase 4 capabilities

@CallableRegistry.register("comprehensive_student_analysis")
def analyze_student_comprehensive(
    student: StudentProfile, 
    config: AdvancedAnalysisConfig
) -> Tuple[AcademicAnalysis, List[Recommendation], PerformanceMetrics]:
    """
    Comprehensive student analysis returning multiple related entities.
    
    This showcases Phase 4's multi-entity unpacking with:
    - Tuple of different entity types
    - List of entities within the tuple
    - Complete sibling relationship tracking
    """
    
    # Create academic analysis
    analysis = AcademicAnalysis(
        overall_score=student.gpa * config.threshold,
        strengths=["Strong GPA"] if student.gpa > 3.5 else [],
        weaknesses=["Low GPA"] if student.gpa < 3.0 else [],
        predicted_graduation=student.credits > 90 and student.gpa > 2.0
    )
    
    # Create recommendations based on analysis
    recommendations = []
    if config.include_recommendations:
        if student.gpa < config.threshold:
            recommendations.append(Recommendation(
                action="study_improvement",
                priority=1,
                description="Focus on improving study habits",
                estimated_impact=0.5
            ))
        
        if student.credits < 120:
            recommendations.append(Recommendation(
                action="credit_planning", 
                priority=2,
                description="Plan remaining credit requirements",
                estimated_impact=0.3
            ))
    
    # Create performance metrics
    metrics = PerformanceMetrics(
        trend="improving" if student.gpa > 3.0 else "needs_attention",
        velocity=student.gpa / max(student.credits / 30, 1),  # GPA per year estimate
        confidence=0.8 if analysis.predicted_graduation else 0.4
    )
    
    return analysis, recommendations, metrics

@CallableRegistry.register("batch_student_processing")
def process_student_batch(
    students: List[StudentProfile],
    config: AdvancedAnalysisConfig
) -> List[Tuple[StudentProfile, AcademicAnalysis]]:
    """
    Process multiple students returning nested entity structures.
    
    This demonstrates complex return patterns with:
    - List of tuples containing entities
    - Nested entity relationships
    - Batch processing capabilities
    """
    results = []
    
    for student in students:
        # Modify student (potential mutation)
        if student.gpa < 2.0:
            student.gpa = min(student.gpa + 0.2, 4.0)  # Grade boost
        
        # Create analysis for each student
        analysis = AcademicAnalysis(
            overall_score=student.gpa * config.threshold,
            predicted_graduation=student.gpa > 2.0
        )
        
        results.append((student, analysis))
    
    return results

@CallableRegistry.register("single_analysis_with_metrics")
def analyze_with_performance_tracking(
    student: StudentProfile,
    depth: str = "standard",
    include_metrics: bool = True
) -> Tuple[AcademicAnalysis, PerformanceMetrics]:
    """
    Analysis with automatic ConfigEntity creation and performance tracking.
    
    Showcases:
    - Dynamic ConfigEntity creation from primitives
    - Performance metadata collection
    - Dual-entity return pattern
    """
    
    analysis = AcademicAnalysis(
        overall_score=student.gpa * 3.5,
        strengths=["Consistent performance"] if student.gpa > 3.0 else [],
        predicted_graduation=student.credits > 60
    )
    
    metrics = PerformanceMetrics(
        trend="improving" if student.gpa > 3.0 else "stable",
        velocity=student.gpa / 4.0,  # Normalized velocity
        confidence=0.9 if include_metrics else 0.5
    )
    
    return analysis, metrics

@CallableRegistry.register("create_recommendation_list")
def generate_recommendations(
    student: StudentProfile,
    count: int = 3,
    focus_area: str = "academic"
) -> List[Recommendation]:
    """
    Generate list of recommendations.
    
    Demonstrates:
    - List of entities return pattern
    - Sibling relationship tracking within lists
    - Dynamic entity creation
    """
    recommendations = []
    
    for i in range(count):
        if focus_area == "academic":
            action = f"academic_improvement_{i}"
            description = f"Academic recommendation #{i+1}"
        else:
            action = f"general_improvement_{i}"
            description = f"General recommendation #{i+1}"
            
        rec = Recommendation(
            action=action,
            priority=i + 1,
            description=description,
            estimated_impact=0.8 - (i * 0.1)
        )
        recommendations.append(rec)
    
    return recommendations

# Create test entities
print("\n📚 Creating test entities...")

student1 = StudentProfile(
    name="Alice Johnson",
    major="Computer Science", 
    gpa=3.2,
    credits=85
)
student1.promote_to_root()
print(f"✅ Created student 1: {student1.name} (ID: {student1.ecs_id})")

student2 = StudentProfile(
    name="Bob Smith",
    major="Mathematics",
    gpa=2.8,
    credits=95
)
student2.promote_to_root()
print(f"✅ Created student 2: {student2.name} (ID: {student2.ecs_id})")

student3 = StudentProfile(
    name="Carol Davis",
    major="Physics",
    gpa=3.6,
    credits=110
)
student3.promote_to_root()
print(f"✅ Created student 3: {student3.name} (ID: {student3.ecs_id})")

# Create configuration entity
config = AdvancedAnalysisConfig(
    depth="deep",
    include_recommendations=True,
    threshold=2.5,
    max_recommendations=5
)
config.promote_to_root()
print(f"✅ Created analysis config: {config.ecs_id}")

print("\n🎯 Demonstrating Phase 4 Multi-Entity Returns...")

# Example 1: Multi-entity tuple unpacking
print("\n1. Multi-Entity Tuple Unpacking:")
print("   Function returns: Tuple[AcademicAnalysis, List[Recommendation], PerformanceMetrics]")

start_time = time.time()
analysis, recommendations, metrics = CallableRegistry.execute(
    "comprehensive_student_analysis",
    student=student1,
    config=config
)
execution_time = time.time() - start_time

print(f"✅ Execution completed in {execution_time:.4f}s")
print(f"📊 Analysis score: {analysis.overall_score:.2f}")
print(f"📋 Recommendations count: {len(recommendations)}")
print(f"📈 Performance trend: {metrics.trend}")

# Demonstrate sibling relationships
print(f"\n🔗 Sibling Relationships:")
print(f"   Analysis siblings: {len(analysis.sibling_output_entities)} entities")
print(f"   Metrics siblings: {len(metrics.sibling_output_entities)} entities")
print(f"   Same execution ID: {analysis.derived_from_execution_id == metrics.derived_from_execution_id}")

# Check execution metadata
execution_id = analysis.derived_from_execution_id
execution_record = EntityRegistry.get_live_entity(execution_id)

print(f"\n📝 Enhanced Execution Metadata:")
print(f"   Function: {execution_record.function_name}")
print(f"   Duration: {execution_record.execution_duration:.4f}s")
print(f"   Was unpacked: {execution_record.was_unpacked}")
print(f"   Output count: {execution_record.entity_count_output}")
print(f"   Semantic classifications: {execution_record.semantic_classifications}")
print(f"   Sibling groups: {len(execution_record.sibling_groups)} groups")
print(f"   Execution pattern: {execution_record.execution_pattern}")

# Example 2: Dynamic ConfigEntity creation
print("\n2. Dynamic ConfigEntity Creation:")
print("   Function parameters automatically create ConfigEntity")

analysis2, metrics2 = CallableRegistry.execute(
    "single_analysis_with_metrics",
    student=student2,
    depth="detailed",
    include_metrics=True
)

print(f"✅ Dynamic ConfigEntity execution completed")
print(f"📊 Analysis score: {analysis2.overall_score:.2f}")
print(f"📈 Metrics confidence: {metrics2.confidence:.2f}")

# Check that this created a ConfigEntity
execution_id2 = analysis2.derived_from_execution_id
execution_record2 = EntityRegistry.get_live_entity(execution_id2)
print(f"   ConfigEntity IDs tracked: {len(execution_record2.config_entity_ids)}")

# Example 3: List of entities unpacking
print("\n3. List of Entities Unpacking:")
print("   Function returns: List[Recommendation]")

recommendation_list = CallableRegistry.execute(
    "create_recommendation_list",
    student=student3,
    count=4,
    focus_area="academic"
)

print(f"✅ Generated {len(recommendation_list)} recommendations")

# Check sibling relationships in list
for i, rec in enumerate(recommendation_list):
    siblings_count = len(rec.sibling_output_entities)
    print(f"   Recommendation {i+1}: {rec.action} (siblings: {siblings_count})")

# Example 4: Batch processing with complex returns
print("\n4. Batch Processing with Nested Returns:")
print("   Function returns: List[Tuple[StudentProfile, AcademicAnalysis]]")

students = [student1, student2, student3]
batch_results = CallableRegistry.execute(
    "batch_student_processing",
    students=students,
    config=config
)

print(f"✅ Processed {len(batch_results)} students")
for i, (student_result, analysis_result) in enumerate(batch_results):
    print(f"   Student {i+1}: {student_result.name} -> Score: {analysis_result.overall_score:.2f}")

# Registry statistics
print("\n📊 Enhanced Registry Statistics:")
total_entities = len(EntityRegistry.live_id_registry)
function_executions = len([e for e in EntityRegistry.live_id_registry.values() 
                          if isinstance(e, FunctionExecution)])
multi_entity_executions = len([e for e in EntityRegistry.live_id_registry.values() 
                              if isinstance(e, FunctionExecution) and e.was_unpacked])

print(f"   Total entities: {total_entities}")
print(f"   Function executions: {function_executions}")
print(f"   Multi-entity executions: {multi_entity_executions}")
print(f"   Trees tracked: {len(EntityRegistry.tree_registry)}")
print(f"   Lineages tracked: {len(EntityRegistry.lineage_registry)}")

# Performance analysis
print("\n⚡ Performance Analysis:")
all_executions = [e for e in EntityRegistry.live_id_registry.values() 
                 if isinstance(e, FunctionExecution) and e.execution_duration]

if all_executions:
    avg_duration = sum(e.execution_duration for e in all_executions) / len(all_executions)
    max_duration = max(e.execution_duration for e in all_executions)
    min_duration = min(e.execution_duration for e in all_executions)
    
    print(f"   Average execution time: {avg_duration:.4f}s")
    print(f"   Fastest execution: {min_duration:.4f}s")
    print(f"   Slowest execution: {max_duration:.4f}s")

# Demonstrate backward compatibility
print("\n🔄 Backward Compatibility Test:")
print("   Testing single-entity return with enhanced processing")

@CallableRegistry.register("simple_analysis")
def simple_student_analysis(student: StudentProfile) -> AcademicAnalysis:
    """Simple function returning single entity."""
    return AcademicAnalysis(
        overall_score=student.gpa * 3.0,
        predicted_graduation=student.gpa > 2.5
    )

simple_result = CallableRegistry.execute("simple_analysis", student=student1)
print(f"✅ Single-entity function works: {simple_result.overall_score:.2f}")

# Function registry capabilities
print("\n🎯 Enhanced Function Registry:")
functions = CallableRegistry.list_functions()
for func_name in functions:
    metadata = CallableRegistry.get_metadata(func_name)
    if metadata and hasattr(metadata, 'supports_unpacking'):
        unpacking_support = "✅ Multi-entity" if metadata.supports_unpacking else "📄 Single-entity"
        expected_count = metadata.expected_output_count
        print(f"   {func_name}: {unpacking_support} (expected: {expected_count})")

print("\n✨ Phase 4 Integration Demo Complete!")
print("🚀 Multi-entity returns working with full semantic detection!")
print("🔗 Sibling relationships tracked for complete audit trails!")
print("📊 Enhanced execution metadata provides deep insights!")
print("⚡ Performance tracking enables optimization!")
print("🎯 Backward compatibility maintained with existing functions!")

# Demonstrate querying capabilities
print("\n🔍 Advanced Querying Capabilities:")

# Find all entities derived from a specific function
analysis_entities = [e for e in EntityRegistry.live_id_registry.values() 
                    if isinstance(e, AcademicAnalysis) and 
                    hasattr(e, 'derived_from_function') and 
                    e.derived_from_function]

print(f"   Analysis entities created by functions: {len(analysis_entities)}")

# Find sibling groups
sibling_groups = [e for e in EntityRegistry.live_id_registry.values() 
                 if isinstance(e, FunctionExecution) and e.sibling_groups]

print(f"   Executions with sibling relationships: {len(sibling_groups)}")

# Find entities with multi-entity siblings
entities_with_siblings = [e for e in EntityRegistry.live_id_registry.values() 
                         if hasattr(e, 'sibling_output_entities') and 
                         e.sibling_output_entities]

print(f"   Entities with siblings: {len(entities_with_siblings)}")

print("\n🎉 Phase 4 integration provides unprecedented insight into function execution!")
print("📈 Complete audit trails from input entities through execution to output relationships!")