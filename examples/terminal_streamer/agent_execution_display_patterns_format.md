# Agent Execution Patterns - Only Existing Entity References

## Key Constraint: Agents Can Only Reference Existing Entities

The registry agent can ONLY pass string addresses to existing entities:
- `@uuid` = direct entity reference
- `@uuid.field` = borrowed field value
- Primitive values (strings, numbers, booleans)

**NO entity creation in tool calls - only references to existing entities in the registry. NO PRIMITIVE CREATION ONLY REFERENCE TO ENTITIES OR FIELDS**

---

## Pattern 1: Pure Field Borrowing (Single Entity Source)

**Registry Strategy**: `pure_borrowing`
**Agent Input**: Only `@uuid.field` addresses from same entity

```
⏱️  START: 2024-07-25T14:30:45.123Z

🚀 calculate_revenue_metrics(start_date: str, end_date: str) -> FunctionExecutionResult

📝 RAW TOOL CALL: {
   "start_date": "@a1b2c3d4-e5f6-7890-abcd-ef1234567890.start_date",
   "end_date": "@a1b2c3d4-e5f6-7890-abcd-ef1234567890.end_date"
}

🔍 RESOLVING:
   start_date: "@a1b2c3d4-e5f6-7890-abcd-ef1234567890.start_date" 
   → @DateRangeConfig|a1b2c3d4 : start_date = "2024-10-01"
   
   end_date: "@a1b2c3d4-e5f6-7890-abcd-ef1234567890.end_date"
   → @DateRangeConfig|a1b2c3d4 : end_date = "2024-12-31"

📥 FUNCTION CALL: calculate_revenue_metrics(start_date="2024-10-01", end_date="2024-12-31")

📤 OUTPUT: FunctionExecutionResult#f1e2d3c4-b5a6-9870-fedc-ba9876543210
   ├─ function_name: "calculate_revenue_metrics"
   ├─ success: true  
   ├─ result_data: {"total_revenue": 15750.50, "orders": 123}

[DateRangeConfig|a1b2c3d4-e5f6-7890-abcd-ef1234567890] ---> [calculate_revenue_metrics|exec-b5c6d7e8-f9a0-1b2c-3d4e-567890abcdef] ---> [FunctionExecutionResult|f1e2d3c4-b5a6-9870-fedc-ba9876543210]

⏱️  END: 2024-07-25T14:30:46.361Z
🔍 RESOLUTION: 3.2ms
📥 EXECUTION: 1,234.5ms  
✅ TOTAL: 1,237.7ms
```

---

## Pattern 2: Multi-Entity Field Borrowing (Different Entity Sources)

**Registry Strategy**: `pure_borrowing`
**Agent Input**: `@uuid.field` addresses from multiple entities

```
⏱️  START: 2024-07-25T14:30:47.890Z

🚀 compare_students(name1: str, name2: str, gpa1: float, gpa2: float) -> ComparisonResult

📝 RAW TOOL CALL: {
   "name1": "@student1-a1b2-c3d4-e5f6-789012345678.name",
   "name2": "@student2-b2c3-d4e5-f678-901234567890.name", 
   "gpa1": "@student1-a1b2-c3d4-e5f6-789012345678.gpa",
   "gpa2": "@student2-b2c3-d4e5-f678-901234567890.gpa"
}

🔍 RESOLVING:
   name1: "@student1-a1b2-c3d4-e5f6-789012345678.name"
   → @Student|student1 : name = "Alice"
   
   name2: "@student2-b2c3-d4e5-f678-901234567890.name"
   → @Student|student2 : name = "Bob"
   
   gpa1: "@student1-a1b2-c3d4-e5f6-789012345678.gpa"
   → @Student|student1 : gpa = 3.8
   
   gpa2: "@student2-b2c3-d4e5-f678-901234567890.gpa"
   → @Student|student2 : gpa = 3.2

📥 FUNCTION CALL: compare_students(name1="Alice", name2="Bob", gpa1=3.8, gpa2=3.2)

📤 OUTPUT: ComparisonResult#comp-c3d4-e5f6-7890-123456789012
   ├─ winner: "Alice"
   ├─ score_difference: 0.6
   ├─ comparison_type: "gpa_based"

[Student|student1-a1b2-c3d4-e5f6-789012345678, Student|student2-b2c3-d4e5-f678-901234567890] ---> [compare_students|exec-d4e5-f678-9012-345678901234] ---> [ComparisonResult|comp-c3d4-e5f6-7890-123456789012]

⏱️  END: 2024-07-25T14:30:48.355Z
🔍 RESOLUTION: 8.7ms
📥 EXECUTION: 456.2ms  
✅ TOTAL: 464.9ms
```

---

