# 10维因子系统 - 快速开始 🚀

## 当前状态

✅ **I因子（独立性）** - 已完全工作
⚠️ **Q因子（清算密度）** - 需要配置API认证

## 3分钟快速配置

### 步骤1: 拉取最新代码

```bash
cd ~/cryptosignal
git pull origin claude/optimize-coin-analysis-speed-011CUYy6rjvHGXbkToyBt9ja
```

### 步骤2: 配置Binance API（启用Q因子）

```bash
# 设置环境变量
export BINANCE_API_KEY="your_api_key_here"
export BINANCE_API_SECRET="your_api_secret_here"

# 测试API配置
python3 test_api_auth.py
```

💡 **获取API Key**: https://www.binance.com/en/my/settings/api-management
⚠️ **重要**: 只启用"读取"权限，不要启用交易权限！

### 步骤3: 验证系统

```bash
# 完整系统验证（推荐）
python3 verify_10d_system.py

# 或快速测试
python3 test_10d_analysis.py
```

## 预期结果

### ✅ 配置成功

```
【BTCUSDT】
  Q(清算密度): +8.5   ✅ 正常工作
  I(独立性): +20.0     ✅ 正常工作
```

### ⚠️ 未配置API

```
【BTCUSDT】
  Q(清算密度): +0.0   ⚠️  需要API认证
  I(独立性): +20.0     ✅ 正常工作
```

## 永久配置（推荐生产环境）

```bash
# 编辑bashrc
nano ~/.bashrc

# 添加以下两行
export BINANCE_API_KEY="your_api_key_here"
export BINANCE_API_SECRET="your_api_secret_here"

# 保存并生效
source ~/.bashrc

# 验证
echo $BINANCE_API_KEY
```

## 故障排查

### 问题：API返回401错误

```bash
# 检查环境变量
env | grep BINANCE

# 确保没有多余空格
export BINANCE_API_KEY="$(echo -n 'your_key_without_spaces')"
```

### 问题：时间戳错误

```bash
# 同步服务器时间
sudo ntpdate pool.ntp.org
```

## 更多信息

- **详细配置**: `cat ENABLE_Q_FACTOR.md`
- **系统状态**: `cat 10D_SYSTEM_STATUS.md`
- **API测试**: `python3 test_api_auth.py`
- **系统验证**: `python3 verify_10d_system.py`

## 需要帮助？

检查以下文档：
1. ENABLE_Q_FACTOR.md - Q因子配置详解
2. 10D_SYSTEM_STATUS.md - 系统完整状态
3. 代码注释 - 技术实现细节

---

**更新时间**: 2025-10-29
**系统版本**: 10维因子系统 v1.0
