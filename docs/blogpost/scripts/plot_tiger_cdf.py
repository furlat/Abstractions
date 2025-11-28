import matplotlib.pyplot as plt
from tiger_analysis import analyze_all_sequences, compute_sequence_probs, compute_belief

# Analyse sequences
all_results = analyze_all_sequences(10)

# ------------------------------------------------------------------
# Get the same thresholds used in the analysis (Table 5 style)
# ------------------------------------------------------------------
unique_max_beliefs = set()
for x in range(9):
    for r in all_results[x]:
        unique_max_beliefs.add(float(r['max_b']))

# All belief levels ≥ 0.5, sorted
all_thresholds = sorted(b for b in unique_max_beliefs if b >= 0.5)

# Take the first 6 to match your table/plot (0.5, 0.85, 0.9698, ...)
thresholds = all_thresholds[:6]

# ------------------------------------------------------------------
# Proper CDF: P(max belief ≥ threshold by step ≤ x)
# ------------------------------------------------------------------
steps = list(range(10))
cdf_data = {t: [] for t in thresholds}

for x in steps:
    for t in thresholds:
        prob_exceeded = 0.0

        # Use sequences of length 10 to cover the whole probability space
        for r in all_results[10]:
            seq = r['seq']
            p_seq = float(r['p_seq'])

            exceeded = False
            for prefix_len in range(x + 1):
                prefix = seq[:prefix_len]
                pp_L, pp_R = compute_sequence_probs(prefix)
                pb_L, pb_R = compute_belief(pp_L, pp_R)
                max_b = max(float(pb_L), float(pb_R))

                # Use >= if you want the prior b=0.5 to count for t=0.5
                if max_b >= t:
                    exceeded = True
                    break

            if exceeded:
                prob_exceeded += p_seq

        cdf_data[t].append(prob_exceeded)

# ------------------------------------------------------------------
# Plot
# ------------------------------------------------------------------
plt.figure(figsize=(12, 7))

colors  = ['grey', 'blue', 'green', 'orange', 'red', 'purple']
markers = ['s', 'o', '^', 'D', 'v', 'p']

for i, t in enumerate(thresholds):
    plt.plot(
        steps,
        cdf_data[t],
        marker=markers[i],
        color=colors[i],
        label=f'threshold = {t:.4f}',
        linewidth=2.5,
        markersize=7,
        alpha=0.85,
    )

plt.xlabel('Number of Listening Steps (x)', fontsize=13)
plt.ylabel('P(max belief ≥ threshold by step ≤ x)', fontsize=13)
plt.title('CDF: Probability of Reaching Belief Threshold by Step x',
          fontsize=15, fontweight='bold')
plt.legend(fontsize=10, loc='lower right', framealpha=0.9)
plt.grid(True, alpha=0.3, linestyle='--')
plt.xticks(steps, fontsize=11)
plt.yticks(fontsize=11)
plt.ylim(-0.05, 1.05)

plt.tight_layout()
plt.savefig('tiger_cdf_proper.png')
plt.show()
