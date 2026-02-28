"""
Test script to prove the RL agent actually learns.
Compares random agent vs trained RL agent performance.
"""

import random
from ai_agent_optimized import OptimizedQLearningAgent
from attack_engine import AttackEngine, AttackAction
from env import EnvironmentState, AccessLevel

def test_random_agent(num_episodes=50, max_steps=100):
    """Test performance with purely random action selection"""
    engine = AttackEngine()
    total_wins = 0
    total_steps = []
    
    for episode in range(num_episodes):
        env = EnvironmentState()
        steps = 0
        
        for step in range(max_steps):
            actions = engine.get_available_actions(env.current_access_level)
            action = random.choice(actions)  # Pure random
            result = engine.execute_attack(action, env)
            steps += 1
            
            if env.current_access_level == AccessLevel.ADMIN:
                total_wins += 1
                total_steps.append(steps)
                break
            
            if result.blocked:
                break
    
    avg_steps = sum(total_steps) / len(total_steps) if total_steps else float('inf')
    return total_wins, avg_steps

def test_rl_agent(num_episodes=50, max_steps=100, training_episodes=200):
    """Test performance with trained RL agent"""
    engine = AttackEngine()
    agent = OptimizedQLearningAgent(
        learning_rate=0.15,
        discount_factor=0.95,
        epsilon=0.3,
        use_experience_replay=True,
        use_double_q=True,
        use_boltzmann=True
    )
    
    # Training phase
    print(f"[*] Training RL agent for {training_episodes} episodes...")
    for episode in range(training_episodes):
        env = EnvironmentState()
        state = f"{env.current_access_level.value}"
        
        for step in range(max_steps):
            actions = engine.get_available_actions(env.current_access_level)
            action_strs = [a.value for a in actions]
            
            chosen = agent.choose_action(state, action_strs, env)
            action = AttackAction(chosen)
            result = engine.execute_attack(action, env)
            
            next_state = f"{env.current_access_level.value}"
            reward = agent.calculate_reward(result, env, chosen)
            done = env.current_access_level == AccessLevel.ADMIN or result.blocked
            
            agent.update_q_value(state, chosen, reward, next_state, done)
            state = next_state
            
            if done:
                break
        
        agent.decay_epsilon()
        
        if (episode + 1) % 50 == 0:
            stats = agent.get_statistics()
            print(f"    Episode {episode+1}: Q-table size={stats['q_table_size']}, epsilon={stats['epsilon']:.3f}")
    
    # Testing phase (low exploration)
    agent.epsilon = 0.05  # Minimal exploration for testing
    agent.use_boltzmann = False
    
    total_wins = 0
    total_steps = []
    
    for episode in range(num_episodes):
        env = EnvironmentState()
        state = f"{env.current_access_level.value}"
        steps = 0
        
        for step in range(max_steps):
            actions = engine.get_available_actions(env.current_access_level)
            action_strs = [a.value for a in actions]
            
            chosen = agent.choose_action(state, action_strs, env)
            action = AttackAction(chosen)
            result = engine.execute_attack(action, env)
            
            state = f"{env.current_access_level.value}"
            steps += 1
            
            if env.current_access_level == AccessLevel.ADMIN:
                total_wins += 1
                total_steps.append(steps)
                break
            
            if result.blocked:
                break
    
    avg_steps = sum(total_steps) / len(total_steps) if total_steps else float('inf')
    return total_wins, avg_steps, agent

def show_learned_policy(agent):
    """Display what the agent learned"""
    print("\n[*] Learned Q-values (policy):")
    
    for state, actions in agent.q_table.table.items():
        if actions:
            sorted_actions = sorted(actions.items(), key=lambda x: x[1], reverse=True)
            print(f"\n  State: {state}")
            for action, qval in sorted_actions[:3]:
                print(f"    {action}: Q={qval:.2f}")

if __name__ == "__main__":
    print("="*70)
    print("RL AGENT LEARNING VERIFICATION TEST")
    print("="*70)
    
    print("\n[Test 1] Random Agent (no learning)...")
    random_wins, random_steps = test_random_agent(num_episodes=100)
    print(f"  Random Agent: {random_wins}/100 wins, avg steps: {random_steps:.1f}")
    
    print("\n[Test 2] RL Agent (with training)...")
    rl_wins, rl_steps, trained_agent = test_rl_agent(
        num_episodes=100, 
        training_episodes=300
    )
    print(f"  RL Agent: {rl_wins}/100 wins, avg steps: {rl_steps:.1f}")
    
    # Show improvement
    print("\n" + "="*70)
    print("RESULTS COMPARISON")
    print("="*70)
    print(f"  Random Agent Win Rate: {random_wins}%")
    print(f"  RL Agent Win Rate:     {rl_wins}%")
    print(f"  Improvement:           {rl_wins - random_wins}% more wins")
    
    if rl_steps != float('inf') and random_steps != float('inf'):
        print(f"\n  Random Agent Avg Steps: {random_steps:.1f}")
        print(f"  RL Agent Avg Steps:     {rl_steps:.1f}")
        print(f"  Efficiency Gain:        {((random_steps - rl_steps) / random_steps * 100):.1f}% faster")
    
    # Show what it learned
    show_learned_policy(trained_agent)
    
    print("\n" + "="*70)
    if rl_wins > random_wins:
        print("VERDICT: RL AGENT IS LEARNING! (Not a gimmick)")
    else:
        print("VERDICT: Results similar - may need more training or tuning")
    print("="*70)
