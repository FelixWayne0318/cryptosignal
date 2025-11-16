# 🔧 FactorConfig 错误修复与服务重启指南

**日期**: 2025-11-16
**版本**: v7.3.47
**优先级**: P0 (Critical)
**状态**: ✅ 代码已修复，需重启服务应用

---

## 📋 问题现象

```
[2025-11-16 04:35:42Z][WARN] ⚠️  FXSUSDT 分析失败: 'FactorConfig' object has no attribute 'get'
```

---

## ✅ 已完成的修复

### 1. 代码修复 ✅

**文件**: `ats_core/pipeline/analyze_symbol.py`

**修复位置1** (Line 793-797):
```python
# v7.3.47: 从配置读取I因子参数（消除P0-1硬编码）
# 修复：FactorConfig对象使用.config.get()而不是.get()
i_factor_params = factor_config.config.get('I因子参数', {})  # ✅ 正确
i_effective_threshold_default = i_factor_params.get('effective_threshold', 50.0)
i_confidence_boost_default = i_factor_params.get('confidence_boost_default', 0.0)
```

**修复位置2** (Line 825-831):
```python
except Exception as e:
    # ...
    # v7.3.47: 从配置读取默认值（消除P0-1硬编码）
    # 修复：FactorConfig对象使用.config.get()而不是.get()
    i_factor_params = factor_config.config.get('I因子参数', {})  # ✅ 正确
```

### 2. 输出配置完善 ✅

**文件**: `config/scan_output.json`

所有输出选项已设置为 `true`，确保显示完整信息：
- ✅ `mode: "full"` - 显示所有币种详情
- ✅ `show_core_factors: true` - 显示6个核心因子
- ✅ `show_modulators: true` - 显示4个调制器
- ✅ `show_f_factor_details: true` - F因子详细信息
- ✅ `show_i_factor_details: true` - I因子详细信息
- ✅ `show_gates: true` - 显示闸门信息
- ✅ `show_prime_breakdown: true` - Prime分解
- ✅ `show_full_statistics: true` - 完整统计报告

### 3. Python缓存清理 ✅

已执行：
```bash
find /home/user/cryptosignal -name "*.pyc" -delete
find /home/user/cryptosignal -name "__pycache__" -type d -exec rm -rf {} +
```

---

## 🚀 重启服务应用修复

### ⚠️ 重要：必须重启服务

**原因**: Python进程会加载并缓存代码，即使修改了 `.py` 文件，正在运行的进程仍然使用旧代码。

### 方法1: 使用setup.sh重启（推荐）⭐

```bash
cd ~/cryptosignal

# 停止旧服务
pkill -f "realtime_signal_scanner.py" || true
sleep 2

# 重新部署和启动
./setup.sh
```

**优点**:
- ✅ 自动检查环境
- ✅ 重新加载所有模块
- ✅ 后台运行 + 日志输出
- ✅ 确保使用最新代码

### 方法2: 手动重启

```bash
cd ~/cryptosignal

# 1. 查找运行中的进程
ps aux | grep realtime_signal_scanner

# 2. 停止进程（替换<PID>为实际进程号）
kill <PID>

# 或者直接杀死所有相关进程
pkill -f "realtime_signal_scanner.py"

# 3. 确认已停止
ps aux | grep realtime_signal_scanner

# 4. 重新启动
nohup python3 scripts/realtime_signal_scanner.py --interval 300 > /tmp/scanner.log 2>&1 &

# 5. 查看日志
tail -f /tmp/scanner.log
```

### 方法3: 使用screen重启

```bash
# 1. 查看现有screen会话
screen -ls

# 2. 进入scanner会话
screen -r scanner  # 或其他会话名

# 3. 按 Ctrl+C 停止程序

# 4. 重新启动
python3 scripts/realtime_signal_scanner.py --interval 300

# 5. 按 Ctrl+A 然后按 D 分离会话
```

---

## ✅ 验证修复是否生效

### 测试1: 导入测试

