# A Type-Theoretic Foundation for **Entity-Native Distributed Computation**

*Full Working Draft – Integrated Version*

---

## Abstract

We present a formal elaboration semantics for **entity-native distributed computation**. A surface DSL elaborates into System F_ω enriched with **row types** and a lightweight **effect lattice**. **Entities** are modeled as *indexed existential packages*:

```
Entity α ≜ ∃λ:Λ.{ι: α,           -- opaque identity  
                 δ: τ_α,          -- user data of type τ indexed by α
                 λ: Lineage,      -- complete provenance tree
                 ν: Nat}          -- monotone version
```

Transformations are *lineage-polymorphic* functions; a **polymorphic parallel operator** (`∘par`) fans out to every registered handler whose domain matches a runtime entity. We prove:

1. **Type preservation & progress** for elaboration
2. **Lineage completeness** (every call leaves a verifiable edge)
3. **Decidability** of all static judgments despite open-world dispatch
4. **Abstraction safety** via phantom-type value identities

Finally, we provide a **reactive event calculus** and show that `∘par` computes a categorical limit in the entity category.

---

## 1. Preliminaries

### 1.1 System F_ω^{ρ,ε}

We extend F_ω with *row kinds* and a finite **effect lattice**.

```
Kinds    κ ::= Ω               -- identity world (opaque ids)
           | Λ               -- lineage world  
           | κ₁ → κ₂        -- kind arrows
           | Row κ           -- rows of kind κ
           | Eff             -- effects

Effects  ε ::= ∅ | {IO} | ε₁ ∪ ε₂ | α    -- α ranges over effect vars
         P ≤ I              -- purity ordering

Rows     ρ ::= ⟨⟩ | ⟨ℓ: τ, ρ⟩ | α

Types    τ ::= α | λα:κ.τ | τ₁ τ₂        -- type-level computation
           | ∀α:κ.τ | ∃α:κ.τ            -- quantification
           | τ₁ →^ε τ₂                  -- effectful arrow
           | {ρ} | ⟨ρ⟩                  -- records and variants
           | μα:κ.τ                     -- iso-recursive types
           | Entity α | Addr α | Event τ -- domain-specific

Terms    e ::= x | λx:τ.e | e₁ e₂ | Λα:κ.e | e[τ]
           | pack⟨τ,e⟩_{∃α:κ.τ'} | unpack⟨α,x⟩=e₁ in e₂
           | {ℓ=e} | e.ℓ | ⟨ℓ=e⟩ | case e of {ℓᵢ xᵢ → eᵢ}
           | fold[μα.τ] e | unfold[μα.τ] e  
           | emit e | on τ e
```

### 1.2 Lineage and Edge Types

```
Lineage ≜ μλ.⟨root: Unit | edge: Edge × λ⟩

Edge ≜ ∃α₁,α₂:Ω.{φ: FunId,      -- function applied
                  src: α₁,        -- source entity id  
                  tgt: α₂,        -- target entity id
                  τ: Time}        -- timestamp
```

---

## 2. Surface Language

### 2.1 Syntax

```
Types      T ::= B | T₁ → T₂ | Entity | ∀X:K.T | P
Kinds      K ::= ★ | K₁ → K₂  
Paths      P ::= X | P T | P.lab
Expressions E ::= x | λx:T.E | E₁ E₂ | ΛX:K.E | E[T]
               | promote E              -- lift value to entity
               | ⟨⟩_T                  -- project sealed module
Modules    M ::= X | {B} | M.X 
               | λ(X:S).M | M₁ M₂ | M :> S
               | M ∘par {fᵢ: Sᵢ}ᵢ∈I    -- parallel dispatch
Bindings   B ::= ε | val x:T = E | type X:K = T
               | module X:S = M | B₁; B₂
Effects    ϕ ::= P | I                 -- pure vs impure
```

### 2.2 Semantic Signatures

