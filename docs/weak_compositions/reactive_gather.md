### Reactive Scatter-Gather: Event-Driven Parallel Composition

The polymorphic parallel operator showed us how to scatter computation across multiple type-matched handlers. But this creates a new challenge: how do we gather the parallel results back together? The framework provides two approaches - explicit borrowing (shown earlier) and reactive gathering through events.

Consider what happens after `∘par` execution:

```python
# Execute parallel branches based on type matching
result = execute_par("analyze_entity" ∘par (
    "student_processor": Student |
    "teacher_processor": Teacher |
    "admin_processor": Admin
))

# This returns a TupleEntity containing all results
# TupleEntity[Optional[StudentResult], Optional[TeacherResult], Optional[AdminResult]]
```

We now have a tuple of results, some of which may be None (muted branches). The traditional approach would be to explicitly access and combine these results. But the framework offers something more elegant: reactive gathering through the event system.

#### The Reactive Pattern

When the `TupleEntity` is created, it's promoted to root like any other entity, which triggers a `CreatedEvent`. This event carries the tuple's type signature, allowing handlers to pattern-match on specific tuple shapes:

```python
# The TupleEntity creation automatically emits:
# CreatedEvent[TupleEntity[Optional[StudentResult], Optional[TeacherResult], Optional[AdminResult]]]

# We can react to this specific pattern
@on(CreatedEvent[TupleEntity])
async def gather_analysis_results(event: CreatedEvent[TupleEntity]):
    """React to any TupleEntity creation"""
    tuple_entity = get(f"@{event.subject_id}")
    
    # Extract non-None results
    active_results = [r for r in tuple_entity.results if r is not None]
    
    # Create gathered report
    if active_results:
        report = ComprehensiveReport(
            analyses=active_results,
            source_count=len(active_results),
            pattern="parallel_analysis"
        )
        
        # Continue the cascade
        await emit(CreatedEvent(
            subject_type=ComprehensiveReport,
            subject_id=report.ecs_id
        ))
```

This simple pattern completes the scatter-gather loop: `∘par` scatters computation across type-matched handlers, creating a `TupleEntity` that emits an event, which triggers gathering handlers that react based on the tuple's content.

#### Type-Specific Gathering

The power of this approach becomes clear when we make the gathering type-aware. Just as `∘par` uses type matching to determine which handlers to execute, we can use type patterns to determine which gatherers to activate:

```python
# Define specific tuple type aliases for clarity
StudentTeacherTuple = TupleEntity[
    Optional[StudentAnalysis], 
    Optional[TeacherAnalysis]
]

# Create type-specific gatherer
@on(CreatedEvent[StudentTeacherTuple])
async def gather_education_analysis(event: CreatedEvent[StudentTeacherTuple]):
    """Gather results from student-teacher parallel analysis"""
    tuple_result = get(f"@{event.subject_id}")
    
    student_analysis = tuple_result[0]
    teacher_analysis = tuple_result[1]
    
    # Handle different sparsity patterns
    if student_analysis and teacher_analysis:
        # Both present - perhaps a teaching assistant
        combined = TeachingAssistantAnalysis(
            student_side=student_analysis,
            teacher_side=teacher_analysis,
            dual_role=True
        )
    elif student_analysis:
        # Only student analysis succeeded
        combined = StudentOnlyAnalysis(
            data=student_analysis,
            teacher_data_absent=True
        )
    else:
        # Only teacher analysis succeeded
        combined = TeacherOnlyAnalysis(
            data=teacher_analysis,
            student_data_absent=True
        )
    
    # Continue the reactive cascade
    await emit(CreatedEvent(subject_type=type(combined), subject_id=combined.ecs_id))
```

The gatherer examines the sparsity pattern in the tuple and creates different outputs based on what actually executed. This is the same principle as the polymorphic parallel operator - we don't force a choice about how to handle the results, we react to what actually happened.

#### Multi-Stage Reactive Pipelines

The reactive scatter-gather pattern naturally extends to multiple stages. Each scatter creates a tuple, which triggers a gather, which might scatter again. This creates pipelines where data flows through alternating phases of parallel exploration and focused aggregation:

