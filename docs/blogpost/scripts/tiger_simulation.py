import random
import argparse

# Parameters
P_CORRECT = 0.85
R_GOLD = 10
R_TIGER = -100
R_LISTEN = -1

class TigerEnvironment:
    def __init__(self):
        self.tiger_loc = None # 'L' or 'R'
        self.reset()

    def reset(self):
        self.tiger_loc = 'L' if random.random() < 0.5 else 'R'
        return "START"

    def step(self, action):
        """
        Action: 'listen', 'open-left', 'open-right'
        Returns: observation, reward, done
        """
        if action == 'listen':
            # Observation logic
            if self.tiger_loc == 'L':
                obs = 'hear-left' if random.random() < P_CORRECT else 'hear-right'
            else: # tiger is R
                obs = 'hear-right' if random.random() < P_CORRECT else 'hear-left'
            return obs, R_LISTEN, False
        
        elif action == 'open-left':
            if self.tiger_loc == 'L':
                return 'tiger', R_TIGER, True
            else:
                return 'gold', R_GOLD, True
        
        elif action == 'open-right':
            if self.tiger_loc == 'R':
                return 'tiger', R_TIGER, True
            else:
                return 'gold', R_GOLD, True
        
        else:
            raise ValueError(f"Invalid action: {action}")

def run_simulation(num_episodes, fixed_steps, use_tiebreak=False):
    env = TigerEnvironment()
    total_reward = 0
    total_steps = 0
    
    for _ in range(num_episodes):
        env.reset()
        episode_reward = 0
        steps = 0
        
        # Track counts for belief
        count_L = 0 # heard left (implies tiger left)
        count_R = 0 # heard right (implies tiger right)
        
        # Listen phase
        done = False
        
        # Determine how many times to listen
        n_listen = fixed_steps
        
        # Execute listening
        for _ in range(n_listen):
            obs, r, d = env.step('listen')
            episode_reward += r
            steps += 1
            if obs == 'hear-left':
                count_L += 1
            else:
                count_R += 1
        
        # Tiebreak logic
        if use_tiebreak and count_L == count_R:
            # Listen one more time
            obs, r, d = env.step('listen')
            episode_reward += r
            steps += 1
            if obs == 'hear-left':
                count_L += 1
            else:
                count_R += 1
        
        # Action phase
        # If count_L > count_R, evidence suggests tiger is Left -> Open Right
        # If count_R > count_L, evidence suggests tiger is Right -> Open Left
        # If equal (only possible if no tiebreak or tiebreak failed/wasn't enough), pick random?
        # In our analytical model, equal belief -> 0.5/0.5 -> Expected reward is same for both.
        # But for simulation we need to pick one.
        
        if count_L > count_R:
            # Tiger likely Left -> Open Right
            action = 'open-right'
        elif count_R > count_L:
            # Tiger likely Right -> Open Left
            action = 'open-left'
        else:
            # Equal evidence. Pick randomly.
            action = 'open-left' if random.random() < 0.5 else 'open-right'
            
        obs, r, d = env.step(action)
        episode_reward += r
        
        total_reward += episode_reward
        total_steps += steps
        
    avg_reward = total_reward / num_episodes
    avg_steps = total_steps / num_episodes
    return avg_reward, avg_steps

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--episodes', type=int, default=100000)
    args = parser.parse_args()
    
    print(f"Running simulation with {args.episodes} episodes per setting...")
    print(f"{'x':<6} {'E[R|policy]':<15} {'E[R|tiebreak]':<20} {'E[steps|TB]':<12}")
    print("-" * 60)
    
    for x in range(11):
        # Standard policy
        r_policy, _ = run_simulation(args.episodes, x, use_tiebreak=False)
        
        # Tiebreak policy
        # Only applicable if x is even (so ties are possible) or x=0?
        # Actually x=0 is a tie (0 vs 0).
        # x=2 (1 vs 1) is a tie.
        # x=1 (1 vs 0) never a tie.
        # So tiebreak only matters for even x.
        
        if x % 2 == 0:
            r_tb, steps_tb = run_simulation(args.episodes, x, use_tiebreak=True)
            tb_str = f"{r_tb:<8.2f} ({steps_tb:.2f})"
        else:
            r_tb = r_policy
            steps_tb = float(x)
            tb_str = "—"
            
        print(f"{x:<6} {r_policy:<15.2f} {tb_str:<20} {steps_tb:<12.2f}")
