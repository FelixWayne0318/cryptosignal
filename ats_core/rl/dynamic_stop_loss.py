# coding: utf-8
"""
强化学习动态止损系统（DQN框架）

理论基础：Deep Q-Network (DQN)
- State: [profit%, hold_time, volatility, signal_prob, market_regime]
- Action: [保持止损, 移至breakeven, 收紧10%, 放宽10%]
- Reward: 最终盈亏 + 风险调整

训练流程：
1. 收集历史交易数据
2. 训练DQN模型
3. 回测验证
4. 实盘部署

使用方法：
    from ats_core.rl.dynamic_stop_loss import DynamicStopLossAgent

    agent = DynamicStopLossAgent()
    agent.load_model("models/dqn_stop_loss_v1.pth")

    # 在交易中使用
    action = agent.get_action(state)
    new_stop_loss = agent.apply_action(current_stop_loss, action)

注意：
- 需要大量历史交易数据训练
- 建议先用模拟数据训练
- 实盘前充分回测
"""

from __future__ import annotations
import numpy as np
from typing import List, Tuple, Dict, Any, Optional
from collections import deque
import random


class ReplayBuffer:
    """经验回放缓冲区"""

    def __init__(self, capacity: int = 10000):
        self.buffer = deque(maxlen=capacity)

    def push(self, state, action, reward, next_state, done):
        """添加经验"""
        self.buffer.append((state, action, reward, next_state, done))

    def sample(self, batch_size: int) -> List:
        """随机采样"""
        return random.sample(self.buffer, min(batch_size, len(self.buffer)))

    def __len__(self):
        return len(self.buffer)


