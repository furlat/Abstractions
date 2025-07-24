# A Type-Theoretic Foundation for Entity-Native Distributed Computation

## Abstract

We present a formal elaboration semantics for distributed entity computation into System F_ω extended with row types and an effect system. Our key contribution is modeling entities as indexed existential packages ∃α:Ω.∃λ:Λ.{ι: α, δ: τ_α, λ: λ, ν: Nat} where α represents abstract identity, λ represents lineage, and transformations are lineage-polymorphic functions. We prove that this elaboration preserves types, maintains complete provenance, and is decidable despite the presence of a polymorphic parallel operator that performs type-directed dispatch.

## 1. Preliminaries

### 1.1 System F_ω^{ρ,ε}

We work in System F_ω extended with row types (ρ) and effects (ε).

**Kinds**
```
κ ::= Ω | Λ | κ₁ → κ₂ | Row κ | Eff
```

**Types**
```
τ ::= α | λα:κ.τ | τ₁ τ₂ | ∀α:κ.τ | ∃α:κ.τ 
    | τ₁ →^ε τ₂ | {ρ} | ⟨ρ⟩ | μα:κ.τ
    | Entity α | Event τ | Addr α
ε ::= ∅ | {ℓ} | ε₁ ∪ ε₂ | ε₁ ⊔ ε₂ | α
ρ ::= ⟨⟩ | ⟨ℓ: τ, ρ⟩ | α
```

**Terms**
```
e ::= x | λx:τ.e | e₁ e₂ | Λα:κ.e | e[τ]
    | pack⟨τ,e⟩_{∃α:κ.τ'} | unpack⟨α,x⟩=e₁ in e₂
    | {ℓ=e} | e.ℓ | ⟨ℓ=e⟩ | case e of {ℓᵢ xᵢ → eᵢ}
    | fold[μα.τ] e | unfold[μα.τ] e
    | emit e | on τ e
```

### 1.2 Entity and Lineage Types

```
Entity α ≜ ∃λ:Λ.{ι: α, δ: Data α, λ: λ, ν: Version}
Lineage ≜ μλ.⟨root: Unit, edge: Edge × λ⟩
Edge ≜ ∃α₁,α₂:Ω.{φ: Fun, src: α₁, tgt: α₂, τ: Time}
```

## 2. Source Language

### 2.1 Syntax

```
Types         T ::= B | T₁ → T₂ | Entity | ∀X:K.T | P
Kinds         K ::= ★ | K₁ → K₂
Type Paths    P ::= X | P T | P.lab
Expressions   E ::= x | λx:T.E | E₁ E₂ | ΛX:K.E | E[T]
                  | promote E | ⟨⟩_T 
Modules       M ::= X | {B} | M.X | λ(X:S).M | M₁ M₂ 
                  | M :> S | M ∘par {fᵢ: Sᵢ}ᵢ∈I
Bindings      B ::= ε | val x:T = E | type X:K = T 
                  | module X:S = M | B₁; B₂
Signatures    S ::= [[T]] | [[= T : K]] | [[= Ξ]] | {D} 
                  | ∀(X:S₁).S₂ | ∃(X:S₁).S₂ | S where type X.ℓ = T
Declarations  D ::= ε | val x:T | type X:K | type X:K = T 
                  | module X:S | D₁; D₂
Effects       ϕ ::= P | I
```

### 2.2 Semantic Objects

```
Abstract Sig  Ξ ::= ∃α⃗.Σ
Concrete Sig  Σ ::= [[τ]] | [[= τ : κ]] | [[= π : τ]] | {ℓᵢ: Σᵢ}ᵢ∈I | ∀α⃗.Σ →^ϕ Ξ
Phantom Path  π ::= α | π τ⃗
```

## 3. Elaboration

### 3.1 Contexts and Judgments

```
Contexts      Γ ::= · | Γ,α:κ | Γ,x:τ | Γ,X:Σ
Judgments     Γ ⊢ T : κ ⇝ τ
              Γ ⊢ E : τ ⇝ e
              Γ ⊢ M :^ϕ Ξ ⇝ e
              Γ ⊢ S ⇝ Ξ
              Γ ⊢ Σ ≤ Ξ ↑ τ⃗ ⇝ f
```

### 3.2 Entity Elaboration

