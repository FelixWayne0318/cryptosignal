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
from collections import defaultdict
from typing import Dict, Any, List, Tuple


class EmpiricalCalibrator:
    """
    统计校准器（经验校准）

    使用历史信号的实际结果，校准confidence到真实胜率的映射
    """

    def __init__(self, storage_path: str = "data/calibration_history.json"):
        """
        初始化校准器

        Args:
            storage_path: 历史记录存储路径
        """
        self.storage_path = storage_path
        self.history = self._load_history()
        self.calibration_table = {}
        self._update_table()

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
        """
        if len(self.history) < 50:  # 至少50个样本
            print(f"[Calibration] 数据不足({len(self.history)}/50)，使用启发式规则")
            return

        # 分桶统计
        buckets = defaultdict(lambda: {"wins": 0, "total": 0})

        for record in self.history:
            conf = record['confidence']
            bucket = int(conf // 10) * 10  # 10分一档：0-10, 10-20, ..., 90-100

            buckets[bucket]["total"] += 1
            if record['result'] == "win":
                buckets[bucket]["wins"] += 1

        # 计算每个桶的实际胜率
        new_table = {}
        for bucket, stats in buckets.items():
            if stats["total"] >= 10:  # 至少10个样本才可靠
                winrate = stats["wins"] / stats["total"]
                new_table[bucket] = winrate
                print(f"  Bucket {bucket}-{bucket+10}: {winrate:.2%} ({stats['wins']}/{stats['total']})")

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

    def _bootstrap_probability(self, confidence: float) -> float:
        """
        启发式概率（冷启动）

        简单线性映射：
        - confidence=0 → P=0.40
        - confidence=50 → P=0.50
        - confidence=100 → P=0.70

        理由：
        - 0.40：即使信号很弱，也有40%胜率（市场随机性）
        - 0.50：中性信号，50%胜率
        - 0.70：强信号，70%胜率（不能过高，避免过度自信）

        Args:
            confidence: 信号置信度 (0-100)

        Returns:
            估算的胜率 (0.35-0.75)
        """
        # 线性映射
        P = 0.40 + (confidence / 100.0) * 0.30

        # 限制范围
        return max(0.35, min(0.75, P))

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
