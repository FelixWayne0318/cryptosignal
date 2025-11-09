# coding: utf-8
"""
完善的分析数据库 - v7.2增强版

设计理念:
1. 预定义所有分析字段，分析时只需填充
2. 分离存储不同层次的数据（市场数据、因子、信号、结果）
3. 支持高效查询和统计分析
4. 支持数据回溯和模型优化

表结构:
1. market_data - 市场原始数据（价格、成交量、资金流）
2. factor_scores - 因子计算结果（Prime, T, F, I, G, H等）
3. signal_analysis - 信号分析完整数据
4. gate_evaluation - 四道闸门评估结果
5. modulator_effects - 调制器影响效果
6. signal_outcomes - 信号实际结果（需人工或自动跟踪）
7. scan_statistics - 扫描统计数据（历史扫描记录）
"""

import sqlite3
import json
import time
from typing import Dict, Any, Optional, List
from pathlib import Path
from datetime import datetime, timedelta, timezone

# UTC+8时区（北京时间）
TZ_UTC8 = timezone(timedelta(hours=8))


class AnalysisDB:
    """完善的分析数据库"""

    def __init__(self, db_path: str = None):
        """
        初始化分析数据库

        Args:
            db_path: SQLite数据库路径（默认为项目根目录下的data/analysis.db）
        """
        if db_path is None:
            # 自动检测项目根目录（从当前文件向上3级）
            import os
            project_root = Path(__file__).resolve().parent.parent.parent
            db_path = os.path.join(str(project_root), "data", "analysis.db")

        self.db_path = db_path

        # 确保data目录存在
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        # 初始化数据库
        self._init_database()

    def _init_database(self):
        """初始化数据库表结构"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # ========================================
        # 表1: 市场原始数据
        # ========================================
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS market_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp INTEGER NOT NULL,
            symbol TEXT NOT NULL,

            -- 价格数据
            price REAL NOT NULL,
            price_24h_change_pct REAL,

            -- 成交量数据
            volume_24h REAL,
            volume_7d_avg REAL,
            volume_30d_avg REAL,

            -- 资金流数据
            inflow_24h REAL,
            outflow_24h REAL,
            net_flow_24h REAL,

            -- 波动率数据
            atr REAL,
            atr_pct REAL,
            volatility_7d REAL,

            -- 市场深度
            bid_depth REAL,
            ask_depth REAL,
            spread_bps REAL,

            -- 大盘数据
            btc_price REAL,
            btc_24h_change_pct REAL,
            eth_price REAL,
            eth_24h_change_pct REAL,

            -- 索引
            UNIQUE(timestamp, symbol)
        )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_market_timestamp ON market_data(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_market_symbol ON market_data(symbol)")

        # ========================================
        # 表2: 因子计算结果
        # ========================================
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS factor_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp INTEGER NOT NULL,
            symbol TEXT NOT NULL,

            -- A组因子 (Direction: 80%)
            mvrv_score REAL,
            prime_score REAL,
            trend_score REAL,

            -- B组因子 (Modulation: 0%, 调整Teff和cost)
            fund_score REAL,              -- F因子
            independence_score REAL,      -- I因子

            -- C组因子 (Quality: 20%)
            governance_score REAL,        -- G因子
            health_score REAL,            -- H因子（可选）

            -- 加权方向分数
            direction_score REAL,         -- MVRV*0.3 + Prime*0.3 + T*0.4
            quality_score REAL,           -- G*0.5 + H*0.5
            weighted_score REAL,          -- direction*0.8 + quality*0.2

            -- 信号方向
            side TEXT,                    -- LONG / SHORT
            side_long INTEGER,            -- 1=LONG, 0=SHORT

            -- F因子细节
            f_price_momentum REAL,
            f_fund_momentum REAL,
            f_divergence REAL,

            -- I因子细节
            i_beta_btc REAL,
            i_beta_eth REAL,
            i_beta_sum REAL,
            i_alpha REAL,
            i_r_squared REAL,

            -- 市场环境
            market_regime REAL,           -- BTC/ETH趋势 [-100, +100]

            -- 索引
            UNIQUE(timestamp, symbol)
        )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_factor_timestamp ON factor_scores(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_factor_symbol ON factor_scores(symbol)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_factor_side ON factor_scores(side)")

        # ========================================
        # 表3: 信号分析完整数据
        # ========================================
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS signal_analysis (
            signal_id TEXT PRIMARY KEY,
            timestamp INTEGER NOT NULL,
            symbol TEXT NOT NULL,
            side TEXT NOT NULL,

            -- 原始输出
            raw_probability REAL,         -- 原始P (lookup表)
            raw_ev REAL,                  -- 原始EV

            -- 调制后输出
            teff_total REAL,              -- 总有效期限调整
            teff_f REAL,                  -- F调制的Teff
            teff_i REAL,                  -- I调制的Teff

            cost_eff_total REAL,          -- 总成本调整
            cost_eff_f REAL,              -- F调制的成本
            cost_eff_i REAL,              -- I调制的成本

            calibrated_probability REAL,  -- 校准后的P
            calibrated_ev REAL,           -- 校准后的EV

            -- 目标设置
            tp_pct REAL,                  -- 止盈目标
            sl_pct REAL,                  -- 止损目标
            base_cost_bps REAL,           -- 基础成本
            adjusted_cost_bps REAL,       -- 调整后成本

            -- 信号质量
            confidence REAL,              -- 综合置信度 (weighted_score)
            signal_strength TEXT,         -- STRONG / NORMAL / WEAK

            -- 是否通过所有闸门
            all_gates_passed INTEGER,     -- 1=通过, 0=未通过
            reject_reason TEXT,           -- 拒绝原因（如果未通过）

            -- 完整数据JSON (备份)
            full_data TEXT,               -- JSON格式的完整分析数据

            -- 索引
            UNIQUE(signal_id)
        )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_signal_timestamp ON signal_analysis(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_signal_symbol ON signal_analysis(symbol)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_signal_side ON signal_analysis(side)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_signal_gates ON signal_analysis(all_gates_passed)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_signal_confidence ON signal_analysis(confidence)")

        # ========================================
        # 表4: 四道闸门评估结果
        # ========================================
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS gate_evaluation (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id TEXT NOT NULL,
            timestamp INTEGER NOT NULL,

            -- 闸门1: 数据质量
            gate1_passed INTEGER,
            gate1_reason TEXT,
            gate1_mvrv_valid INTEGER,
            gate1_prime_valid INTEGER,
            gate1_atr_valid INTEGER,

            -- 闸门2: 资金支持
            gate2_passed INTEGER,
            gate2_reason TEXT,
            gate2_f_score REAL,
            gate2_f_directional REAL,
            gate2_threshold REAL,

            -- 闸门3: 市场风险
            gate3_passed INTEGER,
            gate3_reason TEXT,
            gate3_independence REAL,
            gate3_market_regime REAL,
            gate3_is_adverse INTEGER,

            -- 闸门4: 执行成本
            gate4_passed INTEGER,
            gate4_reason TEXT,
            gate4_ev_net REAL,
            gate4_ev_threshold REAL,
            gate4_cost_bps REAL,

            -- 总结
            all_passed INTEGER,
            first_reject_gate INTEGER,    -- 第一个拒绝的闸门 (1-4)

            FOREIGN KEY (signal_id) REFERENCES signal_analysis(signal_id)
        )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_gate_signal_id ON gate_evaluation(signal_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_gate_timestamp ON gate_evaluation(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_gate_all_passed ON gate_evaluation(all_passed)")

        # ========================================
        # 表5: 调制器影响效果
        # ========================================
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS modulator_effects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id TEXT NOT NULL,
            timestamp INTEGER NOT NULL,

            -- F调制器效果
            f_score REAL,
            f_teff_before REAL,
            f_teff_after REAL,
            f_teff_change_pct REAL,
            f_cost_before REAL,
            f_cost_after REAL,
            f_cost_change_bps REAL,
            f_p_impact_pct REAL,          -- F对P的影响

            -- I调制器效果
            i_score REAL,
            i_teff_before REAL,
            i_teff_after REAL,
            i_teff_change_pct REAL,
            i_cost_before REAL,
            i_cost_after REAL,
            i_cost_change_bps REAL,
            i_p_impact_pct REAL,          -- I对P的影响

            -- 总调制效果
            total_teff REAL,
            total_p_change_pct REAL,      -- 总P变化
            total_ev_change REAL,         -- 总EV变化

            FOREIGN KEY (signal_id) REFERENCES signal_analysis(signal_id)
        )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_mod_signal_id ON modulator_effects(signal_id)")

        # ========================================
        # 表6: 信号实际结果（需跟踪）
        # ========================================
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS signal_outcomes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id TEXT NOT NULL,
            timestamp INTEGER NOT NULL,

            -- 执行信息
            executed INTEGER,             -- 是否执行 (1/0)
            entry_price REAL,
            entry_time INTEGER,

            -- 结果信息
            outcome TEXT,                 -- WIN / LOSS / TIMEOUT / BREAKEVEN
            exit_price REAL,
            exit_time INTEGER,
            exit_reason TEXT,             -- TP / SL / TIMEOUT / MANUAL

            -- 收益数据
            pnl_pct REAL,
            pnl_usdt REAL,
            hold_hours REAL,

            -- 成本数据
            actual_entry_cost_bps REAL,
            actual_exit_cost_bps REAL,
            funding_cost_bps REAL,
            total_cost_bps REAL,

            -- 预测vs实际
            predicted_p REAL,
            actual_win INTEGER,           -- 实际是否赢 (1/0)
            predicted_ev REAL,
            actual_ev REAL,

            -- 备注
            notes TEXT,

            FOREIGN KEY (signal_id) REFERENCES signal_analysis(signal_id)
        )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_outcome_signal_id ON signal_outcomes(signal_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_outcome_timestamp ON signal_outcomes(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_outcome_outcome ON signal_outcomes(outcome)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_outcome_executed ON signal_outcomes(executed)")

        # ========================================
        # 表7: 扫描统计数据（新增v7.2）
        # ========================================
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS scan_statistics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp INTEGER NOT NULL,
            scan_date TEXT,

            -- 扫描基本信息
            total_symbols INTEGER,
            signals_found INTEGER,
            filtered INTEGER,

            -- 市场统计
            avg_edge REAL,
            avg_confidence REAL,
            new_coins_count INTEGER,
            new_coins_pct REAL,

            -- 性能统计
            scan_duration_sec REAL,
            scan_speed_coins_per_sec REAL,
            cache_hit_rate REAL,
            memory_mb REAL,

            -- 拒绝原因统计（JSON）
            rejection_reasons TEXT,

            -- 因子分布统计（JSON）
            factor_distribution TEXT,

            -- 接近阈值的币种（JSON）
            close_to_threshold TEXT,

            -- 阈值建议（JSON）
            threshold_recommendations TEXT,

            -- 发出的信号列表（JSON）
            signals_list TEXT,

            -- 备注
            notes TEXT
        )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_scan_timestamp ON scan_statistics(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_scan_date ON scan_statistics(scan_date)")

        conn.commit()
        conn.close()

    # ========================================
    # 写入方法
    # ========================================

    def write_market_data(self, data: Dict[str, Any]) -> int:
        """
        写入市场原始数据

        Args:
            data: 市场数据字典

        Returns:
            record_id: 记录ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
            INSERT OR REPLACE INTO market_data (
                timestamp, symbol,
                price, price_24h_change_pct,
                volume_24h, volume_7d_avg, volume_30d_avg,
                inflow_24h, outflow_24h, net_flow_24h,
                atr, atr_pct, volatility_7d,
                bid_depth, ask_depth, spread_bps,
                btc_price, btc_24h_change_pct,
                eth_price, eth_24h_change_pct
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data.get('timestamp', int(time.time() * 1000)),
                data['symbol'],
                data['price'],
                data.get('price_24h_change_pct', 0),
                data.get('volume_24h', 0),
                data.get('volume_7d_avg', 0),
                data.get('volume_30d_avg', 0),
                data.get('inflow_24h', 0),
                data.get('outflow_24h', 0),
                data.get('net_flow_24h', 0),
                data.get('atr', 0),
                data.get('atr_pct', 0),
                data.get('volatility_7d', 0),
                data.get('bid_depth', 0),
                data.get('ask_depth', 0),
                data.get('spread_bps', 0),
                data.get('btc_price', 0),
                data.get('btc_24h_change_pct', 0),
                data.get('eth_price', 0),
                data.get('eth_24h_change_pct', 0)
            ))

            record_id = cursor.lastrowid
            conn.commit()
            return record_id

        finally:
            conn.close()

    def write_factor_scores(self, data: Dict[str, Any]) -> int:
        """
        写入因子计算结果

        Args:
            data: 因子数据字典（来自analyze_with_v72_enhancements）

        Returns:
            record_id: 记录ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        scores = data.get('scores', {})
        v72 = data.get('v72_enhancements', {})

        try:
            cursor.execute("""
            INSERT OR REPLACE INTO factor_scores (
                timestamp, symbol,
                mvrv_score, prime_score, trend_score,
                fund_score, independence_score,
                governance_score, health_score,
                direction_score, quality_score, weighted_score,
                side, side_long,
                f_price_momentum, f_fund_momentum, f_divergence,
                i_beta_btc, i_beta_eth, i_beta_sum, i_alpha, i_r_squared,
                market_regime
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data.get('timestamp', int(time.time() * 1000)),
                data['symbol'],
                scores.get('MVRV', 0),
                scores.get('Prime', 0),
                scores.get('T', 0),
                scores.get('F', 0),
                scores.get('I', 50),
                scores.get('G', 0),
                scores.get('H', 0),
                data.get('direction_score', 0),
                data.get('quality_score', 0),
                data.get('weighted_score', 0),
                data.get('side', 'unknown'),
                1 if data.get('side_long', True) else 0,
                data.get('F_components', {}).get('price_momentum', 0),
                data.get('F_components', {}).get('fund_momentum', 0),
                data.get('F_components', {}).get('divergence', 0),
                data.get('I_components', {}).get('beta_BTC', 0),
                data.get('I_components', {}).get('beta_ETH', 0),
                data.get('I_components', {}).get('beta_sum', 0),
                data.get('I_components', {}).get('alpha', 0),
                data.get('I_components', {}).get('R_squared', 0),
                data.get('market_regime', 0)
            ))

            record_id = cursor.lastrowid
            conn.commit()
            return record_id

        finally:
            conn.close()

    def write_signal_analysis(self, data: Dict[str, Any]) -> str:
        """
        写入信号分析完整数据

        Args:
            data: 信号数据字典（来自analyze_with_v72_enhancements）

        Returns:
            signal_id: 信号ID
        """
        timestamp = data.get('timestamp', int(time.time() * 1000))
        symbol = data['symbol']
        signal_id = f"{symbol}_{timestamp}"

        v72 = data.get('v72_enhancements', {})
        modulators = v72.get('modulators', {})

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # 提取调制器效果
            f_mod = modulators.get('F', {})
            i_mod = modulators.get('I', {})

            cursor.execute("""
            INSERT OR REPLACE INTO signal_analysis (
                signal_id, timestamp, symbol, side,
                raw_probability, raw_ev,
                teff_total, teff_f, teff_i,
                cost_eff_total, cost_eff_f, cost_eff_i,
                calibrated_probability, calibrated_ev,
                tp_pct, sl_pct, base_cost_bps, adjusted_cost_bps,
                confidence, signal_strength,
                all_gates_passed, reject_reason,
                full_data
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                signal_id,
                timestamp,
                symbol,
                data.get('side', 'unknown'),
                data.get('probability', 0.5),
                data.get('expected_value', 0),
                v72.get('Teff_total', 1.0),
                f_mod.get('Teff', 1.0),
                i_mod.get('Teff', 1.0),
                v72.get('cost_eff_total', 0),
                f_mod.get('cost_eff', 0),
                i_mod.get('cost_eff', 0),
                v72.get('P_calibrated', 0.5),
                v72.get('EV_net', 0),
                data.get('tp_pct', 0.03),
                data.get('sl_pct', 0.015),
                data.get('base_cost_bps', 5.0),
                v72.get('adjusted_cost_bps', 5.0),
                data.get('weighted_score', 0),
                data.get('signal_strength', 'NORMAL'),
                1 if v72.get('all_gates_passed', False) else 0,
                v72.get('reject_reason', ''),
                json.dumps(data)
            ))

            conn.commit()
            return signal_id

        finally:
            conn.close()

    def write_gate_evaluation(self, signal_id: str, data: Dict[str, Any]):
        """
        写入闸门评估结果

        Args:
            signal_id: 信号ID
            data: 信号数据（包含gate_results）
        """
        v72 = data.get('v72_enhancements', {})
        gate_results = v72.get('gate_results', {})

        # 提取各闸门结果
        g1 = gate_results.get('gate1_data_quality', {})
        g2 = gate_results.get('gate2_fund_support', {})
        g3 = gate_results.get('gate3_market_risk', {})
        g4 = gate_results.get('gate4_execution_cost', {})

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
            INSERT INTO gate_evaluation (
                signal_id, timestamp,
                gate1_passed, gate1_reason,
                gate2_passed, gate2_reason, gate2_f_score, gate2_f_directional,
                gate3_passed, gate3_reason, gate3_independence, gate3_market_regime,
                gate4_passed, gate4_reason, gate4_ev_net, gate4_cost_bps,
                all_passed, first_reject_gate
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                signal_id,
                data.get('timestamp', int(time.time() * 1000)),
                1 if g1.get('passed', False) else 0,
                g1.get('reason', ''),
                1 if g2.get('passed', False) else 0,
                g2.get('reason', ''),
                data.get('scores', {}).get('F', 0),
                g2.get('F_directional', 0),
                1 if g3.get('passed', False) else 0,
                g3.get('reason', ''),
                data.get('scores', {}).get('I', 50),
                data.get('market_regime', 0),
                1 if g4.get('passed', False) else 0,
                g4.get('reason', ''),
                v72.get('EV_net', 0),
                v72.get('adjusted_cost_bps', 5.0),
                1 if v72.get('all_gates_passed', False) else 0,
                self._find_first_reject_gate(gate_results)
            ))

            conn.commit()

        finally:
            conn.close()

    def write_modulator_effects(self, signal_id: str, data: Dict[str, Any]):
        """
        写入调制器影响效果

        Args:
            signal_id: 信号ID
            data: 信号数据（包含modulator效果）
        """
        v72 = data.get('v72_enhancements', {})
        modulators = v72.get('modulators', {})
        f_mod = modulators.get('F', {})
        i_mod = modulators.get('I', {})

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # 计算F的影响
            f_teff = f_mod.get('Teff', 1.0)
            f_p_impact = (f_teff - 1.0) * 100  # Teff=1.2 → +20%

            # 计算I的影响
            i_teff = i_mod.get('Teff', 1.0)
            i_p_impact = (i_teff - 1.0) * 100

            # 总影响
            total_teff = v72.get('Teff_total', 1.0)
            raw_p = data.get('probability', 0.5)
            cal_p = v72.get('P_calibrated', 0.5)
            total_p_change = (cal_p - raw_p) / raw_p * 100 if raw_p > 0 else 0

            raw_ev = data.get('expected_value', 0)
            cal_ev = v72.get('EV_net', 0)
            total_ev_change = cal_ev - raw_ev

            cursor.execute("""
            INSERT INTO modulator_effects (
                signal_id, timestamp,
                f_score, f_teff_before, f_teff_after, f_teff_change_pct,
                f_cost_before, f_cost_after, f_cost_change_bps, f_p_impact_pct,
                i_score, i_teff_before, i_teff_after, i_teff_change_pct,
                i_cost_before, i_cost_after, i_cost_change_bps, i_p_impact_pct,
                total_teff, total_p_change_pct, total_ev_change
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                signal_id,
                data.get('timestamp', int(time.time() * 1000)),
                data.get('scores', {}).get('F', 0),
                1.0, f_teff, (f_teff - 1.0) * 100,
                data.get('base_cost_bps', 5.0),
                data.get('base_cost_bps', 5.0) + f_mod.get('cost_eff', 0),
                f_mod.get('cost_eff', 0),
                f_p_impact,
                data.get('scores', {}).get('I', 50),
                1.0, i_teff, (i_teff - 1.0) * 100,
                data.get('base_cost_bps', 5.0),
                data.get('base_cost_bps', 5.0) + i_mod.get('cost_eff', 0),
                i_mod.get('cost_eff', 0),
                i_p_impact,
                total_teff,
                total_p_change,
                total_ev_change
            ))

            conn.commit()

        finally:
            conn.close()

    def write_complete_signal(self, data: Dict[str, Any]) -> str:
        """
        一次性写入信号的所有数据（市场+因子+信号+闸门+调制器）

        这是最常用的方法 - 分析完成后调用一次即可

        Args:
            data: 完整的信号数据（来自analyze_with_v72_enhancements）

        Returns:
            signal_id: 信号ID
        """
        # 1. 写入市场数据
        self.write_market_data(data)

        # 2. 写入因子分数
        self.write_factor_scores(data)

        # 3. 写入信号分析
        signal_id = self.write_signal_analysis(data)

        # 4. 写入闸门评估
        self.write_gate_evaluation(signal_id, data)

        # 5. 写入调制器效果
        self.write_modulator_effects(signal_id, data)

        return signal_id

    def update_signal_outcome(self, signal_id: str, outcome_data: Dict[str, Any]):
        """
        更新信号实际结果（需要人工或自动跟踪）

        Args:
            signal_id: 信号ID
            outcome_data: 结果数据
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
            INSERT OR REPLACE INTO signal_outcomes (
                signal_id, timestamp,
                executed, entry_price, entry_time,
                outcome, exit_price, exit_time, exit_reason,
                pnl_pct, pnl_usdt, hold_hours,
                actual_entry_cost_bps, actual_exit_cost_bps, funding_cost_bps, total_cost_bps,
                predicted_p, actual_win, predicted_ev, actual_ev,
                notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                signal_id,
                outcome_data.get('timestamp', int(time.time() * 1000)),
                1 if outcome_data.get('executed', False) else 0,
                outcome_data.get('entry_price', 0),
                outcome_data.get('entry_time', 0),
                outcome_data.get('outcome', 'unknown'),
                outcome_data.get('exit_price', 0),
                outcome_data.get('exit_time', 0),
                outcome_data.get('exit_reason', ''),
                outcome_data.get('pnl_pct', 0),
                outcome_data.get('pnl_usdt', 0),
                outcome_data.get('hold_hours', 0),
                outcome_data.get('actual_entry_cost_bps', 0),
                outcome_data.get('actual_exit_cost_bps', 0),
                outcome_data.get('funding_cost_bps', 0),
                outcome_data.get('total_cost_bps', 0),
                outcome_data.get('predicted_p', 0.5),
                1 if outcome_data.get('actual_win', False) else 0,
                outcome_data.get('predicted_ev', 0),
                outcome_data.get('actual_ev', 0),
                outcome_data.get('notes', '')
            ))

            conn.commit()

        finally:
            conn.close()

    # ========================================
    # 查询方法
    # ========================================

    def get_signals_by_timerange(self, start_ts: int, end_ts: int, gates_passed_only: bool = False) -> List[Dict]:
        """查询时间范围内的信号"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        query = """
        SELECT signal_id, timestamp, symbol, side, confidence,
               calibrated_probability, calibrated_ev, all_gates_passed
        FROM signal_analysis
        WHERE timestamp >= ? AND timestamp <= ?
        """

        if gates_passed_only:
            query += " AND all_gates_passed = 1"

        query += " ORDER BY timestamp DESC"

        cursor.execute(query, (start_ts, end_ts))
        rows = cursor.fetchall()
        conn.close()

        return [
            {
                'signal_id': r[0], 'timestamp': r[1], 'symbol': r[2],
                'side': r[3], 'confidence': r[4], 'probability': r[5],
                'ev': r[6], 'gates_passed': bool(r[7])
            }
            for r in rows
        ]

    def get_factor_analysis(self, symbol: str, limit: int = 30) -> List[Dict]:
        """获取币种的因子分析历史"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
        SELECT timestamp, mvrv_score, prime_score, trend_score,
               fund_score, independence_score, weighted_score, side
        FROM factor_scores
        WHERE symbol = ?
        ORDER BY timestamp DESC
        LIMIT ?
        """, (symbol, limit))

        rows = cursor.fetchall()
        conn.close()

        return [
            {
                'timestamp': r[0], 'mvrv': r[1], 'prime': r[2], 't': r[3],
                'f': r[4], 'i': r[5], 'score': r[6], 'side': r[7]
            }
            for r in rows
        ]

    def get_gate_statistics(self) -> Dict[str, Any]:
        """获取闸门统计信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 总信号数
        cursor.execute("SELECT COUNT(*) FROM gate_evaluation")
        total = cursor.fetchone()[0]

        # 各闸门通过率
        stats = {'total_signals': total}

        for i in range(1, 5):
            cursor.execute(f"SELECT COUNT(*) FROM gate_evaluation WHERE gate{i}_passed = 1")
            passed = cursor.fetchone()[0]
            stats[f'gate{i}_pass_rate'] = passed / total if total > 0 else 0

        # 全部通过率
        cursor.execute("SELECT COUNT(*) FROM gate_evaluation WHERE all_passed = 1")
        all_passed = cursor.fetchone()[0]
        stats['all_gates_pass_rate'] = all_passed / total if total > 0 else 0

        # 最常拒绝的闸门
        cursor.execute("""
        SELECT first_reject_gate, COUNT(*) as cnt
        FROM gate_evaluation
        WHERE all_passed = 0
        GROUP BY first_reject_gate
        ORDER BY cnt DESC
        """)
        reject_dist = {row[0]: row[1] for row in cursor.fetchall()}
        stats['reject_distribution'] = reject_dist

        conn.close()
        return stats

    def get_modulator_impact_stats(self) -> Dict[str, Any]:
        """获取调制器影响统计"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
        SELECT
            AVG(f_p_impact_pct) as avg_f_impact,
            AVG(i_p_impact_pct) as avg_i_impact,
            AVG(total_p_change_pct) as avg_total_p_change,
            AVG(total_ev_change) as avg_total_ev_change
        FROM modulator_effects
        """)

        row = cursor.fetchone()
        conn.close()

        return {
            'avg_f_impact_pct': row[0] or 0,
            'avg_i_impact_pct': row[1] or 0,
            'avg_total_p_change_pct': row[2] or 0,
            'avg_total_ev_change': row[3] or 0
        }

    def write_scan_statistics(self, summary_data: Dict[str, Any]) -> int:
        """
        写入扫描统计数据

        Args:
            summary_data: 扫描摘要数据（来自ScanStatistics.generate_summary_data()）

        Returns:
            record_id: 记录ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # 提取数据
            scan_info = summary_data.get('scan_info', {})
            market_stats = summary_data.get('market_stats', {})
            performance = summary_data.get('performance', {})

            # 获取时间戳
            timestamp_str = summary_data.get('timestamp', '')
            try:
                dt = datetime.fromisoformat(timestamp_str)
                # 如果时间戳有时区信息，转换到UTC+8；否则当作UTC+8
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=TZ_UTC8)
                else:
                    dt = dt.astimezone(TZ_UTC8)
                timestamp = int(dt.timestamp() * 1000)
                scan_date = dt.strftime('%Y-%m-%d')
            except:
                timestamp = int(time.time() * 1000)
                scan_date = datetime.now(TZ_UTC8).strftime('%Y-%m-%d')

            cursor.execute("""
            INSERT INTO scan_statistics (
                timestamp, scan_date,
                total_symbols, signals_found, filtered,
                avg_edge, avg_confidence, new_coins_count, new_coins_pct,
                scan_duration_sec, scan_speed_coins_per_sec, cache_hit_rate, memory_mb,
                rejection_reasons, factor_distribution, close_to_threshold,
                threshold_recommendations, signals_list, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                timestamp,
                scan_date,
                scan_info.get('total_symbols', 0),
                scan_info.get('signals_found', 0),
                scan_info.get('filtered', 0),
                market_stats.get('avg_edge', 0),
                market_stats.get('avg_confidence', 0),
                market_stats.get('new_coins_count', 0),
                market_stats.get('new_coins_pct', 0),
                performance.get('total_time_sec', 0),
                performance.get('speed_coins_per_sec', 0),
                performance.get('cache_hit_rate', 0),
                performance.get('memory_mb', 0),
                json.dumps(summary_data.get('rejection_reasons', {})),
                json.dumps(summary_data.get('factor_distribution', {})),
                json.dumps(summary_data.get('close_to_threshold', [])),
                json.dumps(summary_data.get('threshold_recommendations', [])),
                json.dumps(summary_data.get('signals', [])),
                None
            ))

            record_id = cursor.lastrowid
            conn.commit()
            return record_id

        except Exception as e:
            conn.rollback()
            raise Exception(f"写入扫描统计失败: {e}")
        finally:
            conn.close()

    def get_scan_history(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        获取最近N天的扫描历史

        Args:
            days: 查询天数

        Returns:
            扫描记录列表
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 计算起始时间戳
        start_time = datetime.now(TZ_UTC8) - timedelta(days=days)
        start_ts = int(start_time.timestamp() * 1000)

        cursor.execute("""
        SELECT
            timestamp, scan_date, total_symbols, signals_found, filtered,
            avg_edge, avg_confidence, scan_duration_sec, scan_speed_coins_per_sec
        FROM scan_statistics
        WHERE timestamp >= ?
        ORDER BY timestamp DESC
        """, (start_ts,))

        rows = cursor.fetchall()
        conn.close()

        return [
            {
                'timestamp': r[0],
                'scan_date': r[1],
                'total_symbols': r[2],
                'signals_found': r[3],
                'filtered': r[4],
                'avg_edge': r[5],
                'avg_confidence': r[6],
                'scan_duration_sec': r[7],
                'scan_speed_coins_per_sec': r[8]
            }
            for r in rows
        ]

    # ========================================
    # 工具方法
    # ========================================

    def _find_first_reject_gate(self, gate_results: Dict) -> Optional[int]:
        """找到第一个拒绝的闸门"""
        for i in range(1, 5):
            gate_key = f'gate{i}_' + ['data_quality', 'fund_support', 'market_risk', 'execution_cost'][i-1]
            if not gate_results.get(gate_key, {}).get('passed', True):
                return i
        return None


# 全局单例
_analysis_db_instance = None


def get_analysis_db(db_path: str = None) -> AnalysisDB:
    """获取AnalysisDB单例"""
    global _analysis_db_instance
    if _analysis_db_instance is None:
        _analysis_db_instance = AnalysisDB(db_path)
    return _analysis_db_instance
