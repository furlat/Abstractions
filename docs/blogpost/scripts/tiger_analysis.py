from fractions import Fraction
from itertools import product
import math

# Parameters - make them constants to avoid mutation
P_CORRECT = Fraction(85, 100)  # P(hear-left | tiger-left) = 0.85
P_WRONG = Fraction(15, 100)    # P(hear-right | tiger-left) = 0.15

R_GOLD = 10
R_TIGER = -100
R_LISTEN = -1

MAX_LISTENS = 9  # We only allow up to 9 listening steps


def compute_sequence_probs(seq):
    """Compute P(seq | L) and P(seq | R) for a sequence of L/R observations."""
    n_left = seq.count('L')
    n_right = seq.count('R')
    
    # P(seq | tiger on left): hear-left with prob P_CORRECT, hear-right with prob P_WRONG
    p_seq_given_L = (P_CORRECT ** n_left) * (P_WRONG ** n_right)
    
    # P(seq | tiger on right): hear-left with prob P_WRONG, hear-right with prob P_CORRECT  
    p_seq_given_R = (P_WRONG ** n_left) * (P_CORRECT ** n_right)
    
    return p_seq_given_L, p_seq_given_R


def compute_belief(p_seq_L, p_seq_R):
    """Compute posterior belief b(L) and b(R) given uniform prior."""
    total = p_seq_L + p_seq_R
    b_L = p_seq_L / total
    b_R = p_seq_R / total
    return b_L, b_R


def expected_reward_argmax(b_L, b_R):
    """Expected reward of choosing argmax belief action."""
    # open-right: gold if tiger left, tiger if tiger right
    E_open_right = float(b_L) * R_GOLD + float(b_R) * R_TIGER
    # open-left: tiger if tiger left, gold if tiger right
    E_open_left = float(b_L) * R_TIGER + float(b_R) * R_GOLD
    return max(E_open_right, E_open_left)


def analyze_all_sequences(max_depth):
    """Analyze all sequences up to max_depth."""
    all_results = {}
    
    for x in range(max_depth + 1):
        results = []
        
        if x == 0:
            results.append({
                'seq': '∅',
                'p_seq': Fraction(1, 1),
                'b_L': Fraction(1, 2),
                'b_R': Fraction(1, 2),
                'max_b': 0.5,
                'E_argmax': expected_reward_argmax(Fraction(1, 2), Fraction(1, 2)),
            })
        else:
            for seq_tuple in product(['L', 'R'], repeat=x):
                seq = ''.join(seq_tuple)
                p_seq_L, p_seq_R = compute_sequence_probs(seq)
                p_seq = (p_seq_L + p_seq_R) / 2
                b_L, b_R = compute_belief(p_seq_L, p_seq_R)
                max_b = max(float(b_L), float(b_R))
                
                results.append({
                    'seq': seq,
                    'p_seq': p_seq,
                    'b_L': b_L,
                    'b_R': b_R,
                    'max_b': max_b,
                    'E_argmax': expected_reward_argmax(b_L, b_R),
                })
        
        all_results[x] = results
    
    return all_results


