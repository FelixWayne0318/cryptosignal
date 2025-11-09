# CryptoSignal v7.2 - 快速参考指南

## 系统启动流程概览

```
setup.sh
├─ 检查环境 (Python3, pip3)
├─ 安装依赖 (requirements.txt)
├─ 初始化数据库
│  ├─ data/trade_history.db (TradeRecorder)
│  └─ data/analysis.db (AnalysisDB - 7表)
└─ 启动扫描器 (realtime_signal_scanner.py)
   └─ 后台运行，间隔 300 秒扫描一次
```

---

## 核心代码层级结构

### Layer 1: 入口点
- `setup.sh` - 主启动脚本
- `scripts/realtime_signal_scanner.py` - 主扫描服务

### Layer 2: 核心扫描引擎
- **OptimizedBatchScanner** (`ats_core/pipeline/batch_scan_optimized.py`)
  - WebSocket 批量扫描
  - 200 币种 / 12-15 秒
  - 0 次 API 调用

### Layer 3: 数据处理
- **Binance WebSocket** → 实时K线缓存
- **Real-time Kline Cache** (`ats_core/data/realtime_kline_cache.py`)
  - 100+ 根K线 / 币种
  - 支持 1h/4h/1d 多周期

### Layer 4: 因子计算 (7 个活跃因子)
```
1. Basis & Funding Rate      (factors_v2/basis_funding.py)
2. Independence Index        (factors_v2/independence.py)
3. Accumulation Detection    (features/accumulation_detection.py)
4. CVD (Vol Delta)           (features/cvd.py)
5. Liquidity & Price Band    (features/liquidity_priceband.py)
6. Multi-Timeframe Confirm   (features/multi_timeframe.py)
7. [由 analyze_symbol.py 整合]
```

### Layer 5: 概率计算
- **Base Probability** → **Calibrated v2** → **Adaptive Weights**
- EV (Expected Value) = P_win × avg_win% - P_loss × avg_loss%
- Confidence Score (0-100+)

### Layer 6: 四道闸门系统 (v7.2)
```
Gate 1: 概率闸门
  - P_calibrated >= threshold
  - 统计显著性检查

Gate 2: 技术闸门
  - 多周期确认
  - 成交量确认
  - 趋势对齐

Gate 3: 调制闸门
  - 因子调制
  - 价格带检查
  - 风险调制

Gate 4: EV闸门
  - EV_net > 0
  - 风险收益比
  - 止损校准

Final Check: all_gates_passed = TRUE → "Prime Signal"
```

### Layer 7: 信号过滤
- **AntiJitter 防抖动** - 避免重复信号
  - Cooldown period (可配置)
  - 按币种单独追踪

### Layer 8: 输出
- **数据库持久化**
  - `data/trade_history.db` (TradeRecorder)
  - `data/analysis.db` (AnalysisDB - 7表)
- **Telegram 通知** (v7.2 格式)
  - HTML 格式
  - F因子显示
  - Confidence 显示
  - 闸门状态

---

## 活跃模块列表 (34 个)

