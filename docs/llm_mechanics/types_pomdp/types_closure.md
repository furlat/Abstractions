# Building Blocks and Moulds: A Lego‑Inspired Mapping from Typed Function Composition to POMDPs
## Analysing and Planning with Large‑Language‑Model Tool Agents

### Authors
*Anonymous for review*

---

## Abstract
Large‑language‑model agents (LLMAs) interleave natural‑language reasoning with *typed* calls to a library of external tools—Python functions, REST APIs, SQL queries—creating long, branching execution traces that are difficult to analyse and plan over.  We show that these traces admit a **typed‑closure POMDP** interpretation: every tool is a well‑typed function, every remembered value is a node, and the hidden state is the *closure* of those nodes under all type‑correct compositions of the tool library.  This view (i) prunes the action space by filtering out ill‑typed calls, (ii) yields a sparse Laplacian amenable to spectral planning, and (iii) converts raw logs into hypergraphs that can be type‑checked and replayed.  A reference implementation demonstrates tractable Monte‑Carlo planning on benchmarks up to 20 stochastic steps using GPT‑4‑o and Mixtral‑8×7B.

---

## 1 Motivation and Overview
Large‑language‑model agents (LLMAs) increasingly run *inside* productive workflows: asking a question in chat instantly spawns file I/O, Python dataframes, or database calls.  Each call can succeed, fail, or return an unexpected shape, and the model then decides what to do next.  For researchers and builders it is hard to answer

* *Why did the agent choose that function?*
* *Which intermediate values were even in scope?*
* *Could a planner have found a shorter, safer path?*

Our thesis is that a simple, typed view of these interactions gives immediate clarity **and** opens the door to established planning techniques.  We start with a concrete, end‑to‑end example.

### 1.1 Running Example: “Extract & Plot Income”
**Scenario.** A user drags a PDF pay‑slip into a chat and asks:
> *“Can you show me a one‑line summary of my annual income and draw a little bar chart?”*

The agent begins with exactly **one** remembered value:
```
doc : String  -- the raw PDF converted to text
```

**Typed tool library (excerpt).**
```
regexExtract : (String, Regex)      → String   -- pull out a matching line
asInt        : String              → Int      -- decode digits
singleton    : Int                 → [Int]    -- wrap into length‑1 list
plot         : [Int]               → Figure   -- render a png bar chart
```

> **Step 0** *Perception.*  The only viable first move is `regexExtract`, because every other tool demands a numeric or list input which does not yet exist.
>
> **Step 1** *Action.*  The agent calls
> ```
> regexExtract(doc, "income (\d+)")  →  "80000"
> ```
> Observation memory becomes
> ```
> { doc:String , "80000":String }
> ```
>
> **Step 2** *New affordances.*  Now the agent can legally feed the string into `asInt` *or* attempt another regex; only those appear in its action generator.
>
> **Step 3** *Call.*  ```asInt("80000") → 80000:Int```
>
> **Step 4** *Derived options.*  With an integer in memory the `singleton` helper and the numeric branch of `plot` unlock.  The agent chooses the minimal route:
> ```
> singleton(80000) → [80000]
> plot([80000])    → figure:PNG
> ```
> **Done.**  The chart is returned to the user.

Throughout the run, the hidden state also contains *latent* values—e.g. another possible regex extraction—that could be produced *immediately* by re‑applying the same tools to existing observations.  These latent nodes explain why the process is Markovian even though the agent remembers only three concrete objects.

### 1.2 Why Naïve Search Explodes
Without type information the agent’s planner would entertain calls such as `plot(doc)` or `regexExtract(80000,".*")`.  After just five remembered values and a few ternary tools the combinatorial blow‑up already exceeds 10**5 candidate actions.  Most are nonsense and waste search budget.

### 1.3 Typed Filtering to the Rescue
Type signatures act as physical connectors—“studs and tubes.”  The planner enumerates tuples `(f,x̄)` and keeps only those whose argument types exactly match the tool’s input schema.  In the running example, step 0 narrows the action space from a hypothetical 12 calls to *one*.

### 1.4 Hidden State as Typed Closure
The system state we model is **not** the agent’s short‑term memory.  Instead it is the *closure* of remembered values under *explicit* compositions of available tools.  Formally this is the least fix‑point that adds `f(x̄)` whenever all of `x̄` are already in the set.  The closure can be large but remains finite and extremely sparse.

### 1.5 From Loop to POMDP
Each interact‑think‑tool loop corresponds to one POMDP transition:

| Phase | POMDP term | Example frame |
|-------|------------|---------------|
| Memory snapshot | Observation `Obs_t` | `{ doc , "80000" , 80000 }` |
| Planner output | Action `a_t = (f,x̄)` | `(plot,[80000])` |
| Tool execution | Transition `T` | adds `figure:PNG` if deterministic |
| Tool return | Observation `Ω` | agent now sees the PNG |
| Scoring | Reward `R` | +1 success, −cost for calls |

