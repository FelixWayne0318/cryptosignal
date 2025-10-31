# 快速参考手册 (Quick Reference)

> **v6.0 系统快速操作指南 - 1分钟速查**

---

## 🎯 修改代码的标准流程（7步）

```
1. 修改前  → 查阅 standards/MODIFICATION_RULES.md 确定修改哪个文件
2. 修改中  → 只修改允许的文件，遵循规范
3. 修改后  → 必须清除缓存：find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
4. 测试时  → 使用 --max-symbols 20 --once 快速测试
5. 提交时  → 使用规范格式：<类型>: <描述>
6. 文档同步 → 如有配置或逻辑变更，必须更新文档
7. 推送    → git push
```

---

## 📁 常用文件路径

### 配置文件（简单修改）
```
config/params.json           # 权重、阈值、参数
config/telegram.json         # Telegram配置
config/blacklist.json        # 黑名单
```

### 主文件（中等修改）
```
scripts/realtime_signal_scanner.py    # 主文件（唯一运行入口）
ats_core/outputs/telegram_fmt.py      # Telegram消息格式
```

### 因子文件（中等修改）
```
ats_core/features/trend.py            # T-趋势因子
ats_core/features/momentum.py         # M-动量因子
ats_core/features/cvd.py              # C-CVD因子
ats_core/features/structure_sq.py     # S-结构因子
ats_core/features/volume.py           # V-成交量因子
ats_core/features/open_interest.py    # O-持仓量因子
ats_core/features/funding_rate.py     # F-资金费率因子
ats_core/factors_v2/liquidity.py      # L-流动性因子
ats_core/factors_v2/basis_funding.py  # B-基差因子
ats_core/factors_v2/cvd_enhanced.py   # Q-增强CVD因子
ats_core/factors_v2/independence.py   # I-独立性因子
```

### 核心系统（高级修改，需完全理解）
```
ats_core/pipeline/analyze_symbol.py          # 单币种分析管道
ats_core/scoring/scorecard.py                # 评分系统
ats_core/scoring/adaptive_weights.py         # 自适应权重
```

### 禁止修改（除非完全理解系统）
```
❌ ats_core/pipeline/batch_scan_optimized.py   # 批量扫描核心
❌ ats_core/data/realtime_kline_cache.py       # WebSocket缓存
❌ ats_core/sources/binance.py                 # 数据源
❌ ats_core/cfg.py                             # 配置加载
```

---

## 🔧 常用命令

### 清除缓存（每次修改后必须执行）
```bash
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
```

### 验证配置
```bash
# 验证JSON格式
python3 -c "import json; json.load(open('config/params.json'))"

# 验证权重总和=100%
python3 -c "
import json
w = json.load(open('config/params.json'))['weights']
total = sum(w.values())
assert abs(total - 100.0) < 0.01, f'权重总和={total}, 必须=100.0'
print(f'✓ 权重总和={total}')
"
```

### 测试运行
```bash
# 快速测试（20个币种，2-3秒）
python3 scripts/realtime_signal_scanner.py --max-symbols 20 --once

# 完整测试（200个币种，12-15秒）
python3 scripts/realtime_signal_scanner.py --once

# 单个币种测试
python3 scripts/realtime_signal_scanner.py --symbols BTCUSDT --once
```

### 网络诊断
```bash
python3 scripts/diagnose_network.py
```

---

## 📝 Git提交规范

### 提交类型
```
feat:     新功能
fix:      Bug修复
config:   配置修改
refactor: 重构代码
docs:     文档更新
test:     测试相关
chore:    杂项（清理、配置等）
perf:     性能优化
```

### 提交模板
```bash
git commit -m "<类型>: <简短描述>

<详细说明>（可选）
"
```

### 提交示例
```bash
# 配置修改
git commit -m "config: 调整T因子权重从13.9%到15.0%"

# Bug修复
git commit -m "fix: 修复Prime信号过滤逻辑

问题: 使用了不存在的tier字段
修复: 改为使用publish.prime字段
影响: Prime信号现在能正确发送
"
```

---

## 📊 配置修改速查

