# 扫描报告目录

本目录存储全市场扫描的分析报告，用于自动分析和历史追踪。

## 📁 目录结构

```
reports/
├── latest/                    # 最新扫描结果
│   ├── scan_summary.json      # 摘要数据（机器可读）
│   ├── scan_summary.md        # 摘要报告（人类可读）
│   ├── scan_detail.json       # 详细数据（所有404币种）
│   └── scan_progress.json     # 扫描进度（实时更新）
├── history/                   # 历史记录（最近30次）
│   ├── 2025-11-07_01-02-52_scan.json
│   ├── 2025-11-07_02-05-30_scan.json
│   └── ...
└── trends.json                # 趋势数据（历史对比）
```

## 📊 数据说明

### scan_summary.json（摘要）
```json
{
  "timestamp": "2025-11-07T01:02:52",
  "scan_info": {
    "total_symbols": 404,
    "signals_found": 0,
    "filtered": 404
  },
  "signals": [],
  "rejection_reasons": {
    "Edge不足": 341,
    "置信度不足": 327
  },
  "close_to_threshold": [
    {
      "symbol": "KNCUSDT",
      "metric": "Edge",
      "gap": 0.01,
      "current": 0.54,
      "threshold": 0.55
    }
  ],
  "market_stats": {
    "avg_edge": 0.27,
    "avg_confidence": 29.0,
    "new_coins_count": 15,
    "new_coins_pct": 3.7
  },
  "factor_distribution": {
    "T": {"min": -100, "p25": -41, "median": 63, "p75": 100, "max": 100},
    "Edge": {"min": -0.39, "p25": 0.0, "median": 0.27, "p75": 0.41, "max": 0.73}
  },
  "threshold_recommendations": [
    "Edge阈值可能偏高：15个币种非常接近但未通过"
  ],
  "performance": {
    "total_time_sec": 98.6,
    "speed_coins_per_sec": 4.1,
    "api_calls": 0,
    "cache_hit_rate": "98.5%",
    "memory_mb": 234.5
  }
}
```

### scan_detail.json（详细）
包含所有404个币种的完整数据：
- 10因子分数（T/M/C/V/O/B/F/L/S/I）
- 综合指标（confidence/prime_strength/edge/gate_multiplier）
- 拒绝原因
- 数据质量信息

### trends.json（趋势）
```json
{
  "signals_count": [0, 0, 3, 5, 2],
  "avg_edge": [0.27, 0.28, 0.30, 0.32, 0.29],
  "avg_confidence": [29, 31, 35, 38, 33],
  "scan_times": ["2025-11-07T00:00:00", ...],
  "rejection_reasons_history": [...]
}
```

## 🔄 使用方式

### Claude直接读取分析
```
我可以直接读取 reports/latest/scan_summary.json 查看最新扫描结果
无需您手动复制粘贴！
```

### 查看历史趋势
```
git log reports/trends.json  # 查看趋势变化
git diff HEAD~1 reports/latest/scan_summary.json  # 对比上次扫描
```

### 自动提交（可选）
```bash
# 每次扫描后自动提交
cd /home/user/cryptosignal
git add reports/
git commit -m "scan: $(date '+%Y-%m-%d %H:%M:%S')"
git push
```

## 📈 分析示例

Claude会分析：
1. ✅ 信号数量是否合理
2. ✅ 哪些阈值需要调整（基于接近阈值的币种）
3. ✅ 市场整体状态（10因子分布）
4. ✅ 趋势变化（今天vs昨天）
5. ✅ 性能指标（扫描速度、缓存命中率）

## 🚀 优势

- ✅ **自动化** - 扫描完成自动写入
- ✅ **方便** - Claude直接读取，无需复制粘贴
- ✅ **历史追踪** - Git历史记录可追溯
- ✅ **趋势分析** - 自动对比历史数据
- ✅ **多格式** - JSON（机器）+ Markdown（人类）