```
                Γ ⊢ E : τ ⇝ e
    ─────────────────────────────────────── [E-Promote]
    Γ ⊢ promote E : Entity ⇝ 
        Λα:Ω.pack⟨λ:Λ.⟨root⟩,
              {ι=α, δ=e, λ=⟨root=()⟩, ν=0}⟩
    
    
    Γ ⊢ E : Entity ⇝ e    Γ ⊢ S ⇝ ∃α⃗.Σ    Γ ⊢ Σ atomic
    ────────────────────────────────────────────────────── [E-Project]
    Γ ⊢ ⟨⟩_S : Σ ⇝ unpack⟨α⃗,x⟩=e[_] in x
```

### 3.3 Module Elaboration

```
    Γ(X) = Σ
    ────────────────── [M-Var]
    Γ ⊢ X :^P Σ ⇝ λΓ^P.X
    
    
    Γ ⊢ S₁ ⇝ ∃α⃗₁.Σ₁    Γ,α⃗₁,X:Σ₁ ⊢ M :^ϕ ∃α⃗₂.Σ₂ ⇝ e
    ───────────────────────────────────────────────────── [M-Fun-ϕ]
    Γ ⊢ λ(X:S₁).M :^P Ξ_ϕ ⇝ e'
    where Ξ_I = ∀α⃗₁.Σ₁ →^I ∃α⃗₂.Σ₂       e' = λΓ^P.Λα⃗₁.λ^I X:Σ₁.e
          Ξ_P = ∃α⃗₂'.∀α⃗₁.Σ₁ →^P Σ₂     e' = e[λα⃗₁./α⃗₂]
          α⃗₂' fresh, |α⃗₂'| = |α⃗₂|
          κ_αᵢ' = ∀α⃗₁.κ_αᵢ
```

### 3.4 Elaboration of Parallel Operator

```
    Γ ⊢ M :^ϕ ∃α⃗.Σ ⇝ e₁
    ∀i ∈ I. Γ ⊢ Sᵢ ⇝ ∃β⃗ᵢ.Σᵢ
    Σ' = dispatch_type(Σ, {Σᵢ}ᵢ∈I)
    ────────────────────────────────────── [M-Par]
    Γ ⊢ M ∘par {fᵢ: Sᵢ}ᵢ∈I :^ϕ ∃α⃗.Σ' ⇝ 
        unpack⟨α⃗,x⟩=e₁ in 
        pack⟨α⃗, dispatch^ϕ_{Γ}(x, {(fᵢ,Σᵢ)}ᵢ∈I)⟩
```

where dispatch elaborates to:

```
dispatch^I_Γ(x, {(fᵢ,Σᵢ)}) ≜ 
    tuple(parallel_map(λ(f,Σ).
        match_and_apply(x, Σ, f, Γ^I), {(fᵢ,Σᵢ)}))

dispatch^P_Γ(x, {(fᵢ,Σᵢ)}) ≜ 
    λΓ^P.tuple(parallel_map(λ(f,Σ).
        match_and_apply(x, Σ, f, Γ^P), {(fᵢ,Σᵢ)}))
```

### 3.5 Lineage-Preserving Application

```
    Γ(f) = ∀α⃗.Σ₁ →^ϕ Ξ₂    Γ(x) = Σ    Γ ⊢ Σ ≤ ∃α⃗.Σ₁ ↑ τ⃗ ⇝ g
    ─────────────────────────────────────────────────────────── [M-App]
    Γ ⊢ f x :^ϕ Ξ₂[τ⃗/α⃗] ⇝ 
        λΓ^ϕ.preserve_lineage(f[τ⃗](g(x))^ϕ, x, f)
```

where:

```
preserve_lineage(e_result, e_input, f_id) ≜
    unpack⟨α_in,x_in⟩ = e_input in
    unpack⟨α_out,x_out⟩ = e_result in
    pack⟨⟨edge={φ=f_id,src=α_in,tgt=α_out,τ=now}, parent=x_in.λ⟩,
         x_out[λ := ⟨edge={φ=f_id,src=α_in,tgt=α_out,τ=now}, 
                     parent=x_in.λ⟩]⟩
```

## 4. Type-Directed Matching

### 4.1 Signature Subtyping

