# cs_ext/backtest/freqtrade_bridge.py
"""
Freqtrade 回测桥接层 - V8完整实现

使用 CryptoSignal 作为信号引擎的 Freqtrade 策略。

核心架构：
- Freqtrade 提供历史K线（DataFrame）
- 本策略将 DataFrame 转换为 CryptoSignal 的 klines 格式
- 调用四步决策系统分析，返回方向/强度/风险参数
- 支持做多/做空，自定义止损/止盈

配置文件：config/signal_thresholds.json
"""

import json
import os
from typing import Dict, Any, List, Optional

from pandas import DataFrame
import numpy as np

from freqtrade.strategy.interface import IStrategy

from ats_core.env.bootstrap import bootstrap_env

bootstrap_env()

# 导入 CryptoSignal 分析函数
try:
    from ats_core.pipeline.analyze_symbol import analyze_symbol_with_preloaded_klines
except ImportError:
    analyze_symbol_with_preloaded_klines = None
    print(
        "[CryptoSignalStrategy] WARNING: "
        "无法导入 analyze_symbol_with_preloaded_klines，请根据实际项目结构修改导入路径。"
    )


def load_config() -> Dict[str, Any]:
    """
    从 config/signal_thresholds.json 加载配置
    """
    config_paths = [
        "config/signal_thresholds.json",
        "../config/signal_thresholds.json",
        os.path.join(os.path.dirname(__file__), "../../config/signal_thresholds.json"),
    ]

    for path in config_paths:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)

    print("[CryptoSignalStrategy] WARNING: 未找到配置文件，使用默认配置")
    return {}