| 目录 | 模块 | 功能 | 状态 |
|------|------|------|------|
| pipeline/ | batch_scan_optimized.py | WebSocket 批量扫描 | ✅ ACTIVE |
| pipeline/ | analyze_symbol.py | 符号分析主函数 | ✅ ACTIVE |
| pipeline/ | analyze_symbol_v72.py | v7.2 增强分析 | ✅ ACTIVE |
| data/ | realtime_kline_cache.py | 实时K线缓存 | ✅ ACTIVE |
| data/ | trade_recorder.py | 信号快照记录 | ✅ ACTIVE |
| data/ | analysis_db.py | 完整分析存储 | ✅ ACTIVE |
| data/ | quality.py | 数据质量检查 | ✅ ACTIVE |
| execution/ | binance_futures_client.py | Binance 连接 | ✅ ACTIVE |
| execution/ | stop_loss_calculator.py | 风险管理 | ✅ ACTIVE |
| execution/ | metrics_estimator.py | 性能指标 | ✅ ACTIVE |
| factors_v2/ | basis_funding.py | 基差和资金费率 | ✅ ACTIVE |
| factors_v2/ | independence.py | 独立性指数 | ✅ ACTIVE |
| features/ | accumulation_detection.py | 积累检测 | ✅ ACTIVE |
| features/ | cvd.py | 累积成交量差 | ✅ ACTIVE |
| features/ | liquidity_priceband.py | 流动性分析 | ✅ ACTIVE |
| features/ | multi_timeframe.py | 多周期分析 | ✅ ACTIVE |
| gates/ | integrated_gates.py | 四道闸门 | ✅ ACTIVE |
| modulators/ | fi_modulators.py | 因子调制 | ✅ ACTIVE |
| modulators/ | modulator_chain.py | 调制链 | ✅ ACTIVE |
| scoring/ | probability.py | 基础概率 | ✅ ACTIVE |
| scoring/ | probability_v2.py | 校准概率 | ✅ ACTIVE |
| scoring/ | scorecard.py | 信号记分卡 | ✅ ACTIVE |
| scoring/ | adaptive_weights.py | 动态权重 | ✅ ACTIVE |
| scoring/ | scoring_utils.py | 计分工具 | ✅ ACTIVE |
| scoring/ | expected_value.py | EV 计算 | ✅ ACTIVE |
| publishing/ | anti_jitter.py | 防抖动系统 | ✅ ACTIVE |
| outputs/ | telegram_fmt.py | Telegram 格式 | ✅ ACTIVE |
| config/ | anti_jitter_config.py | 防抖配置 | ✅ ACTIVE |
| sources/ | binance.py | Binance 数据源 | ✅ ACTIVE |
| utils/ | outlier_detection.py | 异常值检测 | ✅ ACTIVE |
| (root) | logging.py | 日志系统 | ✅ ACTIVE |
| (root) | cfg.py | 中央配置 | ✅ ACTIVE |
| (root) | backoff.py | 重试机制 | ✅ ACTIVE |
| analysis/ | scan_statistics.py | 扫描统计 | ✅ ACTIVE |

---

## 废弃模块列表 (71 个 - 67.6%)

### 最高优先度删除 (完全未使用)
- `ats_core/execution/auto_trader.py` - 交易执行（未实现）
- `ats_core/execution/position_manager.py` - 仓位管理（未使用）
- `ats_core/execution/settlement_guard.py` - 结算守卫（未使用）
- `ats_core/execution/signal_executor.py` - 信号执行器（未使用）
- `ats_core/database/` (全部 3 个文件) - 旧 ORM 模型
- `ats_core/data_feeds/` (全部 2 个文件) - 新币检测（已移除）
- `ats_core/streaming/websocket_client.py` - 旧 WebSocket
- `ats_core/features/` (大部分 18 个文件) - 遗留因子定义

### 配置文件
- `config/params.json` - 已被 `factors_unified.json` 取代

---

## 关键配置文件

| 文件 | 用途 | 必需 | 状态 |
|------|------|------|------|
| `config/binance_credentials.json` | Binance API 密钥 | ✅ 必需 | - |
| `config/telegram.json` | Telegram 通知配置 | ✅ 必需 | 可禁用 |
| `config/signal_thresholds.json` | v7.2 闸门阈值 | ✅ 必需 | ACTIVE |
| `config/factors_unified.json` | 因子定义和权重 | ✅ 必需 | ACTIVE |
| `config/shadow.json` | 影子模式配置 | ❌ 可选 | ACTIVE |
| `config/params.json` | 旧参数配置 | ❌ 弃用 | DEPRECATED |

---

## 数据库结构

### trade_history.db (TradeRecorder)
```
表: signal_snapshots
├─ symbol (PRIMARY KEY)
├─ timestamp
├─ side (LONG/SHORT)
├─ confidence
├─ predicted_p (概率)
├─ predicted_ev (EV)
└─ all_gates_passed (BOOL)

表: trade_results
├─ signal_id (FK)
├─ entry_price
├─ exit_price
├─ result (WIN/LOSS)
└─ profit_pct
```

### analysis.db (AnalysisDB)
```
表1: market_data
  - K线、成交量、OI等原始数据

表2: factor_scores
  - 每个因子的计算结果

表3: signal_analysis
  - 完整的信号分析数据

表4: gate_evaluation
  - 四道闸门的评估结果

表5: modulator_effects
  - 调制器的影响

表6: signal_outcomes
  - 实际交易结果追踪

表7: scan_statistics (v7.2新增)
  - 扫描历史统计
```

