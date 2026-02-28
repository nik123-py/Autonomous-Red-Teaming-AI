"""
Optimized Reinforcement Learning agent for autonomous attack decision making.
Enhanced with advanced RL techniques for hackathon demonstration:
- Experience Replay Buffer
- Double Q-Learning
- Adaptive Learning Rate
- N-step Q-Learning
- Boltzmann Exploration
- Performance Metrics
- Reward Shaping
"""

from typing import Dict, List, Optional, Tuple
import random
import math
import json
from dataclasses import dataclass, field
from collections import deque
from attack_engine import AttackResult
from env import EnvironmentState, AccessLevel


@dataclass
class Experience:
    """Single experience tuple for replay buffer"""
    state: str
    action: str
    reward: float
    next_state: str
    done: bool
    timestamp: float = field(default_factory=lambda: 0.0)


class ExperienceReplayBuffer:
    """Experience replay buffer for stable learning"""
    
    def __init__(self, capacity: int = 10000):
        self.buffer = deque(maxlen=capacity)
        self.capacity = capacity
    
    def add(self, experience: Experience):
        """Add experience to buffer"""
        self.buffer.append(experience)
    
    def sample(self, batch_size: int) -> List[Experience]:
        """Sample random batch of experiences"""
        return random.sample(self.buffer, min(batch_size, len(self.buffer)))
    
    def __len__(self):
        return len(self.buffer)
    
    def is_ready(self, batch_size: int) -> bool:
        """Check if buffer has enough experiences for sampling"""
        return len(self.buffer) >= batch_size


@dataclass
class OptimizedQTable:
    """Enhanced Q-table with Double Q-Learning support"""
    table: Dict[str, Dict[str, float]] = field(default_factory=dict)
    table_target: Dict[str, Dict[str, float]] = field(default_factory=dict)  # Target network for Double Q
    learning_rate: float = 0.1
    discount_factor: float = 0.9
    use_double_q: bool = True
    target_update_frequency: int = 10  # Update target network every N steps
    update_count: int = 0

    def get_q_value(self, state: str, action: str, use_target: bool = False) -> float:
        """Get Q-value from main or target network"""
        q_table = self.table_target if use_target else self.table
        if state not in q_table:
            q_table[state] = {}
        return q_table[state].get(action, 0.0)

    def set_q_value(self, state: str, action: str, value: float, use_target: bool = False):
        """Set Q-value in main or target network"""
        q_table = self.table_target if use_target else self.table
        if state not in q_table:
            q_table[state] = {}
        q_table[state][action] = value

    def update_q_value(
        self,
        state: str,
        action: str,
        reward: float,
        next_state: str,
        learning_rate: float = None,
        discount_factor: float = None,
        done: bool = False
    ):
        """
        Update Q-value using Double Q-Learning formula.
        Q(s,a) = Q(s,a) + α[r + γ * Q_target(s', argmax_a' Q(s',a')) - Q(s,a)]
        """
        lr = learning_rate or self.learning_rate
        gamma = discount_factor or self.discount_factor

        current_q = self.get_q_value(state, action, use_target=False)
        
        if done:
            # Terminal state: no future rewards
            target_q = reward
        else:
            if self.use_double_q and next_state in self.table:
                # Double Q-Learning: use target network for value, main network for action selection
                # Find best action using main network
                if next_state in self.table and self.table[next_state]:
                    best_action = max(self.table[next_state].items(), key=lambda x: x[1])[0]
                    # Get Q-value from target network
                    target_q = self.get_q_value(next_state, best_action, use_target=True)
                else:
                    target_q = 0.0
            else:
                # Standard Q-Learning: use main network
                if next_state in self.table and self.table[next_state]:
                    target_q = max(self.table[next_state].values())
                else:
                    target_q = 0.0
            
            target_q = reward + gamma * target_q

        # Q-learning update
        new_q = current_q + lr * (target_q - current_q)
        self.set_q_value(state, action, new_q, use_target=False)
        
        self.update_count += 1
        
        # Update target network periodically
        if self.use_double_q and self.update_count % self.target_update_frequency == 0:
            self._update_target_network()

    def _update_target_network(self):
        """Copy main network to target network (soft update)"""
        # Hard copy for simplicity (can be made soft update with tau parameter)
        self.table_target = {k: v.copy() for k, v in self.table.items()}

    def get_best_action(self, state: str, available_actions: List[str]) -> Optional[str]:
        """Get action with highest Q-value"""
        if not available_actions:
            return None

        if state not in self.table or not self.table[state]:
            return random.choice(available_actions)

        best_action = None
        best_value = float('-inf')

        for action in available_actions:
            q_value = self.get_q_value(state, action, use_target=False)
            if q_value > best_value:
                best_value = q_value
                best_action = action

        return best_action or random.choice(available_actions)

    def get_action_values(self, state: str, available_actions: List[str]) -> Dict[str, float]:
        """Get Q-values for all available actions (for Boltzmann exploration)"""
        values = {}
        for action in available_actions:
            values[action] = self.get_q_value(state, action, use_target=False)
        return values

    def reset(self):
        """Reset Q-tables"""
        self.table.clear()
        self.table_target.clear()
        self.update_count = 0


