# 🔍 诊断脚本使用指南

## 问题描述

系统扫描200个币种但产生0个信号。已修复多个bug，但问题仍然存在，需要全面诊断。

---

## 📥 第一步：更新代码

```bash
cd ~/cryptosignal

# 拉取最新代码（包含诊断脚本）
git checkout claude/audit-system-compliance-011CUkshDA3WNmJWFjbAEEn8
git pull origin claude/audit-system-compliance-011CUkshDA3WNmJWFjbAEEn8
```

---

## 🚀 第二步：运行诊断

### 方法A：一键运行（推荐）

```bash
cd ~/cryptosignal
./run_diagnostic.sh
```

按 Enter 开始诊断，等待1-3分钟。

### 方法B：手动运行

```bash
cd ~/cryptosignal
python3 diagnostic_scan.py > diagnostic_report.txt 2>&1
```

---

## 📊 诊断脚本会检查什么？

### 1. 版本和配置检查 ✅
- Git分支和commit版本
- Anti-Jitter阈值配置（应为0.55/0.52，不是0.65/0.58）
- EV字段读取（应为大写'EV'，不是小写'ev'）
- EV计算公式（应使用abs(edge)）
- p_min adjustment限制（应限制为0.02）

### 2. 实际扫描测试 🧪
- 扫描10个币种（快速测试）
- 记录每个信号的详细数据

### 3. 信号详细分析 📋
对每个信号检查：
- 概率值（P）和期望值（EV）
- Prime状态和软约束过滤状态
- Anti-Jitter测试结果（new_level, should_publish）
- 发布条件检查（3个条件逐一验证）

### 4. 统计汇总 📈
- 信号级别分布（PRIME/WATCH/其他）
- 失败原因统计（EV≤0, P<0.55, Anti-Jitter拒绝）
- 概率和EV的分布情况（最小/最大/平均/中位数）

---

## 📋 查看诊断结果

### 报告位置
```bash
ls -lt diagnostic_report_*.txt | head -1
```

### 快速查看关键部分

**1. 配置检查结果：**
```bash
grep -A 20 "第一部分" diagnostic_report_*.txt | tail -1
```

**2. 统计汇总：**
```bash
grep -A 30 "第四部分" diagnostic_report_*.txt | tail -1
```

**3. 诊断结论：**
```bash
grep -A 30 "第五部分" diagnostic_report_*.txt | tail -1
```

**4. 完整报告：**
```bash
cat diagnostic_report_*.txt
```

---

## 🎯 预期结果

### ✅ 如果修复生效

你应该看到：

```
📋 第一部分：版本和配置检查
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   A. Anti-Jitter 配置:
      ✅ prime_entry_threshold = 0.55 (正确)
      ✅ prime_maintain_threshold = 0.52 (正确)
      ✅ EV字段读取使用大写 'EV' (正确)

   B. EV 计算:
      ✅ EV计算使用 abs(edge) (正确)
      ✅ p_min adjustment 限制为 0.02 (正确)
      ✅ publish字典使用大写 'EV' (正确)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📈 第四部分：统计汇总
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
信号级别分布:
   PRIME 级别:  3 / 10 (30.0%)     ← 应该 > 0
   WATCH 级别:  5 / 10 (50.0%)
   其他:        2 / 10

概率分布:
   最小值: 0.5012 (50.12%)
   最大值: 0.5891 (58.91%)
   平均值: 0.5445 (54.45%)        ← 应该在0.50-0.60范围
   中位数: 0.5520 (55.20%)

EV分布:
   最小值: -0.0023
   最大值: 0.0156
   平均值: 0.0067
   EV>0数量: 7 / 10 (70%)          ← 大部分应该 > 0
```

### ❌ 如果问题仍然存在

可能看到：

**情况1：配置未更新**
```
   A. Anti-Jitter 配置:
      ❌ prime_entry_threshold = 0.65 (旧版，应为0.55)
      ❌ prime_maintain_threshold = 0.58 (旧版，应为0.52)
```
**→ 解决方案：代码没有正确更新，重新git pull**

**情况2：概率值太低**
```
概率分布:
   平均值: 0.4523 (45.23%)        ← 远低于0.55阈值
   中位数: 0.4615 (46.15%)
```
**→ 解决方案：需要进一步降低阈值或调整Sigmoid温度参数**

**情况3：EV全部为负**
```
EV分布:
   最大值: -0.0012                 ← 所有EV都≤0
   平均值: -0.0234
   EV>0数量: 0 / 10 (0%)
```
**→ 解决方案：EV计算仍有问题，或cost参数过高**

---

## 🔧 根据诊断结果采取行动

### 场景1：配置问题

如果看到 ❌ 标记的配置：

```bash
# 确认是否在正确的分支和commit
git log -1 --oneline
# 应该显示: 527d584 或更新

# 如果不是，重新拉取
git fetch origin
git reset --hard origin/claude/audit-system-compliance-011CUkshDA3WNmJWFjbAEEn8
```

### 场景2：概率太低（平均P < 0.50）

可能需要调整Sigmoid温度参数，让我们再深入分析

### 场景3：EV问题（大部分EV ≤ 0）

可能需要检查cost计算或edge计算

### 场景4：Anti-Jitter问题

检查诊断报告中每个信号的Anti-Jitter测试结果

---

## 📤 发送诊断报告

将完整诊断报告内容发给我，我将进一步分析：

```bash
# 复制报告内容
cat diagnostic_report_*.txt | tail -1
```

或者如果报告太长：

```bash
# 提取关键部分
echo "=== 配置检查 ==="
grep -A 25 "第一部分" diagnostic_report_*.txt | tail -1

echo ""
echo "=== 统计汇总 ==="
grep -A 35 "第四部分" diagnostic_report_*.txt | tail -1

echo ""
echo "=== 前3个信号详情 ==="
grep -A 100 "信号 #1" diagnostic_report_*.txt | tail -1 | head -80
```

---

## ⚡ 常见问题

**Q: 诊断脚本运行很慢？**
A: 正常，扫描10个币种需要1-3分钟。如果超过5分钟可能卡住了。

**Q: 报错 "No module named ats_core"？**
A: 运行 `pip3 install -e .` 安装项目依赖

**Q: 诊断报告在哪？**
A: 当前目录下的 `diagnostic_report_YYYYMMDD_HHMMSS.txt`

**Q: 可以扫描更多币种吗？**
A: 可以，编辑 `diagnostic_scan.py`，将 `max_symbols=10` 改为 `max_symbols=50`

---

## 📞 需要帮助？

发送以下信息：
1. 完整诊断报告（`cat diagnostic_report_*.txt`）
2. Git状态（`git log -1 --oneline`）
3. 任何错误信息

我会根据诊断结果提供针对性的修复方案。
