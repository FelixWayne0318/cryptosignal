# Telegram通知配置说明

## 配置文件

配置文件位置：`config/telegram.json`

## 配置选项

```json
{
  "enabled": true,                    // 是否启用Telegram通知（总开关）
  "bot_token": "YOUR_BOT_TOKEN",      // Telegram Bot Token
  "chat_id": "YOUR_CHAT_ID",          // Telegram群组/频道ID

  "send_scan_summary": false          // 是否发送扫描摘要消息
}
```

## 详细说明

### `enabled` (boolean)
- **默认值**: `true`
- **说明**: Telegram通知的总开关
- **效果**:
  - `true`: 启用Telegram通知
  - `false`: 完全禁用所有Telegram通知

### `send_scan_summary` (boolean)
- **默认值**: `false`
- **说明**: 控制是否发送扫描摘要消息
- **效果**:
  - `false`: **仅发送交易信号**，不发送扫描完成统计摘要
  - `true`: 同时发送交易信号和扫描摘要

## 消息类型

### 1. 交易信号（始终发送）
当系统发现高质量交易机会时发送，包含：
- 币种信息
- 技术指标
- 入场/止损/止盈建议
- 风险评估

示例：
```
🚀 LONG 信号 - BTCUSDT

📊 技术分析:
  • 置信度: 67.5
  • 概率: 0.582
  • 期望值: 0.0234

💰 建议仓位:
  • 入场: $65,432
  • 止损: $64,234 (-1.8%)
  • 止盈: $67,890 (+3.6%)
```

### 2. 扫描摘要（可选）
每次扫描完成后发送的统计信息，包含：
- 扫描时间
- 扫描币种数量
- 发现信号数量
- 所有Prime信号列表

示例：
```
📊 扫描完成

🕐 时间: 2025-11-10 10:44:01
📈 扫描: 383 个币种
✅ 信号: 173 个

🎯 Prime信号:
  • SOLUSDT: Edge=0.28, Conf=28, Prime=57
  • ZROUSDT: Edge=0.27, Conf=27, Prime=61
  ... 还有171个信号

📝 完整报告: reports/latest/scan_summary.json
```

## 推荐配置

### 场景1：轻量级通知（推荐）
只接收高质量交易信号，避免信息过载：

```json
{
  "enabled": true,
  "send_scan_summary": false    // ✅ 推荐
}
```

**优点**：
- ✅ 避免每5分钟一次的摘要通知
- ✅ 聚焦真正重要的交易机会
- ✅ 减少决策疲劳

### 场景2：完整监控
接收所有信息，包括扫描统计：

```json
{
  "enabled": true,
  "send_scan_summary": true
}
```

**适用于**：
- 需要监控系统运行状态
- 需要了解市场整体情况
- 调试和优化系统

### 场景3：完全禁用
不接收任何Telegram通知：

```json
{
  "enabled": false
}
```

## 修改配置后重启

修改配置文件后，需要重启系统：

```bash
cd ~/cryptosignal
bash restart_system.sh
```

或手动重启：

```bash
pkill -f "python.*cryptosignal"
./setup.sh
```

## 验证配置

查看系统日志，确认配置生效：

```bash
# 查看最新日志
tail -f ~/cryptosignal_*.log

# 如果配置正确，应看到：
# ℹ️  扫描摘要已禁用（send_scan_summary=false），仅发送交易信号
```

## 技术实现

### 代码位置
- **配置读取**: `ats_core/pipeline/batch_scan_optimized.py:838`
- **判断逻辑**: `batch_scan_optimized.py:840`

### 实现原理
```python
# 读取配置
send_scan_summary = telegram_config.get('send_scan_summary', False)

# 判断是否发送
if enabled and bot_token and chat_id and send_scan_summary:
    # 发送扫描摘要
    stats.send_to_telegram(message, bot_token, chat_id)
else:
    log("ℹ️  扫描摘要已禁用（send_scan_summary=false），仅发送交易信号")
```

### 向后兼容
- 如果配置文件中没有 `send_scan_summary` 字段，默认为 `false`
- 旧配置文件无需修改，自动禁用扫描摘要

## 常见问题

### Q1: 为什么没有收到任何消息？
**A**: 检查以下配置：
1. `enabled` 是否为 `true`
2. `bot_token` 和 `chat_id` 是否正确
3. Bot是否已加入群组/频道
4. 群组/频道是否允许Bot发送消息

### Q2: 只想接收某些币种的信号怎么办？
**A**: 这需要修改信号过滤逻辑，不在配置范围内。建议：
- 在Telegram客户端设置关键词过滤
- 或修改 `realtime_signal_scanner.py` 的过滤条件

### Q3: 如何查看历史扫描记录？
**A**: 即使禁用Telegram摘要，系统仍会保存完整报告：
- JSON格式：`reports/latest/scan_summary.json`
- Markdown格式：`reports/latest/scan_summary.md`
- 历史记录：`reports/history/`

---

**版本**: v7.2
**更新时间**: 2025-11-10
**相关文件**:
- `config/telegram.json` - 配置文件
- `ats_core/pipeline/batch_scan_optimized.py` - 实现代码
- `scripts/realtime_signal_scanner.py` - 信号发送逻辑
