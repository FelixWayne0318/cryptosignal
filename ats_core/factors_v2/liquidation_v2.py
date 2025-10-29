"""
清算密度因子 V2 - 基于聚合成交数据

由于Binance清算数据API已停止维护，改用aggTrades（聚合成交数据）
通过分析大额异常交易来推断清算压力

逻辑：
- 大额卖单 → 多单可能被清算（看跌）
- 大额买单 → 空单可能被清算（看涨）
"""

def calculate_liquidation_from_trades(
    agg_trades: list,
    current_price: float,
    params: dict = None
) -> tuple:
    """
    基于聚合成交数据计算清算压力

    Args:
        agg_trades: 聚合成交数据列表
            每条记录: {
                'a': 聚合交易ID,
                'p': 价格 (str),
                'q': 数量 (str),
                'T': 时间戳,
                'm': isBuyerMaker (True=卖单, False=买单)
            }
        current_price: 当前价格
        params: 参数配置

    Returns:
        (score, metadata): 评分(-100到+100) 和 元数据
    """
    if params is None:
        params = {}

    # 参数
    large_trade_threshold = params.get('large_trade_threshold', 0.5)  # 大额交易阈值（BTC数量）
    volume_weight = params.get('volume_weight', 1.0)  # 成交量权重

    if not agg_trades or len(agg_trades) < 10:
        return 0, {
            "note": "数据不足",
            "trades_count": len(agg_trades) if agg_trades else 0
        }

    try:
        # 统计大额交易
        large_sells = []  # 大额卖单（可能是多单清算）
        large_buys = []   # 大额买单（可能是空单清算）
        total_sell_vol = 0
        total_buy_vol = 0

        for trade in agg_trades:
            try:
                price = float(trade['p'])
                qty = float(trade['q'])
                is_sell = trade['m']  # True=卖单成交（主动卖）
                volume_usd = price * qty

                # 识别大额交易
                if qty >= large_trade_threshold:
                    if is_sell:
                        large_sells.append({'price': price, 'qty': qty, 'vol': volume_usd})
                    else:
                        large_buys.append({'price': price, 'qty': qty, 'vol': volume_usd})

                # 累计总成交量
                if is_sell:
                    total_sell_vol += volume_usd
                else:
                    total_buy_vol += volume_usd

            except (KeyError, ValueError, TypeError):
                continue

        # 计算大额交易的成交额
        large_sell_vol = sum(t['vol'] for t in large_sells)
        large_buy_vol = sum(t['vol'] for t in large_buys)

        # 计算清算压力评分
        if large_sell_vol + large_buy_vol == 0:
            score = 0
            interpretation = "无明显大额交易"
        else:
            # 清算压力 = (空单清算 - 多单清算) / 总清算
            # 大额买单 → 空单清算 → 看涨 → 正分
            # 大额卖单 → 多单清算 → 看跌 → 负分
            raw_score = (large_buy_vol - large_sell_vol) / (large_buy_vol + large_sell_vol)
            score = raw_score * 100

            if score > 50:
                interpretation = "强烈空单清算压力（超跌反弹）"
            elif score > 20:
                interpretation = "温和空单清算压力"
            elif score < -50:
                interpretation = "强烈多单清算压力（超涨回调）"
            elif score < -20:
                interpretation = "温和多单清算压力"
            else:
                interpretation = "清算压力平衡"

        # 元数据
        metadata = {
            "liquidation_score": score,
            "large_sells_count": len(large_sells),
            "large_buys_count": len(large_buys),
            "large_sell_volume_usd": large_sell_vol,
            "large_buy_volume_usd": large_buy_vol,
            "total_sell_volume_usd": total_sell_vol,
            "total_buy_volume_usd": total_buy_vol,
            "trades_analyzed": len(agg_trades),
            "interpretation": interpretation,
            "method": "aggTrades_based",
            "threshold_btc": large_trade_threshold
        }

        return int(score), metadata

    except Exception as e:
        return 0, {
            "error": str(e),
            "note": "计算失败"
        }


def calculate_liquidation(
    liquidations: list = None,
    current_price: float = None,
    liquidation_map: dict = None,
    params: dict = None,
    agg_trades: list = None
) -> tuple:
    """
    清算密度计算（兼容函数）

    优先使用agg_trades（新方法），如果没有则尝试使用liquidations（旧方法）

    Args:
        liquidations: 清算数据（已废弃，Binance不再提供）
        current_price: 当前价格
        liquidation_map: 清算价格映射（已废弃）
        params: 参数配置
        agg_trades: 聚合成交数据（新方法）

    Returns:
        (score, metadata): 评分(-100到+100) 和 元数据
    """
    # 优先使用新方法（aggTrades）
    if agg_trades:
        return calculate_liquidation_from_trades(agg_trades, current_price, params)

    # 如果有旧的清算数据，尝试使用（向后兼容）
    if liquidations and len(liquidations) > 0:
        # 导入旧的实现
        try:
            from ats_core.factors_v2.liquidation_legacy import calculate_liquidation_legacy
            return calculate_liquidation_legacy(liquidations, current_price, liquidation_map, params)
        except ImportError:
            pass

    # 没有数据
    return 0, {
        "note": "无可用数据（Binance清算API已停止维护）",
        "suggestion": "请传入agg_trades参数使用新方法"
    }