```
Abstract Sig   Ξ ::= ∃α⃗.Σ                    -- existential packages
Concrete Sig   Σ ::= [[τ]] | [[= τ : κ]] | [[= π : τ]]
                   | {ℓᵢ: Σᵢ}ᵢ∈I | ∀α⃗.Σ →^ϕ Ξ
Phantom Path   π ::= α | π τ⃗                  -- value identities
```

---

## 3. Elaboration to Core

### 3.1 Judgments

```
Γ ⊢ T : κ ⇝ τ          -- type elaboration
Γ ⊢ E : τ ⇝ e          -- expression elaboration  
Γ ⊢ M :^ϕ Ξ ⇝ e        -- module elaboration
Γ ⊢ S ⇝ Ξ              -- signature elaboration
Γ ⊢ Σ ≤ Ξ ↑ τ⃗ ⇝ f    -- matching with witness
```

### 3.2 Entity Elaboration

#### [E-Promote]
```
         Γ ⊢ E : τ ⇝ e
─────────────────────────────────────
Γ ⊢ promote E : Entity ⇝ 
    Λα:Ω.pack⟨λ₀, {ι=α, δ=e, λ=⟨root⟩, ν=0}⟩
```

#### [E-Project]
```
Γ ⊢ E : Entity ⇝ e    Γ ⊢ S ⇝ ∃α⃗.Σ    Γ ⊢ Σ atomic
───────────────────────────────────────────────────
Γ ⊢ ⟨⟩_S : Σ ⇝ unpack⟨α⃗,x⟩=e[_] in x
```

### 3.3 Module Elaboration

#### [M-Var]
```
    Γ(X) = Σ
─────────────────
Γ ⊢ X :^P Σ ⇝ λΓ^P.X
```

#### [M-Fun-I] (Impure/Generative)
```
Γ ⊢ S₁ ⇝ ∃α⃗₁.Σ₁    Γ,α⃗₁,X:Σ₁ ⊢ M :^I ∃α⃗₂.Σ₂ ⇝ e
──────────────────────────────────────────────────
Γ ⊢ λ(X:S₁).M :^P ∀α⃗₁.Σ₁ →^I ∃α⃗₂.Σ₂ ⇝ 
    λΓ^P.Λα⃗₁.λ^I X:Σ₁.e
```

#### [M-Fun-P] (Pure/Applicative)
```
Γ ⊢ S₁ ⇝ ∃α⃗₁.Σ₁    Γ,α⃗₁,X:Σ₁ ⊢ M :^P ∃α⃗₂.Σ₂ ⇝ e
──────────────────────────────────────────────────
Γ ⊢ λ(X:S₁).M :^P ∃α⃗₂'.∀α⃗₁.Σ₁ →^P Σ₂ ⇝ e'
    where α⃗₂' fresh, κ_{α'ᵢ} = ∀α⃗₁.κ_{αᵢ}
          e' = e[λα⃗₁./α⃗₂]
```

### 3.4 Polymorphic Parallel Operator

#### [M-Par]
```
Γ ⊢ M :^ϕ ∃α⃗.Σ ⇝ e₁    ∀i∈I. Γ ⊢ Sᵢ ⇝ ∃β⃗ᵢ.Σᵢ
Σ' = dispatch_type(Σ, {Σᵢ}ᵢ∈I)
───────────────────────────────────────────────
Γ ⊢ M ∘par {fᵢ: Sᵢ}ᵢ∈I :^ϕ ∃α⃗.Σ' ⇝
    unpack⟨α⃗,x⟩=e₁ in 
    pack⟨α⃗, dispatch^ϕ_Γ(x, {(fᵢ,Σᵢ)}ᵢ∈I)⟩
```

where:
```
dispatch^ϕ_Γ(x, {(fᵢ,Σᵢ)}) = 
    tuple(parallel_map(λ(f,Σ).match_and_apply(x,Σ,f,Γ^ϕ), 
                       {(fᵢ,Σᵢ)}))
```