```bash
python3 -c "
import sys
sys.path.insert(0, '/home/user/cryptosignal')
from ats_core.config.factor_config import get_factor_config

factor_config = get_factor_config()
i_params = factor_config.config.get('I因子参数', {})
print('✅ FactorConfig 用法正确，修复已生效')
"
```

**预期输出**:
```
✅ 配置加载成功: /home/user/cryptosignal/config/factors_unified.json (vv7.3.47)
✅ FactorConfig 用法正确，修复已生效
```

### 测试2: 检查日志输出

重启服务后，查看日志应该看到：

**成功分析的币种** (不再报错):
```
[2025-11-16 XX:XX:XXZ] [N/310] 正在分析 FXSUSDT...
[2025-11-16 XX:XX:XXZ]   └─ K线数据: 1h=300根, 4h=200根, 15m=200根, 1d=100根
[2025-11-16 XX:XX:XXZ]   └─ 币种类型：成熟币(数据受限)（299.0小时）
[2025-11-16 XX:XX:XXZ]   └─ 开始因子分析...
[2025-11-16 XX:XX:XXZ] 📊 CVD Mix统计: 均值=-0.01, 标准差=1.52, 偏度=-1.17
[2025-11-16 XX:XX:XXZ]   └─ [评分] confidence=XX, prime_strength=XX
[2025-11-16 XX:XX:XXZ]       A-层核心因子: T=XX, M=XX, C=XX, V=XX, O=XX, B=XX  ✅
[2025-11-16 XX:XX:XXZ]       B-层调制器: L=XX, S=XX, F=XX, I=XX  ✅
[2025-11-16 XX:XX:XXZ]       F因子详情: ...  ✅
[2025-11-16 XX:XX:XXZ]       I因子详情: ...  ✅
```

**完整统计报告**:
```
[2025-11-16 XX:XX:XXZ] ========================================
[2025-11-16 XX:XX:XXZ] 📊 全市场扫描统计分析报告
[2025-11-16 XX:XX:XXZ] ========================================
[2025-11-16 XX:XX:XXZ]
[2025-11-16 XX:XX:XXZ] 因子分布统计:  ✅
[2025-11-16 XX:XX:XXZ]   T因子: 均值=XX, 标准差=XX, ...
[2025-11-16 XX:XX:XXZ]   M因子: 均值=XX, 标准差=XX, ...
[2025-11-16 XX:XX:XXZ]   ...
```

---

## 🔍 故障排查

### 问题1: 重启后仍然报错

**可能原因**:
1. Python模块缓存未清理
2. 使用了虚拟环境，未激活正确的环境
3. 多个Python版本，运行了错误的版本

**解决方案**:
```bash
# 1. 彻底清理缓存
cd ~/cryptosignal
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# 2. 检查Python版本
which python3
python3 --version  # 应该是 3.8+

# 3. 检查模块路径
python3 -c "import sys; print('\n'.join(sys.path))"

# 4. 完全重启
pkill -9 -f "realtime_signal_scanner.py"
./setup.sh
```

### 问题2: 只显示部分因子信息

**检查配置**:
```bash
# 查看输出配置
cat config/scan_output.json | grep -E '"(mode|show_)' | grep -v "_comment"
```

**应该都是 true**:
```json
"mode": "full",
"show_all_factors": true,
"show_core_factors": true,
"show_modulators": true,
"show_gates": true,
"show_prime_breakdown": true,
"show_f_factor_details": true,
"show_i_factor_details": true,
"show_full_statistics": true,
...
```

**如果不是**，修复配置：
```bash
# 备份
cp config/scan_output.json config/scan_output.json.backup

# 使用Git恢复
git checkout config/scan_output.json

# 重启服务
./setup.sh
```

### 问题3: 统计报告不完整

**检查** `batch_scan_optimized.py` 中的统计输出配置：
```python
if self.output_config.get('statistics_output', {}).get('show_full_statistics', True):
    # 应该进入这里
```