class DynamicStopLossAgent:
    """
    动态止损DQN智能体

    State (5维):
        - profit_pct: 当前盈亏百分比 (-10% to +50%)
        - hold_time_hours: 持仓时间（小时）(0-72h)
        - volatility: 当前波动率 (0-5%)
        - signal_probability: 信号概率 (0-1)
        - market_regime: 市场体制 (-100 to +100)

    Action (4个):
        0: 保持当前止损
        1: 移至breakeven（盈亏平衡点）
        2: 收紧10%（向entry靠近）
        3: 放宽10%（远离entry）

    Reward:
        - 触发止损: -abs(loss_pct) * 100
        - 止盈出场: +profit_pct * 100
        - 持仓中: -0.1 * hold_time (持仓成本)
    """

    def __init__(
        self,
        state_dim: int = 5,
        action_dim: int = 4,
        learning_rate: float = 0.001,
        gamma: float = 0.99,
        epsilon: float = 1.0,
        epsilon_decay: float = 0.995,
        epsilon_min: float = 0.01
    ):
        """
        Args:
            state_dim: 状态维度
            action_dim: 动作维度
            learning_rate: 学习率
            gamma: 折扣因子
            epsilon: 探索率
            epsilon_decay: 探索率衰减
            epsilon_min: 最小探索率
        """
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.learning_rate = learning_rate
        self.gamma = gamma
        self.epsilon = epsilon
        self.epsilon_decay = epsilon_decay
        self.epsilon_min = epsilon_min

        # 经验回放
        self.replay_buffer = ReplayBuffer(capacity=10000)

        # Q网络（需要PyTorch实现，这里提供接口）
        self.q_network = None  # TODO: 实现神经网络
        self.target_network = None  # TODO: 实现目标网络

        # 统计
        self.training_steps = 0
        self.episode_rewards = []

        print("[DQN] 动态止损智能体初始化完成")
        print("[DQN] ⚠️ 注意：需要安装 PyTorch: pip install torch")
        print("[DQN] ⚠️ 需要历史交易数据进行训练")

    def get_action(self, state: np.ndarray, explore: bool = True) -> int:
        """
        根据状态选择动作

        Args:
            state: 状态向量 (5维)
            explore: 是否探索（训练时True，推理时False）

        Returns:
            动作索引 (0-3)
        """
        # ε-greedy策略
        if explore and np.random.rand() < self.epsilon:
            return np.random.randint(self.action_dim)

        # Q网络推理（TODO: 实现）
        # q_values = self.q_network(state)
        # return np.argmax(q_values)

        # 临时策略（模拟）
        if state[0] > 0.05:  # 盈利>5%
            return 1  # 移至breakeven
        elif state[0] < -0.03:  # 亏损>3%
            return 0  # 保持止损
        elif state[4] > 60:  # 强势市场
            return 3  # 放宽止损
        else:
            return 0  # 默认保持

    def apply_action(
        self,
        entry_price: float,
        current_price: float,
        current_stop_loss: float,
        action: int,
        direction: str = "LONG"
    ) -> float:
        """
        应用动作，计算新的止损价格

        Args:
            entry_price: 入场价格
            current_price: 当前价格
            current_stop_loss: 当前止损价
            action: 动作索引
            direction: 方向（LONG/SHORT）

        Returns:
            新的止损价格
        """
        if direction == "LONG":
            if action == 0:
                # 保持
                new_stop_loss = current_stop_loss

            elif action == 1:
                # 移至breakeven
                new_stop_loss = entry_price * 0.998  # 略低于entry，覆盖手续费

            elif action == 2:
                # 收紧10%
                distance = current_price - current_stop_loss
                new_stop_loss = current_stop_loss + distance * 0.1

            elif action == 3:
                # 放宽10%
                distance = current_price - current_stop_loss
                new_stop_loss = current_stop_loss - distance * 0.1

            else:
                new_stop_loss = current_stop_loss

            # 确保止损不高于当前价
            new_stop_loss = min(new_stop_loss, current_price * 0.995)

        else:  # SHORT
            if action == 0:
                new_stop_loss = current_stop_loss

            elif action == 1:
                new_stop_loss = entry_price * 1.002

            elif action == 2:
                distance = current_stop_loss - current_price
                new_stop_loss = current_stop_loss - distance * 0.1

            elif action == 3:
                distance = current_stop_loss - current_price
                new_stop_loss = current_stop_loss + distance * 0.1

            else:
                new_stop_loss = current_stop_loss

            # 确保止损不低于当前价
            new_stop_loss = max(new_stop_loss, current_price * 1.005)

        return new_stop_loss

    def train_step(self, batch_size: int = 64) -> Optional[float]:
        """
        训练一步

        Args:
            batch_size: 批量大小

        Returns:
            损失值
        """
        if len(self.replay_buffer) < batch_size:
            return None

        # 采样
        batch = self.replay_buffer.sample(batch_size)

        # TODO: 实现DQN训练逻辑
        # 1. 解包batch
        # 2. 计算Q值
        # 3. 计算目标Q值
        # 4. 计算loss
        # 5. 反向传播
        # 6. 更新参数

        # 更新epsilon
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)

        self.training_steps += 1

        return 0.0  # 临时返回

    def train_episode(
        self,
        trade_data: Dict[str, Any],
        verbose: bool = False
    ) -> float:
        """
        训练一个交易episode

        Args:
            trade_data: 交易数据，包含:
                - entry_price: 入场价
                - klines: K线数据
                - signal_prob: 信号概率
                - market_regime: 市场体制
                - direction: 方向
            verbose: 是否打印详细信息

        Returns:
            Episode总奖励
        """
        # TODO: 实现完整训练流程
        # 1. 初始化状态
        # 2. 循环直到交易结束
        # 3. 选择动作
        # 4. 执行动作
        # 5. 计算奖励
        # 6. 存储经验
        # 7. 训练网络

        episode_reward = 0.0

        if verbose:
            print(f"[DQN] Episode完成，奖励: {episode_reward:.2f}")

        self.episode_rewards.append(episode_reward)
        return episode_reward

    def save_model(self, path: str) -> None:
        """保存模型"""
        print(f"[DQN] 保存模型到 {path}")
        # TODO: 实现模型保存
        # torch.save(self.q_network.state_dict(), path)

    def load_model(self, path: str) -> None:
        """加载模型"""
        print(f"[DQN] 从 {path} 加载模型")
        # TODO: 实现模型加载
        # self.q_network.load_state_dict(torch.load(path))

    def get_stats(self) -> Dict[str, Any]:
        """获取训练统计"""
        return {
            'training_steps': self.training_steps,
            'epsilon': self.epsilon,
            'buffer_size': len(self.replay_buffer),
            'avg_reward_100ep': np.mean(self.episode_rewards[-100:]) if self.episode_rewards else 0.0
        }