## Pattern 3: Direct Entity Reference (Single Entity)

**Registry Strategy**: `single_entity_direct`
**Agent Input**: `@uuid` (no field) to pass entire entity

```
⏱️  START: 2024-07-25T14:30:49.123Z

🚀 analyze_student(student: Student) -> AnalysisResult

📝 RAW TOOL CALL: {
   "student": "@s1a2b3c4-d5e6-7890-abcd-ef1234567890"
}

🔍 RESOLVING:
   student: "@s1a2b3c4-d5e6-7890-abcd-ef1234567890"
   → @Student|s1a2b3c4 [direct entity reference]

📥 FUNCTION CALL: analyze_student(student=Student|s1a2b3c4)

📤 OUTPUT: AnalysisResult#c3d4e5f6-a7b8-9012-cdef-345678901234
   ├─ student_id: "s1a2b3c4-d5e6-7890-abcd-ef1234567890"
   ├─ performance_level: "high"
   ├─ gpa_score: 3.8
   ├─ recommendation: "advanced_placement"

[Student|s1a2b3c4-d5e6-7890-abcd-ef1234567890] ---> [analyze_student|exec-c7d8e9f0-1a2b-3c4d-5e6f-789012345678] ---> [AnalysisResult|c3d4e5f6-a7b8-9012-cdef-345678901234]

⏱️  END: 2024-07-25T14:30:50.110Z
📥 EXECUTION: 987.3ms
✅ TOTAL: 987.3ms
```

---

## Pattern 4: Mixed Direct Entity + Field Borrowing

**Registry Strategy**: `mixed`
**Agent Input**: `@uuid` (entity) + `@uuid.field` (borrowed values)

```
⏱️  START: 2024-07-25T14:30:51.445Z

🚀 enroll_student(student: Student, course_name: str, credits: int) -> EnrollmentResult

📝 RAW TOOL CALL: {
   "student": "@s1a2b3c4-d5e6-7890-abcd-ef1234567890",
   "course_name": "@course123-4567-8901-2345-67890abcdef0.name",
   "credits": "@course123-4567-8901-2345-67890abcdef0.credits"
}

🔍 RESOLVING:
   student: "@s1a2b3c4-d5e6-7890-abcd-ef1234567890"
   → @Student|s1a2b3c4 [direct entity reference]
   
   course_name: "@course123-4567-8901-2345-67890abcdef0.name"
   → @Course|course123 : name = "Advanced Algorithms"
   
   credits: "@course123-4567-8901-2345-67890abcdef0.credits"
   → @Course|course123 : credits = 4

📥 FUNCTION CALL: enroll_student(student=Student|s1a2b3c4, course_name="Advanced Algorithms", credits=4)

📤 OUTPUT: EnrollmentResult#enr-e5f6-7890-1234-56789012345
   ├─ student_id: "s1a2b3c4-d5e6-7890-abcd-ef1234567890"
   ├─ course_name: "Advanced Algorithms"
   ├─ enrollment_date: "2024-07-25"
   ├─ credits_enrolled: 4

[Student|s1a2b3c4-d5e6-7890-abcd-ef1234567890, Course|course123-4567-8901-2345-67890abcdef0] ---> [enroll_student|exec-f678-9012-3456-789012345678] ---> [EnrollmentResult|enr-e5f6-7890-1234-56789012345]

⏱️  END: 2024-07-25T14:30:52.174Z
🔍 RESOLUTION: 5.4ms
📥 EXECUTION: 723.8ms  
✅ TOTAL: 729.2ms
```

---

## Pattern 5: Multiple Direct Entity References

**Registry Strategy**: `multi_entity_composite`
**Agent Input**: Multiple `@uuid` references (no fields)

```
⏱️  START: 2024-07-25T14:30:53.567Z

🚀 calculate_class_average(student1: Student, student2: Student, student3: Student) -> ClassStatistics

📝 RAW TOOL CALL: {
   "student1": "@s1a2b3c4-d5e6-7890-abcd-ef1234567890",
   "student2": "@s2b3c4d5-e6f7-8901-bcde-f23456789012",
   "student3": "@s3c4d5e6-f789-0123-cdef-34567890123a"
}

🔍 RESOLVING:
   student1: "@s1a2b3c4-d5e6-7890-abcd-ef1234567890"
   → @Student|s1a2b3c4 [direct entity reference]
   
   student2: "@s2b3c4d5-e6f7-8901-bcde-f23456789012"
   → @Student|s2b3c4d5 [direct entity reference]
   
   student3: "@s3c4d5e6-f789-0123-cdef-34567890123a"
   → @Student|s3c4d5e6 [direct entity reference]

📥 FUNCTION CALL: calculate_class_average(student1=Student|s1a2b3c4, student2=Student|s2b3c4d5, student3=Student|s3c4d5e6)

📤 OUTPUT: ClassStatistics#stats-f7a8-b9c0-d1e2-f34567890123
   ├─ class_average: 3.5
   ├─ student_count: 3
   ├─ highest_gpa: 3.8
   ├─ lowest_gpa: 3.2

[Student|s1a2b3c4-d5e6-7890-abcd-ef1234567890, Student|s2b3c4d5-e6f7-8901-bcde-f23456789012, Student|s3c4d5e6-f789-0123-cdef-34567890123a] ---> [calculate_class_average|exec-a789-0123-4567-890123456789] ---> [ClassStatistics|stats-f7a8-b9c0-d1e2-f34567890123]

⏱️  END: 2024-07-25T14:30:54.901Z
📥 EXECUTION: 1,334.2ms  
✅ TOTAL: 1,334.2ms
```