### 3.5 Lineage-Preserving Application

#### [M-App]
```
Γ(f) = ∀α⃗.Σ₁ →^ϕ Ξ₂    Γ(x) = Σ    Γ ⊢ Σ ≤ ∃α⃗.Σ₁ ↑ τ⃗ ⇝ g
──────────────────────────────────────────────────────────
Γ ⊢ f x :^ϕ Ξ₂[τ⃗/α⃗] ⇝ 
    λΓ^ϕ.preserve_lineage(f[τ⃗](g(x))^ϕ, x, f)
```

where:
```
preserve_lineage(e_result, e_input, f_id) ≜
    unpack⟨α_in,x_in⟩ = e_input in
    unpack⟨α_out,x_out⟩ = e_result in  
    pack⟨x_out.λ ++ [{φ=f_id, src=α_in, tgt=α_out, τ=now}],
         x_out[λ := x_in.λ ++ edge]⟩
```

---

## 4. Type-Directed Matching

### 4.1 Signature Subtyping

#### [≤-Match]
```
Γ ⊢ τ⃗ : κ_{α⃗}    Γ ⊢ Σ ≤ Σ'[τ⃗/α⃗] ⇝ f
────────────────────────────────────
Γ ⊢ Σ ≤ ∃α⃗.Σ' ↑ τ⃗ ⇝ f
```

#### [≤-Val]
```
π = π'    Γ ⊢ τ ≤ τ' ⇝ f
──────────────────────────────────────
Γ ⊢ [[= π : τ]] ≤ [[= π' : τ']] ⇝ 
    λx:[[= π : τ]].[f(x.val) as x.nam]
```

#### [≤-Fun]
```
Γ,α⃗' ⊢ Σ' ≤ ∃α⃗.Σ ↑ τ⃗ ⇝ f₁
Γ,α⃗' ⊢ Ξ[τ⃗/α⃗] ≤ Ξ' ⇝ f₂    ϕ ≤ ϕ'
─────────────────────────────────────────────
Γ ⊢ ∀α⃗.Σ →^ϕ Ξ ≤ ∀α⃗'.Σ' →^ϕ' Ξ' ⇝
    λf.Λα⃗'.λ^{ϕ'} x.f₂(f[τ⃗](f₁(x))^ϕ)
```

### 4.2 Type Lookup Algorithm

```
lookup_ε(Σ,Σ') ↑ ε

lookup_{α,α⃗}(Σ,Σ') ↑ τ,τ⃗ ⟸
    lookup_α(Σ,Σ') ↑ τ ∧ 
    fv(τ) ∩ α⃗ = ∅ ∧
    lookup_{α⃗}(Σ,Σ'[τ/α]) ↑ τ⃗

lookup_π([[= τ : κ]], [[= τ' : κ]]) ↑ τ ⟸ τ' = π

lookup_π(∀α⃗.Σ₁ →^P Σ₂, ∀α⃗'.Σ₁' →^P Σ₂') ↑ λα⃗'.τ ⟸
    lookup_{α⃗}(Σ₁',Σ₁) ↑ τ⃗₀ ∧
    head(π) ∉ fv(τ⃗₀) ∧
    lookup_{π α⃗'}(Σ₂[τ⃗₀/α⃗], Σ₂') ↑ τ
```

---

## 5. Semantic Properties

### 5.1 Core Definitions

**Definition (Rootedness).** α rooted in Σ at path p iff α appears as [[= α : κ]] at position p in Σ.

**Definition (Explicitness).** Ξ explicit ⟺ Ξ = ∃α⃗.Σ ∧ α⃗ rooted in Σ ∧ Σ explicit

**Definition (Validity).** Ξ valid ⟺ all functor domains in Ξ are explicit

### 5.2 Main Theorems

