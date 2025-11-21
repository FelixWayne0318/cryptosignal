# cs_ext/backtest/freqtrade_bridge.py
"""
Freqtrade 策略桥接器

使用 CryptoSignal 作为信号引擎的 Freqtrade 策略骨架。

Usage:
    复制到 freqtrade/user_data/strategies/
    freqtrade backtesting --strategy CryptoSignalStrategy
"""

from datetime import datetime
from typing import Dict, Any

from freqtrade.strategy.interface import IStrategy
from pandas import DataFrame


class CryptoSignalStrategy(IStrategy):
    """
    使用 CryptoSignal 作为信号引擎的 Freqtrade 策略骨架。
    注意：这里只提供骨架，具体如何调用你的因子和决策逻辑，需要你根据项目实际代码填充。
    """

    timeframe = "1h"   # 根据你系统主时间周期调整
    can_short: bool = True

    minimal_roi = {
        "0": 10  # 占位，回测时可调整
    }

    stoploss = -0.2

    def populate_indicators(self, dataframe: DataFrame, metadata: Dict[str, Any]) -> DataFrame:
        """
        在这里你可以把 dataframe 转交给 CryptoSignal 的因子计算模块。
        简化做法：只在 populate_entry_trend 里调用 CryptoSignal 核心函数。
        """
        return dataframe

    def _call_cryptosignal(self, dataframe: DataFrame, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        TODO: 这里写一个适配层，把 dataframe 转成 CryptoSignal 需要的格式，
        调用你现有的 `analyze_symbol_with_preloaded_klines` 或等价函数，
        然后返回统一结构，例如：
        {
            "direction": "long" / "short" / "none",
            "final_strength": 0..100,
            "probability": 0..1
        }
        """
        # 占位实现
        return {
            "direction": "none",
            "final_strength": 0.0,
            "probability": 0.5,
        }

    def populate_entry_trend(self, dataframe: DataFrame, metadata: Dict[str, Any]) -> DataFrame:
        dataframe["enter_long"] = 0
        dataframe["enter_short"] = 0

        for idx in range(len(dataframe)):
            row = dataframe.iloc[idx:idx+1]
            signal = self._call_cryptosignal(row, metadata)
            direction = signal["direction"]

            if direction == "long":
                dataframe.at[dataframe.index[idx], "enter_long"] = 1
            elif direction == "short":
                dataframe.at[dataframe.index[idx], "enter_short"] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: Dict[str, Any]) -> DataFrame:
        """
        简化：可以用反向信号 / 强度下降 / 持仓时间 等逻辑；
        初期可以先用默认实现。
        """
        dataframe["exit_long"] = 0
        dataframe["exit_short"] = 0
        return dataframe
