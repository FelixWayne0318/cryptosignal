# 扫描报告自动提交策略

## 📋 策略概述

为了避免频繁的Git提交刷屏，同时确保重要信号及时推送，采用**智能提交策略**：

### 提交规则

| 场景 | 提交频率 | 说明 |
|------|---------|------|
| **有信号** | 立即提交 ⚡ | 发现信号时立即推送，确保及时通知 |
| **无信号** | 每小时1次 | 定期更新，避免Git历史刷屏 |
| **首次扫描** | 立即提交 | 首次运行时创建基准报告 |

---

## 🔍 工作原理

### 时间戳文件
```bash
.last_report_commit
```
- **作用**：记录上次提交的Unix时间戳
- **位置**：项目根目录（已被.gitignore排除）
- **格式**：纯数字，如 `1730973600`

### 判断逻辑

```bash
if [ 有信号 ]; then
    立即提交 ⚡
elif [ 距上次提交 >= 60分钟 ]; then
    定期提交
else
    跳过提交（本地文件已更新）
fi
```

---

## 📊 效果对比

### 之前：无限制提交
```
扫描间隔：5分钟
提交频率：每5分钟1次
每天提交：288次 ❌
```

**问题**：
- ❌ Git历史被无用提交刷屏
- ❌ 99%的提交都是"无信号"
- ❌ 难以快速找到有信号的提交

### 现在：智能提交
```
有信号：立即提交 ⚡
无信号：每60分钟1次
每天提交：最多24次 ✅（假设全天无信号）
实际提交：5-15次（有信号时更多）
```

**优势**：
- ✅ Git历史清晰，有信号的提交一目了然（⚡标记）
- ✅ 无信号时每小时汇总，减少99%无用提交
- ✅ 本地文件实时更新，Claude随时可读取

---

## 💬 提交消息格式

### 有信号时（立即提交）
```
scan: 2025-11-07 15:30:00 - 405币种, 5信号 ⚡

自动扫描报告（发现信号）
- 扫描时间: 2025-11-07 15:30:00
- 扫描币种: 405
- 发现信号: 5 ⚡
- 提交原因: 发现信号

文件: reports/latest/scan_summary.json
```

**特点**：
- 标题包含 `⚡` 标记，方便快速识别
- 详细记录信号数量
- 明确提交原因

### 无信号时（定期提交）
```
scan: 2025-11-07 16:30:00 - 405币种, 无信号

定期扫描报告更新（定期更新）
```

**特点**：
- 简洁信息，避免冗余
- 明确标记"无信号"
- 标注提交原因为"定期更新"

---

## 🔍 如何查看提交历史

### 查看所有扫描提交
```bash
cd ~/cryptosignal
git log --oneline --grep="scan:" -20
```

### 只查看有信号的提交
```bash
git log --oneline --grep="信号 ⚡" -10
```

### 查看最近24小时的提交
```bash
git log --since="24 hours ago" --oneline --grep="scan:"
```

### 查看具体提交内容
```bash
git show <commit-hash>
```

---

## 📈 实际运行示例

### 场景1：连续无信号
```
15:00 - 扫描完成，无信号 → 首次提交 ✅
15:05 - 扫描完成，无信号 → 跳过（距上次5分钟）
15:10 - 扫描完成，无信号 → 跳过（距上次10分钟）
...
15:55 - 扫描完成，无信号 → 跳过（距上次55分钟）
16:00 - 扫描完成，无信号 → 定期提交 ✅（距上次60分钟）
```

**结果**：60分钟内12次扫描，只提交2次

### 场景2：发现信号
```
15:00 - 扫描完成，无信号 → 首次提交 ✅
15:05 - 扫描完成，无信号 → 跳过
15:10 - 扫描完成，无信号 → 跳过
15:15 - 扫描完成，3个信号 → 立即提交 ⚡ ✅
15:20 - 扫描完成，5个信号 → 立即提交 ⚡ ✅
15:25 - 扫描完成，无信号 → 跳过
...
16:15 - 扫描完成，无信号 → 定期提交 ✅（距上次信号提交60分钟）
```

**结果**：60分钟内12次扫描，提交4次（2次信号+2次定期）