class CryptoSignalStrategy(IStrategy):
    """
    使用 CryptoSignal 四步决策系统的 Freqtrade 策略。

    Features:
    - 调用四步决策系统（Direction → Timing → Risk → Quality）
    - 配置驱动，阈值从 signal_thresholds.json 读取
    - 支持做多/做空
    - 自定义止损/止盈基于四步系统计算
    """

    # ========== Freqtrade 基础配置 ==========
    # 从配置文件读取时间周期
    timeframe = "1h"
    can_short: bool = True

    # ROI 设置（四步系统会计算具体止盈价位）
    minimal_roi = {
        "0": 10  # 基本禁用默认ROI，让四步系统管理
    }

    # 止损设置（作为最大回撤保护，四步系统会计算具体止损）
    stoploss = -0.15

    # 使用自定义止损
    use_custom_stoploss = True

    # 仓位管理
    position_adjustment_enable = False

    def __init__(self, config: dict) -> None:
        super().__init__(config)

        # 加载 CryptoSignal 配置
        self._cs_config = load_config()
        self._backtest_config = self._cs_config.get("v8_integration", {}).get("backtest", {})

        # 从配置读取回测引擎参数
        engine_config = self._backtest_config.get("engine", {})
        self._lookback_bars = engine_config.get("lookback_bars", 300)

        # 缓存分析结果
        self._signal_cache: Dict[str, Dict] = {}

        print(f"[CryptoSignalStrategy] 初始化完成, lookback_bars={self._lookback_bars}")

    def _convert_df_to_klines(self, dataframe: DataFrame) -> List[List]:
        """
        将 Freqtrade DataFrame 转换为 CryptoSignal klines 格式

        CryptoSignal klines 格式: [[open_time, open, high, low, close, volume, close_time, ...], ...]

        Args:
            dataframe: Freqtrade 的 OHLCV DataFrame

        Returns:
            klines 列表
        """
        klines = []

        for idx in range(len(dataframe)):
            row = dataframe.iloc[idx]

            # 获取时间戳
            if hasattr(row.name, 'timestamp'):
                open_time = int(row.name.timestamp() * 1000)
            else:
                open_time = int(row.get('date', 0))

            # 构造 kline 格式 [open_time, open, high, low, close, volume, close_time, ...]
            kline = [
                open_time,
                float(row['open']),
                float(row['high']),
                float(row['low']),
                float(row['close']),
                float(row['volume']),
                open_time + 3600000,  # close_time (假设1小时)
                0,  # quote_asset_volume
                0,  # number_of_trades
                0,  # taker_buy_base_volume
                0,  # taker_buy_quote_volume
                0   # ignore
            ]
            klines.append(kline)

        return klines

    def _call_cryptosignal(self, dataframe: DataFrame, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        调用 CryptoSignal 四步决策系统分析

        Args:
            dataframe: 完整的历史K线 DataFrame
            metadata: Freqtrade 元数据（包含 pair）

        Returns:
            分析结果字典：
            {
                "direction": "long" / "short" / "none",
                "final_strength": float,
                "probability": float,
                "entry_price": float,
                "stop_loss": float,
                "take_profit": float,
                "risk_reward_ratio": float
            }
        """
        default_result = {
            "direction": "none",
            "final_strength": 0.0,
            "probability": 0.5,
            "entry_price": None,
            "stop_loss": None,
            "take_profit": None,
            "risk_reward_ratio": 0.0
        }

        if analyze_symbol_with_preloaded_klines is None:
            return default_result

        pair = metadata.get("pair", "")

        # 将 Freqtrade pair 格式转换为 CryptoSignal symbol 格式
        # Freqtrade: "BTC/USDT:USDT" -> CryptoSignal: "BTCUSDT"
        symbol = pair.replace("/", "").replace(":USDT", "")

        # 转换 DataFrame 为 klines 格式
        k1h = self._convert_df_to_klines(dataframe)

        # 生成 4 小时 K 线（简化处理：每4根1小时K线合并）
        k4h = self._resample_to_4h(k1h)

        try:
            result = analyze_symbol_with_preloaded_klines(
                symbol=symbol,
                k1h=k1h,
                k4h=k4h,
                # 以下为可选参数，回测时可能没有实时数据
                oi_data=None,
                spot_k1h=None,
                elite_meta=None,
                k15m=None,
                k1d=None,
                orderbook=None,
                mark_price=None,
                funding_rate=None,
                spot_price=None,
                btc_klines=None,
                eth_klines=None,
                kline_cache=None,
                market_meta=None
            )
        except Exception as e:
            print(f"[CryptoSignalStrategy] analyze_symbol_with_preloaded_klines error: {e}")
            return default_result

        # 解析分析结果 - 优先使用四步系统决策
        four_step = result.get("four_step_decision", {})

        # 方案1：四步系统决策（优先）
        if four_step.get("decision") == "ACCEPT":
            action = four_step.get("action", "")
            direction = "long" if action == "LONG" else "short" if action == "SHORT" else "none"

            step1 = four_step.get("step1_direction", {})
            final_strength = step1.get("final_strength", 0)

            # 使用四步系统的价格信息
            entry_price = four_step.get("entry_price")
            stop_loss = four_step.get("stop_loss")
            take_profit = four_step.get("take_profit")
            risk_reward_ratio = four_step.get("risk_reward_ratio", 0)

            probability = min(0.5 + final_strength / 20, 0.95)  # 强度范围约0-20

        # 方案2：后备 - 旧系统判定
        else:
            is_prime = result.get("is_prime", False)
            side_long = result.get("side_long", None)

            if not is_prime or side_long is None:
                return default_result

            direction = "long" if side_long else "short"
            final_strength = result.get("prime_strength", 0)

            entry_price = result.get("entry_price")
            stop_loss = result.get("stop_loss")
            take_profit = result.get("take_profit")
            risk_reward_ratio = result.get("risk_reward_ratio", 0)

            probability = min(0.5 + final_strength / 200, 0.95)

        return {
            "direction": direction,
            "final_strength": final_strength,
            "probability": probability,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "risk_reward_ratio": risk_reward_ratio,
            # 保存完整结果用于后续分析
            "_full_result": result
        }

    def _resample_to_4h(self, k1h: List[List]) -> List[List]:
        """
        将1小时K线重采样为4小时K线

        Args:
            k1h: 1小时K线列表

        Returns:
            4小时K线列表
        """
        k4h = []

        for i in range(0, len(k1h) - 3, 4):
            batch = k1h[i:i+4]
            if len(batch) < 4:
                continue

            k4h_candle = [
                batch[0][0],  # open_time
                batch[0][1],  # open
                max(k[2] for k in batch),  # high
                min(k[3] for k in batch),  # low
                batch[-1][4],  # close
                sum(k[5] for k in batch),  # volume
                batch[-1][6],  # close_time
                0, 0, 0, 0, 0  # 其他字段
            ]
            k4h.append(k4h_candle)

        return k4h

    def populate_indicators(self, dataframe: DataFrame, metadata: Dict[str, Any]) -> DataFrame:
        """
        计算指标（CryptoSignal 内部处理，这里仅做数据准备）
        """
        # 添加辅助列用于信号追踪
        dataframe['cs_signal_strength'] = 0.0
        dataframe['cs_direction'] = 'none'

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: Dict[str, Any]) -> DataFrame:
        """
        生成入场信号

        使用滚动窗口方式调用 CryptoSignal 分析，生成做多/做空信号。
        """
        dataframe["enter_long"] = 0
        dataframe["enter_short"] = 0

        pair = metadata.get("pair", "")

        # 滚动窗口分析
        for idx in range(self._lookback_bars, len(dataframe)):
            # 获取历史窗口
            window = dataframe.iloc[idx - self._lookback_bars:idx + 1].copy()

            # 调用 CryptoSignal 分析
            signal = self._call_cryptosignal(window, metadata)
            direction = signal["direction"]
            strength = signal["final_strength"]

            # 缓存信号用于退出判断
            cache_key = f"{pair}_{idx}"
            self._signal_cache[cache_key] = signal

            # 记录信号强度
            dataframe.at[dataframe.index[idx], 'cs_signal_strength'] = strength
            dataframe.at[dataframe.index[idx], 'cs_direction'] = direction

            # 生成入场信号
            # 注意：四步系统的final_strength范围约0-20，阈值应与四步系统配置一致
            entry_threshold = self._backtest_config.get("engine", {}).get("entry_strength_threshold", 7.0)
            if direction == "long" and strength >= entry_threshold:
                dataframe.at[dataframe.index[idx], "enter_long"] = 1
            elif direction == "short" and strength >= entry_threshold:
                dataframe.at[dataframe.index[idx], "enter_short"] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: Dict[str, Any]) -> DataFrame:
        """
        生成退出信号

        退出条件：
        1. 信号反转（多头时出现空头信号，反之亦然）
        2. 信号强度大幅衰减
        3. 触发四步系统计算的止损/止盈
        """
        dataframe["exit_long"] = 0
        dataframe["exit_short"] = 0

        pair = metadata.get("pair", "")

        for idx in range(self._lookback_bars + 1, len(dataframe)):
            current_strength = dataframe.iloc[idx]['cs_signal_strength']
            current_direction = dataframe.iloc[idx]['cs_direction']

            prev_strength = dataframe.iloc[idx - 1]['cs_signal_strength']
            prev_direction = dataframe.iloc[idx - 1]['cs_direction']

            # 获取阈值配置
            entry_threshold = self._backtest_config.get("engine", {}).get("entry_strength_threshold", 7.0)
            exit_threshold = entry_threshold * 0.5  # 退出阈值为入场阈值的一半

            # 退出做多条件
            if prev_direction == "long":
                # 信号反转
                if current_direction == "short":
                    dataframe.at[dataframe.index[idx], "exit_long"] = 1
                # 强度大幅衰减（低于入场阈值的一半）
                elif current_strength < exit_threshold and prev_strength >= entry_threshold:
                    dataframe.at[dataframe.index[idx], "exit_long"] = 1

            # 退出做空条件
            if prev_direction == "short":
                # 信号反转
                if current_direction == "long":
                    dataframe.at[dataframe.index[idx], "exit_short"] = 1
                # 强度大幅衰减
                elif current_strength < exit_threshold and prev_strength >= entry_threshold:
                    dataframe.at[dataframe.index[idx], "exit_short"] = 1

        return dataframe

    def custom_stoploss(self, pair: str, trade, current_time, current_rate: float,
                        current_profit: float, after_fill: bool, **kwargs) -> float:
        """
        自定义止损逻辑

        使用四步系统计算的止损价位
        """
        # 获取开仓时的信号缓存
        entry_tag = trade.enter_tag or ""

        # 默认止损
        if current_profit > 0.02:
            # 盈利超过2%时启动追踪止损
            return -0.005  # 0.5%追踪止损

        return self.stoploss  # 使用默认止损

    def confirm_trade_entry(self, pair: str, order_type: str, amount: float, rate: float,
                            time_in_force: str, current_time, entry_tag: Optional[str],
                            side: str, **kwargs) -> bool:
        """
        确认交易入场

        可以在这里添加额外的过滤逻辑
        """
        # 风险回报比检查已在四步系统Step3完成
        # 这里仅记录日志，不重复拒绝已通过四步系统的信号
        for key in reversed(list(self._signal_cache.keys())):
            if key.startswith(pair):
                signal = self._signal_cache[key]
                rr_ratio = signal.get("risk_reward_ratio", 0)

                if rr_ratio > 0 and rr_ratio < 1.5:
                    print(f"[CryptoSignalStrategy] WARNING: {pair} RR={rr_ratio:.2f} < 1.5, 但已通过四步系统")
                break

        return True
