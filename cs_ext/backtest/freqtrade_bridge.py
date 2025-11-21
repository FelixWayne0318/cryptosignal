"""
Freqtrade 策略桥接器

将 CryptoSignal 因子系统包装为 Freqtrade 可识别的策略接口。

CryptoSignal 作为"信号引擎"，Freqtrade 负责：
- 回测
- 组合管理
- 成本计算
- 滑点模拟

Usage:
    # 在 freqtrade 的 user_data/strategies/ 目录下创建策略文件
    # 导入此桥接器并配置

    from cs_ext.backtest.freqtrade_bridge import CryptoSignalStrategy

    class MyStrategy(CryptoSignalStrategy):
        # 自定义参数
        pass

Author: Claude Code
Version: v0.1.0
Created: 2025-11-21
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

# 延迟导入freqtrade，允许在未安装时导入模块
try:
    from freqtrade.strategy.interface import IStrategy
    from freqtrade.persistence import Trade
    import pandas as pd
    from pandas import DataFrame
    FREQTRADE_AVAILABLE = True
except ImportError:
    FREQTRADE_AVAILABLE = False
    IStrategy = object
    DataFrame = None

logger = logging.getLogger(__name__)


class CryptoSignalStrategy(IStrategy):
    """
    CryptoSignal 信号引擎的 Freqtrade 策略包装器

    将 CryptoSignal 的四步决策系统集成到 Freqtrade 回测框架中
    """

    # ========== Freqtrade 必需参数 ==========

    # 最小ROI - 可在配置中覆盖
    minimal_roi = {
        "0": 0.10,    # 立即: 10%
        "30": 0.05,   # 30分钟后: 5%
        "60": 0.02,   # 60分钟后: 2%
        "120": 0.01,  # 120分钟后: 1%
    }

    # 止损 - 将被 CryptoSignal Step3 覆盖
    stoploss = -0.05

    # 时间框架
    timeframe = '5m'

    # 启用自定义止损
    use_custom_stoploss = True

    # ========== CryptoSignal 配置 ==========

    # CryptoSignal 配置路径
    cs_config_path: str = "config/params.json"

    # 是否使用 Step3 风险管理的止损
    use_cs_stoploss: bool = True

    # 是否使用 Step4 质量控制
    use_cs_quality_gate: bool = True

    # 最小信号强度阈值
    min_signal_strength: float = 0.3

    # 缓存
    _cs_system = None
    _cs_params = None

    def __init__(self, config: Dict[str, Any]) -> None:
        """初始化策略"""
        if not FREQTRADE_AVAILABLE:
            raise ImportError(
                "Freqtrade 未安装。请运行: pip install freqtrade\n"
                "或者: pip install -e externals/freqtrade"
            )

        super().__init__(config)
        self._load_cryptosignal()

    def _load_cryptosignal(self):
        """加载 CryptoSignal 系统"""
        try:
            # 导入 CryptoSignal 核心模块
            import json
            from ats_core.decision.four_step_system import four_step_decision

            # 加载配置
            config_path = Path(self.cs_config_path)
            if config_path.exists():
                with open(config_path) as f:
                    self._cs_params = json.load(f)
                logger.info(f"Loaded CryptoSignal config from {config_path}")
            else:
                logger.warning(f"CryptoSignal config not found: {config_path}")
                self._cs_params = {}

            self._cs_system = four_step_decision
            logger.info("CryptoSignal system loaded successfully")

        except ImportError as e:
            logger.error(f"Failed to import CryptoSignal: {e}")
            self._cs_system = None

    # ========== Freqtrade 策略接口 ==========

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        计算技术指标

        这里我们使用 CryptoSignal 的因子系统计算指标
        """
        if self._cs_system is None:
            logger.warning("CryptoSignal system not loaded, using empty indicators")
            return dataframe

        # 将 DataFrame 转换为 CryptoSignal 格式的 klines
        klines = self._dataframe_to_klines(dataframe)

        # 为每个时间点计算因子分数
        # 注意：这是简化版本，实际应用中可能需要优化性能
        cs_signals = []

        for i in range(len(klines)):
            if i < 50:  # 需要足够的历史数据
                cs_signals.append({
                    'direction': 0,
                    'timing': 0,
                    'risk_multiplier': 1.0,
                    'quality_passed': False,
                    'signal_strength': 0
                })
                continue

            # 获取历史数据窗口
            window_klines = klines[max(0, i-200):i+1]

            try:
                # 调用 CryptoSignal 四步决策
                result = self._run_cryptosignal(window_klines)
                cs_signals.append(result)
            except Exception as e:
                logger.debug(f"CryptoSignal calculation error at {i}: {e}")
                cs_signals.append({
                    'direction': 0,
                    'timing': 0,
                    'risk_multiplier': 1.0,
                    'quality_passed': False,
                    'signal_strength': 0
                })

        # 将 CryptoSignal 结果添加到 DataFrame
        dataframe['cs_direction'] = [s['direction'] for s in cs_signals]
        dataframe['cs_timing'] = [s['timing'] for s in cs_signals]
        dataframe['cs_risk_mult'] = [s['risk_multiplier'] for s in cs_signals]
        dataframe['cs_quality'] = [s['quality_passed'] for s in cs_signals]
        dataframe['cs_strength'] = [s['signal_strength'] for s in cs_signals]

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        生成入场信号

        基于 CryptoSignal 的方向判断和时机判断
        """
        # 多头入场条件
        dataframe.loc[
            (
                (dataframe['cs_direction'] > 0) &  # Step1: 方向看多
                (dataframe['cs_timing'] > 0) &      # Step2: 时机确认
                (dataframe['cs_quality'] == True) & # Step4: 质量通过
                (dataframe['cs_strength'] >= self.min_signal_strength)  # 信号强度
            ),
            'enter_long'
        ] = 1

        # 空头入场条件（如果支持做空）
        dataframe.loc[
            (
                (dataframe['cs_direction'] < 0) &
                (dataframe['cs_timing'] < 0) &
                (dataframe['cs_quality'] == True) &
                (dataframe['cs_strength'] >= self.min_signal_strength)
            ),
            'enter_short'
        ] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        生成出场信号

        基于 CryptoSignal 的方向反转
        """
        # 多头出场：方向反转为空
        dataframe.loc[
            (dataframe['cs_direction'] < 0) &
            (dataframe['cs_timing'] < 0),
            'exit_long'
        ] = 1

        # 空头出场：方向反转为多
        dataframe.loc[
            (dataframe['cs_direction'] > 0) &
            (dataframe['cs_timing'] > 0),
            'exit_short'
        ] = 1

        return dataframe

    def custom_stoploss(self, pair: str, trade: 'Trade', current_time: datetime,
                        current_rate: float, current_profit: float, **kwargs) -> float:
        """
        自定义止损

        使用 CryptoSignal Step3 的风险管理计算动态止损
        """
        if not self.use_cs_stoploss:
            return self.stoploss

        # 获取最新的 dataframe
        dataframe, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if dataframe.empty:
            return self.stoploss

        # 获取 CryptoSignal 的风险倍数
        last_row = dataframe.iloc[-1]
        risk_mult = last_row.get('cs_risk_mult', 1.0)

        # 基于风险倍数调整止损
        # risk_mult 越小表示风险越高，止损应该越紧
        adjusted_stoploss = self.stoploss * risk_mult

        return max(adjusted_stoploss, -0.10)  # 最大止损 10%

    # ========== 辅助方法 ==========

    def _dataframe_to_klines(self, dataframe: DataFrame) -> List[Dict[str, Any]]:
        """将 Freqtrade DataFrame 转换为 CryptoSignal klines 格式"""
        klines = []
        for _, row in dataframe.iterrows():
            klines.append({
                'timestamp': row['date'].timestamp() * 1000 if hasattr(row['date'], 'timestamp') else row['date'],
                'open': float(row['open']),
                'high': float(row['high']),
                'low': float(row['low']),
                'close': float(row['close']),
                'volume': float(row['volume'])
            })
        return klines

    def _run_cryptosignal(self, klines: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        运行 CryptoSignal 四步决策系统

        Returns:
            {
                'direction': int,      # -1, 0, 1
                'timing': int,         # -1, 0, 1
                'risk_multiplier': float,
                'quality_passed': bool,
                'signal_strength': float
            }
        """
        if self._cs_system is None:
            return {
                'direction': 0,
                'timing': 0,
                'risk_multiplier': 1.0,
                'quality_passed': False,
                'signal_strength': 0
            }

        try:
            # 构造因子分数序列（简化版本）
            # 实际应用中应该使用完整的因子计算
            factor_scores = self._calculate_factors(klines)

            # 调用四步决策
            result = self._cs_system(
                factor_scores_series=[factor_scores],
                klines=klines,
                s_factor_meta={},
                params=self._cs_params or {}
            )

            # 提取关键信息
            direction = result.get('step1', {}).get('direction_score', 0)
            timing = result.get('step2', {}).get('enhanced_f', 0)
            risk_mult = result.get('step3', {}).get('risk_score', 1.0)
            quality = result.get('step4', {}).get('quality_passed', False)

            # 计算综合信号强度
            strength = abs(direction) * abs(timing) * risk_mult
            if not quality:
                strength *= 0.5  # 质量未通过则降低强度

            return {
                'direction': 1 if direction > 0 else (-1 if direction < 0 else 0),
                'timing': 1 if timing > 0 else (-1 if timing < 0 else 0),
                'risk_multiplier': risk_mult,
                'quality_passed': quality if self.use_cs_quality_gate else True,
                'signal_strength': min(strength, 1.0)
            }

        except Exception as e:
            logger.error(f"CryptoSignal execution error: {e}")
            return {
                'direction': 0,
                'timing': 0,
                'risk_multiplier': 1.0,
                'quality_passed': False,
                'signal_strength': 0
            }

    def _calculate_factors(self, klines: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        计算因子分数

        简化版本：基于K线数据计算基本因子
        实际应用中应该使用完整的因子模块
        """
        if len(klines) < 20:
            return {
                'T': 0.0, 'M': 0.0, 'C': 0.0,
                'V': 0.0, 'O': 0.0, 'B': 0.0
            }

        # 简单趋势判断
        closes = [k['close'] for k in klines[-20:]]
        sma_short = sum(closes[-5:]) / 5
        sma_long = sum(closes) / len(closes)

        # T因子：趋势
        t_score = (sma_short - sma_long) / sma_long * 100

        # M因子：动量
        momentum = (closes[-1] - closes[-10]) / closes[-10] * 100

        # V因子：波动率
        high_low_range = [(k['high'] - k['low']) / k['low'] for k in klines[-10:]]
        volatility = sum(high_low_range) / len(high_low_range) * 100

        # 简化的其他因子
        return {
            'T': max(-100, min(100, t_score * 10)),
            'M': max(-100, min(100, momentum * 5)),
            'C': 0.0,  # 需要订单簿数据
            'V': max(-100, min(100, volatility * 10)),
            'O': 0.0,  # 需要OI数据
            'B': 0.0   # 需要资金流数据
        }


# ========== 预设策略变体 ==========

class CryptoSignalConservative(CryptoSignalStrategy):
    """保守型策略 - 更严格的信号过滤"""

    min_signal_strength = 0.5
    use_cs_quality_gate = True

    minimal_roi = {
        "0": 0.15,
        "60": 0.08,
        "120": 0.04,
    }

    stoploss = -0.03


class CryptoSignalAggressive(CryptoSignalStrategy):
    """激进型策略 - 更宽松的信号过滤"""

    min_signal_strength = 0.2
    use_cs_quality_gate = False

    minimal_roi = {
        "0": 0.08,
        "30": 0.04,
        "60": 0.02,
    }

    stoploss = -0.08


# ========== 便捷函数 ==========

def create_strategy_from_config(config_path: str) -> type:
    """
    从配置文件创建策略类

    Args:
        config_path: 策略配置文件路径

    Returns:
        配置好的策略类
    """
    import yaml

    with open(config_path) as f:
        strategy_config = yaml.safe_load(f)

    # 动态创建策略类
    class ConfiguredStrategy(CryptoSignalStrategy):
        cs_config_path = strategy_config.get('cs_config_path', 'config/params.json')
        min_signal_strength = strategy_config.get('min_signal_strength', 0.3)
        use_cs_quality_gate = strategy_config.get('use_cs_quality_gate', True)
        use_cs_stoploss = strategy_config.get('use_cs_stoploss', True)
        timeframe = strategy_config.get('timeframe', '5m')
        stoploss = strategy_config.get('stoploss', -0.05)

        if 'minimal_roi' in strategy_config:
            minimal_roi = strategy_config['minimal_roi']

    return ConfiguredStrategy


# ========== 示例用法 ==========

if __name__ == "__main__":
    print("CryptoSignal Freqtrade Bridge")
    print("=" * 40)
    print()
    print("Usage:")
    print("  1. Copy this strategy to freqtrade's user_data/strategies/")
    print("  2. Configure in config.json:")
    print('     "strategy": "CryptoSignalStrategy"')
    print("  3. Run backtest:")
    print("     freqtrade backtesting --strategy CryptoSignalStrategy")
    print()
    print("Available strategies:")
    print("  - CryptoSignalStrategy (default)")
    print("  - CryptoSignalConservative")
    print("  - CryptoSignalAggressive")