### 场景3：高频信号
```
15:00 - 扫描完成，2个信号 → 立即提交 ⚡ ✅
15:05 - 扫描完成，3个信号 → 立即提交 ⚡ ✅
15:10 - 扫描完成，5个信号 → 立即提交 ⚡ ✅
15:15 - 扫描完成，4个信号 → 立即提交 ⚡ ✅
...
```

**结果**：每次有信号都提交（这是期望的行为）

---

## 🛠️ 技术实现

### 脚本：`scripts/auto_commit_reports.sh`

**核心逻辑**：
```bash
# 读取扫描结果
SIGNALS=$(grep -o '"signals_found": [0-9]*' reports/latest/scan_summary.json)

# 策略1：有信号立即提交
if [ "$SIGNALS" != "0" ]; then
    SHOULD_COMMIT=true
    echo "📝 发现 $SIGNALS 个信号，立即提交..."
else
    # 策略2：无信号时检查时间间隔
    CURRENT_TIME=$(date +%s)
    LAST_COMMIT_TIME=$(cat .last_report_commit)
    TIME_DIFF=$((CURRENT_TIME - LAST_COMMIT_TIME))

    if [ $TIME_DIFF -ge 3600 ]; then  # 60分钟
        SHOULD_COMMIT=true
        echo "📝 距上次提交已过 1小时，定期提交..."
    else
        MINUTES=$((TIME_DIFF / 60))
        echo "⏳ 无信号，距上次提交 ${MINUTES}分钟，暂不提交"
    fi
fi

# 执行提交
if [ "$SHOULD_COMMIT" = true ]; then
    git commit ...
    git push ...
    date +%s > .last_report_commit  # 更新时间戳
fi
```

---

## 🔧 配置调整

### 修改提交间隔

编辑 `scripts/auto_commit_reports.sh`：

```bash
# 60分钟 = 3600秒
if [ $TIME_DIFF -ge 3600 ]; then
```

**调整选项**：
- **30分钟**：`1800`
- **2小时**：`7200`
- **3小时**：`10800`

### 禁用自动提交

编辑 `ats_core/pipeline/batch_scan_optimized.py`，注释掉自动提交部分：

```python
# log("\n🔄 自动提交报告到Git仓库...")
# import subprocess
# ...
```

---

## 📊 监控和调试

### 查看提交日志
```bash
tail -f ~/cryptosignal/logs/scanner_*.log | grep "提交"
```

### 查看时间戳文件
```bash
cat ~/cryptosignal/.last_report_commit
date -d @$(cat ~/cryptosignal/.last_report_commit)
```

### 手动触发提交
```bash
cd ~/cryptosignal
bash scripts/auto_commit_reports.sh
```

### 重置时间戳（强制下次提交）
```bash
rm ~/cryptosignal/.last_report_commit
```

---

## ⚠️ 注意事项

### 1. 时间戳文件不应提交到Git
- ✅ 已添加到 `.gitignore`
- ✅ 每台服务器独立维护自己的时间戳

### 2. 网络失败不影响本地文件
- ✅ 推送失败时，本地commit已完成
- ✅ 下次扫描会自动重试推送

### 3. 分支切换不影响时间戳
- ✅ 时间戳文件在项目根目录
- ✅ 切换分支后继续使用同一个时间戳

### 4. 多服务器不会冲突
- ✅ 每台服务器push到相同分支
- ✅ Git自动处理合并（报告文件总是覆盖式更新）

---

## 🎯 最佳实践

### 1. Claude分析报告
每次扫描后，报告文件已实时更新到 `reports/latest/`，Claude可以随时读取分析，无需等待Git提交。

### 2. 查看历史趋势
```bash
# 查看trends.json获取最近30次扫描的趋势
cat ~/cryptosignal/reports/trends.json
```

### 3. 快速定位信号
```bash
# 使用⚡标记快速找到有信号的提交
git log --oneline --all --grep="⚡"
```

---

## 📚 相关文档

- **自动Git提交**：`scripts/auto_commit_reports.sh`
- **报告生成**：`ats_core/analysis/report_writer.py`
- **扫描主流程**：`ats_core/pipeline/batch_scan_optimized.py`
- **GitHub配置**：`docs/VULTR_GITHUB_SETUP.md`
