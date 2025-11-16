# coding: utf-8
"""
统计校准器（v7.2阶段1）

核心理念：
- 用历史信号的实际结果，校准confidence → 真实胜率的映射
- 不需要ML训练，只需简单的分桶统计
- 随着交易积累，自动优化

工作原理：
1. 收集历史信号：每个信号记录confidence和结果（win/loss）
2. 分桶统计：把confidence分成10个桶（0-10, 10-20, ..., 90-100）
3. 计算每个桶的实际胜率
4. 新信号查表：confidence=65 → 查桶60-70 → 返回该桶的实际胜率

冷启动：
- 初期没有历史数据时，使用启发式规则（线性映射）
- 积累50+个信号后，开始使用统计校准
- 积累500+个信号后，校准稳定

示例：
    calibrator = EmpiricalCalibrator()

    # 新信号
    P_calibrated = calibrator.get_calibrated_probability(confidence=65)

    # 交易结束后记录结果
    calibrator.record_signal_result(confidence=65, result="win")
"""

import json
import os
import time
import math
from collections import defaultdict
from typing import Dict, Any, List, Tuple, Optional


class EmpiricalCalibrator:
    """
    统计校准器（经验校准）

    使用历史信号的实际结果，校准confidence到真实胜率的映射

    v7.3.44 P0修复：添加幸存者偏差修复
    - 时间衰减：旧数据权重降低
    - MTM估值：包含未平仓信号（使用当前市价估值）
    """

    def __init__(self, storage_path: str = "data/calibration_history.json", silent: bool = False, recorder=None):
        """
        初始化校准器

        Args:
            storage_path: 历史记录存储路径
            silent: 是否静默模式（不打印初始化日志）
            recorder: TradeRecorder实例（用于获取未平仓信号）
        """
        self.storage_path = storage_path
        self.history = self._load_history()
        self.calibration_table = {}
        self._silent = silent
        self.recorder = recorder

        # v7.3.44 P0修复：加载配置
        self._load_config()

        self._update_table()

        # v7.3.41：只在初始化时打印一次状态信息
        if not self._silent:
            if len(self.history) < 30:
                print(f"[Calibration] 初始化完成：数据不足({len(self.history)}/30)，使用启发式规则")
            else:
                print(f"[Calibration] 初始化完成：已加载 {len(self.history)} 条历史记录，使用统计校准")
                # v7.3.44：打印P0修复配置状态
                if self.include_mtm_unrealized:
                    print(f"[Calibration] P0修复已启用：时间衰减={self.decay_period_days}天，MTM权重={self.mtm_weight_factor}")

    def _load_config(self):
        """
        v7.3.44 P0修复：加载统计校准配置

        从config/signal_thresholds.json读取：
        - decay_period_days: 时间衰减周期
        - include_mtm_unrealized: 是否包含未平仓MTM估值
        - mtm_weight_factor: 未平仓信号权重因子
        """
        try:
            from ats_core.config.threshold_config import get_thresholds
            config = get_thresholds()
            calib_config = config.config.get('统计校准参数', {})

            self.decay_period_days = calib_config.get('decay_period_days', 30)
            self.include_mtm_unrealized = calib_config.get('include_mtm_unrealized', False)
            self.mtm_weight_factor = calib_config.get('mtm_weight_factor', 0.5)

            # 验证配置
            assert self.decay_period_days > 0, f"decay_period_days必须>0，当前={self.decay_period_days}"
            assert 0 < self.mtm_weight_factor <= 1.0, f"mtm_weight_factor必须在(0,1]，当前={self.mtm_weight_factor}"
        except Exception as e:
            # 配置加载失败时使用默认值
            if not self._silent:
                print(f"[Calibration] 配置加载失败，使用默认值: {e}")
            self.decay_period_days = 30
            self.include_mtm_unrealized = False
            self.mtm_weight_factor = 0.5

    def _load_history(self) -> List[Dict[str, Any]]:
        """加载历史记录"""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                return []
        return []

    def _save_history(self):
        """保存历史记录"""
        try:
            os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
            with open(self.storage_path, 'w') as f:
                json.dump(self.history, f, indent=2)
        except Exception as e:
            print(f"[Calibration] 保存历史记录失败: {e}")

    def record_signal_result(self, confidence: float, result: str, metadata: Dict[str, Any] = None):
        """
        记录信号结果

        Args:
            confidence: 信号置信度 (0-100)
            result: "win" 或 "loss"
            metadata: 可选的元数据（如symbol, F_score等）
        """
        record = {
            "confidence": confidence,
            "result": result,
            "timestamp": time.time()
        }

        if metadata:
            record["metadata"] = metadata

        self.history.append(record)
        self._save_history()

        # 每100个新记录重新计算校准表
        if len(self.history) % 100 == 0:
            self._update_table()
            print(f"[Calibration] 已累积 {len(self.history)} 个信号，重新校准")

    def _update_table(self):
        """
        更新校准表

        分桶统计：把confidence分成10个桶，计算每个桶的实际胜率

        v7.3.44 P0修复：
        - 时间衰减：旧数据权重降低（exp(-age/decay_period)）
        - MTM估值：包含未平仓信号（权重=mtm_weight_factor）
        """
        # P0.3修复：降低启用阈值从50→30，加快冷启动
        # v7.3.41修复：移除重复日志，只在初始化时打印一次
        if len(self.history) < 30:  # 至少30个样本
            return

        # 当前时间（用于计算age）
        current_time = time.time()

        # 分桶统计（使用加权统计）
        buckets = defaultdict(lambda: {"weighted_wins": 0.0, "weighted_total": 0.0, "count": 0})

        # 1. 处理已平仓信号（权重=1.0，带时间衰减）
        for record in self.history:
            conf = record['confidence']
            bucket = int(conf // 10) * 10  # 10分一档：0-10, 10-20, ..., 90-100

            # v7.3.44：计算时间衰减权重
            age_seconds = current_time - record.get('timestamp', current_time)
            age_days = age_seconds / 86400.0
            decay_weight = math.exp(-age_days / self.decay_period_days) if self.decay_period_days > 0 else 1.0

            # 已平仓信号权重=1.0（基础权重）* decay_weight（时间衰减）
            signal_weight = 1.0 * decay_weight

            buckets[bucket]["weighted_total"] += signal_weight
            buckets[bucket]["count"] += 1
            if record['result'] == "win":
                buckets[bucket]["weighted_wins"] += signal_weight

        # 2. v7.3.44 P0修复：包含未平仓信号MTM估值（如果启用）
        if self.include_mtm_unrealized and self.recorder is not None:
            open_signals_mtm = self._get_open_signals_mtm()
            for signal_data in open_signals_mtm:
                conf = signal_data.get('confidence', 50)
                bucket = int(conf // 10) * 10

                # 未平仓信号使用MTM估值 + 较低权重
                mtm_is_win = signal_data.get('mtm_is_win', False)
                signal_weight = self.mtm_weight_factor  # 默认0.5

                buckets[bucket]["weighted_total"] += signal_weight
                buckets[bucket]["count"] += 1
                if mtm_is_win:
                    buckets[bucket]["weighted_wins"] += signal_weight

        # 计算每个桶的加权胜率
        new_table = {}
        for bucket, stats in buckets.items():
            if stats["count"] >= 10:  # 至少10个样本才可靠
                winrate = stats["weighted_wins"] / stats["weighted_total"] if stats["weighted_total"] > 0 else 0.5
                new_table[bucket] = winrate
                # v7.3.44：显示加权统计信息
                if not self._silent:
                    print(f"  Bucket {bucket}-{bucket+10}: {winrate:.2%} (加权胜利={stats['weighted_wins']:.1f}/加权总数={stats['weighted_total']:.1f}, 样本数={stats['count']})")

        self.calibration_table = new_table

        # 保存校准表到文件
        table_path = self.storage_path.replace('.json', '_table.json')
        try:
            with open(table_path, 'w') as f:
                json.dump({
                    "calibration_table": self.calibration_table,
                    "total_signals": len(self.history),
                    "last_update": time.time()
                }, f, indent=2)
        except Exception as e:
            print(f"[Calibration] 保存校准表失败: {e}")

    def get_calibrated_probability(self, confidence: float) -> float:
        """
        获取校准后的概率

        如果没有足够历史数据，使用启发式规则

        Args:
            confidence: 信号置信度 (0-100)

        Returns:
            校准后的胜率 (0.0-1.0)
        """
        # 如果没有校准表（数据不足），使用启发式规则
        if not self.calibration_table:
            return self._bootstrap_probability(confidence)

        # 查表
        bucket = int(confidence // 10) * 10

        # 直接命中
        if bucket in self.calibration_table:
            return self.calibration_table[bucket]

        # 插值（如果相邻桶都有数据）
        lower = bucket - 10
        upper = bucket + 10

        if lower in self.calibration_table and upper in self.calibration_table:
            # 线性插值
            p_lower = self.calibration_table[lower]
            p_upper = self.calibration_table[upper]
            # confidence在桶内的位置（0-1）
            weight = (confidence - lower) / 20.0
            return p_lower * (1 - weight) + p_upper * weight

        # 降级到启发式
        return self._bootstrap_probability(confidence)

    def _bootstrap_probability(self, confidence: float, F_score: float = None, I_score: float = None, side_long: bool = True) -> float:
        """
        启发式概率（v7.3.48改进：修复空单F逻辑）

        线性映射 + F/I因子线性调整：
        - confidence=0 → P=0.45（基准）
        - confidence=50 → P=0.52
        - confidence=100 → P=0.68
        - F因子线性调整：F在[-30, 0, 70]之间线性调整P（-3% ~ +5%）
        - I因子线性调整：I在[20, 50, 80]之间线性调整P（-2% ~ +3%）

        v7.3.48改进：
        - ✅ 修复空单F逻辑：添加side_long参数，使用get_effective_F

        v7.3.47改进：
        - ✅ 移除硬编码的F>30/15/-30（违反规范）
        - ✅ 改为线性平滑调整（避免断崖效应）
        - ✅ 参数从配置文件读取（可调整）
        - ✅ 与v7.3.46蓄势分级一致（都使用线性）

        Args:
            confidence: 信号置信度 (0-100)
            F_score: F因子分数 [-100, +100]（可选）
            I_score: I因子分数 [0, 100]（可选）
            side_long: 做多(True)还是做空(False)，默认True

        Returns:
            估算的胜率 (0.40-0.75)
        """
        # 导入线性函数工具
        from ats_core.utils.math_utils import linear_reduce, get_effective_F
        from ats_core.config.threshold_config import get_thresholds

        # 基础线性映射（改进后的范围）
        P = 0.45 + (confidence / 100.0) * 0.23  # 45%-68%范围

        # 读取概率校准配置（v7.3.47新增）
        try:
            config = get_thresholds()
            prob_calib_config = config.config.get('概率校准线性参数', {})

            # F因子线性调整（v7.3.48改进：修复空单F逻辑）
            if F_score is not None:
                F_calib_config = prob_calib_config.get('F因子线性校准', {})
                F_enabled = F_calib_config.get('_enabled', True)

                if F_enabled:
                    F_max = F_calib_config.get('F_bonus_threshold_max', 70)
                    F_min = F_calib_config.get('F_bonus_threshold_min', -30)
                    P_bonus_max = F_calib_config.get('P_bonus_at_F_max', 0.05)
                    P_penalty_min = F_calib_config.get('P_penalty_at_F_min', -0.03)

                    # v7.3.48修复：使用F_effective考虑多空方向
                    F_effective = get_effective_F(F_score, side_long)

                    # 线性调整：F在[-30, 0, 70]之间线性插值
                    if F_effective >= F_max:
                        P += P_bonus_max  # F≥70: +5%
                    elif F_effective >= 0:
                        # F在0~70之间线性增加（0% ~ +5%）
                        P_bonus = linear_reduce(F_effective, 0, F_max, 0, P_bonus_max)
                        P += P_bonus
                    elif F_effective >= F_min:
                        # F在-30~0之间线性减少（-3% ~ 0%）
                        P_penalty = linear_reduce(F_effective, F_min, 0, P_penalty_min, 0)
                        P += P_penalty
                    else:
                        P += P_penalty_min  # F≤-30: -3%

            # I因子线性调整（v7.3.47改进：同样改为线性）
            if I_score is not None:
                I_calib_config = prob_calib_config.get('I因子线性校准', {})
                I_enabled = I_calib_config.get('_enabled', True)

                if I_enabled:
                    I_max = I_calib_config.get('I_bonus_threshold_max', 80)
                    I_min = I_calib_config.get('I_bonus_threshold_min', 20)
                    P_bonus_max = I_calib_config.get('P_bonus_at_I_max', 0.03)
                    P_penalty_min = I_calib_config.get('P_penalty_at_I_min', -0.02)

                    # 线性调整：I在[20, 50, 80]之间线性插值
                    if I_score >= I_max:
                        P += P_bonus_max  # I≥80: +3%
                    elif I_score >= 50:
                        # I在50~80之间线性增加（0% ~ +3%）
                        P_bonus = linear_reduce(I_score, 50, I_max, 0, P_bonus_max)
                        P += P_bonus
                    elif I_score >= I_min:
                        # I在20~50之间保持0%（中性）
                        pass
                    else:
                        # I<20: 线性减少至-2%
                        P_penalty = linear_reduce(I_score, 0, I_min, P_penalty_min, 0)
                        P += P_penalty

        except Exception as e:
            # 配置加载失败，使用保守的默认值（不调整）
            pass

        # 限制范围
        return max(0.40, min(0.75, P))

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取统计信息

        Returns:
            统计字典
        """
        if not self.history:
            return {
                "total_signals": 0,
                "status": "no_data"
            }

        total = len(self.history)
        wins = sum(1 for r in self.history if r['result'] == 'win')
        winrate = wins / total if total > 0 else 0

        return {
            "total_signals": total,
            "wins": wins,
            "losses": total - wins,
            "overall_winrate": winrate,
            "calibration_status": "active" if self.calibration_table else "bootstrap",
            "buckets_calibrated": len(self.calibration_table),
            "calibration_table": self.calibration_table
        }

    def reset_history(self):
        """清空历史记录（慎用！）"""
        self.history = []
        self.calibration_table = {}
        self._save_history()
        print("[Calibration] 历史记录已清空")

    def _get_open_signals_mtm(self) -> List[Dict[str, Any]]:
        """
        v7.3.44 P0修复：获取未平仓信号的MTM（Mark-to-Market）估值

        从TradeRecorder获取未平仓信号，并计算当前盈亏状态

        Returns:
            List of dicts with keys:
            - confidence: 信号置信度
            - mtm_is_win: MTM估值是否为盈利（True/False）
            - mtm_pnl_pct: MTM盈亏百分比（用于调试）

        TODO: 需要外部系统（TradeRecorder/AnalysisDB）提供以下接口：
        - get_open_signals(): 获取所有未平仓信号
        - 每个信号需包含：confidence, entry_price, current_price, side
        """
        if self.recorder is None:
            return []

        try:
            # 尝试从recorder获取未平仓信号
            if hasattr(self.recorder, 'get_open_signals'):
                open_signals = self.recorder.get_open_signals()

                mtm_results = []
                for signal in open_signals:
                    # 获取必要字段
                    confidence = signal.get('confidence', 50)
                    entry_price = signal.get('entry_price', 0)
                    current_price = signal.get('current_price', 0)
                    side_long = signal.get('side_long', True)

                    # 计算MTM盈亏
                    if entry_price > 0 and current_price > 0:
                        if side_long:
                            pnl_pct = (current_price - entry_price) / entry_price
                        else:
                            pnl_pct = (entry_price - current_price) / entry_price

                        # MTM是否为盈利（阈值可以配置，这里简单使用0）
                        mtm_is_win = pnl_pct > 0

                        mtm_results.append({
                            'confidence': confidence,
                            'mtm_is_win': mtm_is_win,
                            'mtm_pnl_pct': pnl_pct
                        })

                return mtm_results
            else:
                # recorder没有get_open_signals方法，返回空列表
                if not self._silent:
                    print("[Calibration] recorder没有get_open_signals()方法，跳过MTM估值")
                return []

        except Exception as e:
            if not self._silent:
                print(f"[Calibration] 获取未平仓信号失败: {e}")
            return []


# 测试代码
if __name__ == "__main__":
    print("=" * 60)
    print("统计校准器测试")
    print("=" * 60)

    # 使用临时文件
    calibrator = EmpiricalCalibrator(storage_path="test_calibration.json")

    # 模拟100个历史信号
    print("\n模拟100个历史信号...")
    import random
    random.seed(42)

    for i in range(100):
        # 模拟：confidence越高，胜率越高
        conf = random.randint(30, 90)

        # 真实胜率 = 0.40 + conf/100 * 0.35（加一点噪音）
        true_winrate = 0.40 + conf / 100.0 * 0.35
        win = random.random() < true_winrate

        result = "win" if win else "loss"
        calibrator.record_signal_result(conf, result, metadata={"test_id": i})

    # 查看统计
    print("\n统计信息:")
    stats = calibrator.get_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    # 测试校准
    print("\n测试校准结果:")
    test_confidences = [40, 55, 70, 85]
    for conf in test_confidences:
        P = calibrator.get_calibrated_probability(conf)
        P_bootstrap = calibrator._bootstrap_probability(conf)
        print(f"  confidence={conf} → P_calibrated={P:.3f}, P_bootstrap={P_bootstrap:.3f}")

    # 清理测试文件
    import os
    try:
        os.remove("test_calibration.json")
        os.remove("test_calibration_table.json")
        print("\n测试文件已清理")
    except:
        pass

    print("\n" + "=" * 60)
