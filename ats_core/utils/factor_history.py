"""
v7.4 因子历史计算工具 - 用于四步系统Step2 Enhanced F Factor

Purpose:
    计算过去N小时的因子得分序列，用于Step2时机判断层的flow_momentum计算

Implementation Note:
    初版实现（v7.4.0）：
    - 完整实现：T, M 因子（仅需K线数据）
    - 简化实现：C, V, O, B 因子（使用当前值或降级逻辑）
    - 原因：历史CVD、OI数据获取复杂，初版先实现核心功能

Future Enhancement (v7.5+):
    - 添加CVD历史缓存，实现完整C因子历史
    - 添加OI历史计算，实现完整O因子历史
    - 实现V/B因子历史（如需要）

Author: Claude Code
Version: v7.4.0
Created: 2025-11-16
"""

from typing import List, Dict, Any, Optional
from ats_core.logging import log, warn


def get_factor_scores_series(
    klines_1h: List[Dict[str, Any]],
    window_hours: int = 7,
    current_factor_scores: Optional[Dict[str, float]] = None,
    params: Optional[Dict[str, Any]] = None
) -> List[Dict[str, float]]:
    """
    计算历史因子得分序列（用于Enhanced F Factor v2）

    Args:
        klines_1h: 1小时K线数据（至少需要window_hours + 24根，确保每个历史点都有足够数据计算）
        window_hours: 回溯窗口（默认7小时，对应6小时前→当前）
        current_factor_scores: 当前因子得分（可选，用于C/O/V/B的降级）
        params: 配置参数（可选，用于因子计算）

    Returns:
        factor_scores_series: 历史因子得分序列
        [
            {"T": 25, "M": 10, "C": 80, "V": 70, "O": 60, "B": 50},  # 6小时前
            {"T": 28, "M": 12, "C": 82, "V": 71, "O": 62, "B": 51},  # 5小时前
            ...
            {"T": 35, "M": 20, "C": 90, "V": 75, "O": 65, "B": 55}   # 当前
        ]

    Implementation:
        - T/M因子：使用滑动窗口完整计算
        - C/O/V/B因子：使用简化逻辑（初版）
          - 如果提供current_factor_scores，使用当前值
          - 否则返回中性值0
    """
    if params is None:
        from ats_core.cfg import CFG
        params = CFG.params

    # 数据验证
    min_required = window_hours + 24  # 每个历史点需要24根K线计算T因子
    if len(klines_1h) < min_required:
        warn(f"⚠️  K线数量不足: 需要{min_required}根，实际{len(klines_1h)}根")
        return []

    series = []

    # 对过去window_hours小时，每小时计算一次
    for offset in range(window_hours, 0, -1):
        # offset=7 → 6小时前（klines[:-7]）
        # offset=1 → 当前（klines[:-1]，不包括最新正在形成的K线）
        # offset=0 → 当前（klines，包括最新K线）

        # 取该时刻之前的K线窗口
        if offset > 1:
            klines_window = klines_1h[:-offset]
        elif offset == 1:
            klines_window = klines_1h[:-1]
        else:  # offset == 0
            klines_window = klines_1h

        # 确保窗口有足够数据
        if len(klines_window) < 24:
            warn(f"⚠️  offset={offset}时K线窗口不足24根，跳过")
            continue

        # 计算该时刻的因子得分
        scores = _calculate_factors_at_time(
            klines_window,
            params,
            current_factor_scores
        )

        series.append(scores)

    return series