```python
# Stage 1: Initial classification returns a single type
@CallableRegistry.register("classify_document")
def classify_document(doc: Document) -> Union[TextDoc, ImageDoc, VideoDoc]:
    """Classify document into specific type"""
    if doc.mime_type.startswith("text/"):
        return TextDoc(content=doc.content, format=doc.format)
    elif doc.mime_type.startswith("image/"):
        return ImageDoc(data=doc.content, dimensions=doc.metadata)
    else:
        return VideoDoc(stream=doc.content, duration=doc.metadata)

# Stage 2: Type-specific handlers scatter into parallel analysis
@on(CreatedEvent[TextDoc])
async def analyze_text_document(event: CreatedEvent[TextDoc]):
    """When TextDoc is created, scatter into parallel text analyses"""
    doc = get(f"@{event.subject_id}")
    
    # Scatter across text-specific processors
    result = await execute_par("text_pipeline" ∘par (
        "sentiment": TextDoc |      # Sentiment analysis
        "entities": TextDoc |       # Entity extraction
        "summary": TextDoc          # Text summarization
    ))
    # Creates: TupleEntity[Optional[Sentiment], Optional[Entities], Optional[Summary]]

# Stage 3: Gather text analysis results reactively
@on(lambda e: e.type == "created" and 
    isinstance(getattr(e, 'subject_type', None), type) and
    issubclass(e.subject_type, TupleEntity) and
    hasattr(e.subject_type, '__args__') and
    any("Sentiment" in str(arg) for arg in e.subject_type.__args__))
async def gather_text_analyses(event: CreatedEvent):
    """Gather results from text analysis scatter"""
    tuple_entity = get(f"@{event.subject_id}")
    
    # Create unified report from whatever succeeded
    report = TextAnalysisReport(
        sentiment=tuple_entity[0] if tuple_entity[0] else None,
        entities=tuple_entity[1].entities if tuple_entity[1] else [],
        summary=tuple_entity[2].text if tuple_entity[2] else "No summary available"
    )
    
    await emit(CreatedEvent(subject_type=TextAnalysisReport, subject_id=report.ecs_id))
```

Each stage operates independently - the document classifier doesn't know about the parallel analyses, and the analyses don't know about the gathering. The pattern emerges from the type relationships and event propagation.

#### Understanding the Complete Flow

To see how scatter and gather work together reactively, let's trace through a complete example:

```python
# 1. SCATTER: The ∘par operator creates parallel branches
async def process_mixed_entity(entity: Entity) -> None:
    """Process an entity that might match multiple handler types"""
    
    # The par operator scatters based on type matching
    result = await execute_par("classify_and_process" ∘par (
        "as_student": Student |
        "as_teacher": Teacher |
        "as_researcher": Researcher
    ))
    # Returns: TupleEntity[Optional[StudentResult], Optional[TeacherResult], Optional[ResearcherResult]]
    # The framework automatically emits: CreatedEvent[TupleEntity[...]]

# 2. GATHER: React to tuple creation with pattern matching
@on(predicate=lambda e: 
    e.type == "created" and 
    isinstance(getattr(e, 'subject_type', None), type) and
    issubclass(e.subject_type, TupleEntity))
async def examine_parallel_results(event: CreatedEvent):
    """Examine what the parallel execution produced"""
    
    tuple_entity = get(f"@{event.subject_id}")
    
    # Count active results (non-None branches)
    active_results = [(i, r) for i, r in enumerate(tuple_entity.results) if r is not None]
    
    if len(active_results) == 0:
        # No handlers matched - unusual case
        await emit(NoMatchesWarning(
            original_entity_id=event.subject_id,
            attempted_branches=len(tuple_entity.results)
        ))
        
    elif len(active_results) == 1:
        # Single match - common case for union types
        idx, result = active_results[0]
        await emit(SingleMatchEvent(
            result_id=result.ecs_id,
            branch_name=tuple_entity.branch_names[idx],
            branch_index=idx
        ))
        
    else:
        # Multiple matches - interesting case for hierarchies
        await emit(MultipleMatchesEvent(
            result_ids=[r.ecs_id for _, r in active_results],
            branch_names=[tuple_entity.branch_names[i] for i, _ in active_results],
            match_count=len(active_results)
        ))
```

The gathering handler doesn't make assumptions about what should happen - it observes the sparsity pattern and emits appropriate events. Other handlers can then react to these patterns.

#### Conditional Gathering Based on Sparsity

The sparsity pattern in the tuple - which branches executed and which were muted - carries information. Reactive gatherers can create different outputs based on these patterns:

```python
# Type alias for a compliance checking tuple
ComplianceTuple = TupleEntity[
    Optional[FinancialAnalysis],
    Optional[RiskAnalysis],
    Optional[ComplianceCheck]
]

@on(CreatedEvent[ComplianceTuple])
async def adaptive_compliance_gathering(event: CreatedEvent[ComplianceTuple]):
    """Create different reports based on what analyses completed"""
    
    tuple_result = get(f"@{event.subject_id}")
    financial = tuple_result[0]
    risk = tuple_result[1] 
    compliance = tuple_result[2]
    
    # The sparsity pattern determines the output type
    if financial and risk and compliance:
        # Full analysis completed - create comprehensive report
        report = FullComplianceReport(
            financial_data=financial,
            risk_assessment=risk,
            compliance_status=compliance,
            confidence="high",
            completeness=1.0
        )
        
    elif financial and risk and not compliance:
        # Compliance check failed or wasn't applicable
        report = ProvisionalReport(
            financial_data=financial,
            risk_assessment=risk,
            missing_components=["compliance"],
            confidence="medium",
            completeness=0.67
        )
        
    elif any([financial, risk, compliance]):
        # Partial results - create what we can
        available = [name for name, result in 
                    [("financial", financial), ("risk", risk), ("compliance", compliance)]
                    if result is not None]
        
        report = PartialAnalysis(
            available_components=available,
            completeness=len(available) / 3.0,
            confidence="low"
        )
        
    else:
        # Nothing succeeded - this itself is information
        report = AnalysisFailure(
            reason="No analysis components completed successfully",
            timestamp=datetime.now()
        )
    
    # The report type itself carries information about what happened
    await emit(CreatedEvent(subject_type=type(report), subject_id=report.ecs_id))
```

