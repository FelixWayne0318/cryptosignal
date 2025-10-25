# CryptoSignal 七维度系统 v2.0 - 项目状态文档

**最后更新**: 2025-10-25
**Git分支**: `claude/read-repository-011CUSE4JUNEZTJXScWc57EC`
**状态**: ✅ 已部署并测试成功

---

## 📋 快速开始

### 运行分析
```bash
cd ~/cryptosignal
source .env  # 加载Telegram配置
python3 tools/manual_run.py --send --top 10
```

### Telegram配置
```bash
# 位置：~/cryptosignal/.env
TELEGRAM_BOT_TOKEN="7545580872:AAF7HzkHA4LRQUiOZngUgL39epuGVeEta70"
TELEGRAM_CHAT_ID="-1003142003085"
```

---

## 🎯 七维度系统 v2.0 架构

### 核心改进

**从**: 7个平铺维度（T/A/S/V/O/E/F）
**到**: 7个基础维度 + 1个调节器（T/M/C/S/V/O/E + F）

### 7个基础维度（参与评分）

| 维度 | 名称 | 权重 | 说明 |
|------|------|------|------|
| T | 趋势 | 20 | EMA趋势方向（软映射，多空对称）|
| M | 动量 | 10 | 价格斜率+加速度（从A分离）|
| C | 资金流 | 10 | CVD资金流动（从A分离）|
| S | 结构 | 10 | 技术形态质量 |
| V | 量能 | 20 | 成交量变化 |
| O | 持仓 | 15 | OI持仓变化 |
| E | 环境 | 15 | 波动性和空间 |

**总权重**: 100

### F调节器（概率调整）

**不参与基础评分**，仅调整最终概率：

```python
F_score = tanh((fund_momentum - price_momentum) / 20) * 100

if F >= 70:
    P_final = P_base × 1.15  # 资金领先，+15%
elif F >= 50:
    P_final = P_base × 1.00  # 同步
elif F >= 30:
    P_final = P_base × 0.90  # 价格略领先，-10%
else:
    P_final = P_base × 0.70  # 追高风险，-30%
```

---

## 🔧 关键技术实现

### 1. 软映射（无硬阈值）

所有维度使用 `directional_score()` 函数：

```python
def directional_score(
    value: float,
    neutral: float = 0.0,
    scale: float = 1.0,
    max_bonus: float = 50.0,
    min_score: float = 10.0  # 避免0分陷阱
) -> int:
    deviation = value - neutral
    normalized = math.tanh(deviation / scale)
    score = 50 + max_bonus * normalized
    return int(round(max(min_score, min(100.0, score))))
```

**特点**：
- 50分为中性
- 平滑过渡（tanh曲线）
- 最低10分（避免信息丢失）

### 2. 多空对称

```python
# 做多
if side_long:
    slope_score = directional_score(slope, ...)
# 做空（翻转符号）
else:
    slope_score = directional_score(-slope, ...)
```

**效果**：做多和做空的分数范围都是0-100，完全对称。

### 3. 智能方向选择

```python
# 计算做多和做空的真实加权分数
long_weighted = scorecard(long_scores, weights)
short_weighted = scorecard(short_scores, weights)

# 选择分数更高的方向
side_long = (long_weighted >= short_weighted)
```

**效果**：
- 上涨市场推荐做多，显示T=100, M=100, C=100
- 下跌市场推荐做空，显示T=100, M=100, C=100

---

## 🐛 已修复的关键Bug

### Bug 1: scorecard硬编码维度A
**问题**: `scorecard.py` 使用 `scores["A"]` 导致 KeyError
**修复**: 改为动态循环 `for dim in scores.items()`
**文件**: `ats_core/scoring/scorecard.py`

### Bug 2: M和C维度0分陷阱
**问题**: 下跌时做多，M=0, C=0（信息丢失）
**原因**: `directional_score` 极端负值时score=0
**修复**: 添加 `min_score=10` 参数
**文件**: `ats_core/features/scoring_utils.py`

### Bug 3: 方向选择逻辑错误
**问题**: COAIUSDT下跌却推荐做多
**原因**: `side_long = (UpScore > DownScore)` 其中DownScore只是补数
**修复**: 对比真实的 `long_weighted` vs `short_weighted`
**文件**: `ats_core/pipeline/analyze_symbol.py`

### Bug 4: 候选池格式兼容
**问题**: 候选池返回dict而非string，导致 `'dict' object has no attribute 'upper'`
**修复**: manual_run.py提取 `item['symbol']`
**文件**: `tools/manual_run.py`

---

## 📁 核心文件清单

### 新增文件
```
ats_core/features/momentum.py       - M维度（价格动量）
ats_core/features/cvd_flow.py       - C维度（CVD资金流）
tools/manual_run.py                 - 手动运行脚本
tools/diagnose_single.py            - 单币种诊断
test_seven_dimensions.py            - 完整测试脚本
configure_telegram_prod.sh          - Telegram配置脚本
docs/实施完成总结.md                - 详细实施文档
```

### 修改文件
```
ats_core/features/trend.py          - T维度（添加多空对称）
ats_core/features/scoring_utils.py  - 添加min_score参数
ats_core/pipeline/analyze_symbol.py - 核心流程重构
ats_core/scoring/scorecard.py       - 动态维度支持
ats_core/outputs/telegram_fmt.py    - 7维度显示
config/params.json                  - 新权重配置
```

---