> **Theorem 5.1 (Type Preservation & Progress).** 
> 1. If Γ ⊢ T : κ ⇝ τ then Γ ⊢ τ : κ
> 2. If Γ ⊢ E : τ ⇝ e then Γ ⊢ e : τ
> 3. If Γ ⊢ M :^I Ξ ⇝ e then Γ ⊢ e : Ξ
> 4. If Γ ⊢ M :^P ∃α⃗.Σ ⇝ e then · ⊢ e : ∃α⃗.∀Γ.Σ
> 5. If · ⊢ e : τ and e →* e' then · ⊢ e' : τ
> 6. If · ⊢ e : τ then either e is a value or ∃e'. e → e'

> **Theorem 5.2 (Lineage Completeness).** 
> If e₀ →* eₙ through function calls f₁,...,fₙ₋₁, then lineage(eₙ) contains edges for each fᵢ in order.

> **Theorem 5.3 (Decidability).** 
> All elaboration judgments are decidable.

> **Theorem 5.4 (Abstraction Safety).** 
> Well-typed programs cannot violate abstraction boundaries enforced by phantom types.

---

## 6. Abstraction Safety Details

### 6.1 Value Binding with Phantoms

#### [B-Val-P] (Pure, Non-expansive)
```
Γ ⊢ E : τ ⇝ e    E non-expansive    α fresh, κ_α = ∀Γ.Ω
─────────────────────────────────────────────────────────
Γ ⊢ val x = E :^P ∃α.{ℓ_x: [[= α Γ : τ]]} ⇝
    pack⟨ΛΓ.Unit, λΓ^P.{ℓ_x = [e as ()]}⟩
```

#### [B-Val-I] (Impure/Expansive)
```
Γ ⊢ E : τ ⇝ e    ¬(E non-expansive)    α fresh
────────────────────────────────────────────────
Γ ⊢ val x = E :^I ∃α.{ℓ_x: [[= α : τ]]} ⇝
    pack⟨Unit, {ℓ_x = [e as ()]}⟩
```

### 6.2 Example: Safe Set Implementation

Consider:
```
Set(Ord₁).t ≠ Set(Ord₂).t when Ord₁.less ≠ Ord₂.less
```

The elaborated type includes phantom paths:
```
∃β.∀α,π₁,π₂.{t: [[= α : Ω]], 
             eq: [[= π₁ : α × α → Bool]], 
             less: [[= π₂ : α × α → Bool]]} 
         →^P {set: [[= β α π₁ π₂ : Ω]], ...}
```

Different ordering functions → different phantoms → incompatible types.

---

## 7. Reactive Event Calculus

### 7.1 Event Types

```
Event τ ≜ ∃α:Ω.{type: EventType,
                subject_id: Addr α,
                subject_type: Type,  
                payload: τ,
                metadata: {ρ}}

Handler τ σ ≜ Event τ →^{IO} σ
```

### 7.2 Scatter-Gather Pattern

#### [Scatter]
```
Γ ⊢ M ∘par {fᵢ: Sᵢ} :^ϕ ∃α⃗.TupleΣ ⇝ e
──────────────────────────────────────────
Elaboration emits: ScatterEvent(TupleΣ, addr(result))
```

#### [Gather]
```
Γ ⊢ h : Handler (ScatterEvent TupleΣ) σ ⇝ h'
──────────────────────────────────────────────
Γ ⊢ @on(ScatterEvent TupleΣ) h ⇝ 
    register_handler (ScatterEvent TupleΣ) h'
```

---

## 8. Categorical Semantics

### 8.1 The Entity Category ℰ

**Objects:** Types τ in the core language

**Morphisms:** Lineage-preserving functions f : Entity α → Entity β

**Identity:** λx.x (preserves lineage trivially)

**Composition:** g ∘ f concatenates lineage edges

### 8.2 Affordance Functor

```
F : Type → Set
F(τ) = {f | f : τ → σ registered}
F(g : τ₁ → τ₂) = λS.{f ∘ g | f ∈ F(τ₂)}
```