```
    Γ ⊢ τ : κ_α⃗    Γ ⊢ Σ ≤ Σ'[τ⃗/α⃗] ⇝ f
    ──────────────────────────────────── [≤-Match]
    Γ ⊢ Σ ≤ ∃α⃗.Σ' ↑ τ⃗ ⇝ f
    
    
    π = π'    Γ ⊢ τ ≤ τ' ⇝ f
    ────────────────────────────────── [≤-Val]
    Γ ⊢ [[= π : τ]] ≤ [[= π' : τ']] ⇝ λx:[[= π : τ]].[f(x.val) as x.nam]
    
    
    Γ,α⃗' ⊢ Σ' ≤ ∃α⃗.Σ ↑ τ⃗ ⇝ f₁    Γ,α⃗' ⊢ Ξ[τ⃗/α⃗] ≤ Ξ' ⇝ f₂    ϕ ≤ ϕ'
    ──────────────────────────────────────────────────────────────── [≤-Fun]
    Γ ⊢ ∀α⃗.Σ →^ϕ Ξ ≤ ∀α⃗'.Σ' →^ϕ' Ξ' ⇝ 
        λf:∀α⃗.Σ →^ϕ Ξ.Λα⃗'.λ^{ϕ'} x:Σ'.f₂(f[τ⃗](f₁(x))^ϕ)
```

### 4.2 Type Lookup Algorithm

```
lookup_ε(Σ,Σ') ↑ ε

lookup_{α⃗,α⃗'}(Σ,Σ') ↑ τ⃗,τ⃗'  ⟸
    lookup_α⃗(Σ,Σ') ↑ τ⃗ ∧ 
    α⃗' ∩ fv(τ⃗) = ∅ ∧
    lookup_{α⃗'}(Σ,Σ'[τ⃗/α⃗]) ↑ τ⃗'

lookup_π([[= τ : κ]], [[= τ' : κ]]) ↑ τ  ⟸  τ' = π

lookup_π(∀α⃗.Σ₁ →^P Σ₂, ∀α⃗'.Σ₁' →^P Σ₂') ↑ λα⃗'.τ  ⟸
    lookup_α⃗(Σ₁',Σ₁) ↑ τ⃗₀ ∧
    head(π) ∉ fv(τ⃗₀) ∧
    lookup_{π α⃗'}(Σ₂[τ⃗₀/α⃗], Σ₂') ↑ τ
```

## 5. Semantic Properties

### 5.1 Validity and Explicitness

```
Definition (Explicitness). Ξ explicit ⟺ 
    Ξ = ∃α⃗.Σ ∧ α⃗ rooted in Σ ∧ Σ explicit

Definition (Validity). Ξ valid ⟺ 
    all functor domains in Ξ are explicit
```

### 5.2 Elaboration Invariants

**Theorem 5.1 (Type Preservation)**
```
1. Γ ⊢ T : κ ⇝ τ ⟹ Γ ⊢ τ : κ
2. Γ ⊢ E : τ ⇝ e ⟹ Γ ⊢ e : τ  
3. Γ ⊢ M :^I Ξ ⇝ e ⟹ Γ ⊢ e : Ξ
4. Γ ⊢ M :^P ∃α⃗.Σ ⇝ e ⟹ · ⊢ e : ∃α⃗.∀Γ.Σ
```

*Proof*. By mutual induction on derivations. The pure case (4) requires showing that environment abstraction preserves types:
- For [M-Var]: λΓ^P.X has type ∀Γ.Γ(X) when Γ(X) = Σ
- For [M-Fun-P]: Skolemization preserves well-formedness □

### 5.3 Lineage Properties

```
Definition (Lineage Well-formedness). ⊢ λ : Lineage wf ⟺
    λ = ⟨root⟩ ∨ 
    (λ = ⟨edge=e, parent=λ'⟩ ∧ ⊢ λ' wf ∧ e.src ∈ ancestors(λ'))

Definition (Reachability). reaches(λ, α₁, α₂) ⟺
    ∃e ∈ edges(λ). e.src = α₁ ∧ e.tgt = α₂ ∨
    ∃α'. ∃e ∈ edges(λ). e.src = α₁ ∧ e.tgt = α' ∧ reaches(tail(λ), α', α₂)
```

**Theorem 5.2 (Lineage Completeness)**
If `e₁ →* e_n` via transformations `f₁,...,f_{n-1}`, then the lineage of `e_n` contains edges recording each `fᵢ`.

*Proof*. By induction on reduction length. Each [M-App] extends lineage. □

### 5.4 Decidability

**Lemma 5.3 (Finite Registry)**
The set of registered transformations is finite at any point.

**Theorem 5.4 (Decidable Elaboration)**
All elaboration judgments are decidable.