---

## Pattern 6: Same Entity In, Same Entity Out (Lineage Continuation - Mutation)

**Registry Strategy**: `single_entity_direct`
**Agent Input**: `@uuid` 
**Semantic**: `mutation` - Modifies input entity in-place

```
⏱️  START: 2024-07-25T14:30:55.445Z

🚀 update_student_gpa(student: Student) -> Student

📝 RAW TOOL CALL: {
   "student": "@s1a2b3c4-d5e6-7890-abcd-ef1234567890"
}

🔍 RESOLVING:
   student: "@s1a2b3c4-d5e6-7890-abcd-ef1234567890"
   → @Student|s1a2b3c4 [direct entity reference]
   

📥 FUNCTION CALL: update_student_gpa(student=Student|s1a2b3c4)

📤 OUTPUT: Student#s1a2b3c4-d5e6-7890-abcd-ef1234567890 [MUTATION - LINEAGE CONTINUED]
   ├─ name: "Alice Johnson"
   ├─ gpa: 3.9
   ├─ courses: ["CS101", "CS201"]

[Student|s1a2b3c4-d5e6-7890-abcd-ef1234567890] ---> [update_student_gpa|exec-b890-1234-5678-901234567890] ---> [Student|s1a2b3c4-d5e6-7890-abcd-ef1234567890 CONTINUED]

⏱️  END: 2024-07-25T14:30:56.123Z
📥 EXECUTION: 678.4ms  
✅ TOTAL: 678.4ms
```

---

## Pattern 7: Same Entity In, Multiple Entities Out (One Continues Lineage)

**Registry Strategy**: `single_entity_direct` with multi-entity unpacking
**Agent Input**: `@uuid` reference
**Semantic**: `mutation` for continued entity, `creation` for new entities

```
⏱️  START: 2024-07-25T14:30:57.234Z

🚀 split_student_record(student: Student) -> Tuple[Student, AcademicRecord]

📝 RAW TOOL CALL: {
   "student": "@s1a2b3c4-d5e6-7890-abcd-ef1234567890"
}

🔍 RESOLVING:
   student: "@s1a2b3c4-d5e6-7890-abcd-ef1234567890"
   → @Student|s1a2b3c4 [direct entity reference]

📥 FUNCTION CALL: split_student_record(student=Student|s1a2b3c4)

📤 UNPACKED OUTPUTS:
   ├─ Student#s1a2b3c4-d5e6-7890-abcd-ef1234567890 [index: 0] [MUTATION - LINEAGE CONTINUED]
   │  ├─ name: "Alice Johnson"
   │  ├─ gpa: 3.8
   │  └─ sibling_output_entities: ["rec-b3c4-d5e6-7890-123456789012"]
   │
   └─ AcademicRecord#rec-b3c4-d5e6-7890-123456789012 [index: 1] [CREATION - NEW ENTITY]
      ├─ student_id: "s1a2b3c4-d5e6-7890-abcd-ef1234567890"
      ├─ total_credits: 48
      ├─ graduation_eligible: true
      └─ sibling_output_entities: ["s1a2b3c4-d5e6-7890-abcd-ef1234567890"]

[Student|s1a2b3c4-d5e6-7890-abcd-ef1234567890] ---> [split_student_record|exec-c456-7890-1234-567890123456] ---> [Student|s1a2b3c4-d5e6-7890-abcd-ef1234567890 CONTINUED, AcademicRecord|rec-b3c4-d5e6-7890-123456789012 NEW]

⏱️  END: 2024-07-25T14:30:58.269Z
🔍 RESOLUTION: 2.3ms
📥 EXECUTION: 987.4ms
📦 UNPACKING: 45.2ms
✅ TOTAL: 1,034.9ms
```

---

## Pattern 8: Same Entity Type Out But Not Lineage Continuation (Creation)