### 调整因子权重
```json
// config/params.json
{
  "weights": {
    "T": 13.9,  // 趋势
    "M": 8.3,   // 动量
    "C": 11.1,  // CVD
    "S": 5.6,   // 结构
    "V": 8.3,   // 成交量
    "O": 11.1,  // 持仓量
    "L": 11.1,  // 流动性
    "B": 8.3,   // 基差
    "Q": 5.6,   // 增强CVD
    "I": 6.7,   // 独立性
    "E": 0,     // （保留）
    "F": 10.0   // 资金费率
  }
  // 总和必须=100.0
}
```

### 调整Prime阈值
```json
// config/params.json
{
  "publish": {
    "prime_threshold": 35,        // Prime信号阈值
    "confidence_threshold": 0.55  // 置信度阈值
  }
}
```

### Telegram配置
```json
// config/telegram.json
{
  "enabled": true,
  "bot_token": "YOUR_BOT_TOKEN",
  "chat_id": "YOUR_CHAT_ID"
}
```

---

## 🚨 常见错误和解决方法

### 错误1: 权重总和不等于100%
```bash
# 症状：运行后权重不生效
# 原因：weights总和 ≠ 100.0

# 解决：验证权重
python3 -c "
import json
w = json.load(open('config/params.json'))['weights']
print(f'总和={sum(w.values())}')
"
# 必须=100.0
```

### 错误2: 修改代码后不生效
```bash
# 症状：修改代码后运行结果没变
# 原因：Python缓存了旧代码

# 解决：清除__pycache__
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
```

### 错误3: Prime信号不发送
```bash
# 症状：有信号但Telegram没收到
# 原因1：过滤逻辑错误

# 检查：scripts/realtime_signal_scanner.py line 234-235
# 错误: s.get('tier') == 'prime'
# 正确: s.get('publish', {}).get('prime', False)
```

### 错误4: 数据结构访问错误
```bash
# 症状：KeyError或None错误
# 原因：使用了不存在的字段

# 解决：查阅 docs/ARCHITECTURE.md 确认数据结构
# batch_scan返回格式:
{
  'symbol': 'BTCUSDT',
  'final_score': 45.0,
  'publish': {
    'prime': True,      # ✓ 正确
    'confidence': 0.78
  }
  # 'tier': ...         # ✗ 不存在
}
```

---

## 📚 文档速查

### 必读文档（按优先级）

| 优先级 | 文档 | 用途 | 阅读时间 |
|-------|------|------|---------|
| ⭐⭐⭐⭐⭐ | **SYSTEM_OVERVIEW.md** | 新对话框必读，快速了解系统 | 5-10分钟 |
| ⭐⭐⭐⭐ | **MODIFICATION_RULES.md** | 修改前必读，确定改哪个文件 | 3-5分钟 |
| ⭐⭐⭐⭐ | **QUICK_REFERENCE.md** | 快速查阅常用命令和路径 | 1-2分钟 |
| ⭐⭐⭐⭐ | **DEVELOPMENT_WORKFLOW.md** | 完整开发流程和示例 | 10-15分钟 |
| ⭐⭐⭐ | **CONFIGURATION_GUIDE.md** | 所有参数详细说明 | 15-20分钟 |
| ⭐⭐⭐ | **ARCHITECTURE.md** | 技术架构和数据流 | 15-20分钟 |

### 文档位置
```
standards/                         # 规范文档（规则性质）
  ├── MODIFICATION_RULES.md        # 修改规范
  └── STANDARDIZATION_REPORT.md    # 标准化报告

docs/                              # 说明文档（指南性质）
  ├── QUICK_REFERENCE.md           # 本文档（1分钟速查）
  ├── SYSTEM_OVERVIEW.md           # 系统总览
  ├── DEVELOPMENT_WORKFLOW.md      # 开发流程
  ├── CONFIGURATION_GUIDE.md       # 配置详解
  └── ARCHITECTURE.md              # 技术架构
```

---

## 🎯 3个最常见场景

