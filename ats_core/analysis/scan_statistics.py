"""
扫描统计分析模块
每次批量扫描后自动收集数据、分析分布、发送到Telegram
帮助快速定位问题：阈值设置、因子分布、拒绝原因等
"""

import json
import statistics
from typing import Dict, List, Any
from datetime import datetime, timedelta, timezone

# UTC+8时区（北京时间）
TZ_UTC8 = timezone(timedelta(hours=8))


class ScanStatistics:
    """扫描统计分析器"""

    def __init__(self):
        self.reset()

    def reset(self):
        """重置统计数据"""
        self.symbols_data = []  # 所有币种的详细数据
        self.signals = []  # 发出的信号
        self.rejections = {}  # 拒绝原因统计
        # v7.3.49新增：v7.2增强统计
        self.v72_enhanced_count = 0  # v7.2增强成功数量
        self.v72_failed_count = 0  # v7.2增强失败数量
        self.v72_decision_changed_count = 0  # v7.2决策变更数量（拒绝了基础层通过的信号）

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
        scores_meta = result.get('scores_meta', {})  # v7.2+: 元数据

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
            # 方向和权重
            'side': result.get('side', 'unknown'),
            'weighted_score': result.get('weighted_score', 0),
            # 信号状态
            'is_prime': publish_info.get('prime', False),
            'rejection_reason': publish_info.get('rejection_reason', []),
            # 数据质量
            'bars': result.get('bars', 0),
            'coin_age_hours': result.get('coin_age_hours', 0),
            # v7.2+: F因子元数据
            'F_meta': scores_meta.get('F', {}),
            # v7.2+: I因子元数据
            'I_meta': scores_meta.get('I', {}),
            # v7.3.40 P0-Critical修复：保存intermediate_data（供realtime_signal_scanner的v7.2增强使用）
            # 根因：add_symbol_result()未保存intermediate_data导致scan_detail.json中klines/cvd_series为空
            # 结果：realtime_signal_scanner读取时发现数据长度=0，跳过v7.2增强，导致100%失败
            'intermediate_data': result.get('intermediate_data', {}),
        }

        self.symbols_data.append(data)

        # v7.3.49新增：统计v7.2增强情况
        v72_enhancements = result.get('v72_enhancements', {})
        if v72_enhancements:
            self.v72_enhanced_count += 1
            # 检查决策是否变更
            final_decision = v72_enhancements.get('final_decision', {})
            decision_changed = final_decision.get('decision_changed', False)
            original_was_prime = final_decision.get('original_was_prime', False)
            current_is_prime = final_decision.get('is_prime', False)
            # 如果基础层通过但v7.2拒绝，记录为决策变更
            if original_was_prime and not current_is_prime:
                self.v72_decision_changed_count += 1
        else:
            self.v72_failed_count += 1

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
            "timestamp": datetime.now(TZ_UTC8).isoformat(),
            "scan_info": {
                "total_symbols": len(self.symbols_data),
                "signals_found": len(self.signals),
                "filtered": len(self.symbols_data) - len(self.signals)
            },
            "signals": [
                {
                    "symbol": s['symbol'],
                    "side": s.get('side', 'unknown'),
                    "weighted_score": round(s.get('weighted_score', 0), 2),
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
            "factor_anomalies": self._detect_factor_anomalies(),  # v7.2+: 因子异常检测
            "threshold_recommendations": self._generate_threshold_suggestions()
        }

    def generate_detail_data(self) -> dict:
        """
        生成详细数据（所有币种的完整信息）

        Returns:
            详细数据字典
        """
        return {
            "timestamp": datetime.now(TZ_UTC8).isoformat(),
            "total_symbols": len(self.symbols_data),
            "symbols": self.symbols_data
        }

    def _detect_factor_anomalies(self) -> Dict[str, Any]:
        """
        v7.2+: 检测因子异常（饱和、固定值、双峰分布等）

        Returns:
            异常检测结果字典
        """
        anomalies = {
            'F_saturation': {'count': 0, 'pct': 0, 'coins': []},
            'I_default': {'count': 0, 'pct': 0, 'coins': []},
            'F_meta_summary': {},
            'I_meta_summary': {}
        }

        if not self.symbols_data:
            return anomalies

        total = len(self.symbols_data)

        # F因子饱和检测
        F_saturated_coins = []
        F_raw_values = []
        fund_momentum_values = []
        price_momentum_values = []

        for d in self.symbols_data:
            F_value = d.get('F', 0)
            F_meta = d.get('F_meta', {})

            # 检测饱和（|F| >= 98）
            if abs(F_value) >= 98:
                F_saturated_coins.append({
                    'symbol': d['symbol'],
                    'F': F_value,
                    'F_raw': F_meta.get('F_raw', 'N/A')
                })

            # 收集元数据
            if F_meta:
                F_raw = F_meta.get('F_raw')
                if F_raw != 'N/A' and F_raw is not None:
                    F_raw_values.append(F_raw)

                fund_momentum = F_meta.get('fund_momentum')
                if fund_momentum != 'N/A' and fund_momentum is not None:
                    fund_momentum_values.append(fund_momentum)

                price_momentum = F_meta.get('price_momentum')
                if price_momentum != 'N/A' and price_momentum is not None:
                    price_momentum_values.append(price_momentum)

        anomalies['F_saturation']['count'] = len(F_saturated_coins)
        anomalies['F_saturation']['pct'] = len(F_saturated_coins) / total * 100 if total > 0 else 0
        anomalies['F_saturation']['coins'] = F_saturated_coins[:10]  # 只记录前10个

        # F因子元数据统计
        if F_raw_values:
            anomalies['F_meta_summary'] = {
                'F_raw': self._calc_simple_stats(F_raw_values),
                'fund_momentum': self._calc_simple_stats(fund_momentum_values) if fund_momentum_values else {},
                'price_momentum': self._calc_simple_stats(price_momentum_values) if price_momentum_values else {}
            }

        # I因子默认值检测（I=50表示数据不足或计算失败）
        I_default_coins = []
        beta_btc_values = []
        # v7.4.0: 移除beta_eth（BTC-only回归，专注BTC独立性）

        for d in self.symbols_data:
            I_value = d.get('I', 0)
            I_meta = d.get('I_meta', {})

            # I=50可能是默认值
            if I_value == 50 or I_value == 0:
                error = I_meta.get('error')
                if error:  # 有error说明是降级到默认值
                    I_default_coins.append({
                        'symbol': d['symbol'],
                        'I': I_value,
                        'error': error
                    })

            # 收集Beta系数（v7.4.0: 仅BTC独立性分析）
            if I_meta and 'error' not in I_meta:
                beta_btc = I_meta.get('beta_btc')
                if beta_btc != 'N/A' and beta_btc is not None:
                    beta_btc_values.append(beta_btc)

        anomalies['I_default']['count'] = len(I_default_coins)
        anomalies['I_default']['pct'] = len(I_default_coins) / total * 100 if total > 0 else 0
        anomalies['I_default']['coins'] = I_default_coins[:10]

        # I因子元数据统计（v7.4.0: BTC独立性分析）
        if beta_btc_values:
            anomalies['I_meta_summary'] = {
                'beta_btc': self._calc_simple_stats(beta_btc_values)
            }

        return anomalies

    def _calc_simple_stats(self, values: List[float]) -> Dict[str, float]:
        """计算简单统计（用于元数据）"""
        if not values:
            return {}

        return {
            'min': round(min(values), 4),
            'mean': round(statistics.mean(values), 4),
            'median': round(statistics.median(values), 4),
            'max': round(max(values), 4),
            'count': len(values)
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
        report.append(f"🕐 时间: {datetime.now(TZ_UTC8).strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"📈 扫描币种: {len(self.symbols_data)} 个")
        report.append(f"✅ 信号数量: {len(self.signals)} 个")
        report.append(f"📉 过滤数量: {len(self.symbols_data) - len(self.signals)} 个")
        report.append("")

        # v7.4.0：系统配置区块
        report.append("⚙️  【系统配置】")
        try:
            from ats_core.cfg import CFG
            params = CFG.params

            # v7.4四步系统配置
            four_step_enabled = params.get("four_step_system", {}).get("enabled", False)
            fusion_enabled = params.get("four_step_system", {}).get("fusion_mode", {}).get("enabled", False)

            if four_step_enabled and fusion_enabled:
                report.append(f"  🚀 v7.4.0 四步决策系统（融合模式）")
                report.append(f"     Step1: 方向确认（A层+I因子+BTC对齐+硬veto）")
                report.append(f"     Step2: 时机判断（Enhanced F v2 六级评分）")
                report.append(f"     Step3: 风险管理（Entry/SL/TP精确价格）")
                report.append(f"     Step4: 质量控制（四道闸门：成交量/噪声/强度/矛盾）")
                report.append(f"  配置文件: ✅ 已加载 (config/params.json)")
            else:
                # 降级显示（如果四步系统未启用）
                from ats_core.config.threshold_config import get_thresholds
                config = get_thresholds()
                confidence_min = config.get_gate_threshold('gate6_综合质量', 'confidence_min', 20)
                prime_strength_min = config.get_gate_threshold('gate6_综合质量', 'prime_strength_min', 45)
                report.append(f"  ⚠️  v7.4.0 四步系统未启用（运行v6.6旧系统）")
                report.append(f"  Gate6阈值: confidence_min={confidence_min}, prime_strength_min={prime_strength_min}")
                report.append(f"  配置文件: ✅ 已加载 (config/signal_thresholds.json)")
        except Exception as e:
            report.append(f"  ⚠️  配置加载失败: {e}")
        report.append("")

        # v7.4.0：四步系统/旧系统增强统计
        if self.v72_enhanced_count > 0 or self.v72_failed_count > 0:
            total_count = self.v72_enhanced_count + self.v72_failed_count
            enhanced_pct = self.v72_enhanced_count / total_count * 100 if total_count > 0 else 0
            failed_pct = self.v72_failed_count / total_count * 100 if total_count > 0 else 0
            changed_pct = self.v72_decision_changed_count / total_count * 100 if total_count > 0 else 0
            signals_pct = len(self.signals) / total_count * 100 if total_count > 0 else 0

            try:
                from ats_core.cfg import CFG
                params = CFG.params
                four_step_enabled = params.get("four_step_system", {}).get("enabled", False)
                fusion_enabled = params.get("four_step_system", {}).get("fusion_mode", {}).get("enabled", False)

                if four_step_enabled and fusion_enabled:
                    report.append("🚀 【v7.4.0 四步系统统计】")
                    report.append(f"  四步分析完成: {self.v72_enhanced_count}个 ({enhanced_pct:.1f}%)")
                    if self.v72_failed_count > 0:
                        report.append(f"  分析失败: {self.v72_failed_count}个 ({failed_pct:.1f}%) ⚠️")
                    report.append(f"  决策变更: {self.v72_decision_changed_count}个 (四步系统覆盖旧系统)")
                    report.append(f"  四道闸门全部通过: {len(self.signals)}个 ({signals_pct:.1f}%)")
                else:
                    report.append("🔧 【v6.6增强统计（旧系统）】")
                    report.append(f"  增强成功: {self.v72_enhanced_count}个 ({enhanced_pct:.1f}%)")
                    if self.v72_failed_count > 0:
                        report.append(f"  增强失败: {self.v72_failed_count}个 ({failed_pct:.1f}%) ⚠️")
                    report.append(f"  决策变更: {self.v72_decision_changed_count}个")
                    report.append(f"  所有闸门通过: {len(self.signals)}个 ({signals_pct:.1f}%)")
            except:
                # 降级显示（配置读取失败）
                report.append("🔧 【系统增强统计】")
                report.append(f"  增强成功: {self.v72_enhanced_count}个 ({enhanced_pct:.1f}%)")
                if self.v72_failed_count > 0:
                    report.append(f"  增强失败: {self.v72_failed_count}个 ({failed_pct:.1f}%) ⚠️")
                report.append(f"  决策变更: {self.v72_decision_changed_count}个")
                report.append(f"  所有闸门通过: {len(self.signals)}个 ({signals_pct:.1f}%)")

            report.append("")

        # v7.2+: 因子异常检测
        anomalies = self._detect_factor_anomalies()

        # 如果有异常，优先显示
        if anomalies['F_saturation']['count'] > 0 or anomalies['I_default']['count'] > 0:
            report.append("⚠️  【因子异常警告】")

            if anomalies['F_saturation']['count'] > 0:
                sat_count = anomalies['F_saturation']['count']
                sat_pct = anomalies['F_saturation']['pct']
                report.append(f"  🔴 F因子饱和: {sat_count}个币种 ({sat_pct:.1f}%) |F|>=98")
                report.append(f"     可能原因: scale参数过小，建议从2.0增大到5.0+")

                # 显示几个例子
                for coin in anomalies['F_saturation']['coins'][:5]:
                    report.append(f"     - {coin['symbol']}: F={coin['F']}, F_raw={coin['F_raw']}")

            if anomalies['I_default']['count'] > 0:
                default_count = anomalies['I_default']['count']
                default_pct = anomalies['I_default']['pct']
                report.append(f"  ⚠️  I因子降级: {default_count}个币种 ({default_pct:.1f}%) 使用默认值")
                report.append(f"     可能原因: BTC K线数据不足（v7.4.0需要48h BTC数据用于独立性分析）")

            report.append("")

        # 1. 信号列表（v7.3.49新增：Gate6/7通过标记 - 建议3）
        if self.signals:
            report.append("🎯 【发出的信号】")
            # 获取Gate6阈值用于标记
            try:
                from ats_core.config.threshold_config import get_thresholds
                config = get_thresholds()
                confidence_min = config.get_gate_threshold('gate6_综合质量', 'confidence_min', 20)
                prime_strength_min = config.get_gate_threshold('gate6_综合质量', 'prime_strength_min', 45)
            except:
                confidence_min = 25
                prime_strength_min = 50

            for sig in sorted(self.signals, key=lambda x: x['edge'], reverse=True)[:10]:
                # 检查是否通过Gate6阈值，添加✓标记
                conf_val = sig['confidence']
                conf_mark = "✓" if conf_val >= confidence_min else ""
                prime_val = sig['prime_strength']
                prime_mark = "✓" if prime_val >= prime_strength_min else ""

                report.append(
                    f"  {sig['symbol']}: "
                    f"Edge={sig['edge']:.2f}, "
                    f"Conf={conf_val:.1f}{conf_mark}, "
                    f"Prime={prime_val:.1f}{prime_mark}, "
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

        # v7.2+: F/I因子元数据统计
        if anomalies['F_meta_summary'] or anomalies['I_meta_summary']:
            report.append("📊 【F/I因子诊断数据】")

            if anomalies['F_meta_summary']:
                F_raw_stats = anomalies['F_meta_summary'].get('F_raw', {})
                if F_raw_stats:
                    report.append(
                        f"  F_raw: "
                        f"Min={F_raw_stats.get('min', 0):.2f}, "
                        f"Mean={F_raw_stats.get('mean', 0):.2f}, "
                        f"Median={F_raw_stats.get('median', 0):.2f}, "
                        f"Max={F_raw_stats.get('max', 0):.2f} "
                        f"({F_raw_stats.get('count', 0)}个币种)"
                    )

                    # 判断scale是否合适
                    max_abs_F_raw = max(abs(F_raw_stats.get('min', 0)), abs(F_raw_stats.get('max', 0)))
                    if max_abs_F_raw > 6.0:  # scale=2.0时的饱和点
                        report.append(f"     ⚠️  最大|F_raw|={max_abs_F_raw:.2f} > 6.0，建议增大scale参数")

                fund_momentum_stats = anomalies['F_meta_summary'].get('fund_momentum', {})
                if fund_momentum_stats:
                    report.append(
                        f"  fund_momentum: "
                        f"Mean={fund_momentum_stats.get('mean', 0):.4f}, "
                        f"Median={fund_momentum_stats.get('median', 0):.4f}"
                    )

                price_momentum_stats = anomalies['F_meta_summary'].get('price_momentum', {})
                if price_momentum_stats:
                    report.append(
                        f"  price_momentum: "
                        f"Mean={price_momentum_stats.get('mean', 0):.4f}, "
                        f"Median={price_momentum_stats.get('median', 0):.4f}"
                    )

            if anomalies['I_meta_summary']:
                beta_btc_stats = anomalies['I_meta_summary'].get('beta_btc', {})
                if beta_btc_stats:
                    report.append(
                        f"  beta_btc (BTC独立性分析): "
                        f"Min={beta_btc_stats.get('min', 0):.2f}, "
                        f"Mean={beta_btc_stats.get('mean', 0):.2f}, "
                        f"Median={beta_btc_stats.get('median', 0):.2f}, "
                        f"Max={beta_btc_stats.get('max', 0):.2f} "
                        f"({beta_btc_stats.get('count', 0)}个币种)"
                    )
                # v7.4.0: 移除beta_eth显示（已废弃ETH依赖）

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
        # v7.3.47修复：从配置文件读取阈值，不再硬编码
        # 注意：v7.2实际使用五道闸门（F/EV/P/I/data_quality），但这里为了向后兼容
        # 仍然检查confidence/prime_strength等综合指标
        try:
            from ats_core.config.unified_config import UnifiedConfig
            config = UnifiedConfig()
            # 读取Gate6综合质量阈值（v7.3.47新增）
            confidence_min = config.get_gate_threshold('gate6_综合质量', 'confidence_min', 20)
            prime_strength_min = config.get_gate_threshold('gate6_综合质量', 'prime_strength_min', 45)
            # edge和gate_multiplier暂时保留旧值（向后兼容）
            THRESHOLDS = {
                'confidence': confidence_min,
                'edge': 0.12,  # 从配置mature_coin.edge_min读取
                'prime_strength': prime_strength_min,
                'gate_multiplier': 0.84,
            }
        except Exception as e:
            # 配置读取失败，使用兜底值
            THRESHOLDS = {
                'confidence': 20,
                'edge': 0.12,
                'prime_strength': 45,
                'gate_multiplier': 0.84,
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
