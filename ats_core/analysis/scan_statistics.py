"""
扫描统计分析模块
每次批量扫描后自动收集数据、分析分布、发送到Telegram
帮助快速定位问题：阈值设置、因子分布、拒绝原因等
"""

import json
import statistics
from typing import Dict, List, Any
from datetime import datetime


class ScanStatistics:
    """扫描统计分析器"""

    def __init__(self):
        self.reset()

    def reset(self):
        """重置统计数据"""
        self.symbols_data = []  # 所有币种的详细数据
        self.signals = []  # 发出的信号
        self.rejections = {}  # 拒绝原因统计

    def add_symbol_result(self, symbol: str, result: Dict[str, Any]):
        """
        添加单个币种的分析结果

        Args:
            symbol: 币种名称
            result: analyze_symbol返回的完整结果
        """
        if not result:
            return

        # 提取关键数据
        scores = result.get('scores', {})
        modulation = result.get('modulation', {})
        publish_info = result.get('publish', {})
        gates_info = result.get('gates', {})
        prime_breakdown = publish_info.get('prime_breakdown', {})

        data = {
            'symbol': symbol,
            # 10因子（6核心+4调制器）
            'T': scores.get('T', 0),
            'M': scores.get('M', 0),
            'C': scores.get('C', 0),
            'V': scores.get('V', 0),
            'O': scores.get('O', 0),
            'B': scores.get('B', 0),
            'F': modulation.get('F', 0),
            'L': modulation.get('L', 0),
            'S': modulation.get('S', 0),
            'I': modulation.get('I', 0),
            # 综合指标
            'confidence': result.get('confidence', 0),
            'prime_strength': publish_info.get('prime_strength', 0),
            'edge': result.get('edge', 0),
            'gate_multiplier': gates_info.get('gate_multiplier', 0),
            'P_chosen': prime_breakdown.get('P_chosen', 0),
            'p_min_adjusted': result.get('p_min_adjusted', 0),
            # 信号状态
            'is_prime': publish_info.get('prime', False),
            'rejection_reason': publish_info.get('rejection_reason', []),
            # 数据质量
            'bars': result.get('bars', 0),
            'coin_age_hours': result.get('coin_age_hours', 0),
        }

        self.symbols_data.append(data)

        # 统计信号
        if data['is_prime']:
            self.signals.append(data)
        else:
            # 统计拒绝原因
            for reason in data['rejection_reason']:
                if isinstance(reason, str) and '❌' in reason:
                    # 提取主要原因（去掉具体数值）
                    key_reason = reason.split('(')[0].strip()
                    self.rejections[key_reason] = self.rejections.get(key_reason, 0) + 1

    def generate_summary_data(self) -> dict:
        """
        生成摘要数据（JSON格式，用于写入仓库）

        Returns:
            摘要数据字典
        """
        if not self.symbols_data:
            return {"error": "无数据可分析"}

        # 计算平均值
        edge_values = [abs(d['edge']) for d in self.symbols_data if d['edge'] != 0]
        conf_values = [d['confidence'] for d in self.symbols_data if d['confidence'] > 0]
        avg_edge = statistics.mean(edge_values) if edge_values else 0
        avg_confidence = statistics.mean(conf_values) if conf_values else 0

        # 新币统计
        new_coins = [d for d in self.symbols_data if d['coin_age_hours'] < 168]

        return {
            "timestamp": datetime.now().isoformat(),
            "scan_info": {
                "total_symbols": len(self.symbols_data),
                "signals_found": len(self.signals),
                "filtered": len(self.symbols_data) - len(self.signals)
            },
            "signals": [
                {
                    "symbol": s['symbol'],
                    "edge": round(s['edge'], 3),
                    "confidence": round(s['confidence'], 1),
                    "prime_strength": round(s['prime_strength'], 1),
                    "P_chosen": round(s['P_chosen'], 3)
                }
                for s in sorted(self.signals, key=lambda x: abs(x['edge']), reverse=True)
            ],
            "rejection_reasons": self.rejections,
            "close_to_threshold": [
                {
                    "symbol": c['symbol'],
                    "metric": c['metric'],
                    "gap": round(c['gap'], 3),
                    "current": round(c['current'], 3),
                    "threshold": round(c['threshold'], 3)
                }
                for c in self._find_close_to_threshold()[:20]
            ],
            "market_stats": {
                "avg_edge": round(avg_edge, 3),
                "avg_confidence": round(avg_confidence, 1),
                "new_coins_count": len(new_coins),
                "new_coins_pct": round(len(new_coins) / len(self.symbols_data) * 100, 1)
            },
            "factor_distribution": {
                factor: {
                    "min": round(self._calc_distribution(factor)['min'], 1),
                    "p25": round(self._calc_distribution(factor)['p25'], 1),
                    "median": round(self._calc_distribution(factor)['p50'], 1),
                    "p75": round(self._calc_distribution(factor)['p75'], 1),
                    "max": round(self._calc_distribution(factor)['max'], 1)
                }
                for factor in ['T', 'M', 'C', 'V', 'O', 'B', 'F', 'L', 'S', 'I']
            },
            "threshold_recommendations": self._generate_threshold_suggestions()
        }

    def generate_detail_data(self) -> dict:
        """
        生成详细数据（所有币种的完整信息）

        Returns:
            详细数据字典
        """
        return {
            "timestamp": datetime.now().isoformat(),
            "total_symbols": len(self.symbols_data),
            "symbols": self.symbols_data
        }

    def generate_statistics_report(self) -> str:
        """
        生成统计分析报告（Telegram格式）

        Returns:
            格式化的统计报告文本
        """
        if not self.symbols_data:
            return "❌ 无数据可分析"

        report = []
        report.append("=" * 50)
        report.append("📊 全市场扫描统计分析报告")
        report.append("=" * 50)
        report.append(f"🕐 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"📈 扫描币种: {len(self.symbols_data)} 个")
        report.append(f"✅ 信号数量: {len(self.signals)} 个")
        report.append(f"📉 过滤数量: {len(self.symbols_data) - len(self.signals)} 个")
        report.append("")

        # 1. 信号列表
        if self.signals:
            report.append("🎯 【发出的信号】")
            for sig in sorted(self.signals, key=lambda x: x['edge'], reverse=True)[:10]:
                report.append(
                    f"  {sig['symbol']}: "
                    f"Edge={sig['edge']:.2f}, "
                    f"Conf={sig['confidence']:.1f}, "
                    f"Prime={sig['prime_strength']:.1f}, "
                    f"P={sig['P_chosen']:.3f}"
                )
            if len(self.signals) > 10:
                report.append(f"  ... 还有{len(self.signals) - 10}个信号")
            report.append("")

        # 2. 接近阈值的币种（最有价值的分析！）
        report.append("🔍 【接近阈值的币种】（需要调整阈值的证据）")
        close_coins = self._find_close_to_threshold()
        if close_coins:
            for coin in close_coins[:15]:
                report.append(f"  {coin['desc']}")
            if len(close_coins) > 15:
                report.append(f"  ... 还有{len(close_coins) - 15}个币种接近阈值")
        else:
            report.append("  ✅ 无币种接近阈值（阈值设置合理）")
        report.append("")

        # 3. 拒绝原因统计
        if self.rejections:
            report.append("❌ 【拒绝原因分布】")
            sorted_rejections = sorted(self.rejections.items(), key=lambda x: x[1], reverse=True)
            for reason, count in sorted_rejections[:8]:
                pct = count / len(self.symbols_data) * 100
                report.append(f"  {reason}: {count}个 ({pct:.1f}%)")
            report.append("")

        # 4. 因子分布统计
        report.append("📊 【10因子分布统计】")
        factors = ['T', 'M', 'C', 'V', 'O', 'B', 'F', 'L', 'S', 'I']
        for factor in factors:
            stats = self._calc_distribution(factor)
            report.append(
                f"  {factor}: "
                f"Min={stats['min']:.1f}, "
                f"P25={stats['p25']:.1f}, "
                f"中位={stats['p50']:.1f}, "
                f"P75={stats['p75']:.1f}, "
                f"Max={stats['max']:.1f}"
            )
        report.append("")

        # 5. 综合指标分布
        report.append("📊 【综合指标分布】")
        metrics = [
            ('confidence', '置信度'),
            ('prime_strength', 'Prime强度'),
            ('edge', 'Edge优势'),
            ('gate_multiplier', '四门槛'),
        ]
        for metric_key, metric_name in metrics:
            stats = self._calc_distribution(metric_key)
            report.append(
                f"  {metric_name}: "
                f"Min={stats['min']:.2f}, "
                f"P25={stats['p25']:.2f}, "
                f"中位={stats['p50']:.2f}, "
                f"P75={stats['p75']:.2f}, "
                f"Max={stats['max']:.2f}"
            )
        report.append("")

        # 6. 数据质量分布
        report.append("📊 【数据质量分布】")
        bars_list = [d['bars'] for d in self.symbols_data if d['bars'] > 0]
        if bars_list:
            report.append(f"  K线数量: Min={min(bars_list)}, 中位={int(statistics.median(bars_list))}, Max={max(bars_list)}")

        age_hours = [d['coin_age_hours'] for d in self.symbols_data if d['coin_age_hours'] > 0]
        if age_hours:
            report.append(f"  币龄(小时): Min={min(age_hours):.1f}, 中位={statistics.median(age_hours):.1f}, Max={max(age_hours):.1f}")

        new_coins = len([d for d in self.symbols_data if d['coin_age_hours'] < 168])  # <7天
        report.append(f"  新币数量: {new_coins} 个 (<7天)")
        report.append("")

        # 7. 阈值建议
        report.append("💡 【阈值调整建议】")
        suggestions = self._generate_threshold_suggestions()
        if suggestions:
            for suggestion in suggestions:
                report.append(f"  {suggestion}")
        else:
            report.append("  ✅ 当前阈值设置合理，无需调整")

        report.append("=" * 50)

        return "\n".join(report)

    def _calc_distribution(self, field: str) -> Dict[str, float]:
        """计算某个字段的分布统计"""
        values = [d[field] for d in self.symbols_data if field in d]
        if not values:
            return {'min': 0, 'p25': 0, 'p50': 0, 'p75': 0, 'max': 0}

        # 使用statistics.quantiles计算分位数
        # quantiles(data, n=4) 返回 [p25, p50, p75]
        try:
            quantiles = statistics.quantiles(values, n=4)  # 返回 [25%, 50%, 75%]
            return {
                'min': min(values),
                'p25': quantiles[0],
                'p50': quantiles[1],
                'p75': quantiles[2],
                'max': max(values),
            }
        except statistics.StatisticsError:
            # 数据太少时（<2个），返回默认值
            val = values[0] if values else 0
            return {'min': val, 'p25': val, 'p50': val, 'p75': val, 'max': val}

    def _find_close_to_threshold(self) -> List[Dict[str, Any]]:
        """
        找到接近阈值的币种（最关键的分析！）

        Returns:
            接近阈值的币种列表，按缺口从小到大排序
        """
        # 当前阈值（需要和analyze_symbol.py保持一致）
        THRESHOLDS = {
            'confidence': 45,
            'edge': 0.48,
            'prime_strength': 54,
            'gate_multiplier': 0.84,  # P2.2: 从0.87降低到0.84
        }

        close_coins = []

        for data in self.symbols_data:
            if data['is_prime']:
                continue  # 已经通过的不看

            gaps = []

            # 检查每个阈值的缺口
            if data['confidence'] < THRESHOLDS['confidence']:
                gap = THRESHOLDS['confidence'] - data['confidence']
                if gap <= 5:  # 差距<=5
                    gaps.append(('Conf', gap, data['confidence'], THRESHOLDS['confidence']))

            if abs(data['edge']) < THRESHOLDS['edge']:
                gap = THRESHOLDS['edge'] - abs(data['edge'])
                if gap <= 0.10:  # 差距<=0.10
                    gaps.append(('Edge', gap, abs(data['edge']), THRESHOLDS['edge']))

            if data['prime_strength'] < THRESHOLDS['prime_strength']:
                gap = THRESHOLDS['prime_strength'] - data['prime_strength']
                if gap <= 5:  # 差距<=5
                    gaps.append(('Prime', gap, data['prime_strength'], THRESHOLDS['prime_strength']))

            if data['gate_multiplier'] < THRESHOLDS['gate_multiplier']:
                gap = THRESHOLDS['gate_multiplier'] - data['gate_multiplier']
                if gap <= 0.05:  # 差距<=0.05
                    gaps.append(('Gate', gap, data['gate_multiplier'], THRESHOLDS['gate_multiplier']))

            # 如果有接近阈值的指标，记录
            if gaps:
                # 找到最小缺口
                min_gap = min(gaps, key=lambda x: x[1])
                metric_name, gap, current, threshold = min_gap

                close_coins.append({
                    'symbol': data['symbol'],
                    'metric': metric_name,
                    'gap': gap,
                    'current': current,
                    'threshold': threshold,
                    'desc': f"{data['symbol']}: {metric_name}={current:.2f} (阈值{threshold:.2f}, 缺口{gap:.2f})"
                })

        # 按缺口从小到大排序
        return sorted(close_coins, key=lambda x: x['gap'])

    def _generate_threshold_suggestions(self) -> List[str]:
        """基于数据分布生成阈值调整建议"""
        suggestions = []

        close_coins = self._find_close_to_threshold()

        if not close_coins:
            return suggestions

        # 统计各指标的接近情况
        metric_counts = {}
        for coin in close_coins[:20]:  # 只看TOP 20最接近的
            metric = coin['metric']
            metric_counts[metric] = metric_counts.get(metric, 0) + 1

        # 如果某个指标有5个以上币种接近，建议降低
        for metric, count in sorted(metric_counts.items(), key=lambda x: x[1], reverse=True):
            if count >= 5:
                suggestions.append(f"⚠️ {metric}阈值可能偏高：{count}个币种非常接近但未通过，建议降低阈值")

        # 如果信号数为0，强烈建议
        if len(self.signals) == 0 and len(close_coins) >= 10:
            suggestions.append(f"🔴 当前0个信号，但有{len(close_coins)}个币种接近阈值，强烈建议降低阈值！")

        return suggestions

    def send_to_telegram(self, report: str, bot_token: str, chat_id: str) -> bool:
        """
        发送报告到Telegram

        Args:
            report: 报告文本
            bot_token: Telegram bot token
            chat_id: Telegram chat ID

        Returns:
            是否发送成功
        """
        try:
            import urllib.request
            import urllib.parse
            import json

            # 分段发送（Telegram有4096字符限制）
            max_length = 4000
            parts = []

            if len(report) <= max_length:
                parts = [report]
            else:
                # 分段发送
                lines = report.split('\n')
                current_part = []
                current_length = 0

                for line in lines:
                    line_length = len(line) + 1  # +1 for \n
                    if current_length + line_length > max_length:
                        parts.append('\n'.join(current_part))
                        current_part = [line]
                        current_length = line_length
                    else:
                        current_part.append(line)
                        current_length += line_length

                if current_part:
                    parts.append('\n'.join(current_part))

            # 发送每个分段
            api = f"https://api.telegram.org/bot{bot_token}/sendMessage"

            for i, part in enumerate(parts, 1):
                text = part
                if len(parts) > 1:
                    text = f"【第{i}/{len(parts)}部分】\n{part}"

                payload = {
                    'chat_id': chat_id,
                    'text': text
                    # 不使用parse_mode，纯文本模式（避免<>等字符被误解析为HTML）
                }

                data = urllib.parse.urlencode(payload).encode('utf-8')
                req = urllib.request.Request(api, data=data, method='POST')

                with urllib.request.urlopen(req, timeout=10) as response:
                    result = json.loads(response.read().decode('utf-8'))
                    if not result.get('ok'):
                        print(f"❌ Telegram API错误: {result}")
                        return False

            return True
        except Exception as e:
            print(f"❌ 发送Telegram失败: {e}")
            import traceback
            traceback.print_exc()
            return False


# 全局单例
_global_stats = ScanStatistics()


def get_global_stats() -> ScanStatistics:
    """获取全局统计实例"""
    return _global_stats


def reset_global_stats():
    """重置全局统计"""
    _global_stats.reset()