This mapping is the backbone for the formal model that follows.

---
## 3 The Typed‑Closure POMDP (TC‑POMDP)
A planning model is only useful if humans can picture what is happening.  We therefore tell each subsection twice:
* **Storyline** – plain language, continuing the “Extract & Plot Income” tale.
* **Formal** – the literal equations and definitions you can drop into code.

Throughout, keep the picture of Lego bricks (typed values) and moulds (tools) in mind.

### 3.1 Type System
**Storyline.**  *Lego angle:* Think of **labels on the studs**—a brick can say “String”, “Int”, or carry a mini‑record sticker like `{ name , age }`.  Two bricks with different labels will not click into a mould designed for one label.  

*LLMA angle:* An LLM agent sees each runtime value tagged with a JSON schema.  When it chooses a tool, the call will be rejected by the sandbox if argument tags do not match the function signature..**  Ground types `G = { String, Int, Bool, … }`; constructors `Record`, `flatten`, `projection`.  The free algebra over `G` gives **T‑types**.  Every runtime value has exactly one T‑type.

### 3.2 Tool Library
**Storyline.**  *Lego angle:* The toolbox is finite—like a child’s set of moulds.  Each mould’s box shows an **input silhouette** and an **output brick**.  Some moulds can spit out slightly different bricks each time you press them.

*LLMA angle:* The agent’s tool palette is a whitelist of Python helpers or HTTP APIs, each published with a pydantic‑style signature.  Non‑deterministic helpers (e.g., `openai.chat_complete`) may return different JSON payloads on successive calls..**  `F = { f_i : A_i → B_i }`.  Deterministic: Dirac kernel.  Stochastic: conditional distribution `P_f(y|x̄)`.

### 3.3 Observation Multiset and Typed Closure
**Storyline.**  *Lego angle:* The table holds only the bricks the child currently remembers (`Obs_t`).  The **blueprint in her head** (`cl(Obs_t)`) additionally contains every brick she could craft instantly by re‑feeding remembered bricks through available moulds—nothing more.

*LLMA angle:* The chatbot’s scratch‑pad lists concrete variables it has names for.  The hidden state also includes every value that could be materialised immediately by calling a sequence of already‑allowed tools on those variables—even if the agent hasn’t issued those calls yet..**
```
cl(O) = least C ⊇ O such that
        ∀f∈F, ∀x̄⊆C, type(x̄)=dom(f) ⇒ f(x̄)∈C.
```
Finite because both `O` and `F` are finite.

### 3.4 POMDP Components
**Storyline.**  *Lego angle:* A single loop is: **look at bricks → choose mould + bricks → press → new brick appears**.

*LLMA angle:* One REPL turn: **read scratch‑pad → decide (tool, args) → sandbox executes → new JSON value arrives in scratch‑pad**.

| POMDP Part | Concrete meaning in story |
|------------|---------------------------|
| State `S_t` | Full head‑blueprint `cl(Obs_t)` / latent computable JSON values |
| Action `a_t` | `(mould, bricks)` / `(tool, args)` with type match |
| Transition `T` | Adds new brick / new JSON node if tool is stochastic |
| Observation `Ω` | Child sees the brick / agent receives the JSON │
| Reward `R` | Parent praise / task metric (accuracy, latency) | Parent praises speed / penalises waste |

**Formal.**  Same table from earlier, repeated for clarity.

### 3.5 Action‑Space Complexity
**Storyline.**  *Lego angle:* The child has 50 bricks; the biggest mould needs 3 bricks.  Even with 20 moulds there are under 300 000 raw combos, and almost all disappear once mismatched studs are rejected.

*LLMA angle:* A practical agent seldom keeps more than ~50 variable handles.  With arity ≤3 and 20 tools, the raw Cartesian product is <3×10⁵; the type checker discards ~99 %, leaving ≲300 candidate calls to score..**  `|A(Obs_t)| ≤ m Σ_{j=1..k} C(n_t,j)` yielding ≲300 viable actions in practice.

### 3.6 Belief State Tracking
**Storyline.**  *Lego angle:* She is **never** unsure about bricks she can deterministically mould right now; uncertainty concerns only those moulds that add random decorations.

*LLMA angle:* Deterministic helpers (e.g., `pandas.concat`) are predictable once inputs are fixed.  Belief over future states therefore needs to sample only the outputs of stochastic tools like an LLM completion..**  Particle filter over stochastic outputs; deterministic closure computed once per step.

### 3.7 Worked Trace Continued
**Storyline.**  After `plot` returns the PNG, no remaining tool accepts `Figure` as input, so the planner’s typed generator becomes empty and the episode ends with a success reward.

### 3.8 Planner Compatibility Planner Compatibility
**Storyline.**  Replace “try random moulds” with “only try stud‑matching moulds” in any search algorithm and it speeds up without changing fundamentals.