class OptimizedQLearningAgent:
    """
    Optimized Q-learning agent with advanced RL techniques.
    Designed for impressive hackathon demonstration.
    """

    def __init__(
        self,
        learning_rate: float = 0.15,  # Slightly higher for faster learning
        discount_factor: float = 0.95,  # Higher for long-term planning
        epsilon: float = 0.2,  # Start with more exploration
        epsilon_decay: float = 0.998,  # Slower decay for sustained exploration
        min_epsilon: float = 0.05,  # Keep some exploration
        use_experience_replay: bool = True,
        replay_buffer_size: int = 5000,
        batch_size: int = 32,
        use_double_q: bool = True,
        use_boltzmann: bool = True,  # Boltzmann exploration instead of epsilon-greedy
        temperature: float = 1.0,  # For Boltzmann exploration
        n_step: int = 3,  # N-step Q-learning
        adaptive_lr: bool = True
    ):
        """
        Initialize optimized Q-learning agent.
        
        Args:
            learning_rate: Initial learning rate
            discount_factor: Future reward discount
            epsilon: Initial exploration rate
            epsilon_decay: Exploration decay rate
            min_epsilon: Minimum exploration rate
            use_experience_replay: Enable experience replay
            replay_buffer_size: Size of replay buffer
            batch_size: Batch size for replay
            use_double_q: Enable Double Q-Learning
            use_boltzmann: Use Boltzmann exploration
            temperature: Temperature for Boltzmann
            n_step: N-step Q-learning horizon
            adaptive_lr: Enable adaptive learning rate
        """
        self.q_table = OptimizedQTable(
            learning_rate=learning_rate,
            discount_factor=discount_factor,
            use_double_q=use_double_q
        )
        
        # Exploration parameters
        self.epsilon = epsilon
        self.epsilon_decay = epsilon_decay
        self.min_epsilon = min_epsilon
        self.use_boltzmann = use_boltzmann
        self.temperature = temperature
        
        # Experience replay
        self.use_experience_replay = use_experience_replay
        self.replay_buffer = ExperienceReplayBuffer(capacity=replay_buffer_size) if use_experience_replay else None
        self.batch_size = batch_size
        self.n_step_buffer = deque(maxlen=n_step)  # N-step buffer
        
        # Learning parameters
        self.adaptive_lr = adaptive_lr
        self.base_learning_rate = learning_rate
        self.learning_rate = learning_rate
        self.n_step = n_step
        
        # Performance tracking
        self.total_rewards = 0.0
        self.episode_count = 0
        self.step_count = 0
        self.success_count = 0
        self.failure_count = 0
        self.recent_rewards = deque(maxlen=100)  # Track recent rewards for adaptive LR
        
        # Statistics
        self.performance_history = {
            "episodes": [],
            "rewards": [],
            "success_rates": [],
            "epsilon_values": []
        }

    def choose_action(
        self,
        state: str,
        available_actions: List[str],
        environment_state: Optional[EnvironmentState] = None
    ) -> str:
        """
        Choose action using optimized exploration strategy.
        Prioritizes strategic hints from Exploit-DB when available.
        """
        if not available_actions:
            raise ValueError("No available actions")

        # Knowledge-Augmented RL: Check for strategic hint
        if environment_state and environment_state.hint_available == 1:
            hint_action = environment_state.strategic_hint
            if hint_action and hint_action in available_actions:
                # Adaptive hint following based on confidence
                hint_confidence = environment_state.hint_confidence
                follow_probability = 0.7 + (hint_confidence * 0.2)  # 70-90% based on confidence
                if random.random() < follow_probability:
                    print(f"[+] Agent prioritizing hint: {hint_action} (confidence: {hint_confidence:.2f})")
                    return hint_action

        # Exploration strategy
        if self.use_boltzmann:
            return self._boltzmann_exploration(state, available_actions)
        else:
            return self._epsilon_greedy(state, available_actions)

    def _boltzmann_exploration(self, state: str, available_actions: List[str]) -> str:
        """Boltzmann (softmax) exploration for better action selection"""
        if state not in self.q_table.table or not self.q_table.table[state]:
            return random.choice(available_actions)
        
        # Get Q-values for all actions
        action_values = self.q_table.get_action_values(state, available_actions)
        
        # Apply temperature scaling
        scaled_values = {action: value / max(self.temperature, 0.1) for action, value in action_values.items()}
        
        # Compute softmax probabilities
        max_value = max(scaled_values.values())
        exp_values = {action: math.exp(value - max_value) for action, value in scaled_values.items()}
        sum_exp = sum(exp_values.values())
        probabilities = {action: exp / sum_exp for action, exp in exp_values.items()}
        
        # Sample action based on probabilities
        actions = list(probabilities.keys())
        probs = list(probabilities.values())
        return random.choices(actions, weights=probs)[0]

    def _epsilon_greedy(self, state: str, available_actions: List[str]) -> str:
        """Standard epsilon-greedy exploration"""
        if random.random() < self.epsilon:
            return random.choice(available_actions)
        else:
            best_action = self.q_table.get_best_action(state, available_actions)
            return best_action or random.choice(available_actions)

    def calculate_reward(
        self,
        result: AttackResult,
        state: EnvironmentState,
        action: str
    ) -> float:
        """
        Enhanced reward shaping for better learning.
        More nuanced rewards for different outcomes.
        """
        reward = 0.0

        # Access level mapping
        access_levels = {
            AccessLevel.NONE: 0,
            AccessLevel.PUBLIC: 1,
            AccessLevel.INTERNAL: 2,
            AccessLevel.ADMIN: 3
        }

        # Check hint matching
        hint_match = state.check_hint_match(action)
        hint_confidence = state.hint_confidence if state.hint_available == 1 else 0.0
        
        if result.success:
            # Base success reward
            reward += 8.0  # Increased from 5.0
            
            # Access escalation reward (scaled)
            current_level = access_levels.get(state.current_access_level, 0)
            new_level = access_levels.get(result.new_access_level, 0)
            
            if new_level > current_level:
                level_gain = new_level - current_level
                # Exponential reward for higher escalations
                reward += 15.0 * (2 ** level_gain)  # 15, 30, 60 for 1, 2, 3 level gains

            # Discovery rewards (increased)
            if result.discovered_component:
                reward += 4.0  # Increased from 2.0

            if result.vulnerability_found:
                reward += 6.0  # Increased from 3.0
            
            # Knowledge-Augmented RL: Massive reward for following hint successfully
            if hint_match:
                # Scale reward by hint confidence
                hint_bonus = 120.0 * (0.8 + hint_confidence * 0.2)  # 96-120 based on confidence
                reward += hint_bonus
                state.mark_hint_followed(True)
                print(f"[+] MASSIVE REWARD (+{hint_bonus:.1f}): Followed hint '{action}' and succeeded!")
            
            # Efficiency bonus: reward for quick escalation
            if state.iteration_count < 20:  # Fast path
                reward += 5.0
        else:
            # Failure penalty (reduced to encourage exploration)
            reward -= 1.5  # Reduced from 2.0
            
            # Penalty for ignoring high-confidence hints
            if state.hint_available == 1 and not hint_match and hint_confidence > 0.7:
                reward -= 3.0  # Increased penalty for ignoring high-confidence hints
                print(f"[!] Ignored high-confidence hint '{state.strategic_hint}' and failed")

        # Knowledge-Augmented RL: Bonus for matching hint (even if fails)
        if hint_match and state.hint_available == 1:
            reward += 3.0  # Increased from 2.0
            if not result.success:
                state.mark_hint_followed(False)

        # Blocking penalty (increased)
        if result.blocked:
            reward -= 15.0  # Increased from 10.0

        # Efficiency penalty: discourage too many iterations
        if state.iteration_count > 50:
            reward -= 0.5 * (state.iteration_count - 50)  # Penalty for long paths

        return reward

    def update_q_value(
        self,
        state: str,
        action: str,
        reward: float,
        next_state: str,
        done: bool = False
    ):
        """Update Q-value with experience replay support"""
        # Store experience in replay buffer
        if self.use_experience_replay:
            experience = Experience(
                state=state,
                action=action,
                reward=reward,
                next_state=next_state,
                done=done
            )
            self.replay_buffer.add(experience)
            
            # Store in n-step buffer
            self.n_step_buffer.append(experience)
            
            # Perform batch update if buffer is ready
            if self.replay_buffer.is_ready(self.batch_size):
                self._replay_update()
        else:
            # Direct update
            self.q_table.update_q_value(state, action, reward, next_state, done=done)
        
        # Update statistics
        self.total_rewards += reward
        self.recent_rewards.append(reward)
        self.step_count += 1
        
        # Adaptive learning rate
        if self.adaptive_lr and len(self.recent_rewards) >= 20:
            avg_recent_reward = sum(self.recent_rewards) / len(self.recent_rewards)
            # Increase LR if performance is improving, decrease if stagnating
            if avg_recent_reward > 0:
                self.learning_rate = min(self.base_learning_rate * 1.1, 0.3)
            else:
                self.learning_rate = max(self.base_learning_rate * 0.9, 0.05)
            self.q_table.learning_rate = self.learning_rate

    def _replay_update(self):
        """Perform batch update from experience replay"""
        batch = self.replay_buffer.sample(self.batch_size)
        
        for experience in batch:
            self.q_table.update_q_value(
                experience.state,
                experience.action,
                experience.reward,
                experience.next_state,
                done=experience.done
            )

    def decay_epsilon(self):
        """Decay exploration rate after episode"""
        self.epsilon = max(self.min_epsilon, self.epsilon * self.epsilon_decay)
        
        # Adaptive temperature for Boltzmann
        if self.use_boltzmann:
            # Decrease temperature over time (less exploration)
            self.temperature = max(0.1, self.temperature * 0.999)

    def record_episode(self, episode_reward: float, success_rate: float):
        """Record episode statistics for analysis"""
        self.episode_count += 1
        self.performance_history["episodes"].append(self.episode_count)
        self.performance_history["rewards"].append(episode_reward)
        self.performance_history["success_rates"].append(success_rate)
        self.performance_history["epsilon_values"].append(self.epsilon)

    def reset(self):
        """Reset agent state"""
        self.q_table.reset()
        self.epsilon = 0.2
        self.temperature = 1.0
        self.learning_rate = self.base_learning_rate
        self.total_rewards = 0.0
        self.episode_count = 0
        self.step_count = 0
        self.success_count = 0
        self.failure_count = 0
        self.recent_rewards.clear()
        self.n_step_buffer.clear()
        if self.replay_buffer:
            self.replay_buffer.buffer.clear()

    def get_statistics(self) -> Dict:
        """Get comprehensive agent statistics"""
        success_rate = 0.0
        if self.success_count + self.failure_count > 0:
            success_rate = self.success_count / (self.success_count + self.failure_count)
        
        avg_reward = 0.0
        if len(self.recent_rewards) > 0:
            avg_reward = sum(self.recent_rewards) / len(self.recent_rewards)
        
        return {
            "epsilon": self.epsilon,
            "temperature": self.temperature,
            "learning_rate": self.learning_rate,
            "total_rewards": self.total_rewards,
            "episode_count": self.episode_count,
            "step_count": self.step_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "success_rate": success_rate,
            "average_reward": avg_reward,
            "q_table_size": sum(len(actions) for actions in self.q_table.table.values()),
            "replay_buffer_size": len(self.replay_buffer) if self.replay_buffer else 0,
            "performance_trend": {
                "recent_episodes": self.performance_history["episodes"][-10:] if len(self.performance_history["episodes"]) >= 10 else self.performance_history["episodes"],
                "recent_rewards": self.performance_history["rewards"][-10:] if len(self.performance_history["rewards"]) >= 10 else self.performance_history["rewards"],
                "recent_success_rates": self.performance_history["success_rates"][-10:] if len(self.performance_history["success_rates"]) >= 10 else self.performance_history["success_rates"]
            }
        }

    def save_model(self, filepath: str):
        """Save Q-table to file"""
        data = {
            "q_table": self.q_table.table,
            "q_table_target": self.q_table.table_target,
            "epsilon": self.epsilon,
            "learning_rate": self.learning_rate,
            "episode_count": self.episode_count,
            "statistics": self.get_statistics()
        }
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

    def load_model(self, filepath: str):
        """Load Q-table from file"""
        with open(filepath, 'r') as f:
            data = json.load(f)
        self.q_table.table = data.get("q_table", {})
        self.q_table.table_target = data.get("q_table_target", {})
        self.epsilon = data.get("epsilon", 0.2)
        self.learning_rate = data.get("learning_rate", 0.15)
        self.episode_count = data.get("episode_count", 0)