This pattern embraces the information in sparsity. Instead of treating None results as failures, they become part of the computation - different combinations lead to different outcomes.

## Why This Pattern is Powerful

### 1. **No Explicit Coordination**
The scatter happens through `∘par`, the gather happens through `@on`. No orchestrator needed.

### 2. **Type-Safe Cascades**
Each stage has clear input/output types. The `TupleEntity` type parameters ensure type safety through the entire flow.

### 3. **Composable Patterns**
You can chain scatter-gather stages indefinitely:
```python
Document → ∘par → TupleEntity → @on → Report → ∘par → TupleEntity → @on → Summary
```

### 4. **Natural Sparsity Handling**
`Optional[T]` in tuple positions naturally handles muted branches. Gatherers can react appropriately to missing data.

### 5. **Distributed-Ready**
Since everything is event-driven, gatherers can run anywhere. The tuple entity is just another addressable entity in the system.

#### Chaining Reactive Scatter-Gather Stages

The true power emerges when multiple scatter-gather stages chain together. Each gather can trigger another scatter, creating complex processing pipelines that emerge from simple local rules:

```python
# Stage 1: Document classification
@CallableRegistry.register("classify_document")
def classify_document(doc: Document) -> Union[LegalDoc, TechnicalDoc, MarketingDoc]:
    """Classify document into specific type based on content"""
    # Classification logic returns one specific type
    return classified_doc

# Stage 2: Type-specific parallel analysis
@on(CreatedEvent[LegalDoc])
async def analyze_legal_document(event: CreatedEvent[LegalDoc]):
    """When a legal document is created, scatter into parallel legal analyses"""
    doc = get(f"@{event.subject_id}")
    
    result = await execute_par("legal_analysis" ∘par (
        "contract_review": LegalDoc |     # Contract clause analysis
        "compliance_check": LegalDoc |    # Regulatory compliance
        "risk_assessment": LegalDoc       # Legal risk analysis
    ))
    # Creates: TupleEntity[Optional[ContractReview], Optional[ComplianceResult], Optional[RiskReport]]

# Stage 3: Gather legal analyses into unified report
@on(lambda e: e.type == "created" and 
    isinstance(getattr(e, 'subject_type', None), type) and
    issubclass(e.subject_type, TupleEntity) and
    hasattr(e.subject_type, '__args__') and
    any("ContractReview" in str(arg) for arg in e.subject_type.__args__))
async def create_legal_report(event: CreatedEvent):
    """Gather legal analysis results into comprehensive report"""
    tuple_entity = get(f"@{event.subject_id}")
    
    # Build report from available analyses
    report = LegalReport(
        contract_issues=tuple_entity[0].issues if tuple_entity[0] else [],
        compliance_status=tuple_entity[1].status if tuple_entity[1] else "pending",
        risk_level=tuple_entity[2].level if tuple_entity[2] else "unknown",
        completeness=sum(1 for r in tuple_entity.results if r is not None) / 3.0
    )
    
    await emit(CreatedEvent(subject_type=LegalReport, subject_id=report.ecs_id))

# Stage 4: Executive summary reacts to any report type
@on(Union[LegalReport, TechnicalReport, MarketingReport])
async def create_executive_summary(event: CreatedEvent):
    """Create executive summary from any report type"""
    report = get(f"@{event.subject_id}")
    
    # Extract key information based on report type
    summary = ExecutiveSummary(
        document_type=type(report).__name__,
        key_findings=report.extract_key_findings(),
        recommended_actions=report.get_recommendations(),
        confidence_level=report.completeness if hasattr(report, 'completeness') else 1.0
    )
    
    await emit(CreatedEvent(subject_type=ExecutiveSummary, subject_id=summary.ecs_id))
```

Each stage operates independently:
- The classifier doesn't know about parallel analyses
- The parallel analyses don't know about report generation
- The report generator doesn't know about executive summaries

Yet they form a cohesive pipeline through type relationships and event propagation.

## Conclusion

By using `@on` decorators to gather from `TupleEntity` results, you complete the reactive scatter-gather pattern. The type system (via Union types and tuple parameters) drives both the scattering (which handlers execute) and the gathering (which events to react to).

This creates a fully reactive system where:
- **Scatter** happens through type affordances (`∘par`)
- **Intermediate results** are addressable entities (TupleEntity)
- **Gather** happens through event reactions (`@on`)
- **Type safety** is maintained throughout
- **No orchestration** is needed

The entire pattern emerges from local rules: functions declare what they can process, the framework executes all matches in parallel, results emit events, and handlers react to continue the flow. Complex workflows self-organize from these simple principles.