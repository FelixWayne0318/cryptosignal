# 开发工作流规范 (Development Workflow)

> **v6.0 系统规范化开发流程**

---

## 📋 目录

1. [修改代码前的检查清单](#修改代码前的检查清单)
2. [Git提交规范](#git提交规范)
3. [文件修改协议](#文件修改协议)
4. [测试要求](#测试要求)
5. [文档更新要求](#文档更新要求)

---

## ✅ 修改代码前的检查清单

在修改任何代码之前，必须完成以下检查：

### 1. 明确修改目标

- [ ] 我知道要修改什么功能
- [ ] 我已查阅 [MODIFICATION_RULES.md](./MODIFICATION_RULES.md) 确定应该修改哪个文件
- [ ] 我理解修改的影响范围

### 2. 查阅相关文档

根据修改类型，查阅对应文档：

| 修改类型 | 必读文档 |
|---------|---------|
| 调整权重/阈值 | [CONFIGURATION_GUIDE.md](./CONFIGURATION_GUIDE.md) |
| 修改核心逻辑 | [ARCHITECTURE.md](./ARCHITECTURE.md) |
| 添加新因子 | [ARCHITECTURE.md § 因子系统](./ARCHITECTURE.md) + [SYSTEM_OVERVIEW.md](./SYSTEM_OVERVIEW.md) |
| 修改Telegram | [CONFIGURATION_GUIDE.md § Telegram](./CONFIGURATION_GUIDE.md) |

### 3. 确认修改文件合法性

**允许修改的文件** (按场景):

```
简单修改（无需深入理解系统）:
  ✅ config/params.json          # 权重、阈值、参数
  ✅ config/telegram.json        # Telegram配置

中等修改（需理解数据结构）:
  ✅ scripts/realtime_signal_scanner.py  # 主文件逻辑
  ✅ ats_core/outputs/telegram_fmt.py    # Telegram格式化
  ✅ ats_core/features/*/           # 单个因子逻辑
  ✅ ats_core/factors_v2/*/         # 新因子逻辑

高级修改（需完全理解架构）:
  ⚠️ ats_core/pipeline/analyze_symbol.py  # 单币种分析管道
  ⚠️ ats_core/scoring/scorecard.py       # 评分系统
  ⚠️ ats_core/scoring/adaptive_weights.py # 自适应权重
```

**禁止修改的文件** (除非完全理解系统):

```
❌ ats_core/pipeline/batch_scan_optimized.py  # 批量扫描核心
❌ ats_core/data/realtime_kline_cache.py      # WebSocket缓存
❌ ats_core/sources/binance.py                # 数据源
❌ ats_core/cfg.py                            # 配置加载
```

---

## 📝 Git提交规范

### 提交消息格式

所有提交必须遵循以下格式：

```
<类型>: <简短描述>

<详细说明>（可选）
```

### 提交类型

| 类型 | 说明 | 示例 |
|-----|------|------|
| `feat` | 新功能 | `feat: 添加L因子流动性分析` |
| `fix` | Bug修复 | `fix: 修复Prime信号过滤逻辑` |
| `refactor` | 重构代码 | `refactor: 统一v6.0权重百分比系统` |
| `docs` | 文档更新 | `docs: 更新CONFIGURATION_GUIDE.md` |
| `test` | 测试相关 | `test: 添加scorecard单元测试` |
| `chore` | 杂项（清理、配置等） | `chore: 删除冗余测试文件` |
| `perf` | 性能优化 | `perf: 优化batch_scan缓存策略` |

### 提交消息示例

**简单修改**:
```bash
git commit -m "fix: 修复adaptive_weights负权重问题"
```

**复杂修改**:
```bash
git commit -m "feat: 增强realtime_signal_scanner支持config文件配置

- 添加--config参数支持自定义配置文件
- 默认读取config/params.json
- 保持向后兼容性
- 更新使用文档
"
```

**重大变更**:
```bash
git commit -m "refactor: 统一v6.0权重百分比系统

重大变更:
- 180分制 → 100%百分比系统
- F因子权重 0 → 10.0%
- Prime阈值 65分 → 35分
- 更新所有文档至v6.0规范

影响范围:
- config/params.json
- ats_core/pipeline/analyze_symbol.py
- standards/*.md
"
```

### 提交前检查清单

- [ ] 代码已通过测试
- [ ] 清除了`__pycache__`缓存
- [ ] 提交消息清晰描述了改动
- [ ] 如有配置变更，已更新文档
- [ ] 如有API变更，已更新ARCHITECTURE.md

---

## 🔧 文件修改协议

### 修改config/params.json

**要求**:
1. 权重总和必须=100.0%
2. 修改后必须验证JSON格式
3. 修改后必须测试运行
4. 如修改核心权重，需更新文档

**验证命令**:
```bash
# 验证JSON格式
python3 -c "import json; json.load(open('config/params.json'))"

# 验证权重总和
python3 -c "
import json
w = json.load(open('config/params.json'))['weights']
total = sum(w.values())
assert abs(total - 100.0) < 0.01, f'权重总和={total}, 必须=100.0'
print(f'✓ 权重总和={total}')
"
```

**提交模板**:
```bash
git add config/params.json
git commit -m "config: 调整因子权重

- T: 13.9% → 15.0%
- F: 10.0% → 8.9%
- 总权重: 100.0% ✓
"
```

### 修改主文件 (scripts/realtime_signal_scanner.py)

**要求**:
1. 修改前必须理解当前逻辑
2. 修改后必须测试 `--max-symbols 20 --once`
3. 如修改数据结构访问，必须核对batch_scan返回格式
4. 保持向后兼容性

**测试命令**:
```bash
# 清除缓存
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null

# 测试运行
python3 scripts/realtime_signal_scanner.py --max-symbols 20 --once
```

### 修改因子代码 (ats_core/features/*, ats_core/factors_v2/*)

**要求**:
1. 保持返回格式: `{"value": float, "signal": int, "label": str, "reason": str}`
2. value范围: -100 ~ +100
3. signal取值: -1 (看跌), 0 (中性), +1 (看涨)
4. 添加详细的reason说明

**测试示例**:
```python
# test_new_factor.py
from ats_core.features.my_factor import calculate_my_factor

result = calculate_my_factor(df)
assert -100 <= result['value'] <= 100, "value超出范围"
assert result['signal'] in [-1, 0, 1], "signal取值错误"
assert 'reason' in result, "缺少reason字段"
print(f"✓ 因子测试通过: {result}")
```

### 修改Telegram格式 (ats_core/outputs/telegram_fmt.py)

**要求**:
1. 保持HTML格式兼容性
2. 测试特殊字符转义
3. 测试长消息截断（4096字符限制）
4. 保持emoji使用一致性

**测试命令**:
```bash
# 发送测试消息
python3 -c "
from ats_core.outputs.telegram_fmt import format_signal_message
msg = format_signal_message({
    'symbol': 'BTCUSDT',
    'final_score': 45.0,
    'prime_strength': 38.5,
    'factors': {...}
})
print(msg)
"
```

---

## 🧪 测试要求

### 修改后必须执行的测试

#### 1. 配置修改测试

```bash
# 验证JSON格式
python3 -c "import json; json.load(open('config/params.json'))"

# 验证权重总和
python3 -c "
import json
w = json.load(open('config/params.json'))['weights']
assert abs(sum(w.values()) - 100.0) < 0.01
"
```

#### 2. 代码修改测试

```bash
# 清除缓存
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null

# 快速测试（20个币种）
python3 scripts/realtime_signal_scanner.py --max-symbols 20 --once

# 完整测试（200个币种）
python3 scripts/realtime_signal_scanner.py --once
```

#### 3. Telegram集成测试

```bash
# 测试单个币种发送
python3 scripts/realtime_signal_scanner.py --max-symbols 1 --once

# 检查Telegram是否收到消息
```

### 性能基准测试

修改核心代码后，需验证性能未退化：

```bash
# 记录扫描时间
time python3 scripts/realtime_signal_scanner.py --max-symbols 200 --once

# 预期时间: 12-15秒
# 如果超过20秒，需检查是否引入API调用或缓存失效
```

---

## 📚 文档更新要求

### 何时需要更新文档

| 修改类型 | 需要更新的文档 |
|---------|---------------|
| 添加新参数 | [CONFIGURATION_GUIDE.md](./CONFIGURATION_GUIDE.md) |
| 修改核心逻辑 | [ARCHITECTURE.md](./ARCHITECTURE.md) |
| 添加新因子 | [SYSTEM_OVERVIEW.md](./SYSTEM_OVERVIEW.md) + [ARCHITECTURE.md](./ARCHITECTURE.md) |
| 修改主文件 | [MODIFICATION_RULES.md](./MODIFICATION_RULES.md) |
| 重大架构变更 | 所有standards/*.md文件 |

### 文档更新检查清单

- [ ] 文档中的代码示例已更新
- [ ] 版本号已更新（如适用）
- [ ] 示例输出已更新（如适用）
- [ ] 旧信息已删除或标记为过时

### 文档提交规范

```bash
# 单独提交文档更新
git add standards/
git commit -m "docs: 更新CONFIGURATION_GUIDE.md添加新参数说明

- 添加L因子流动性参数配置
- 更新示例配置文件
- 补充常见问题FAQ
"
```

---

## 🚀 完整修改流程示例

### 场景1: 调整因子权重

```bash
# 1. 修改配置
vim config/params.json
# 修改 T: 13.9 → 15.0, F: 10.0 → 8.9

# 2. 验证权重
python3 -c "
import json
w = json.load(open('config/params.json'))['weights']
total = sum(w.values())
assert abs(total - 100.0) < 0.01, f'总和={total}'
print(f'✓ 权重总和={total}')
"

# 3. 清除缓存
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null

# 4. 测试运行
python3 scripts/realtime_signal_scanner.py --max-symbols 20 --once

# 5. 提交
git add config/params.json
git commit -m "config: 调整T和F因子权重

- T: 13.9% → 15.0%（增强趋势权重）
- F: 10.0% → 8.9%（平衡整体权重）
- 总权重: 100.0% ✓
"
git push
```

### 场景2: 修复Bug

```bash
# 1. 定位问题
# 发现Prime信号过滤逻辑错误

# 2. 修复代码
vim scripts/realtime_signal_scanner.py
# 修改 line 234-235

# 3. 清除缓存
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null

# 4. 测试修复
python3 scripts/realtime_signal_scanner.py --max-symbols 20 --once
# 验证Prime信号正确发送

# 5. 提交
git add scripts/realtime_signal_scanner.py
git commit -m "fix: 修复Prime信号过滤逻辑

问题: 使用了不存在的tier字段导致Prime信号全部被过滤
修复: 改为使用publish.prime字段判断
影响: Prime信号现在能正确发送至Telegram
"
git push
```

### 场景3: 添加新功能

```bash
# 1. 阅读架构文档
cat standards/ARCHITECTURE.md

# 2. 实现新功能
vim ats_core/features/new_factor.py
# 编写新因子代码

# 3. 更新主文件（如需要）
vim scripts/realtime_signal_scanner.py
# 集成新因子

# 4. 更新配置
vim config/params.json
# 添加新因子权重

# 5. 清除缓存并测试
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
python3 scripts/realtime_signal_scanner.py --max-symbols 20 --once

# 6. 更新文档
vim standards/SYSTEM_OVERVIEW.md
vim standards/ARCHITECTURE.md
vim standards/CONFIGURATION_GUIDE.md

# 7. 提交（分两次提交）
git add ats_core/features/new_factor.py config/params.json
git commit -m "feat: 添加新因子X分析

- 实现X因子计算逻辑
- 添加配置参数支持
- 集成至主扫描流程
- 权重分配: 5.0%
"

git add standards/
git commit -m "docs: 更新文档添加新因子X说明

- SYSTEM_OVERVIEW.md: 添加X因子概述
- ARCHITECTURE.md: 补充X因子技术细节
- CONFIGURATION_GUIDE.md: 添加X因子参数说明
"

git push
```

---

## ⚠️ 常见错误和避免方法

### 1. 权重总和不等于100%

**错误**:
```json
{
  "weights": {
    "T": 15.0,
    "F": 10.0,
    // ... 其他因子
    // 总和 = 101.0 ❌
  }
}
```

**避免方法**: 每次修改后运行验证脚本

### 2. 缓存导致的逻辑错误

**错误**: 修改代码后直接运行，未清除`__pycache__`

**避免方法**: 每次修改后必须清除缓存

```bash
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
```

### 3. 数据结构访问错误

**错误**:
```python
# batch_scan返回 {'publish': {'prime': True}}
# 错误访问: signal.get('tier') == 'prime'
```

**避免方法**: 查看batch_scan返回格式，使用正确的字段路径

### 4. 修改禁止文件

**错误**: 直接修改 `batch_scan_optimized.py` 而不理解影响范围

**避免方法**: 查阅 [MODIFICATION_RULES.md](./MODIFICATION_RULES.md) 确认文件是否可修改

### 5. 提交消息不规范

**错误**:
```bash
git commit -m "update"  # 信息不明确
git commit -m "修复bug"  # 没有类型前缀
```

**正确**:
```bash
git commit -m "fix: 修复Prime信号过滤逻辑"
```

---

## 📞 遇到问题

### 检查清单

1. **我是否查阅了相关文档?**
   - [MODIFICATION_RULES.md](./MODIFICATION_RULES.md)
   - [CONFIGURATION_GUIDE.md](./CONFIGURATION_GUIDE.md)
   - [ARCHITECTURE.md](./ARCHITECTURE.md)

2. **我是否清除了缓存?**
   ```bash
   find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
   ```

3. **我是否运行了测试?**
   ```bash
   python3 scripts/realtime_signal_scanner.py --max-symbols 20 --once
   ```

4. **我的修改是否符合规范?**
   - 权重总和=100%
   - 提交消息格式正确
   - 文档已更新

---

## 📌 重要原则

1. **单一入口**: 只有 `scripts/realtime_signal_scanner.py` 是运行入口
2. **配置驱动**: 参数调整通过 `config/params.json`，不硬编码
3. **文档同步**: 代码修改必须同步更新文档
4. **测试优先**: 修改后必须测试，通过后才提交
5. **规范提交**: 使用规范的Git提交消息格式

---

**版本**: v6.0
**最后更新**: 2025-10-30