def _calculate_factors_at_time(
    klines: List[Dict[str, Any]],
    params: Dict[str, Any],
    current_scores: Optional[Dict[str, float]] = None
) -> Dict[str, float]:
    """
    计算特定时刻的因子得分

    Args:
        klines: K线数据（该时刻之前的所有数据）
        params: 配置参数
        current_scores: 当前因子得分（用于降级）

    Returns:
        因子得分字典 {"T": float, "M": float, "C": float, ...}
    """
    scores = {}

    # v7.4 P0修复：兼容不同K线数据格式
    # Binance K线可能是字典格式或列表格式：
    # - 字典格式: [{open: x, high: y, low: z, close: w, volume: v}, ...]
    # - 列表格式: [[timestamp, open, high, low, close, volume, ...], ...]
    def extract_kline_values(klines):
        """提取K线的high/low/close值，兼容不同格式"""
        h_list, l_list, c_list = [], [], []

        for k in klines:
            if isinstance(k, dict):
                # 字典格式
                h_list.append(k.get('high', 0))
                l_list.append(k.get('low', 0))
                c_list.append(k.get('close', 0))
            elif isinstance(k, (list, tuple)) and len(k) >= 5:
                # 列表格式: [timestamp, open, high, low, close, ...]
                h_list.append(float(k[2]) if k[2] else 0)  # high
                l_list.append(float(k[3]) if k[3] else 0)  # low
                c_list.append(float(k[4]) if k[4] else 0)  # close
            else:
                # 未知格式，使用0
                h_list.append(0)
                l_list.append(0)
                c_list.append(0)

        return h_list, l_list, c_list

    # 准备K线数据（兼容不同格式）
    h, l, c = extract_kline_values(klines)

    # ---- T因子（趋势）：完整计算 ----
    try:
        from ats_core.features.trend import score_trend
        trend_cfg = params.get("trend", {})
        c4 = []  # 历史计算暂不需要4h K线
        T, _ = score_trend(h, l, c, c4, trend_cfg)
        scores["T"] = int(T)
    except Exception as e:
        warn(f"⚠️  T因子历史计算失败: {e}")
        scores["T"] = 0

    # ---- M因子（动量）：完整计算 ----
    try:
        from ats_core.features.momentum import score_momentum
        momentum_cfg = params.get("momentum", {})
        M, _ = score_momentum(h, l, c, momentum_cfg)
        scores["M"] = int(M)
    except Exception as e:
        warn(f"⚠️  M因子历史计算失败: {e}")
        scores["M"] = 0

    # ---- C/O/V/B因子：简化实现（初版）----
    # v7.4.0: 使用当前值或中性值
    # v7.5+: 实现完整历史计算（需要CVD/OI历史数据）

    if current_scores:
        scores["C"] = current_scores.get("C", 0)
        scores["V"] = current_scores.get("V", 0)
        scores["O"] = current_scores.get("O", 0)
        scores["B"] = current_scores.get("B", 0)
    else:
        scores["C"] = 0  # 中性值
        scores["V"] = 0
        scores["O"] = 0
        scores["B"] = 0

    return scores


def calculate_factor_scores_series_for_symbol(
    symbol: str,
    result: Dict[str, Any],
    klines_1h: List[Dict[str, Any]],
    window_hours: int = 7
) -> List[Dict[str, float]]:
    """
    为特定交易对计算因子得分序列（便捷封装函数）

    这个函数从analyze_symbol的result中提取当前因子得分，
    然后调用get_factor_scores_series计算历史序列

    Args:
        symbol: 交易对符号
        result: analyze_symbol的返回结果（包含当前因子得分）
        klines_1h: 1小时K线数据
        window_hours: 回溯窗口

    Returns:
        factor_scores_series: 历史因子得分序列
    """
    # 从result中提取当前因子得分
    current_scores = {
        "T": result.get("T", 0),
        "M": result.get("M", 0),
        "C": result.get("C", 0),
        "V": result.get("V", 0),
        "O": result.get("O", 0),
        "B": result.get("B", 0),
    }

    from ats_core.cfg import CFG
    params = CFG.params

    # 计算历史序列
    series = get_factor_scores_series(
        klines_1h=klines_1h,
        window_hours=window_hours,
        current_factor_scores=current_scores,
        params=params
    )

    if series:
        log(f"✅ {symbol} 因子历史计算完成: {len(series)}个时间点")
    else:
        warn(f"⚠️  {symbol} 因子历史计算失败")

    return series


# ============ 使用示例 ============

if __name__ == "__main__":
    """
    测试用例：验证factor_scores_series计算

    Usage:
        python3 -m ats_core.utils.factor_history
    """
    print("="*60)
    print("v7.4 因子历史计算工具 - 测试")
    print("="*60)

    # 模拟K线数据
    test_klines = []
    base_price = 100
    for i in range(40):  # 40根1h K线
        test_klines.append({
            "high": base_price + (i % 10),
            "low": base_price - (i % 10),
            "close": base_price + (i % 5),
            "volume": 1000000 + i * 10000
        })

    # 测试计算
    series = get_factor_scores_series(
        klines_1h=test_klines,
        window_hours=7,
        current_factor_scores={"C": 80, "V": 70, "O": 60, "B": 50},
        params={}
    )

    print(f"\n✅ 计算完成：{len(series)}个时间点")
    print(f"\n📊 历史序列示例：")
    for i, scores in enumerate(series):
        hours_ago = len(series) - i - 1
        print(f"   {hours_ago}小时前: T={scores['T']:+3d}, M={scores['M']:+3d}, "
              f"C={scores['C']:+3d}, V={scores['V']:+3d}, O={scores['O']:+3d}, B={scores['B']:+3d}")

    print("\n" + "="*60)
    print("✅ 测试完成")
    print("="*60)
