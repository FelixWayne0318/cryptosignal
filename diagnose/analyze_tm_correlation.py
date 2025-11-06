#!/usr/bin/env python3
# coding: utf-8
"""
diagnose/analyze_tm_correlation.py

T-M因子相关性分析脚本（P1.3）

目标：
- 实证分析T和M因子的实际相关性
- 决定是否需要正交化或重新设计M因子
- 为P2.2提供数据支撑

决策逻辑：
- 如果 avg_corr(T, M) < 0.5：保持现状，无需正交化
- 如果 0.5 ≤ avg_corr < 0.7：降低M权重（17% → 10%）
- 如果 avg_corr ≥ 0.7：需要正交化或重新设计M因子（方案C：短窗口版本）

作者：Claude (Sonnet 4.5)
日期：2025-11-05
版本：P1.3
"""

import sys
import json
import numpy as np
import pandas as pd
from typing import List, Dict, Tuple
from datetime import datetime, timedelta


def load_factor_history(symbol: str, factor_name: str, days: int = 30, use_realtime: bool = False) -> List[float]:
    """
    加载历史因子数据

    Args:
        symbol: 交易对符号
        factor_name: 因子名称（'T' 或 'M'）
        days: 天数
        use_realtime: 是否使用实时计算（调用analyze_symbol）

    注意：
    - use_realtime=False: 使用模拟数据（默认，用于测试）
    - use_realtime=True: 调用analyze_symbol实时计算（慢，但使用真实数据）
    - 生产环境建议：从日志文件或时序数据库读取历史因子值

    实际生产实现建议：
    1. 从Redis/InfluxDB等时序数据库读取历史因子值
    2. 从系统日志文件中解析因子值
    3. 从专门的因子存储表中查询
    """

    if use_realtime:
        # 实时计算选项：调用analyze_symbol获取当前因子值
        # 注意：这只能获取当前快照，无法获取历史序列
        # 如需历史序列，需要实现专门的存储机制
        try:
            from ats_core.pipeline.analyze_symbol import analyze_symbol
            result = analyze_symbol(symbol)
            if result.get('success') and factor_name in result:
                # 只能获取单个点，无法构建历史序列
                # 返回重复值作为占位（实际应该有历史存储）
                current_value = result[factor_name]
                print(f"  [实时] {symbol} 当前{factor_name}={current_value}")
                print(f"  [警告] 实时模式只能获取当前值，历史序列仍为模拟数据")
                # 生成模拟历史，但最新值使用真实值
                history = _generate_simulated_history(symbol, factor_name, days)
                history[-1] = current_value  # 最后一个点使用真实值
                return history
        except Exception as e:
            print(f"  [错误] 实时计算失败: {e}，降级到模拟数据")

    # 模拟数据模式（默认）
    print(f"  [模拟] {symbol} {factor_name}因子使用模拟数据")
    return _generate_simulated_history(symbol, factor_name, days)


def _generate_simulated_history(symbol: str, factor_name: str, days: int) -> List[float]:
    """
    生成模拟历史数据（用于测试）

    Args:
        symbol: 交易对符号
        factor_name: 因子名称
        days: 天数

    Returns:
        模拟的历史因子值列表
    """
    # 模拟数据：生成相关性约0.6的T和M
    np.random.seed(hash(symbol) % 2**32)
    n = days * 24  # 假设每小时一个数据点

    if factor_name == 'T':
        # T因子：趋势，范围[-100, +100]
        base_trend = np.cumsum(np.random.randn(n)) * 2
        T = np.clip(base_trend, -100, 100)
        return list(T)
    elif factor_name == 'M':
        # M因子：动量，与T有一定相关但不完全一致
        T = _generate_simulated_history(symbol, 'T', days)
        noise = np.random.randn(len(T)) * 30
        M = 0.6 * np.array(T) + 0.4 * noise  # 模拟0.6左右的相关性
        M = np.clip(M, -100, 100)
        return list(M)
    else:
        raise ValueError(f"不支持的因子: {factor_name}")