# ============================================================================
# MAIN ANALYSIS
# ============================================================================
if __name__ == "__main__":
    all_results = analyze_all_sequences(MAX_LISTENS)
    
    # ========================================================================
    # TABLE 1: Detailed sequences for x = 0, 1, 2, 3
    # ========================================================================
    print("=" * 110)
    print("DETAILED SEQUENCE TABLE (x = 0, 1, 2, 3)")
    print("=" * 110)
    
    for x in range(4):
        results = all_results[x]
        print(f"\n--- x = {x} ---")
        print(f"{'seq':<8} {'P(seq)':<10} {'b(L)':<8} {'b(R)':<8} {'max_b':<8} {'E[argmax]':<12} {'cost':<6} {'E[total]':<10}")
        print("-" * 80)
        
        for r in results:
            cost = x * R_LISTEN
            E_total = r['E_argmax'] + cost
            print(f"{r['seq']:<8} {float(r['p_seq']):<10.4f} {float(r['b_L']):<8.3f} {float(r['b_R']):<8.3f} {r['max_b']:<8.3f} {r['E_argmax']:<12.1f} {cost:<6} {E_total:<10.1f}")
    
    # ========================================================================
    # TABLE 2: Fixed-step policy summary with tiebreak
    # ========================================================================
    print("\n" + "=" * 100)
    print("FIXED-STEP POLICY: Listen x times, then act on argmax belief")
    print("(Tiebreak: if b=0.5, listen once more when feasible)")
    print("=" * 100)
    print(f"{'x':<6} {'E[R|act]':<12} {'E[R|policy]':<15} {'E[R|tiebreak]':<20} {'E[steps|TB]':<12}")
    print("-" * 70)
    
    E_after_tiebreak = expected_reward_argmax(P_CORRECT, P_WRONG)  # -6.5
    
    for x in range(MAX_LISTENS + 1):  # x = 0..9
        results = all_results[x]
        
        E_act = sum(float(r['p_seq']) * r['E_argmax'] for r in results)
        E_policy = E_act + x * R_LISTEN
        
        # Compute tiebreak version
        P_tie = sum(float(r['p_seq']) for r in results if abs(r['max_b'] - 0.5) < 1e-9)
        
        # Tiebreak feasible only if we can listen one more time (x < MAX_LISTENS)
        if P_tie > 0 and x < MAX_LISTENS:
            # E[steps] = P_tie * (x+1) + (1-P_tie) * x = x + P_tie
            E_steps_tb = x + P_tie
            # E[R] for non-tied cases
            E_act_notie = sum(float(r['p_seq']) * r['E_argmax'] for r in results if abs(r['max_b'] - 0.5) >= 1e-9)
            # E[R] for tied cases (they get -6.5 after one more listen)
            E_act_tie = P_tie * E_after_tiebreak
            E_tb = E_act_notie + E_act_tie + E_steps_tb * R_LISTEN
            tb_str = f"{E_tb:<8.2f} ({E_steps_tb:.2f})"
        else:
            E_steps_tb = float(x)
            E_tb = E_policy
            tb_str = "—"
        
        print(f"{x:<6} {E_act:<12.2f} {E_policy:<15.2f} {tb_str:<20} {E_steps_tb:<12.2f}")
    
    # ========================================================================
    # TABLE 3: Belief Space Analysis (Cardinality & Entropy)
    # ========================================================================
    print("\n" + "=" * 90)
    print("BELIEF SPACE ANALYSIS")
    print("=" * 90)
    print(f"{'x':<6} {'Card(x)':<12} {'Card(≤x)':<12} {'Entropy H(B)':<15}")
    print("-" * 60)

    unique_max_beliefs = set()
    cumulative_beliefs = {}  # Track all beliefs seen up to this depth

    for x in range(MAX_LISTENS + 1):  # 0..9
        results = all_results[x]
        
        # Group by belief (b_L, b_R) to find unique beliefs and their probabilities
        belief_dist = {}
        for r in results:
            b_key = (r['b_L'], r['b_R'])
            if b_key not in belief_dist:
                belief_dist[b_key] = 0.0
            belief_dist[b_key] += float(r['p_seq'])
            
            # Add to cumulative beliefs
            if b_key not in cumulative_beliefs:
                cumulative_beliefs[b_key] = 0.0
            cumulative_beliefs[b_key] += float(r['p_seq'])
            
            unique_max_beliefs.add(r['max_b'])
            
        cardinality_exact = len(belief_dist)
        cardinality_cumulative = len(cumulative_beliefs)
        
        # Calculate Entropy H(B) = - sum P(b) log2 P(b)
        entropy = 0.0
        for p_b in belief_dist.values():
            if p_b > 0:
                entropy -= p_b * math.log2(p_b)
                
        print(f"{x:<6} {cardinality_exact:<12} {cardinality_cumulative:<12} {entropy:<15.4f}")

    # ========================================================================
    # TABLE 4: Probability distribution at each depth (NOT cumulative)
    # ========================================================================
    print("\n" + "=" * 90)
    print("P(max_belief > threshold | exactly x steps)")
    print("=" * 90)
    
    thresholds = [0.85, 0.90, 0.95, 0.97, 0.99]
    
    print(f"{'x':<6}", end="")
    for t in thresholds:
        print(f"{'P(b>'+str(t)+')':<12}", end="")
    print()
    print("-" * 70)
    
    for x in range(MAX_LISTENS + 1):  # 0..9
        results = all_results[x]
        print(f"{x:<6}", end="")
        for t in thresholds:
            prob = sum(float(r['p_seq']) for r in results if r['max_b'] > t)
            print(f"{prob:<12.4f}", end="")
        print()
    
    # ========================================================================
    # TABLE 5: Threshold-based policies (using unique belief levels)
    # ========================================================================
    print("\n" + "=" * 80)
    print("THRESHOLD POLICY: Listen until confidence >= threshold, then act")
    print(f"(Max {MAX_LISTENS} listening steps; environment ends after final action at step 10)")
    print("=" * 80)
    print(f"{'Threshold':<12} {'E[R]':<12} {'E[steps]':<12} {'P(timeout)':<12}")
    print("-" * 50)
    
    sorted_thresholds = sorted([float(b) for b in unique_max_beliefs if float(b) >= 0.5])
    
    for threshold in sorted_thresholds:
        current_total_reward = 0.0
        current_total_steps = 0.0
        current_prob_timeout = 0.0
        
        # Use sequences of length MAX_LISTENS (9) to represent all trajectories
        for r in all_results[MAX_LISTENS]:
            seq = r['seq']
            p_seq = float(r['p_seq'])
            
            # Default: stop at MAX_LISTENS if threshold never met earlier
            stop_len = MAX_LISTENS
            stop_E_argmax = None
            
            # Check prefixes from length 0 up to MAX_LISTENS
            for l in range(MAX_LISTENS + 1):  # 0..9
                prefix = seq[:l]
                pp_L, pp_R = compute_sequence_probs(prefix)
                pb_L, pb_R = compute_belief(pp_L, pp_R)
                p_max_b = max(float(pb_L), float(pb_R))
                
                if p_max_b >= threshold - 1e-9:
                    stop_len = l
                    stop_E_argmax = expected_reward_argmax(pb_L, pb_R)
                    break
            
            # If never crossed threshold by MAX_LISTENS, treat as timeout
            if stop_len == MAX_LISTENS:
                pp_L, pp_R = compute_sequence_probs(seq)
                pb_L, pb_R = compute_belief(pp_L, pp_R)
                p_max_b = max(float(pb_L), float(pb_R))
                stop_E_argmax = expected_reward_argmax(pb_L, pb_R)
                
                if p_max_b < threshold - 1e-9:
                    current_prob_timeout += p_seq
            
            reward = stop_E_argmax + stop_len * R_LISTEN
            current_total_reward += p_seq * reward
            current_total_steps += p_seq * stop_len
            
        print(f"{threshold:<12.4f} {current_total_reward:<12.2f} {current_total_steps:<12.2f} {current_prob_timeout:<12.4f}")