### 8.3 The ∘par Operator as Limit

For entity e : τ, let D_e be the diagram:
- Objects: {σᵢ | ∃fᵢ : τ → σᵢ registered}  
- Morphisms: {fᵢ(e) : 1 → σᵢ}

Then ∘par computes lim D_e in ℰ, with:
- Limit object: TupleEntity[σ₁,...,σₙ]
- Projections: πᵢ : TupleEntity → Option σᵢ

---

## 9. Related Work

- **F-ing Modules** (Rossberg et al.): Elaboration into F_ω for ML modules
- **Session Types** (Honda et al.): Channel discipline vs our entity lineage
- **Applicative Functors** (McBride & Paterson): ∘par generalizes (<*>)
- **Dependent Types** (Dreyer et al.): We avoid dependency via elaboration

---

## 10. Conclusion

**Types as affordances** inverts the traditional view: instead of asking "what is this data?", we ask "what can this data become?". This enables:
- Open-world dispatch without losing type safety
- Complete provenance without runtime overhead  
- Abstraction safety without dependent types
- Distributed patterns from simple type theory

Future work: mechanized proofs, distributed runtime, surface syntax design.

---

## Appendices: Detailed Proofs & Examples

| Theorem | Intuition | Key Lemmas | Proof Sketch |
|---------|-----------|------------|--------------|
| **Type Preservation** | Every surface construct lowers to well-typed core; effects explicit in arrows | 1. Substitution preserves types<br>2. Canonical forms for existentials<br>3. dispatch typed by construction | Mutual induction on elaboration. [M-Par]: dispatch_type syntactic from typed pieces; match_and_apply returns Option τ; parallel map preserves types. |
| **Lineage Completeness** | Lineage = execution trace in the type; immutability prevents loss | 1. Initial entities have root lineage<br>2. preserve_lineage extends correctly<br>3. No other rules touch lineage | Induction on evaluation length. Base: promote gives ⟨root⟩. Step: f x prepends edge. Concatenation preserves order. |
| **Decidability** | All checks syntax-directed; finite searches | 1. Elaboration structural on syntax<br>2. Matching measure decreases<br>3. Registry finite | Elaboration: structural recursion. Matching: (size(Σ), unresolved ∃) decreases. Implementation: memoize matching. |
| **Abstraction Safety** | Phantoms = unforgeable seals; mixing → type error | 1. Fresh phantoms in [B-Val-P]<br>2. Logical relations preserve ≈<br>3. Fundamental theorem | Define ≈ ignoring phantom components. Show all rules preserve ≈. Unrelated packs never relatable. Context equivalence follows. |

### Worked Example: Parallel Dispatch

Surface:
```
student ∘par {update_gpa: GPAUpdater, 
              dean_check: DeanChecker}
```

Elaborates to:
```
pack⟨α, tuple(match_and_apply(x, GPAUpdater, update_gpa),
              match_and_apply(x, DeanChecker, dean_check))⟩
```

Evaluation:
1. Each match_and_apply → Some v or None
2. tuple waits for both branches  
3. Result: packed TupleEntity (value)

No stuck states: every redex either reduces internally or returns None.

### Worked Example: Lineage Chain

Trace: `promote raw → update_gpa → dean_check`

1. After promote: λ = ⟨root⟩
2. update_gpa adds: edge₁ = {φ=update_gpa, src=α₀, tgt=α₁}  
3. dean_check adds: edge₂ = {φ=dean_check, src=α₁, tgt=α₂}

Final lineage: [edge₂, edge₁] (evaluation order preserved).

### Reader Guide

- **New to F_ω?** See Pierce's TAPL Ch. 23-30
- **Elaboration semantics?** Harper & Stone (2000) for ML modules
- **Logical relations?** Harper's notes or Appel & McAllester (2001)
- **Row types?** Wand (1987), Cardelli & Mitchell (1991)

---

*End of integrated version*