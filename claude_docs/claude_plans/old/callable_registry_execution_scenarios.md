# Callable Registry: Execution Scenarios & Edge Cases

## Introduction

This document explores concrete execution scenarios to validate the callable registry design. Each scenario demonstrates specific patterns, edge cases, and the expected behavior according to our design principles.

## Scenario 1: Pure Borrowing - Simple Data Composition

### **Function Definition**
```python
@CallableRegistry.register("calculate_gpa")
def calculate_gpa(grades: List[float], credit_hours: List[int], bonus: float = 0.0) -> float:
    """Calculate weighted GPA with optional bonus."""
    total_points = sum(g * h for g, h in zip(grades, credit_hours))
    total_hours = sum(credit_hours)
    return (total_points / total_hours) + bonus
```

### **Execution**
```python
result = execute("calculate_gpa", 
    grades="@student_record.grades",
    credit_hours="@student_record.credit_hours", 
    bonus=0.1
)
```

### **Expected Flow**
1. **Input Analysis**: String addresses + primitive parameter
2. **Composite Input Creation**: 
   - `InputEntity(grades=borrowed_list, credit_hours=borrowed_list, bonus=0.1)`
   - `attribute_source = {"grades": student_record_ecs_id, "credit_hours": student_record_ecs_id, "bonus": None}`
3. **Execution**: Function receives primitive values, returns float
4. **Output Analysis**: Non-entity result → wrap in `OutputEntity(result=3.85)`
5. **Functional Tracking**: `FunctionExecution` links input→function→output

### **Key Insights**
- Pure borrowing always creates new entities
- Parameter entity not needed for single primitive
- Complete provenance chain maintained

---

## Scenario 2: Entity + Parameters - Mixed Input Pattern

### **Function Definition**
```python
@CallableRegistry.register("update_student_status")
def update_student_status(student: Student, new_gpa: float, reason: str, effective_date: datetime) -> Student:
    """Update student with new GPA and status reason."""
    student.gpa = new_gpa
    student.status_reason = reason
    student.last_updated = effective_date
    return student
```

### **Execution**
```python
result = execute("update_student_status",
    student=live_student_entity,
    new_gpa=3.8,
    reason="Academic improvement",
    effective_date=datetime.now()
)
```

### **Expected Flow**
1. **Input Analysis**: Direct entity + 3 parameters
2. **Parameter Entity Creation**: 
   - `ParameterEntity(new_gpa=3.8, reason="Academic improvement", effective_date=datetime.now())`
3. **Composite Input Creation**:
   - `InputEntity(student=student, parameters=param_entity)`
4. **Isolation**: 
   - Get `stored_entity(student.root_ecs_id, student.ecs_id)` for execution
   - Disconnect live_student_entity from registry
5. **Execution**: Function modifies student copy, returns same object
6. **Output Analysis**: `result.live_id == execution_copy.live_id` → **MUTATION**
7. **Entity Operations**:
   - `result.update_ecs_ids()` (preserve lineage)
   - Register updated student
   - Version original student tree

### **Key Insights**
- Parameter entities enable clean mixed input handling
- Live_id comparison detects in-place mutation
- Original entity lineage preserved through mutation chain

---

## Scenario 3: Multi-Entity Unpacking - Student Record Split

### **Function Definition**
```python
@CallableRegistry.register("split_student_record")
def split_student_record(student: Student) -> Tuple[Student, AcademicRecord, FinancialRecord]:
    """Split student into separate domain records."""
    academic = AcademicRecord(
        student_id=student.student_id,
        grades=student.grades,
        gpa=student.gpa
    )
    financial = FinancialRecord(
        student_id=student.student_id,
        tuition_balance=student.tuition_balance,
        payment_history=student.payment_history
    )
    
    # Clean student entity
    student.grades = []
    student.gpa = 0.0
    student.tuition_balance = 0.0
    student.payment_history = []
    
    return student, academic, financial
```

### **Execution**
```python
result = execute("split_student_record", student=student_entity, unpack=True)
```

### **Expected Flow**
1. **Input Analysis**: Single entity input
2. **Execution**: Function creates new entities, modifies input
3. **Output Analysis**: `Tuple[Student, AcademicRecord, FinancialRecord]` with unpack=True
4. **live_id Detection**:
   - `student.live_id == execution_copy.live_id` → **MUTATION**
   - `academic.live_id ∉ input_live_ids` → **CREATION**  
   - `financial.live_id ∉ input_live_ids` → **CREATION**