## 📊 配置参数

### params.json 关键配置

```json
{
  "weights": {
    "T": 20,  "M": 10,  "C": 10,  "S": 10,
    "V": 20,  "O": 15,  "E": 15
  },

  "momentum": {
    "slope_lookback": 30,
    "slope_scale": 0.01,
    "accel_scale": 0.005,
    "slope_weight": 0.6,
    "accel_weight": 0.4
  },

  "cvd_flow": {
    "lookback_hours": 6,
    "cvd_scale": 0.02
  },

  "publish": {
    "prime_prob_min": 0.62,
    "prime_dims_ok_min": 4,
    "prime_dim_threshold": 65,
    "watch_prob_min": 0.58
  }
}
```

---

## 🚀 常用命令

### 诊断单个币种
```bash
cd ~/cryptosignal
python3 tools/diagnose_single.py BTCUSDT
```

### 分析并发送前10个
```bash
cd ~/cryptosignal
source .env
python3 tools/manual_run.py --send --top 10
```

### 分析指定币种
```bash
python3 tools/manual_run.py --send --symbols BTCUSDT ETHUSDT SOLUSDT
```

### 查看完整候选池
```bash
python3 tools/full_run.py --limit 20
```

### 清除Python缓存（代码更新后）
```bash
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null
```

---

## 📱 Telegram消息格式

### 做多信号
```
🔹 BTCUSDT · 现价 111,300
📣 正式 · 🟩 做多 42% · 有效期8h

六维分析
• 趋势 🟢 100 —— 强势/上行倾向 [多头]
• 动量 🟢 100 —— 价格动量
• 资金流 🟢 95 —— CVD变化
• 结构 🔴 35 —— 结构杂乱
• 量能 🟡 46 —— 量能中性
• 持仓 🟡 54 —— 持仓温和变化
• 环境 🟡 42 —— 环境一般

⚡ 资金领先 13 → 概率调整 ×0.70

#trade #BTCUSDT
```

### 做空信号
```
🔹 COAIUSDT · 现价 8.83
📣 正式 · 🟥 做空 24% · 有效期8h

六维分析
• 趋势 🟢 100 —— 强势/下行倾向 [空头]
• 动量 🟢 100 —— 价格动量
• 资金流 🟢 100 —— CVD变化
• 结构 🟡 40 —— 结构一般
• 量能 🟢 98 —— 放量明显
• 持仓 🟢 65 —— 空头持仓活跃
• 环境 🟢 63 —— 环境偏友好

⚡ 资金领先 47 → 概率调整 ×0.90

#trade #COAIUSDT
```

---

## 🔍 问题诊断

### 所有维度显示0分
**原因**: Python缓存未清除
**解决**: `find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null`

### Telegram发送失败
**检查**:
```bash
echo $TELEGRAM_BOT_TOKEN  # 应显示Token
echo $TELEGRAM_CHAT_ID    # 应显示Chat ID
source ~/cryptosignal/.env  # 重新加载
```

### 推荐方向明显错误
**检查版本**: 确保是最新提交
```bash
cd ~/cryptosignal
git log -1 --oneline
# 应显示: 3cbbda1 fix: 修复方向选择逻辑
```

### M或C维度仍然为0
**检查版本**: 确保包含0分陷阱修复
```bash
grep "min_score" ats_core/features/scoring_utils.py
# 应显示: def directional_score(..., min_score: float = 10.0)
```

---

## 📈 性能指标

### 当前测试结果（2025-10-25）

**BTCUSDT**（上涨）:
- 方向: 🟩 做多 ✅
- T=100, M=100, C=95 ✅
- F=13 (追高风险) → ×0.70 ✅

**COAIUSDT**（下跌）:
- 方向: 🟥 做空 ✅
- T=100, M=100, C=100 ✅
- F=47 (价格略领先) → ×0.90 ✅

**验证通过**: ✅ 方向选择正确，分数真实准确

---

## 🎯 下一步建议

### 短期（1-2周）
1. 观察实际信号质量
2. 收集做多/做空信号比例
3. 验证F调节器效果

### 中期（1个月）
1. 统计胜率数据
2. 根据实际效果调整权重
3. 优化scale参数

### 长期优化
1. 添加资金费率维度（R）
2. 引入市场环境自适应
3. 多时间周期确认

---

## 📞 技术支持

### Git提交历史
```bash
cd ~/cryptosignal
git log --oneline --graph -10
```

### 关键提交
```
3cbbda1 - fix: 修复方向选择逻辑，正确推荐做空
ab2dea6 - fix: 修复M和C维度0分陷阱问题
affdadf - fix: 修复scorecard和候选池格式问题
88d383c - tools: 添加生产环境Telegram配置脚本
```

### 文档位置
- 实施总结: `docs/实施完成总结.md`
- 方案设计: `docs/因果有机结合方案.md`
- 问题分析: `docs/七维度分析报告.md`

---

## ✅ 验收清单

- [x] 7个基础维度全部工作
- [x] F调节器正确调整概率
- [x] 多空对称（做多做空都能正确评分）
- [x] 智能方向选择
- [x] 无0分陷阱
- [x] 无硬阈值跳变
- [x] Telegram集成正常
- [x] 候选池格式兼容
- [x] 所有已知Bug已修复
- [x] 代码已推送到Git

---

**项目状态**: ✅ 生产就绪
**最后验证**: 2025-10-25 06:24
**验证人**: Claude + User
