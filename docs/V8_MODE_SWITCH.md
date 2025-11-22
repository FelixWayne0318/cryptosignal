# V8 真模式切换说明

**版本**: v8.0.1
**日期**: 2025-11-22

---

## 概述

系统从 v7.4.2 批量轮询模式切换到真正的 V8 实时流模式。

### 变更对比

| 项目 | V7.4.2模式 | V8真模式 |
|------|-----------|----------|
| 数据源 | HTTP批量轮询 | Cryptofeed WebSocket流 |
| 因子计算 | 批量扫描后计算 | 实时流式计算 |
| 币种加载 | 直接Binance API | CCXT统一API |
| 数据存储 | SQLite数据库 | Cryptostore持久化 |
| 启动脚本 | `realtime_signal_scanner.py` | `start_realtime_stream.py` |

---

## 配置说明

### 新增配置项 (`config/signal_thresholds.json`)

```json
{
  "v8_integration": {
    "scanner": {
      "enabled": true,
      "mode": "full",
      "dynamic_symbols": true,
      "min_volume_usdt": 3000000,
      "max_symbols": null,
      "scan_interval_seconds": 300
    }
  }
}
```

### 配置参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `mode` | `"full"` | 运行模式：`full`=完整V8管道，`simple`=仅数据流 |
| `dynamic_symbols` | `true` | 是否从CCXT动态加载全市场币种 |
| `min_volume_usdt` | `3000000` | 最小24h成交额（3M USDT） |
| `max_symbols` | `null` | 最大币种数（null=不限制） |
| `scan_interval_seconds` | `300` | 扫描间隔（秒） |

---

## 使用方法

### 启动系统

```bash
# 标准启动（真V8模式）
./setup.sh

# 自定义参数
V8_MODE=simple SCAN_INTERVAL=600 ./setup.sh

# 禁用全市场扫描（仅BTC/ETH）
ALL_SYMBOLS=false ./setup.sh
```

### 手动运行

```bash
# 全市场真V8模式
python scripts/start_realtime_stream.py --mode full --all-symbols

# 指定币种
python scripts/start_realtime_stream.py --mode full --symbols BTC,ETH,SOL

# 仅数据流（调试用）
python scripts/start_realtime_stream.py --mode simple --symbols BTC
```

### 管理命令

```bash
# 查看状态
ps aux | grep start_realtime_stream

# 停止程序
pkill -f start_realtime_stream.py

# 查看日志
tail -f ~/cryptosignal_*.log
```

---

## V8六层架构

```
Layer1: Cryptofeed      → WebSocket实时数据流
Layer2: CryptoSignal    → 实时因子计算（CVD/OBI/LDI/VWAP）
Layer3: CCXT            → 动态加载全市场币种
Layer4: Cryptostore     → 数据持久化
Layer5: Decision        → 信号生成
Layer6: Execution       → 订单执行（dry_run模式）
```

---

## 文件变更

### 修改的文件

1. **config/signal_thresholds.json**
   - 新增 `v8_integration.scanner` 配置节

2. **scripts/start_realtime_stream.py**
   - 新增 `--all-symbols` 参数
   - 新增 `--interval` 参数
   - 新增 `load_dynamic_symbols()` 函数

3. **setup.sh**
   - 切换启动脚本到 `start_realtime_stream.py`
   - 更新环境变量和帮助信息

---

## 回滚方法

如需回滚到V7.4.2模式：

```bash
# 修改setup.sh中的启动命令
SCANNER_SCRIPT="scripts/realtime_signal_scanner.py"
nohup python3 "$SCANNER_SCRIPT" --interval 300 > "$LOG_FILE" 2>&1 &
```

---

## 注意事项

1. **依赖要求**: 需要安装 `ccxt`、`cryptofeed` 等V8依赖
2. **网络要求**: WebSocket连接需要稳定网络
3. **资源消耗**: 全市场扫描会消耗更多内存和带宽
4. **dry_run模式**: 默认不执行真实交易，需手动开启

---

**相关文档**:
- `standards/SYSTEM_ENHANCEMENT_STANDARD.md`
- `ats_core/pipeline/v8_realtime_pipeline.py`
- `cs_ext/data/cryptofeed_stream.py`