5. **Unpacking Strategy**: 
   - Don't register packed tuple entity
   - Register each entity individually
   - Create `FunctionExecution` linking to all 3 outputs
6. **Sibling Relationships**:
   - All outputs get same `derived_from_execution_id`
   - `sibling_output_entities` lists other outputs
   - `output_index` indicates tuple position

### **Key Insights**
- Unpacking avoids unnecessary container entities
- Mixed semantic analysis (mutation + creation)
- Sibling tracking maintains output relationships

---

## Scenario 4: Tree Extraction - Returning Root + Child

### **Function Definition**
```python
@CallableRegistry.register("update_and_extract_grade")
def update_and_extract_grade(student: Student, course_id: str, new_grade: float) -> Tuple[Student, Grade]:
    """Update specific grade and return both student and the modified grade."""
    # Find and update the grade
    target_grade = None
    for grade in student.academic_record.grades:
        if grade.course_id == course_id:
            grade.score = new_grade
            grade.last_modified = datetime.now()
            target_grade = grade
            break
    
    # Recalculate student GPA
    student.gpa = calculate_new_gpa(student.academic_record.grades)
    
    return student, target_grade
```

### **Execution**
```python
result = execute("update_and_extract_grade", 
    student=student_entity, 
    course_id="CS101", 
    new_grade=95.0
)
```

### **Expected Flow**
1. **Input Analysis**: Entity + parameters (creates parameter entity)
2. **Execution**: Modifies both student and nested grade
3. **Output Analysis**: `Tuple[Student, Grade]`
4. **live_id Detection**:
   - `student.live_id == execution_copy.live_id` → **MUTATION**
   - `grade.live_id ∈ input_tree_live_ids` → **POTENTIAL DETACHMENT**
5. **Tree Analysis**: 
   - Build tree from returned student
   - Check if grade still exists in student's tree
   - Result: Grade still present → **IN-PLACE MODIFICATION** (not detachment)
6. **Registration**:
   - Version student entity (mutation detected)
   - Grade automatically versioned as part of student tree
   - Both outputs reference same execution

### **Key Insights**
- Tree analysis distinguishes detachment from in-place modification
- Child entity changes propagate through parent versioning
- Complex semantic analysis beyond simple live_id comparison

---

## Scenario 5: Ambiguous Child Extraction

### **Function Definition**
```python
@CallableRegistry.register("extract_best_grade")
def extract_best_grade(student: Student) -> Grade:
    """Extract the highest grade from student record."""
    best_grade = max(student.academic_record.grades, key=lambda g: g.score)
    return best_grade
```

### **Execution**
```python
result = execute("extract_best_grade", student=student_entity)
```

### **Expected Flow**
1. **Input Analysis**: Single entity input
2. **Execution**: Function returns existing grade from tree
3. **Output Analysis**: Single Grade entity
4. **live_id Detection**: `grade.live_id ∈ input_tree_live_ids` → **DETACHMENT**
5. **Ambiguity Resolution**: 
   - Could be detachment (grade removed from tree)
   - Could be in-place extraction (grade still in tree)
   - **Design Decision**: Always interpret as detachment for consistency
6. **Entity Operations**:
   - `grade.detach()` - promote to independent root
   - Update student tree to reflect removal
   - Version both student and extracted grade

### **Key Insights**
- Ambiguous cases need consistent interpretation rules
- Default to detachment maintains predictable semantics
- Clear separation between extraction and reference

---

## Scenario 6: Curried Function Execution

### **Function Definition**
```python
@CallableRegistry.register("grade_analysis")
def grade_analysis(grades: List[float], threshold: float, weight: float, bonus: float) -> Dict[str, float]:
    """Analyze grades with configurable parameters."""
    avg = sum(grades) / len(grades)
    weighted_avg = avg * weight + bonus
    above_threshold = len([g for g in grades if g >= threshold])
    
    return {
        "average": avg,
        "weighted_average": weighted_avg,
        "above_threshold_count": above_threshold,
        "pass_rate": above_threshold / len(grades)
    }
```

### **Parameter Entity Setup**
```python
# Pre-create reusable parameter configuration
analysis_params = ParameterEntity(threshold=85.0, weight=1.2, bonus=5.0)
analysis_params.promote_to_root()  # Cache in registry
```