**确认配置文件加载**:
```python
python3 -c "
import json
config = json.load(open('config/scan_output.json'))
print(f\"统计输出: {config['statistics_output']['show_full_statistics']}\")
"
```

---

## 📊 预期效果

### 修复前 ❌
```
[WARN] ⚠️  FXSUSDT 分析失败: 'FactorConfig' object has no attribute 'get'
[WARN] ⚠️  BTCUSDT 分析失败: 'FactorConfig' object has no attribute 'get'
...
分析成功率: 0%
```

### 修复后 ✅
```
[310/310] 正在分析 FXSUSDT...
  └─ [评分] confidence=68, prime_strength=72
      A-层核心因子: T=45.2, M=32.1, C=56.8, V=28.4, O=41.2, B=12.3
      B-层调制器: L=82.5, S=65.3, F=48.7, I=55.2
      F因子详情: F=48, F_raw=0.45, fund_momentum=2.3, ...
      I因子详情: I=55, beta_btc=0.85, beta_eth=0.92, level=独立
      四门调节: DataQual=0.98, EV=0.85, Execution=0.92, Probability=0.88

[统计分析]
因子分布统计:
  T因子: 均值=42.3, 标准差=18.5, 偏度=-0.12, ...
  M因子: 均值=35.6, 标准差=22.1, 偏度=0.23, ...
  ...

分析成功率: 100%
```

---

## 📁 相关文件

**代码修复**:
- `ats_core/pipeline/analyze_symbol.py` - Line 795, 827

**配置文件**:
- `config/scan_output.json` - 输出详细度配置
- `config/factors_unified.json` - 因子参数配置

**文档**:
- `docs/BUGFIX_FACTORCONFIG_v7.3.47_2025-11-16.md` - 详细修复报告
- `docs/SERVICE_RESTART_GUIDE_v7.3.47_2025-11-16.md` - 本文档

---

## 🎯 重要提示

### ⚠️ 必须重启服务

代码修复 **不会自动生效**，必须重启 Python 进程！

### ✅ 推荐操作流程

```bash
# 1. 停止旧服务
pkill -f "realtime_signal_scanner.py"

# 2. 清理缓存（可选但推荐）
cd ~/cryptosignal
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# 3. 重新启动
./setup.sh

# 4. 查看日志验证
# 日志位置根据 setup.sh 配置，通常是：
tail -f /tmp/scanner.log
# 或
screen -r scanner  # 然后查看输出
```

### 🔒 配置锁定

**重要**: 以下配置已锁定，请勿随意修改：

```json
{
  "output_detail_level": { "mode": "full" },  // 🔒 始终完整输出
  "factor_output": {
    "show_core_factors": true,    // 🔒 必须显示
    "show_modulators": true,      // 🔒 必须显示
    "show_gates": true,           // 🔒 必须显示
    "show_prime_breakdown": true  // 🔒 必须显示
  },
  "diagnostic_output": {
    "show_f_factor_details": true,  // 🔒 必须显示
    "show_i_factor_details": true   // 🔒 必须显示
  },
  "statistics_output": {
    "show_full_statistics": true  // 🔒 必须显示完整报告
  }
}
```

**如果需要临时减少输出**，使用以下方式：
```bash
# 临时限制输出前10个币种（不修改配置文件）
python3 scripts/realtime_signal_scanner.py --max-symbols 10
```

---

## 📞 支持

如果重启后仍有问题，请检查：

1. ✅ Git commit `734b125` 是否已拉取
2. ✅ Python缓存是否已清理
3. ✅ 服务是否已重启
4. ✅ 日志中是否还有 `'FactorConfig' object has no attribute 'get'` 错误

如果以上都确认，但仍有问题，请提供：
- 完整的错误日志
- Python版本 (`python3 --version`)
- Git版本信息 (`git log -1 --oneline`)

---

**文档版本**: v7.3.47
**最后更新**: 2025-11-16
**状态**: ✅ 修复完成，等待重启验证
