# Scatter Gather
## The Borrowing Pattern for ∘par Results

```python
# ∘par produces: Tuple[StudentResult, TeacherResult]
parallel_result = execute_par("classify_entity", entity=some_entity)
# Returns: (student_analysis, teacher_analysis) or (student_analysis, None) if muted

# Downstream function borrows from tuple positions!
@CallableRegistry.register("create_comprehensive_report")
def create_comprehensive_report(
    student_data: str = f"@{parallel_result.ecs_id}[0].analysis",  # Borrow from position 0
    teacher_data: str = f"@{parallel_result.ecs_id}[1].summary",   # Borrow from position 1  
    metadata: Dict = {"source": "parallel_analysis"}
) -> Report:
    return Report(
        content=f"Student: {student_data}, Teacher: {teacher_data}",
        metadata=metadata
    )
```

## Extending Your String Addressing for Tuples

```python
class TupleAddressResolver:
    """Extend string addressing to handle tuple results from ∘par"""
    
    @staticmethod
    def resolve_tuple_address(address: str) -> Any:
        """
        Handle addresses like:
        - @{uuid}[0] - First element of tuple
        - @{uuid}[1].field - Field from second element
        - @{uuid}[0][2].field - Nested tuples from over-representation
        """
        # Parse the address
        match = re.match(r'@\{([^}]+)\}(\[[\d\[\]]+\])?(.*)$', address)
        if not match:
            return None
            
        entity_id = match.group(1)
        indices = match.group(2) or ""
        field_path = match.group(3)
        
        # Get the tuple entity
        entity = EntityRegistry.get_stored_entity(UUID(entity_id), UUID(entity_id))
        if not entity:
            return None
            
        # Navigate tuple indices
        result = entity
        if indices:
            # Parse [0][1][2] into list of indices
            index_list = re.findall(r'\[(\d+)\]', indices)
            for idx in index_list:
                if hasattr(result, '__getitem__'):
                    result = result[int(idx)]
                else:
                    return None
        
        # Navigate field path if present
        if field_path:
            result = get(f"@{result.ecs_id}{field_path}")
            
        return result
```

## The TupleEntity Pattern

```python
@CallableRegistry.register("execute_par")
def execute_par(composition: str, **kwargs) -> Entity:
    """
    Execute ∘par composition and return results as a TupleEntity
    """
    # Parse the composition to get branches
    branches = parse_par_branches(composition)
    
    # Execute all branches in parallel
    results = []
    for branch_func, expected_type in branches:
        try:
            result = CallableRegistry.execute(branch_func, **kwargs)
            results.append(result)
        except:
            results.append(None)  # Muted branch
    
    # Create TupleEntity to hold results
    class ParallelResultTuple(Entity):
        results: Tuple[Optional[Entity], ...] = Field(default_factory=tuple)
        branch_names: List[str] = Field(default_factory=list)
        execution_pattern: str = "parallel_par"
        muted_positions: List[int] = Field(default_factory=list)
        
        def __getitem__(self, index: int) -> Optional[Entity]:
            """Allow direct indexing of results"""
            return self.results[index] if index < len(self.results) else None
    
    # Create and populate
    tuple_entity = ParallelResultTuple(
        results=tuple(results),
        branch_names=[b[0] for b in branches],
        muted_positions=[i for i, r in enumerate(results) if r is None]
    )
    
    # Register with provenance
    tuple_entity.promote_to_root()
    
    return tuple_entity
```

## Borrowing Composition Examples

### Example 1: Selective Borrowing from Parallel Results

```python
# First ∘par executes multiple analyses
analysis_results = execute("process_entity" ∘par (
    "basic_analysis": Entity |
    "detailed_analysis": Student |
    "performance_analysis": HighPerformer
))

# Second function borrows selectively from the tuple
@CallableRegistry.register("synthesize_report")
def synthesize_report(
    basic: str = "@{analysis_results}[0].summary",
    details: Optional[str] = "@{analysis_results}[1].details",  # Might be None if muted
    performance: Optional[str] = "@{analysis_results}[2].metrics"
) -> SynthesisReport:
    # Compose report from available data
    sections = [basic]
    if details:
        sections.append(f"Details: {details}")
    if performance:
        sections.append(f"Performance: {performance}")
    
    return SynthesisReport(content="\n".join(sections))
```

### Example 2: Chaining ∘par Operations

```python
# Chain multiple ∘par operations with borrowing
composition = """
@{input_entity}
    ∘par (
        "student_path": Student |
        "teacher_path": Teacher
    )
    -> @{result1}
    ∘map (
        create_analysis(
            entity="@{result1}[0]",  # Student result
            context="@{result1}[1]"   # Teacher result for context
        )
    )
    ∘par (
        "generate_report": Report |
        "generate_summary": Summary
    )
"""
```

### Example 3: Handling Over-Representation

```python
# When hierarchy causes multiple matches, we get nested tuples
@CallableRegistry.register("handle_nested_results")
def handle_nested_results(
    # ClassRepresentative matched both Student and Person handlers
    student_result: str = "@{par_result}[0][0]",  # First match in first position
    person_result: str = "@{par_result}[0][1]",   # Second match in first position
    teacher_result: str = "@{par_result}[1]"      # Second position (no fork)
) -> CombinedAnalysis:
    return CombinedAnalysis(
        specific_analysis=student_result,
        general_analysis=person_result,
        other_analysis=teacher_result
    )
```

## Integration with Your CallableRegistry

Your `borrow_from_address` pattern already handles the heavy lifting! Just extend it:

```python
def borrow_from_tuple_address(entity: Entity, address: str, target_field: str):
    """Extended borrowing that handles tuple indexing"""
    
    # Resolve the address (including tuple indices)
    resolved_value = TupleAddressResolver.resolve_tuple_address(address)
    
    if resolved_value is None:
        # Handle optional/muted branches gracefully
        setattr(entity, target_field, None)
        entity.attribute_source[target_field] = None
    else:
        # Standard borrowing with provenance
        entity.borrow_attribute_from(resolved_value, 'result', target_field)
```

## Why This Is Powerful

1. **Composable Parallelism**: ∘par results become first-class entities that can be composed
2. **Selective Consumption**: Functions can borrow just what they need from parallel results
3. **Provenance Preservation**: Full tracking of which parallel branch produced which data
4. **Graceful Degradation**: Muted branches (None) are handled transparently
5. **Type Safety**: The tuple structure is preserved and checkable

## Future: Reduce Operations

When you add reduce operations, they become special borrowing patterns:

```python
@CallableRegistry.register("reduce_par_results")
def reduce_par_results(
    tuple_entity: ParallelResultTuple,
    reduction_op: str = "merge"  # "merge", "select_best", "aggregate"
) -> Entity:
    """Reduce tuple results into single entity"""
    
    non_muted = [r for r in tuple_entity.results if r is not None]
    
    if reduction_op == "merge":
        # Borrow from all non-muted results
        merged = MergedResult()
        for i, result in enumerate(non_muted):
            merged.borrow_attribute_from(
                result, 
                'data', 
                f'branch_{i}_data'
            )
        return merged
    # ... other reduction strategies
```

This creates a complete algebra for parallel computation where:
- **∘par** = Branch into parallel paths
- **Tuples** = Structured parallel results
- **Borrowing** = Selective composition from parallel results
- **Reduce** = Collapse parallel results (future)

You've essentially created **Parallel Functional Dataflow with Provenance**! 🚀