# cs_ext/backtest/freqtrade_bridge.py
from typing import Dict, Any

from pandas import DataFrame

from freqtrade.strategy.interface import IStrategy

from ats_core.env.bootstrap import bootstrap_env

bootstrap_env()

# 根据你的真实路径调整，如果函数名或模块不一致，请在后续人工微调
try:
    from ats_core.pipeline.analyze_symbol import analyze_symbol_with_preloaded_klines
except ImportError:
    analyze_symbol_with_preloaded_klines = None
    print(
        "[CryptoSignalStrategy] WARNING: "
        "无法导入 analyze_symbol_with_preloaded_klines，请根据实际项目结构修改导入路径。"
    )


class CryptoSignalStrategy(IStrategy):
    """
    使用 CryptoSignal 作为信号引擎的 Freqtrade 策略骨架。

    核心思路：
    - Freqtrade 提供历史K线（dataframe）
    - 本策略将 dataframe 转给 CryptoSignal 的分析逻辑
    - 根据返回的方向/强度/概率，告诉 Freqtrade 何时做多/做空
    """

    timeframe = "1h"
    can_short: bool = True

    minimal_roi = {
        "0": 10
    }
    stoploss = -0.2

    use_custom_stoploss = False

    def _call_cryptosignal(self, df_row: DataFrame, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        调用 CryptoSignal 分析逻辑。

        这里采用"单行 DataFrame"，你也可以改为传整个窗口给 analyze_symbol。
        返回统一结构：
            {
                "direction": "long" / "short" / "none",
                "final_strength": float,
                "probability": float,
            }
        """
        if analyze_symbol_with_preloaded_klines is None:
            return {
                "direction": "none",
                "final_strength": 0.0,
                "probability": 0.5,
            }

        pair = metadata.get("pair", "")

        # 占位：这里直接把 df_row 当作 klines，后续可根据你的函数签名调整
        klines = df_row.copy()

        try:
            result = analyze_symbol_with_preloaded_klines(
                symbol=pair,
                klines=klines,
                # TODO: 其他必要参数请根据实际函数签名补充
            )
        except Exception as e:
            print(f"[CryptoSignalStrategy] analyze_symbol_with_preloaded_klines error: {e}")
            return {
                "direction": "none",
                "final_strength": 0.0,
                "probability": 0.5,
            }

        # 假设 result 是 dict，包含以下字段，如有不同请后续调整
        direction = result.get("direction", "none")  # 'long' / 'short' / 'none'
        final_strength = float(result.get("final_strength", 0.0))
        probability = float(result.get("probability", 0.5))

        return {
            "direction": direction,
            "final_strength": final_strength,
            "probability": probability,
        }

    def populate_indicators(self, dataframe: DataFrame, metadata: Dict[str, Any]) -> DataFrame:
        """
        Freqtrade 要求的接口。当前依赖 CryptoSignal，因此此处直接返回即可。
        """
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: Dict[str, Any]) -> DataFrame:
        """
        逐行调用 CryptoSignal，生成做多/做空信号。
        """
        dataframe["enter_long"] = 0
        dataframe["enter_short"] = 0

        for idx in range(len(dataframe)):
            row = dataframe.iloc[idx:idx + 1]
            signal = self._call_cryptosignal(row, metadata)
            direction = signal["direction"]

            if direction == "long":
                dataframe.at[dataframe.index[idx], "enter_long"] = 1
            elif direction == "short":
                dataframe.at[dataframe.index[idx], "enter_short"] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: Dict[str, Any]) -> DataFrame:
        """
        退场逻辑：
        - 初期可以全部交给全局止损/ROI
        - 后续可接入你自己的反向信号 / 强度衰减逻辑
        """
        dataframe["exit_long"] = 0
        dataframe["exit_short"] = 0
        return dataframe