**Registry Strategy**: `single_entity_direct`
**Agent Input**: `@uuid` reference
**Semantic**: `creation` - New entity of same type but different lineage

```
⏱️  START: 2024-07-25T14:30:59.567Z

🚀 create_similar_student(template: Student) -> Student

📝 RAW TOOL CALL: {
   "template": "@s1a2b3c4-d5e6-7890-abcd-ef1234567890"
}

🔍 RESOLVING:
   template: "@s1a2b3c4-d5e6-7890-abcd-ef1234567890"
   → @Student|s1a2b3c4 [direct entity reference]

📥 FUNCTION CALL: create_similar_student(template=Student|s1a2b3c4)

📤 OUTPUT: Student#new-d4e5-f678-9012-345678901234 [CREATION - NEW LINEAGE]
   ├─ name: "Alice Johnson Clone"
   ├─ gpa: 3.8
   ├─ courses: ["CS101", "CS201"]

[Student|s1a2b3c4-d5e6-7890-abcd-ef1234567890] ---> [create_similar_student|exec-e567-8901-2345-678901234567] ---> [Student|new-d4e5-f678-9012-345678901234 NEW]

⏱️  END: 2024-07-25T14:31:00.110Z
📥 EXECUTION: 543.2ms  
✅ TOTAL: 543.2ms
```

---

## Pattern 9: Multi-Entity Output (Tuple Return)

**Registry Strategy**: `single_entity_direct` with tuple unpacking
**Agent Input**: `@uuid` reference
**Semantic**: `creation` for all output entities

```
⏱️  START: 2024-07-25T14:31:01.445Z

🚀 analyze_performance(student: Student) -> Tuple[Assessment, Recommendation]

📝 RAW TOOL CALL: {
   "student": "@s1a2b3c4-d5e6-7890-abcd-ef1234567890"
}

🔍 RESOLVING:
   student: "@s1a2b3c4-d5e6-7890-abcd-ef1234567890"
   → @Student|s1a2b3c4 [direct entity reference]

📥 FUNCTION CALL: analyze_performance(student=Student|s1a2b3c4)

📤 UNPACKED OUTPUTS:
   ├─ Assessment#out001-2e3f-4a5b-6c7d-890123456789 [index: 0] [CREATION]
   │  ├─ student_id: "s1a2b3c4-d5e6-7890-abcd-ef1234567890"
   │  ├─ performance_level: "high"
   │  ├─ gpa_score: 3.8
   │  └─ sibling_output_entities: ["out002-3f4a-5b6c-7d8e-901234567890"]
   │
   └─ Recommendation#out002-3f4a-5b6c-7d8e-901234567890 [index: 1] [CREATION]
      ├─ student_id: "s1a2b3c4-d5e6-7890-abcd-ef1234567890"
      ├─ action: "advanced_placement"
      ├─ reasoning: "Strong performance across all metrics"
      └─ sibling_output_entities: ["out001-2e3f-4a5b-6c7d-890123456789"]

[Student|s1a2b3c4-d5e6-7890-abcd-ef1234567890] ---> [analyze_performance|exec-d8e9f0a1-2b3c-4d5e-6f78-901234567890] ---> [Assessment|out001-2e3f-4a5b-6c7d-890123456789, Recommendation|out002-3f4a-5b6c-7d8e-901234567890]

⏱️  END: 2024-07-25T14:31:02.991Z
🔍 RESOLUTION: 1.8ms
📥 EXECUTION: 1,456.2ms
📦 UNPACKING: 89.3ms
✅ TOTAL: 1,547.3ms
```

---



---

## Error Pattern: Address Resolution Failure

**Agent Input**: Invalid `@uuid` reference

```
⏱️  START: 2024-07-25T14:31:06.345Z

🚀 process_invalid_data(data: DataEntity) -> ProcessedResult

📝 RAW TOOL CALL: {
   "data": "@bad123-4567-8901-2345-67890abcdef0"
}

🔍 RESOLVING:
   data: "@bad123-4567-8901-2345-67890abcdef0"
   ❌ RESOLUTION FAILED: Entity bad123-4567-8901-2345-67890abcdef0 not found in registry

📤 ERROR: AddressResolutionError
   ├─ error_type: "entity_not_found"
   ├─ error_message: "Entity bad123-4567-8901-2345-67890abcdef0 not found in registry"
   └─ suggestions: ["Verify the UUID is correct", "Check if entity has been registered"]

[] ---> [process_invalid_data|exec-d5e6f7a8-9012-3456-7890-123456789012] ---> [ERROR]

⏱️  END: 2024-07-25T14:31:06.358Z
🔍 RESOLUTION: 12.3ms (failed)
✅ TOTAL: 12.3ms (failed)
```