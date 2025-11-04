# 🔍 系统诊断工具使用说明

## 📥 更新代码

```bash
cd ~/cryptosignal
git checkout claude/audit-system-compliance-011CUkshDA3WNmJWFjbAEEn8
git pull origin claude/audit-system-compliance-011CUkshDA3WNmJWFjbAEEn8
```

---

## 🚀 运行方式

### 方式 1: Telegram通知版 ⭐ 推荐

**自动将诊断报告发送到Telegram群，无需手动复制粘贴**

```bash
cd ~/cryptosignal
./run_diagnostic_telegram.sh
```

**特点:**
- ✅ 实时显示诊断过程
- ✅ 自动发送摘要到Telegram
- ✅ 上传完整报告文件
- ✅ 无需手动复制粘贴
- ⏱️ 1-3分钟完成

**Telegram会收到:**
1. 📋 **配置检查摘要** - 所有关键修复的验证结果
2. 📈 **统计汇总** - 信号分布、概率分布、EV分布
3. 📄 **完整报告文件** - 可下载查看详细内容

---

### 方式 2: 本地版

**只在本地生成报告，需要手动查看和复制**

```bash
cd ~/cryptosignal
./run_diagnostic.sh
```

查看报告：
```bash
cat diagnostic_report_*.txt
```

---

## 📊 诊断内容

### 1️⃣ 版本和配置检查
- Git分支和commit验证
- Anti-Jitter阈值检查（0.55/0.52）
- EV字段读取检查（大写'EV'）
- EV计算公式验证（abs(edge)）
- p_min adjustment限制检查（0.02）

### 2️⃣ 实际扫描测试
- 扫描10个高流动性币种
- 获取真实市场数据
- 生成实际信号

### 3️⃣ 信号详细分析
对每个信号检查：
- 概率值（P）和期望值（EV）
- Prime状态和软约束过滤
- Anti-Jitter测试结果
- 三个发布条件验证
- 失败原因分析

### 4️⃣ 统计汇总
- 信号级别分布（PRIME/WATCH/IGNORE）
- 失败原因统计
- 概率分布（最小/最大/平均/中位数）
- EV分布统计

---

## 📱 Telegram消息示例

### 摘要消息
```
🔍 CryptoSignal 系统诊断报告

⏰ 时间: 2025-11-04 12:00:00
🌿 分支: claude/audit-system-compliance-011CUkshDA3WNmJWFjbAEEn8

📋 配置检查结果
✅ prime_entry_threshold = 0.55 (正确)
✅ prime_maintain_threshold = 0.52 (正确)
✅ EV字段读取使用大写 'EV' (正确)
✅ EV计算使用 abs(edge) (正确)
✅ p_min adjustment 限制为 0.02 (正确)

📈 统计汇总
信号级别分布:
   PRIME 级别:  3 / 10 (30.0%)
   WATCH 级别:  5 / 10 (50.0%)

概率分布:
   平均值: 0.5445 (54.45%)
   中位数: 0.5520 (55.20%)

EV分布:
   平均值: 0.0067
   EV>0数量: 7 / 10 (70%)

📄 完整报告已上传（见附件）
```

### 附件
- 📄 `diagnostic_report_20251104_120000.txt` - 完整诊断报告

---

## 🎯 预期结果

### ✅ 如果修复生效

**配置检查应全部通过:**
```
✅ prime_entry_threshold = 0.55 (正确)
✅ prime_maintain_threshold = 0.52 (正确)
✅ EV字段读取使用大写 'EV' (正确)
✅ EV计算使用 abs(edge) (正确)
✅ p_min adjustment 限制为 0.02 (正确)
```

**应该有PRIME级别信号:**
```
PRIME 级别:  2-5 / 10 (20-50%)  ← 不再是0
```

**概率应在合理范围:**
```
平均值: 0.50-0.60 (50-60%)
```

**大部分EV应为正:**
```
EV>0数量: 6-8 / 10 (60-80%)
```

---

### ❌ 如果问题仍存在

**场景1: 配置未更新**
```
❌ prime_entry_threshold = 0.65 (旧版)
```
→ 代码未正确更新，需要重新拉取

**场景2: 所有信号都是WATCH**
```
PRIME 级别:  0 / 10 (0%)
WATCH 级别:  10 / 10 (100%)
```
→ 概率值低于阈值，需要进一步调整

**场景3: 所有EV为负**
```
EV>0数量: 0 / 10 (0%)
```
→ EV计算或cost参数有问题

---

## 🔧 故障排除

### 问题1: Telegram未收到消息

检查配置:
```bash
cat config/telegram.json
```

确认:
- `enabled`: true
- `bot_token`: 正确的token
- `chat_id`: 正确的群组ID

### 问题2: 诊断脚本报错

检查依赖:
```bash
pip3 install requests
```

### 问题3: 扫描失败

查看错误信息:
```bash
cat diagnostic_report_*.txt | grep "失败"
```

---

## 📞 需要帮助？

运行诊断后，如果：
- ✅ 收到Telegram消息 → 直接在群里讨论结果
- ❌ 未收到消息 → 运行本地版并手动发送报告

---

## 🎉 优势对比

| 特性 | Telegram版 | 本地版 |
|-----|-----------|--------|
| 操作便捷性 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| 结果展示 | ⭐⭐⭐⭐⭐ 自动推送 | ⭐⭐⭐ 手动查看 |
| 协作效率 | ⭐⭐⭐⭐⭐ 即时分享 | ⭐⭐ 需复制粘贴 |
| 数据保存 | ⭐⭐⭐⭐⭐ 群组+本地 | ⭐⭐⭐⭐ 仅本地 |
| 运行速度 | ⭐⭐⭐⭐ 略慢（上传） | ⭐⭐⭐⭐⭐ 最快 |

**推荐使用 Telegram版！** 🎯