---

## 性能指标

| 指标 | 数值 |
|------|------|
| 初始化时间 | 3-4 分钟 (首次 WebSocket 预热) |
| 单次扫描 | 12-15 秒 (200 币种) |
| 每币种检查 | ~50ms |
| API 调用/扫描 | 0 次 (纯 WebSocket) |
| 数据新鲜度 | 实时 (WebSocket) |

---

## 启动命令参考

```bash
# 标准启动（推荐）
bash ~/cryptosignal/setup.sh

# 手动启动扫描器
python3 ~/cryptosignal/scripts/realtime_signal_scanner.py --interval 300

# 禁用 Telegram 通知
python3 ~/cryptosignal/scripts/realtime_signal_scanner.py --no-telegram --interval 300

# 禁用数据记录
python3 ~/cryptosignal/scripts/realtime_signal_scanner.py --no-record --interval 300

# 查看数据统计
python3 ~/cryptosignal/scripts/realtime_signal_scanner.py --show-stats

# 重新启动
~/cryptosignal/auto_restart.sh

# 停止扫描器
pkill -f realtime_signal_scanner.py

# 查看日志
tail -f ~/cryptosignal_*.log

# 查看数据库
python3 ~/cryptosignal/scripts/view_database.py
```

---

## 关键源代码文件路径

### 主要文件
- `/home/user/cryptosignal/setup.sh` - 启动脚本
- `/home/user/cryptosignal/scripts/realtime_signal_scanner.py` - 主扫描服务
- `/home/user/cryptosignal/scripts/init_databases.py` - 数据库初始化
- `/home/user/cryptosignal/ats_core/pipeline/batch_scan_optimized.py` - 核心扫描引擎

### 核心分析
- `/home/user/cryptosignal/ats_core/pipeline/analyze_symbol.py` - 符号分析
- `/home/user/cryptosignal/ats_core/pipeline/analyze_symbol_v72.py` - v7.2 增强

### 因子计算
- `/home/user/cryptosignal/ats_core/factors_v2/` - 新型因子
- `/home/user/cryptosignal/ats_core/features/` - 特征提取

### 评分系统
- `/home/user/cryptosignal/ats_core/scoring/` - 概率和评分
- `/home/user/cryptosignal/ats_core/gates/integrated_gates.py` - 四道闸门

### 数据存储
- `/home/user/cryptosignal/ats_core/data/trade_recorder.py` - 信号记录
- `/home/user/cryptosignal/ats_core/data/analysis_db.py` - 分析数据库

---

## 废弃代码清理建议

### 第一阶段（高优先）
删除完全未使用的模块：
```bash
rm -rf ats_core/execution/auto_trader.py
rm -rf ats_core/execution/position_manager.py
rm -rf ats_core/execution/settlement_guard.py
rm -rf ats_core/execution/signal_executor.py
rm -rf ats_core/database/
rm -rf ats_core/data_feeds/
rm -rf ats_core/streaming/websocket_client.py
```

### 第二阶段（中优先）
归档遗留因子：
```bash
mkdir -p ats_core/deprecated/legacy_features
mv ats_core/features/{accel,momentum,trend,volume}.py deprecated/legacy_features/
```

### 第三阶段（低优先）
删除旧配置：
```bash
rm config/params.json (保留备份)
```

---

## 总结统计

| 指标 | 数值 |
|------|------|
| 总 Python 文件 (ats_core) | 105 |
| 活跃模块 | 34 (32.4%) |
| 废弃模块 | 71 (67.6%) |
| 核心依赖深度 | 4 层 |
| 配置文件数 | 6 个 |
| 活跃数据库表 | 9 个 |
| 主要入口点 | 3 个 |

---

## 参考文档

- 详细分析: `DEPENDENCY_ANALYSIS.txt`
- 架构图: `DEPENDENCY_DIAGRAM.txt`
- 系统检查报告: `SYSTEM_CHECK_REPORT.md`
- 重组总结: `REORGANIZATION_SUMMARY.md`
- 规范索引: `standards/00_INDEX.md`

---

*生成时间: 2025-11-09*
*分析深度: Medium*

