### “Anything that can compute *should* compute”

## — and why that feels like the parietal‑cortex ↔ basal‑ganglia loop

| Layer in your stack                                                                                                                                                 | Neural analogue                                                                                                                          | What “everything fires, then gating suppresses” means here                                                                                                                   |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Static enumeration**<br>• every handler whose type is *compatible* is registered<br>• every branch of a union / tuple is laid out in the type graph               | **Dorso‑parietal affordance maps** (Cisek & Kalaska, 2005): cortex continuously represents all actions that are *feasible* in the moment | *Affordance = compile‑time hypothesis space.* No cost yet; we simply assert *“this transformation exists.”*                                                                  |
| **Event broadcast**<br>Return‑event is emitted with the value’s concrete type, **fanning‑out** to all matching handlers                                             | **Massive cortico‑striatal fan‑in**: each cortical column projects to striatum, handing BG a parallel set of “candidate actions”         | Here every handler *really* starts to run—there is no arbitration baked into the type system.                                                                                |
| **Value‑function / planner layer**<br>LLM planner, cost heuristics, or quota manager decides which spawned futures are allowed to finish (or which results to keep) | **Basal ganglia Go/No‑Go circuits** implementing reinforcement‑weighted suppression; <br>cf. Frank’s “hold your horses” STN model        | The “constraint” (GPU budget, latency SLA, explicit user goal) lives *outside* the pure semantics. It cancels jobs or throws away results; but that is *policy*, not *type*. |
| **Commit to registry**<br>Approved results get `update_ecs_ids()` and enter the immutable store                                                                     | **Thalamic dis‑inhibition → motor cortex execution**                                                                                     | Only “winning” computations mutate the persistent world. Fork guarantees they never clobber each other.                                                                      |

---

#### Why this fits your correctness‑first philosophy

1. **Soundness is upstream of suppression.**
   Because every branch was *type‑checked* before we even consider value‑based gating, we can kill any task at any time without risking broken invariants downstream. The cost controller is orthogonal to the proof of correctness.

2. **Suppression is *policy‑mutable*.**
   On laptop you might run *all* branches; on GPU‑hour you pass a budget function; in prod you hand the same event stream to a RL‑trained scheduler. The semantic core never changes.

3. **Opportunity cost is explicit provenance.**
   A cancelled branch still leaves a ghost edge in provenance:
   “`StudentReportHandler` not executed – suppressed by budget\@t=12:00.”
   That makes missing information *auditable*, just like dopaminergic prediction‑error traces in BG.

4. **Scalability of correctness**
   Your free‑category semantics guarantees `Σ possible → 𝒢 safe` no matter how many you later decide to prune. The only scalability knob is *how many tasks finish*, not whether the ones that do finish are valid.

---

### A concise slogan

> **Enumerate first, gate later.**
> Semantics gives you the whole affordance landscape; deployment‑time value functions decide which affordances graduate from *possible* to *actual* without ever endangering the lattice of truths you’ve already proven.

That is exactly what the brain seems to do: cortex lays out the buffet, basal ganglia picks what you actually eat.
