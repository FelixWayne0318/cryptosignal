# coding: utf-8
"""
v2.2扩展：集成微观结构指标

在v3.0基础上增加：
1. D指标：订单簿深度（OBI）
2. FR指标：资金费率与基差
3. FWI风险过滤器

使用方式：
from ats_core.pipeline.analyze_symbol_v22 import analyze_symbol_v22
result = await analyze_symbol_v22(symbol)
"""

from typing import Dict, Any, List, Tuple
from ats_core.pipeline.analyze_symbol import _analyze_symbol_core, _make_empty_result
from ats_core.sources.binance import get_klines, get_open_interest_hist, get_spot_klines
from ats_core.data.binance_async_client import BinanceAsyncClient
from ats_core.features.orderbook_depth import score_orderbook_depth, validate_orderbook
from ats_core.features.funding_rate import (
    score_funding_rate,
    calculate_fwi,
    validate_funding_data
)
from ats_core.features.risk_filters import apply_risk_filters
from ats_core.cfg import CFG
from ats_core.logging import log, warn, error


async def fetch_microstructure_data(
    client: BinanceAsyncClient,
    symbol: str
) -> Dict[str, Any]:
    """
    获取微观结构数据（v2.2）

    Args:
        client: 异步客户端
        symbol: 币种

    Returns:
        {
            'orderbook': {...},
            'premium': {...},
            'has_data': bool
        }
    """
    try:
        # 并发获取订单簿深度和标记价格
        import asyncio
        depth_task = client.get_depth(symbol, limit=20)

        # 获取所有标记价格（批量接口）
        premium_list_task = client.get_all_premium_index()

        depth, premium_list = await asyncio.gather(depth_task, premium_list_task)

        # 从批量数据中找到目标币种
        premium = None
        if premium_list:
            for p in premium_list:
                if p.get('symbol') == symbol:
                    premium = p
                    break

        # 验证数据
        has_orderbook = validate_orderbook(depth)
        has_premium = premium is not None and validate_funding_data(
            float(premium.get('markPrice', 0)),
            float(premium.get('indexPrice', 0)),
            float(premium.get('lastFundingRate', 0))
        )

        return {
            'orderbook': depth if has_orderbook else None,
            'premium': premium if has_premium else None,
            'has_data': has_orderbook and has_premium
        }

    except Exception as e:
        error(f"❌ 获取微观结构数据失败 {symbol}: {e}")
        return {'orderbook': None, 'premium': None, 'has_data': False}


def calculate_microstructure_indicators(
    symbol: str,
    micro_data: Dict[str, Any],
    price_change_30m: float,
    oi_change_30m: float,
    params: Dict[str, Any]
) -> Tuple[int, int, Dict, Dict, Dict]:
    """
    计算微观结构指标（D和FR）

    Args:
        symbol: 币种
        micro_data: 微观结构数据
        price_change_30m: 30分钟价格变化率
        oi_change_30m: 30分钟OI变化率
        params: 参数配置

    Returns:
        (D分数, FR分数, D元数据, FR元数据, FWI结果)
    """
    D_params = params.get('orderbook_depth', {})
    FR_params = params.get('funding_rate', {})

    # 默认值（无数据时）
    D = 0
    FR = 0
    D_meta = {'has_data': False}
    FR_meta = {'has_data': False}
    fwi_result = {'fwi': 0.0, 'fwi_warning': False}

    # 计算D指标（订单簿深度）
    if micro_data.get('orderbook'):
        try:
            D, D_meta = score_orderbook_depth(
                micro_data['orderbook'],
                params=D_params
            )
            D_meta['has_data'] = True
        except Exception as e:
            error(f"❌ 计算D指标失败 {symbol}: {e}")

    # 计算FR指标（资金费率）
    if micro_data.get('premium'):
        try:
            premium = micro_data['premium']
            mark_price = float(premium.get('markPrice', 0))
            index_price = float(premium.get('indexPrice', 0))
            funding_rate = float(premium.get('lastFundingRate', 0))
            next_funding_time = int(premium.get('nextFundingTime', 0))

            FR, FR_meta = score_funding_rate(
                mark_price=mark_price,
                spot_price=index_price,  # 用indexPrice作为现货价格近似
                funding_rate=funding_rate,
                params=FR_params
            )
            FR_meta['has_data'] = True
            FR_meta['next_funding_time'] = next_funding_time

            # 计算FWI
            fwi_result = calculate_fwi(
                funding_rate=funding_rate,
                next_funding_time=next_funding_time,
                price_change_30m=price_change_30m,
                oi_change_30m=oi_change_30m
            )[1]  # 只要元数据

        except Exception as e:
            error(f"❌ 计算FR指标失败 {symbol}: {e}")

    return D, FR, D_meta, FR_meta, fwi_result