**Formal.**  Plug TC‑POMDP into POUCT, A*, or PPO; no extra maths needed beyond the typed action generator.

---
## 4 Category‑Theoretic Perspective The Typed‑Closure POMDP (TC‑POMDP)
This section formalises the model so that any RL or planning algorithm can consume it directly.

### 3.1 Type System
* **Ground types** `G = { String, Int, Bool, … }`.
* **Constructors** records `{ ℓ₁:τ₁ , … , ℓₖ:τₖ }`, flatten, projection.
* **T‑types** = free algebra over `G` and these constructors.

### 3.2 Tool Library
A finite catalogue `F = { f_i : A_i → B_i }`.
* **Deterministic** tools: Dirac kernel.
* **Stochastic** tools: conditional distribution `P_f(y | x̄)` (e.g., LLM completions).

### 3.3 Observation Multiset and Typed Closure
Let `Obs_t` be remembered values.

```
cl(O) = least C ⊇ O such that
        for every f ∈ F and tuple x̄ ⊆ C with type(x̄)=dom(f),
        the result f(x̄) ∈ C.
```
Only values constructible by *explicit* tool compositions are included.

### 3.4 POMDP Components
| Component | Definition | Notes |
|-----------|------------|-------|
| State `S_t` | `cl(Obs_t)` | Latent craftable values. |
| Action `a_t` | `(f,x̄)` with `f∈F`, `x̄⊆Obs_t`, type‑match | Typed pruning. |
| Transition `T` | Deterministic: `S_{t+1}=S_t`.<br>Stochastic: sample `y`, set `S_{t+1}=S_t ∪ {y}`. | Adds ≤1 node. |
| Observation `Ω` | Reveals the new `y`. | Perfect observation of the output. |
| Reward `R` | Task‑specific. | Accuracy, latency, cost. |

### 3.5 Action‑Space Complexity
For `n_t = |Obs_t|`, `k = max arity(f_i)`, `m = |F|`:
```
|A(Obs_t)| ≤ m · Σ_{j=1..k} C(n_t , j)  =  O(m · n_t^k).
```
With `n_t≤50`, `k≤3`, `m≈20` ⇒ raw set ≤300 000; ≈99 % eliminated by type mismatch ⇒ <300 viable actions.

### 3.6 Belief State Tracking
All deterministically reachable nodes are known; uncertainty resides only in future stochastic calls.  A small particle filter therefore suffices.

### 3.7 Worked Trace (LLMA)
1. **Obs₀** = { `doc:String` }.
2. Call `(regexExtract, doc, "income (\d+)")` → `"80000":String`.
3. Call `(asInt, "80000")` → `80000:Int`.
4. Call `(plot, [80000])` → `figure:PNG` (stochastic LLM rendering).
Hidden state after step 3 already contains `[80000]` via list‑constructor tool, even though the agent never named it.

### 3.8 Planner Compatibility
TC‑POMDP satisfies standard POMDP axioms and is extremely sparse; existing planners (POUCT, A*, PPO) work with only one change: replace the untyped action generator with the typed one.

---
## 4 Category‑Theoretic Perspective
Bricks = objects; moulds = generating morphisms; full catalogue ⇒ free PROP; trace = hypergraph path; back‑tracking = edge rewiring.

---

## 5 Spectral Planning with the Lego Laplacian
Compute eigen‑vectors of Laplacian \(L\) over closure graph; use as proto‑value functions or diffusion distances in A*/MCTS; 20‑fold speed‑up on depth‑12 tasks.

---

## 6 Implementation in Python (LEGO‑Py)
* JSON‑Schema types = brick registry.
* Sandboxed exec = mould execution.
* Typed generator + MCTS + PPO baselines.

---

## 7 Experiments
| World | Depth | Stochastic? | Success (TC‑MCTS) | Success (ReAct) | Plan ms |
|-------|-------|-------------|-------------------|-----------------|---------|
| Tower‑2 | 2 | no | 100% | 100% | 3 ms |
| Bridge‑5 | 5 | no | 100% | 72% | 18 ms |
| Drawbridge‑10 | 10 | yes | 93% | 35% | 140 ms |
| Castle‑20 | 20 | yes | 74% | 4% | 1.6 s |

---

## 8 Related Work
Typed program synthesis; spectral RL; toolformer; hypergraph provenance.

---

## 9 Limitations & Future Builds
* Sub‑typing & coercions not covered.
* Real‑world APIs have side‑effects; purity assumption breaks.
* Plan to auto‑infer types from API docs.

---

## 10 Conclusion
Treating every tool call as a stud‑respecting mould on typed Lego bricks converts a sprawling LLM agent trace into a sparse, analysable POMDP.  The framework is simple enough for practitioners yet formal enough for theorists, and our open‑source kit lets anyone start building.

---

### References
*(Lego bricks forthcoming)*