### **Execution**
```python
result = execute("grade_analysis",
    grades="@student_record.final_grades",
    **analysis_params.model_dump(exclude_entity_fields=True)
)
```

### **Expected Flow**
1. **Input Analysis**: Address + cached parameters
2. **Parameter Reuse**: Reference existing parameter entity instead of creating new one
3. **Composite Input**: Links to both borrowed data and cached parameters
4. **Execution**: Standard borrowing pattern execution
5. **Functional Tracking**: Records reuse of cached parameter entity

### **Key Insights**
- Parameter entities enable efficient currying
- Cached parameters create reusable configuration patterns
- Function execution tracks parameter provenance

---

## Scenario 7: Cross-Tree Entity Processing

### **Function Definition**
```python
@CallableRegistry.register("compare_students")
def compare_students(student1: Student, student2: Student) -> ComparisonResult:
    """Compare two students from potentially different trees."""
    return ComparisonResult(
        gpa_difference=student1.gpa - student2.gpa,
        age_difference=student1.age - student2.age,
        better_performer=student1.student_id if student1.gpa > student2.gpa else student2.student_id
    )
```

### **Execution**
```python
result = execute("compare_students",
    student1=student_from_tree_a,  # Different root trees
    student2=student_from_tree_b
)
```

### **Expected Flow**
1. **Input Analysis**: Two entities from different trees
2. **Multi-Tree Handling**:
   - Create execution copies from both trees
   - Composite input entity references both
   - Track dependencies on multiple trees
3. **Execution**: Function accesses both entities
4. **Output Analysis**: New entity creation (comparison result)
5. **Multi-Tree Provenance**: 
   - Function execution tracks input from multiple trees
   - Output entity references both input lineages

### **Key Insights**
- Multi-tree operations require careful dependency tracking
- Cross-tree provenance more complex than single-tree scenarios
- Function execution becomes bridge between independent entity graphs

---

## Scenario 8: Null/Error Handling Edge Case

### **Function Definition**
```python
@CallableRegistry.register("safe_grade_calculation")
def safe_grade_calculation(student: Student, course_id: str) -> Optional[Grade]:
    """Safely extract grade, return None if not found."""
    if not student.academic_record or not student.academic_record.grades:
        return None
    
    for grade in student.academic_record.grades:
        if grade.course_id == course_id:
            return grade
    
    return None  # Not found
```

### **Execution**
```python
result = execute("safe_grade_calculation", 
    student=student_entity, 
    course_id="MISSING101"
)
```

### **Expected Flow**
1. **Input Analysis**: Entity + parameter
2. **Execution**: Function returns None
3. **Output Analysis**: `Optional[Grade]` with None result
4. **None Handling**:
   - Wrap in `OutputEntity(result=None)`
   - Or create special `NullResult` entity
   - Function execution still tracked even with null result
5. **Registration**: Output entity indicates null/missing result

### **Key Insights**
- Null results still need entity representation
- Function execution tracking independent of result content
- Optional types require special handling logic

---

## Scenario 9: Exception During Execution

### **Function Definition**
```python
@CallableRegistry.register("risky_calculation")
def risky_calculation(student: Student, divisor: float) -> float:
    """Calculation that might fail."""
    if divisor == 0:
        raise ValueError("Cannot divide by zero")
    
    return student.gpa / divisor
```

### **Execution**
```python
try:
    result = execute("risky_calculation", student=student_entity, divisor=0.0)
except Exception as e:
    print(f"Execution failed: {e}")
```

### **Expected Flow**
1. **Input Analysis**: Standard entity + parameter processing
2. **Execution**: Function raises ValueError
3. **Exception Handling**:
   - Create `FailedExecution` entity instead of normal output
   - Record error message, stack trace, input entity
   - Still create `FunctionExecution` entity (marked as failed)
4. **Registry State**: 
   - Input entity still registered (for audit trail)
   - Failed execution tracked for debugging
   - No output entity created

### **Key Insights**
- Failed executions still need complete tracking
- Error information becomes part of execution record
- Input processing completes even if function fails

---

## Scenario 10: Circular Reference Handling

### **Function Definition**
```python
@CallableRegistry.register("create_circular_ref")
def create_circular_ref(student: Student) -> Student:
    """Attempt to create circular reference (should be prevented)."""
    # This should be prevented by the entity system
    student.self_reference = student  # Circular reference
    return student
```