def analyze_symbol_tm_correlation(
    symbol: str,
    days: int = 30
) -> Dict:
    """
    分析单个币种的T-M相关性

    Args:
        symbol: 交易对符号
        days: 分析天数

    Returns:
        分析结果字典
    """
    try:
        # 加载T和M因子历史数据
        T_history = load_factor_history(symbol, 'T', days=days)
        M_history = load_factor_history(symbol, 'M', days=days)

        if len(T_history) < 10 or len(M_history) < 10:
            return {
                'symbol': symbol,
                'error': '数据不足',
                'data_points': min(len(T_history), len(M_history))
            }

        # 确保长度一致
        min_len = min(len(T_history), len(M_history))
        T_array = np.array(T_history[-min_len:])
        M_array = np.array(M_history[-min_len:])

        # 计算相关系数
        correlation = float(np.corrcoef(T_array, M_array)[0, 1])

        # 计算统计信息
        T_mean = float(np.mean(T_array))
        T_std = float(np.std(T_array))
        M_mean = float(np.mean(M_array))
        M_std = float(np.std(M_array))

        # 计算信息重叠度（绝对相关系数）
        info_overlap = abs(correlation)

        return {
            'symbol': symbol,
            'correlation': round(correlation, 4),
            'info_overlap': round(info_overlap, 4),
            'T_stats': {
                'mean': round(T_mean, 2),
                'std': round(T_std, 2),
                'range': [round(float(np.min(T_array)), 2), round(float(np.max(T_array)), 2)]
            },
            'M_stats': {
                'mean': round(M_mean, 2),
                'std': round(M_std, 2),
                'range': [round(float(np.min(M_array)), 2), round(float(np.max(M_array)), 2)]
            },
            'data_points': min_len,
            'analysis_period_days': days
        }

    except Exception as e:
        return {
            'symbol': symbol,
            'error': str(e)
        }


def analyze_tm_correlation_batch(
    symbol_list: List[str],
    days: int = 30
) -> Tuple[pd.DataFrame, Dict]:
    """
    批量分析T-M相关性

    Args:
        symbol_list: 交易对列表
        days: 分析天数

    Returns:
        (results_df, recommendation)
    """
    print(f"\n{'='*60}")
    print(f"T-M因子相关性分析")
    print(f"{'='*60}")
    print(f"分析币种数: {len(symbol_list)}")
    print(f"分析周期: 最近{days}天")
    print(f"{'='*60}\n")

    results = []
    for i, symbol in enumerate(symbol_list, 1):
        print(f"[{i}/{len(symbol_list)}] 分析 {symbol}...")
        result = analyze_symbol_tm_correlation(symbol, days=days)
        results.append(result)

    # 转换为DataFrame
    df = pd.DataFrame(results)

    # 过滤错误数据
    valid_df = df[~df['error'].notna()].copy() if 'error' in df.columns else df.copy()

    if len(valid_df) == 0:
        print("\n❌ 没有有效数据")
        return df, {'error': '没有有效数据'}

    # 统计分析
    avg_correlation = valid_df['correlation'].mean()
    median_correlation = valid_df['correlation'].median()
    std_correlation = valid_df['correlation'].std()
    abs_avg_correlation = valid_df['info_overlap'].mean()

    # 相关性分布
    high_corr_count = len(valid_df[valid_df['info_overlap'] > 0.7])
    medium_corr_count = len(valid_df[(valid_df['info_overlap'] >= 0.5) & (valid_df['info_overlap'] <= 0.7)])
    low_corr_count = len(valid_df[valid_df['info_overlap'] < 0.5])

    # 生成建议
    if abs_avg_correlation < 0.5:
        recommendation_text = "保持现状，无需正交化"
        action = "no_action"
        reason = "平均信息重叠度<50%，T和M因子保持独立性"
    elif abs_avg_correlation < 0.7:
        recommendation_text = "降低M因子权重：17% → 10%"
        action = "reduce_weight"
        reason = "中度相关，通过降低权重减少信息重复"
    else:
        recommendation_text = "需要正交化或重新设计M因子（方案C：短窗口版本）"
        action = "orthogonalize"
        reason = "高度相关，存在显著信息重叠"

    recommendation = {
        'recommendation': recommendation_text,
        'action': action,
        'reason': reason,
        'statistics': {
            'avg_correlation': round(avg_correlation, 4),
            'median_correlation': round(median_correlation, 4),
            'std_correlation': round(std_correlation, 4),
            'avg_info_overlap': round(abs_avg_correlation, 4),
            'valid_samples': len(valid_df),
            'total_samples': len(symbol_list)
        },
        'distribution': {
            'high_corr_count': high_corr_count,
            'medium_corr_count': medium_corr_count,
            'low_corr_count': low_corr_count,
            'high_corr_ratio': round(high_corr_count / len(valid_df), 3) if len(valid_df) > 0 else 0
        },
        'top_correlated_symbols': valid_df.nlargest(5, 'info_overlap')[['symbol', 'correlation', 'info_overlap']].to_dict('records') if len(valid_df) >= 5 else []
    }

    return df, recommendation


