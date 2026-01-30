"""
Reinforcement Learning agent for autonomous attack decision making.
Uses Q-learning to learn optimal attack strategies.
"""

from typing import Dict, List, Optional
import random
import math
from dataclasses import dataclass, field
from attack_engine import AttackResult
from env import EnvironmentState, AccessLevel


@dataclass
class QTable:
    """Q-table for Q-learning algorithm"""
    table: Dict[str, Dict[str, float]] = field(default_factory=dict)
    learning_rate: float = 0.1
    discount_factor: float = 0.9
    epsilon: float = 0.1  # Exploration rate

    def get_q_value(self, state: str, action: str) -> float:
        """Get Q-value for state-action pair"""
        if state not in self.table:
            self.table[state] = {}
        return self.table[state].get(action, 0.0)

    def set_q_value(self, state: str, action: str, value: float):
        """Set Q-value for state-action pair"""
        if state not in self.table:
            self.table[state] = {}
        self.table[state][action] = value

    def update_q_value(
        self,
        state: str,
        action: str,
        reward: float,
        next_state: str,
        learning_rate: float = None,
        discount_factor: float = None
    ):
        """
        Update Q-value using Q-learning formula:
        Q(s,a) = Q(s,a) + α[r + γ * max(Q(s',a')) - Q(s,a)]
        """
        lr = learning_rate or self.learning_rate
        gamma = discount_factor or self.discount_factor

        current_q = self.get_q_value(state, action)
        
        # Get max Q-value for next state
        if next_state in self.table:
            max_next_q = max(self.table[next_state].values()) if self.table[next_state] else 0.0
        else:
            max_next_q = 0.0

        # Q-learning update
        new_q = current_q + lr * (reward + gamma * max_next_q - current_q)
        self.set_q_value(state, action, new_q)

    def get_best_action(self, state: str, available_actions: List[str]) -> Optional[str]:
        """Get action with highest Q-value for given state"""
        if not available_actions:
            return None

        if state not in self.table or not self.table[state]:
            return random.choice(available_actions)

        # Find action with max Q-value
        best_action = None
        best_value = float('-inf')

        for action in available_actions:
            q_value = self.get_q_value(state, action)
            if q_value > best_value:
                best_value = q_value
                best_action = action

        return best_action or random.choice(available_actions)

    def reset(self):
        """Reset Q-table"""
        self.table.clear()


class QLearningAgent:
    """
    Q-learning agent for autonomous attack decision making.
    Learns optimal attack sequences through trial and error.
    """

    def __init__(
        self,
        learning_rate: float = 0.1,
        discount_factor: float = 0.9,
        epsilon: float = 0.1,
        epsilon_decay: float = 0.995,
        min_epsilon: float = 0.01
    ):
        """
        Initialize Q-learning agent.
        
        Args:
            learning_rate: How much new information overrides old (0-1)
            discount_factor: Importance of future rewards (0-1)
            epsilon: Exploration rate (0-1)
            epsilon_decay: Rate at which exploration decreases
            min_epsilon: Minimum exploration rate
        """
        self.q_table = QTable(learning_rate=learning_rate, discount_factor=discount_factor, epsilon=epsilon)
        self.epsilon = epsilon
        self.epsilon_decay = epsilon_decay
        self.min_epsilon = min_epsilon
        self.total_rewards = 0.0
        self.episode_count = 0

    def choose_action(
        self,
        state: str,
        available_actions: List[str],
        environment_state: Optional[EnvironmentState] = None
    ) -> str:
        """
        Choose action using epsilon-greedy policy with Knowledge-Augmented RL.
        Prioritizes strategic hints from Exploit-DB when available.
        
        Args:
            state: Current state key
            available_actions: List of available action strings
            environment_state: Optional EnvironmentState for hint checking
            
        Returns:
            Selected action string
        """
        if not available_actions:
            raise ValueError("No available actions")

        # Knowledge-Augmented RL: Check for strategic hint
        if environment_state and environment_state.hint_available == 1:
            hint_action = environment_state.strategic_hint
            if hint_action and hint_action in available_actions:
                # Prioritize hint action with high probability (80%)
                if random.random() < 0.8:
                    print(f"[+] Agent prioritizing hint: {hint_action}")
                    return hint_action

        # Epsilon-greedy: explore or exploit
        if random.random() < self.epsilon:
            # Explore: choose random action
            return random.choice(available_actions)
        else:
            # Exploit: choose best known action
            best_action = self.q_table.get_best_action(state, available_actions)
            return best_action or random.choice(available_actions)

    def calculate_reward(
        self,
        result: AttackResult,
        state: EnvironmentState,
        action: str
    ) -> float:
        """
        Calculate reward for attack result with Knowledge-Augmented RL hints.
        Reward structure:
        - +10 for deeper access level
        - +5 for successful attack
        - +3 for discovering vulnerability
        - +2 for discovering new component
        - -2 for failed attempt
        - -10 if blocked
        - +2 bonus if action matches hint (trust intel)
        - +100 massive reward if following hint succeeds
        """
        reward = 0.0

        # Access escalation reward
        access_levels = {
            AccessLevel.NONE: 0,
            AccessLevel.PUBLIC: 1,
            AccessLevel.INTERNAL: 2,
            AccessLevel.ADMIN: 3
        }

        # Knowledge-Augmented RL: Check if action matches strategic hint
        hint_match = state.check_hint_match(action)
        
        if result.success:
            reward += 5.0  # Base success reward
            
            current_level = access_levels.get(state.current_access_level, 0)
            new_level = access_levels.get(result.new_access_level, 0)
            
            if new_level > current_level:
                # Escalation reward proportional to level gained
                reward += 10.0 * (new_level - current_level)

            # Discovery rewards
            if result.discovered_component:
                reward += 2.0

            if result.vulnerability_found:
                reward += 3.0
            
            # Knowledge-Augmented RL: Massive reward for following hint successfully
            if hint_match:
                reward += 100.0  # Massive reward for trusting intel and succeeding
                state.mark_hint_followed(True)
                print(f"[+] MASSIVE REWARD (+100): Followed hint '{action}' and succeeded!")
        else:
            reward -= 2.0  # Failure penalty
            
            # Knowledge-Augmented RL: Penalty for ignoring hint and failing
            if state.hint_available == 1 and not hint_match:
                reward -= 1.0  # Small penalty for ignoring available hint
                print(f"[!] Ignored hint '{state.strategic_hint}' and failed")

        # Knowledge-Augmented RL: Small bonus for matching hint (even if fails)
        if hint_match and state.hint_available == 1:
            reward += 2.0  # Bonus for trusting known intel
            if not result.success:
                state.mark_hint_followed(False)

        # Blocking penalty
        if result.blocked:
            reward -= 10.0

        return reward

    def update_q_value(
        self,
        state: str,
        action: str,
        reward: float,
        next_state: str
    ):
        """Update Q-table with new experience"""
        self.q_table.update_q_value(state, action, reward, next_state)
        self.total_rewards += reward

    def decay_epsilon(self):
        """Decay exploration rate after episode"""
        self.epsilon = max(self.min_epsilon, self.epsilon * self.epsilon_decay)

    def reset(self):
        """Reset agent state"""
        self.q_table.reset()
        self.epsilon = 0.1
        self.total_rewards = 0.0
        self.episode_count = 0

    def get_statistics(self) -> Dict:
        """Get agent learning statistics"""
        return {
            "epsilon": self.epsilon,
            "total_rewards": self.total_rewards,
            "episode_count": self.episode_count,
            "q_table_size": sum(len(actions) for actions in self.q_table.table.values())
        }