# ========== 工具函数 ==========

def build_state(
    entry_price: float,
    current_price: float,
    entry_time: float,
    current_time: float,
    volatility: float,
    signal_probability: float,
    market_regime: float
) -> np.ndarray:
    """
    构建状态向量

    Returns:
        状态向量 (5维)
    """
    # 1. 盈亏百分比
    profit_pct = (current_price - entry_price) / entry_price

    # 2. 持仓时间（小时）
    hold_time_hours = (current_time - entry_time) / 3600

    # 3. 波动率 (归一化)
    volatility_norm = volatility  # 假设已归一化

    # 4. 信号概率
    signal_prob_norm = signal_probability

    # 5. 市场体制（归一化到[-1, 1]）
    market_regime_norm = market_regime / 100.0

    state = np.array([
        profit_pct,
        hold_time_hours / 72.0,  # 归一化到0-1
        volatility_norm,
        signal_prob_norm,
        market_regime_norm
    ], dtype=np.float32)

    return state


# ========== 测试代码 ==========

if __name__ == "__main__":
    print("=" * 70)
    print("强化学习动态止损系统测试")
    print("=" * 70)

    # 创建智能体
    agent = DynamicStopLossAgent()

    # 测试场景
    print("\n[测试1] 盈利5%，市场强势")
    state = build_state(
        entry_price=50000,
        current_price=52500,
        entry_time=0,
        current_time=7200,  # 2小时
        volatility=0.02,
        signal_probability=0.75,
        market_regime=70
    )
    action = agent.get_action(state, explore=False)
    print(f"  状态: profit=+5%, hold=2h, vol=2%, prob=75%, regime=+70")
    print(f"  动作: {action} ({'保持/移平/收紧/放宽'.split('/')[action]})")

    # 应用动作
    new_sl = agent.apply_action(
        entry_price=50000,
        current_price=52500,
        current_stop_loss=49000,
        action=action,
        direction="LONG"
    )
    print(f"  旧止损: 49000, 新止损: {new_sl:.0f}")

    print("\n[测试2] 亏损3%，市场震荡")
    state = build_state(
        entry_price=50000,
        current_price=48500,
        entry_time=0,
        current_time=3600,  # 1小时
        volatility=0.03,
        signal_probability=0.55,
        market_regime=10
    )
    action = agent.get_action(state, explore=False)
    print(f"  状态: profit=-3%, hold=1h, vol=3%, prob=55%, regime=+10")
    print(f"  动作: {action} ({'保持/移平/收紧/放宽'.split('/')[action]})")

    new_sl = agent.apply_action(
        entry_price=50000,
        current_price=48500,
        current_stop_loss=49000,
        action=action,
        direction="LONG"
    )
    print(f"  旧止损: 49000, 新止损: {new_sl:.0f}")

    # 统计
    print(f"\n统计: {agent.get_stats()}")

    print("\n" + "=" * 70)
    print("✅ 强化学习止损框架测试完成")
    print("=" * 70)
    print("\n📌 训练步骤：")
    print("1. pip install torch numpy")
    print("2. 收集历史交易数据（至少1000笔）")
    print("3. 实现Q网络（3层MLP: 5→64→64→4）")
    print("4. 训练agent（建议10000+ episodes）")
    print("5. 回测验证")
    print("6. 实盘部署")
