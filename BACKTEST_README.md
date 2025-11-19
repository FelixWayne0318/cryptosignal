# CryptoSignal v7.4.2 回测运行指南

## 📋 快速开始

### 方式1: 使用一键脚本（推荐）⭐

```bash
# 1. 设置Binance API密钥
export BINANCE_API_KEY="your_api_key_here"
export BINANCE_API_SECRET="your_api_secret_here"

# 2. 运行回测脚本
cd ~/cryptosignal
./RUN_BACKTEST.sh
```

---

### 方式2: 手动运行回测

```bash
# 基础回测（单币种）
python3 scripts/backtest_four_step.py \
    --symbols ETHUSDT \
    --start 2024-08-01 \
    --end 2024-11-01 \
    --output reports/backtest_eth_3m.json

# 多币种回测
python3 scripts/backtest_four_step.py \
    --symbols ETHUSDT,BTCUSDT,BNBUSDT \
    --start 2024-08-01 \
    --end 2024-11-01 \
    --output reports/backtest_multi_3m.json \
    --report-format markdown \
    --report-output reports/backtest_multi_3m.md

# 短期回测（快速测试）
python3 scripts/backtest_four_step.py \
    --symbols ETHUSDT \
    --start 2024-10-01 \
    --end 2024-11-01 \
    --output reports/backtest_eth_1m.json
```

---

## 🔑 如何获取Binance API密钥

### 步骤1: 登录Binance

访问：https://www.binance.com/zh-CN/my/settings/api-management

### 步骤2: 创建API Key

1. 点击"创建API"
2. 标签：CryptoSignal Backtest
3. **权限设置**（重要）：
   - ✅ 只勾选"Enable Reading"（启用读取）
   - ❌ 不要勾选交易、提现等权限
4. 完成验证（邮箱/手机/谷歌验证器）

### 步骤3: 保存密钥

```bash
# 临时设置（当前会话有效）
export BINANCE_API_KEY="your_key_here"
export BINANCE_API_SECRET="your_secret_here"

# 永久设置（写入配置文件）
echo 'export BINANCE_API_KEY="your_key_here"' >> ~/.bashrc
echo 'export BINANCE_API_SECRET="your_secret_here"' >> ~/.bashrc
source ~/.bashrc
```

---

## 📊 回测参数说明

### 必需参数

| 参数 | 说明 | 示例 |
|------|------|------|
| `--symbols` | 交易对（逗号分隔） | `ETHUSDT,BTCUSDT` |
| `--start` | 开始日期 | `2024-08-01` |
| `--end` | 结束日期 | `2024-11-01` |
| `--output` | 输出JSON文件路径 | `reports/backtest.json` |

### 可选参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--interval` | K线周期 | `1h` |
| `--report-format` | 报告格式 | `json` |
| `--report-output` | 报告输出路径 | 无（打印到终端） |
| `--verbose` | 详细日志 | False |

---

## 📈 推荐的测试场景

### 场景1: 快速验证（5-10分钟）

```bash
# 测试1个月，1个币种
python3 scripts/backtest_four_step.py \
    --symbols ETHUSDT \
    --start 2024-10-01 \
    --end 2024-11-01 \
    --output reports/test_1m.json
```

### 场景2: 标准回测（15-30分钟）

```bash
# 测试3个月，3个主流币
python3 scripts/backtest_four_step.py \
    --symbols ETHUSDT,BTCUSDT,BNBUSDT \
    --start 2024-08-01 \
    --end 2024-11-01 \
    --output reports/standard_3m.json \
    --report-format markdown \
    --report-output reports/standard_3m.md
```

### 场景3: 全面回测（30-60分钟）

```bash
# 测试6个月，5个币种
python3 scripts/backtest_four_step.py \
    --symbols ETHUSDT,BTCUSDT,BNBUSDT,SOLUSDT,AVAXUSDT \
    --start 2024-05-01 \
    --end 2024-11-01 \
    --output reports/full_6m.json \
    --report-format markdown \
    --report-output reports/full_6m.md \
    --verbose
```

---

## 📤 反馈结果给开发者

运行完成后，请提供以下信息：

### 必需反馈

1. **Markdown报告**（最重要）
```bash
cat reports/backtest_*.md
```

2. **运行日志**（如果失败）
```bash
# 运行时的错误信息截图
```

### 可选反馈

3. **JSON结果**（用于深度分析）
```bash
cat reports/backtest_*.json
```

4. **系统信息**
```bash
python3 --version
pip list | grep -E "numpy|pandas|xgboost"
```

---

## 🔧 常见问题

### Q0: 回测产生0个信号 ✅ 已修复

**症状**: 运行回测后显示"Total Signals: 0"，日志中显示"Final strength insufficient: X.X < 20.0"

**原因**: v7.4.2早期版本中`min_final_strength`阈值设置过高（20.0），导致所有信号被Step1拒绝

**修复**: 已调整阈值至5.0（config/params.json line 390）

**验证**:
```bash
# 运行验证脚本
python3 scripts/validate_p0_fix.py

# 或检查配置
python3 -c "from ats_core.cfg import CFG; print(CFG.params['four_step_system']['step1_direction']['min_final_strength'])"
# 应输出: 5.0
```

---

### Q1: 提示"403 Forbidden"

**原因**: API密钥未设置或无效

**解决**:
```bash
# 检查环境变量
echo $BINANCE_API_KEY
echo $BINANCE_API_SECRET

# 如果为空，重新设置
export BINANCE_API_KEY="your_key"
export BINANCE_API_SECRET="your_secret"
```

### Q2: 提示"ModuleNotFoundError"

**原因**: 缺少依赖包

**解决**:
```bash
pip install numpy pandas
```

### Q3: 回测很慢

**原因**: 数据量大或网络慢

**解决**:
- 先测试1个月数据
- 使用缓存（会自动启用）
- 减少币种数量

### Q4: 内存不足

**原因**: 回测数据量过大

**解决**:
- 减少时间范围
- 减少币种数量
- 分批运行

---

## 📊 预期输出示例

### Markdown报告示例

```markdown
# Backtest Report - CryptoSignal v7.4.2

## Summary
- Symbols: ETHUSDT, BTCUSDT, BNBUSDT
- Time Range: 2024-08-01 ~ 2024-11-01
- Total Signals: 45
- Win Rate: 62.2%
- Average RR: 2.3
- Sharpe Ratio: 1.45

## Signal Metrics
- Long Signals: 25 (55.6%)
- Short Signals: 20 (44.4%)
- Average Holding Time: 18.5 hours
- Max Consecutive Wins: 5
- Max Consecutive Losses: 3

## Performance by Symbol
### ETHUSDT
- Signals: 18
- Win Rate: 66.7%
- Total PnL: +12.5%

### BTCUSDT
- Signals: 15
- Win Rate: 60.0%
- Total PnL: +8.3%

...
```

---

## 💡 提示

1. **首次运行**: 建议先测试1个月，确认能正常运行
2. **API限制**: Binance API有速率限制，不要同时运行多个回测
3. **缓存使用**: 第二次运行相同时间段会更快（使用缓存）
4. **报告格式**: Markdown格式更易读，JSON格式方便程序分析

---

## 📞 需要帮助？

如果遇到问题，请提供：
1. 完整的错误信息
2. 运行的命令
3. Python版本和系统信息

**准备好后，运行脚本并把结果发给我！** 🚀