async def analyze_symbol_v22(
    symbol: str,
    client: BinanceAsyncClient = None
) -> Dict[str, Any]:
    """
    完整分析函数（v2.2）

    在v3.0基础上增加D和FR指标，应用风险过滤

    Args:
        symbol: 币种
        client: 异步客户端（可选，如果不提供会创建临时客户端）

    Returns:
        分析结果字典（包含v2.2扩展字段）
    """
    params = CFG.params or {}

    # 创建临时客户端（如果需要）
    temp_client = False
    if client is None:
        client = BinanceAsyncClient()
        await client.start()
        temp_client = True

    try:
        # 1. 获取基础数据（K线、OI）
        # 使用同步API（保持兼容性）
        k1 = get_klines(symbol, '1h', limit=300)
        k4 = get_klines(symbol, '4h', limit=100)
        oi_data = get_open_interest_hist(symbol, period='1h', limit=200)

        # 现货数据（可选）
        try:
            spot_k1 = get_spot_klines(symbol, '1h', limit=300)
        except Exception:
            spot_k1 = None

        # 2. 获取微观结构数据（v2.2新增）
        micro_data = await fetch_microstructure_data(client, symbol)

        # 3. 执行原有分析（v3.0）
        base_result = _analyze_symbol_core(
            symbol=symbol,
            k1=k1,
            k4=k4,
            oi_data=oi_data,
            spot_k1=spot_k1,
            elite_meta=None
        )

        # 如果基础分析失败，直接返回
        if not base_result.get('ok'):
            return base_result

        # 4. 计算30分钟变化率（用于FWI）
        if k1 and len(k1) >= 2:
            price_change_30m = (float(k1[-1][4]) - float(k1[-2][4])) / float(k1[-2][4])
        else:
            price_change_30m = 0.0

        if oi_data and len(oi_data) >= 2:
            oi_change_30m = (float(oi_data[-1].get('sumOpenInterest', 0)) -
                            float(oi_data[-2].get('sumOpenInterest', 0))) / \
                            max(1e-12, float(oi_data[-2].get('sumOpenInterest', 1)))
        else:
            oi_change_30m = 0.0

        # 5. 计算微观结构指标（v2.2）
        D, FR, D_meta, FR_meta, fwi_result = calculate_microstructure_indicators(
            symbol=symbol,
            micro_data=micro_data,
            price_change_30m=price_change_30m,
            oi_change_30m=oi_change_30m,
            params=params
        )

        # 6. 重新计算权重和分数（集成D和FR）
        weights = params.get("weights", {})

        # 获取原有分数
        scores = base_result.get('scores', {})
        T = scores.get('T', 0)
        M = scores.get('M', 0)
        C = scores.get('C', 0)
        S = scores.get('S', 0)
        V = scores.get('V', 0)
        O = scores.get('O', 0)

        # 添加新分数
        scores['D'] = D
        scores['FR'] = FR

        # 计算新的加权分数
        weighted_score_v22 = (
            T * weights.get('T', 35) +
            M * weights.get('M', 10) +
            C * weights.get('C', 25) +
            S * weights.get('S', 2) +
            V * weights.get('V', 3) +
            O * weights.get('O', 12) +
            D * weights.get('D', 8) +
            FR * weights.get('F', 5)  # 注意：配置中用F表示资金费率
        ) / 100

        # 7. 应用风险过滤（v2.2核心功能）
        indicator_scores = {
            'T': T, 'M': M, 'C': C, 'O': O, 'D': D, 'F': FR
        }

        risk_result = apply_risk_filters(
            base_score=weighted_score_v22,
            D_meta=D_meta,
            F_meta=FR_meta,
            fwi_result=fwi_result,
            indicator_scores=indicator_scores
        )

        # 8. 更新结果
        v22_result = base_result.copy()
        v22_result.update({
            'version': 'v2.2',
            'scores': scores,
            'scores_meta': {
                **base_result.get('scores_meta', {}),
                'D': D_meta,
                'FR': FR_meta
            },
            'weighted_score_v22': weighted_score_v22,
            'adjusted_score': risk_result['adjusted_score'],
            'risk_level': risk_result['risk_level'],
            'warnings': risk_result['warnings'],
            'should_skip': risk_result['should_skip'],
            'has_conflict': risk_result['has_conflict'],
            'fwi': fwi_result
        })

        # 9. 更新概率（如果有风险调整）
        if risk_result['warnings']:
            # 根据风险等级调整概率
            risk_penalty = {
                'low': 1.0,
                'medium': 0.9,
                'high': 0.7
            }.get(risk_result['risk_level'], 1.0)

            P_long = base_result.get('P_long', 0.5) * risk_penalty
            P_short = base_result.get('P_short', 0.5) * risk_penalty

            v22_result['P_long'] = P_long
            v22_result['P_short'] = P_short
            v22_result['P_chosen'] = P_long if base_result.get('side_long') else P_short

        # 10. 更新发布决策
        if risk_result['should_skip']:
            v22_result['tier'] = 'skip'
            v22_result['reason'] = f"v2.2风险过滤: {', '.join(risk_result['warnings'])}"

        return v22_result

    except Exception as e:
        error(f"❌ v2.2分析失败 {symbol}: {e}")
        import traceback
        traceback.print_exc()
        return _make_empty_result(symbol, f"v22_error: {str(e)}")

    finally:
        # 关闭临时客户端
        if temp_client and client:
            await client.close()


# 便捷函数：批量分析
async def batch_analyze_v22(
    symbols: List[str],
    max_concurrent: int = 10
) -> Dict[str, Dict[str, Any]]:
    """
    批量分析（v2.2）

    Args:
        symbols: 币种列表
        max_concurrent: 最大并发数

    Returns:
        {symbol: result, ...}
    """
    import asyncio

    # 创建共享客户端
    client = BinanceAsyncClient()
    await client.start()

    results = {}

    try:
        # 分批处理
        for i in range(0, len(symbols), max_concurrent):
            batch = symbols[i:i+max_concurrent]

            # 并发分析
            tasks = [analyze_symbol_v22(symbol, client) for symbol in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            # 收集结果
            for symbol, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    error(f"❌ 分析失败 {symbol}: {result}")
                    results[symbol] = _make_empty_result(symbol, f"exception: {str(result)}")
                else:
                    results[symbol] = result

        return results

    finally:
        await client.close()