def print_recommendation(recommendation: Dict):
    """
    打印推荐结果

    Args:
        recommendation: 推荐字典
    """
    print(f"\n{'='*60}")
    print("分析结果")
    print(f"{'='*60}\n")

    stats = recommendation['statistics']
    dist = recommendation['distribution']

    print(f"有效样本: {stats['valid_samples']}/{stats['total_samples']}")
    print(f"平均相关系数: {stats['avg_correlation']:+.4f}")
    print(f"中位数相关系数: {stats['median_correlation']:+.4f}")
    print(f"标准差: {stats['std_correlation']:.4f}")
    print(f"平均信息重叠度: {stats['avg_info_overlap']:.1%}")

    print(f"\n相关性分布:")
    print(f"  高度相关 (>0.7): {dist['high_corr_count']} ({dist['high_corr_ratio']:.1%})")
    print(f"  中度相关 (0.5-0.7): {dist['medium_corr_count']}")
    print(f"  低度相关 (<0.5): {dist['low_corr_count']}")

    print(f"\n📊 推荐: {recommendation['recommendation']}")
    print(f"理由: {recommendation['reason']}")

    if recommendation['action'] == 'no_action':
        print(f"\n✅ T和M因子保持当前设计")
        print(f"   权重维持：T=24%, M=17%")
    elif recommendation['action'] == 'reduce_weight':
        print(f"\n⚠️ 建议调整M因子权重")
        print(f"   当前：T=24%, M=17%")
        print(f"   建议：T=24%, M=10%，空余7%分配给其他因子（如C或O）")
    else:  # orthogonalize
        print(f"\n🔴 建议重新设计M因子")
        print(f"   方案A：去掉slope，只保留加速度")
        print(f"   方案B：改用RSI+MACD")
        print(f"   方案C：保留slope但使用更短窗口（EMA3/5 vs T的EMA20）【推荐】")

    # 打印top相关币种
    if recommendation.get('top_correlated_symbols'):
        print(f"\nTop 5 高相关币种:")
        for i, item in enumerate(recommendation['top_correlated_symbols'], 1):
            print(f"  {i}. {item['symbol']:12s}: corr={item['correlation']:+.3f}, overlap={item['info_overlap']:.1%}")

    print(f"\n{'='*60}\n")


def main():
    """
    主函数
    """
    # 默认测试币种列表（实际使用时应从系统配置读取）
    default_symbols = [
        'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'ADAUSDT',
        'DOGEUSDT', 'MATICUSDT', 'DOTUSDT', 'AVAXUSDT', 'LINKUSDT',
        'UNIUSDT', 'ATOMUSDT', 'LTCUSDT', 'ETCUSDT', 'XRPUSDT'
    ]

    # 解析命令行参数
    if len(sys.argv) > 1:
        symbols_input = sys.argv[1]
        if symbols_input.endswith('.json'):
            # 从JSON文件读取
            with open(symbols_input, 'r') as f:
                symbol_list = json.load(f)
        else:
            # 从命令行读取（逗号分隔）
            symbol_list = symbols_input.split(',')
    else:
        symbol_list = default_symbols
        print(f"使用默认币种列表({len(symbol_list)}个)")

    # 分析天数
    days = int(sys.argv[2]) if len(sys.argv) > 2 else 30

    # 执行分析
    df, recommendation = analyze_tm_correlation_batch(symbol_list, days=days)

    # 保存结果
    output_file = f'tm_correlation_analysis_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    df.to_csv(output_file, index=False)
    print(f"\n💾 详细结果已保存到: {output_file}")

    # 保存推荐到JSON
    recommendation_file = output_file.replace('.csv', '_recommendation.json')
    with open(recommendation_file, 'w', encoding='utf-8') as f:
        json.dump(recommendation, f, indent=2, ensure_ascii=False)
    print(f"💾 推荐结果已保存到: {recommendation_file}")

    # 打印推荐
    print_recommendation(recommendation)

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