### **Execution**
```python
result = execute("create_circular_ref", student=student_entity)
```

### **Expected Flow**
1. **Input Analysis**: Standard entity processing
2. **Execution**: Function attempts circular reference
3. **Post-Execution Tree Analysis**:
   - `build_entity_tree(result)` detects circular reference
   - Raises `ValueError: "Circular entity reference detected"`
4. **Error Recovery**:
   - Function execution marked as failed
   - Original entity state preserved
   - Error details recorded in execution record

### **Key Insights**
- Entity system constraints enforced post-execution
- Circular references caught before registry corruption
- Failed constraint checks create execution failure records

---

## Scenario 11: Large-Scale Batch Processing

### **Function Definition**
```python
@CallableRegistry.register("bulk_grade_update")
def bulk_grade_update(students: List[Student], grade_adjustments: Dict[str, float]) -> List[Student]:
    """Update grades for multiple students."""
    updated_students = []
    for student in students:
        if student.student_id in grade_adjustments:
            adjustment = grade_adjustments[student.student_id]
            student.gpa += adjustment
            student.last_updated = datetime.now()
        updated_students.append(student)
    
    return updated_students
```

### **Execution**
```python
result = execute("bulk_grade_update",
    students=[student1, student2, student3, student4],
    grade_adjustments={"STU001": 0.1, "STU003": -0.05}
)
```

### **Expected Flow**
1. **Input Analysis**: List of entities + parameter dict
2. **Composite Input**: 
   - `InputEntity(students=entity_list, grade_adjustments=dict)`
   - Each student creates separate execution copy
3. **Execution**: Function modifies some students, not others
4. **Output Analysis**: `List[Student]` - should this unpack?
   - Design decision: List return types don't auto-unpack (unlike Tuple)
   - Create container entity with student list
5. **Individual Analysis**: 
   - Compare each output student with corresponding input
   - Mix of mutations (students 1&3) and no-ops (students 2&4)
6. **Batch Results**: Single function execution with complex multi-entity semantics

### **Key Insights**
- Batch operations create complex semantic analysis requirements
- List vs Tuple return types have different unpacking semantics
- Individual entity analysis within collection operations

---

## Scenario 12: Recursive Entity Processing

### **Function Definition**
```python
@CallableRegistry.register("flatten_course_hierarchy")
def flatten_course_hierarchy(course: Course) -> List[Course]:
    """Flatten nested course structure into linear list."""
    result = [course]
    for prerequisite in course.prerequisites:
        result.extend(flatten_course_hierarchy(prerequisite))  # Recursive call
    return result
```

### **Execution**
```python
result = execute("flatten_course_hierarchy", course=advanced_course)
```

### **Expected Flow**
1. **Input Analysis**: Single entity with nested tree structure
2. **Execution Complexity**: 
   - Recursive function calls within execution
   - Multiple entity references within same tree
   - Potential for deep nesting
3. **Output Analysis**: `List[Course]` with multiple entity references
4. **Entity Deduplication**:
   - Same course entity may appear multiple times in result
   - Need to handle duplicate live_ids in output analysis
5. **Tree Relationships**: 
   - Output list contains entities from input tree
   - All are references, not mutations or creations
   - Complex provenance: output derived from multiple input entities

### **Key Insights**
- Recursive functions create complex entity relationship patterns
- Output analysis must handle duplicate entity references
- Single function execution can reference many entities from input tree

---

## Edge Case Summary

### **Complex Detection Scenarios**
1. **Multi-entity outputs** with mixed semantics (mutation + creation + detachment)
2. **Tree extraction** requiring structural analysis beyond live_id comparison
3. **Cross-tree operations** with multiple dependency sources
4. **Ambiguous child extraction** requiring consistent interpretation rules

### **Error Handling Requirements**
1. **Exception during execution** - complete audit trail even on failure
2. **Constraint violations** - post-execution validation and rollback
3. **Null/missing results** - entity representation of absence

### **Performance Considerations**
1. **Batch operations** - efficient handling of multiple entity processing
2. **Recursive operations** - managing complex entity relationship graphs
3. **Large tree operations** - scalable tree analysis and versioning

### **Design Validation**
All scenarios demonstrate that the unified entity-centric approach with live_id detection can handle the full range of function execution patterns while maintaining complete audit trails and consistent semantics across diverse execution scenarios.