*Proof sketch*. 
- Most rules are syntax-directed
- [M-Fun-I] vs [M-Fun-P] distinguished by effect checking on M
- Matching decidable by Theorem 5.5 below □

**Theorem 5.5 (Decidable Matching)**
If Γ valid, Σ valid, Ξ explicit, then `Γ ⊢ Σ ≤ Ξ ↑ τ⃗ ⇝ f` is decidable.

*Proof*. The lookup algorithm terminates:
- Structural recursion on signatures
- Contravariant lookup in functors preserves structure
- Rootedness prevents cycles □

## 6. Abstraction Safety

### 6.1 Value Identity Tracking

Extend semantic signatures with phantom types:
```
Σ ::= ... | [[= π : τ]]    where π ::= α | π τ⃗
```

### 6.2 Refined Elaboration

```
    Γ ⊢ E : τ ⇝ e    E non-expansive    α fresh, κ_α = ∀Γ.Ω
    ──────────────────────────────────────────────────── [B-Val-P]
    Γ ⊢ val x = E :^P ∃α.{ℓ_x: [[= α Γ : τ]]} ⇝ 
        pack⟨Λ(Γ).Unit, λΓ^P.{ℓ_x = [e as ()]}⟩
```

### 6.3 Safety Theorem

**Definition (Abstraction Respecting)**. A context C[-] is abstraction-respecting for Ξ if it cannot distinguish different implementations of Ξ.

**Theorem 6.1 (Abstraction Safety)**
Well-typed programs cannot violate abstraction boundaries:
If `Γ ⊢ M :^ϕ Ξ ⇝ e` and `Γ ⊢ M' :^ϕ Ξ ⇝ e'` where M,M' have identical type components but different value implementations, then for all abstraction-respecting contexts C[-], C[M] and C[M'] have identical observable behavior.

*Proof sketch*. Phantom types ensure value identities propagate through type system. Different values → different phantoms → different types → type error if mixed. □

## 7. Reactive Event Calculus

### 7.1 Event Types and Handlers

```
Event τ ≜ ∃α:Ω.{
    type: EventType,
    subject_id: Addr α,
    subject_type: Type,
    payload: τ,
    metadata: {ρ}
}

Handler τ σ ≜ Event τ →^{IO} σ
```

### 7.2 Scatter-Gather Elaboration

```
    Γ ⊢ M ∘par {fᵢ: Sᵢ} :^ϕ ∃α⃗.TupleΣ ⇝ e
    ─────────────────────────────────────────── [Scatter]
    with auto-emission of:
        emit(ScatterEvent(TupleΣ, addr(result)))
        
    
    Γ ⊢ h : Handler (ScatterEvent TupleΣ) σ ⇝ h'
    ─────────────────────────────────────────── [Gather]  
    Γ ⊢ @on(ScatterEvent TupleΣ) h ⇝ 
        register_handler (ScatterEvent TupleΣ) h'
```

## 8. Categorical Semantics

### 8.1 Entity Category

Objects: Types τ
Morphisms: Lineage-preserving functions f : Entity α → Entity β
Identity: λx.x (preserves lineage trivially)
Composition: Lineage concatenation

### 8.2 Affordance Functor

The affordance relation induces a functor F : Type → P(Transform):
```
F(τ) = {f | f : τ → σ registered}
F(g : τ₁ → τ₂) = λS.{f ∘ g | f ∈ F(τ₂), f ∘ g defined}
```

### 8.3 Parallel Operator as Limit

The ∘par operator computes the limit of the diagram formed by all applicable transformations, with TupleEntity as the limit object.

## 9. Related Work

Our approach differs from dependent type approaches (Dreyer et al., 2003) by achieving similar expressiveness through elaboration. Unlike session types for distribution (Honda et al., 2008), we maintain purely functional semantics. The parallel operator generalizes both applicative functors (McBride & Paterson, 2008) and arrow combinators (Hughes, 2000).

## 10. Conclusion

We have presented a type-theoretic foundation for distributed entity computation that:
1. Models entities as lineage-tracking existential packages
2. Treats types as affordances rather than descriptions  
3. Achieves automatic provenance through elaboration
4. Supports polymorphic dispatch while maintaining decidability
5. Ensures abstraction safety through phantom type propagation

The key insight is that viewing types generatively—as defining possible transformations rather than static structure—enables a natural account of distributed computation patterns within standard polymorphic type theory.