### 场景1: 调整因子权重（2分钟）
```bash
# 1. 查阅文档（确定修改文件）
cat standards/MODIFICATION_RULES.md  # 确认修改 config/params.json

# 2. 修改配置
vim config/params.json
# T: 13.9 → 15.0, F: 10.0 → 8.9

# 3. 验证权重总和=100%
python3 -c "import json; w=json.load(open('config/params.json'))['weights']; assert abs(sum(w.values())-100)<0.01; print('✓ 权重总和正确')"

# 4. 清除缓存
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null

# 5. 测试
python3 scripts/realtime_signal_scanner.py --max-symbols 20 --once

# 6. 更新文档（如有重大权重调整）
# vim docs/CONFIGURATION_GUIDE.md  # 如有必要

# 7. 提交并推送
git add config/params.json
git commit -m "config: 调整T和F因子权重

- T: 13.9% → 15.0%（增强趋势权重）
- F: 10.0% → 8.9%（平衡整体权重）
- 总权重: 100.0% ✓
"
git push
```

### 场景2: 修复Bug（5分钟）
```bash
# 1. 查阅文档（理解数据结构）
cat docs/ARCHITECTURE.md  # 查看batch_scan返回格式

# 2. 定位并修复Bug
vim scripts/realtime_signal_scanner.py
# 修改 line 234-235: s.get('tier') → s.get('publish', {}).get('prime', False)

# 3. 清除缓存
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null

# 4. 测试修复
python3 scripts/realtime_signal_scanner.py --max-symbols 20 --once
# 验证Prime信号正确发送到Telegram

# 5. 提交（无需更新文档，因为是Bug修复不改变规范）

# 6. 提交并推送
git add scripts/realtime_signal_scanner.py
git commit -m "fix: 修复Prime信号过滤逻辑

问题: 使用了不存在的tier字段导致Prime信号全部被过滤
修复: 改为使用publish.prime字段判断
影响: Prime信号现在能正确发送至Telegram
测试: 20个币种测试通过，Prime信号正常发送
"
git push
```

### 场景3: 修改Telegram格式（3分钟）
```bash
# 1. 查阅文档（确认修改文件）
cat standards/MODIFICATION_RULES.md  # 确认修改 telegram_fmt.py

# 2. 修改格式化代码
vim ats_core/outputs/telegram_fmt.py
# 修改消息格式逻辑

# 3. 清除缓存
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null

# 4. 测试（发送单个币种验证格式）
python3 scripts/realtime_signal_scanner.py --max-symbols 1 --once
# 检查Telegram消息格式是否正确

# 5. 更新文档（如有格式规范变更）
# vim docs/ARCHITECTURE.md  # 如果改变了消息格式规范

# 6. 提交并推送
git add ats_core/outputs/telegram_fmt.py
git commit -m "feat: 增强Telegram消息格式

- 添加因子值emoji指示器
- 优化Prime信号高亮显示
- 调整字段对齐和可读性
"
git push
```

---

## 🔑 核心要点（永远记住）

1. **唯一入口**: `scripts/realtime_signal_scanner.py` 是唯一运行入口
2. **配置驱动**: 参数调整通过 `config/params.json`，不硬编码
3. **清除缓存**: 每次修改后必须清除 `__pycache__`
4. **权重总和**: 必须=100.0，否则不生效
5. **测试优先**: 修改后必须测试，通过后才提交
6. **文档同步**: 配置或逻辑变更必须同步更新文档
7. **规范提交**: 使用 `<类型>: <描述>` 格式

---

## 💡 新对话框引用方式

**方法1: 直接引用（推荐）**
```
请读取 docs/QUICK_REFERENCE.md 和 standards/MODIFICATION_RULES.md
```

**方法2: 按场景引用**
```
我要调整因子权重，请读取 docs/QUICK_REFERENCE.md 场景1
```

**方法3: 完整理解系统**
```
请按顺序读取：
1. docs/SYSTEM_OVERVIEW.md
2. standards/MODIFICATION_RULES.md
3. docs/QUICK_REFERENCE.md
```

---

**版本**: v6.0
**最后更新**: 2025-10-30
**维护者**: FelixWayne0318/cryptosignal
