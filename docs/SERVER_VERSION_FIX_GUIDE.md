# CryptoSignal v7.4 服务器版本修复指南

## 🔍 问题诊断

**症状**：服务器日志显示v7.3版本，而不是v7.4四步系统

**典型日志特征**：
```
❌ 显示 "v7.3.2-Full版本"
❌ 使用"七道闸门"（Gate1-7）
❌ 显示旧F因子（包含T/M价格因子）
❌ 缺少Step1-4四步系统输出
❌ 缺少Entry/SL/TP价格
```

**原因**：
1. 服务器代码未更新到最新版本
2. Python缓存导致旧代码仍在运行
3. 服务器进程未重启

---

## 🔧 快速修复（推荐）

### 方法1：一键修复脚本

```bash
cd ~/cryptosignal
./fix_server_version.sh
```

**脚本会自动完成**：
1. ✅ 停止旧进程
2. ✅ 拉取最新代码
3. ✅ 清理Python缓存
4. ✅ 验证v7.4配置
5. ✅ 验证四步系统模块
6. ✅ 重启v7.4服务器
7. ✅ 显示实时日志

---

### 方法2：使用setup.sh

```bash
cd ~/cryptosignal
./setup.sh
```

`setup.sh`会：
- 自动拉取最新代码
- 清理Python缓存
- 重启服务器
- 显示实时日志

---

### 方法3：手动修复

```bash
# 1. 进入项目目录
cd ~/cryptosignal

# 2. 停止旧进程
pkill -f realtime_signal_scanner
sleep 2

# 3. 拉取最新代码
git pull --rebase origin $(git branch --show-current)

# 4. 清理Python缓存（重要！）
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true

# 5. 验证配置
python3 -c "
import json
with open('config/params.json') as f:
    params = json.load(f)
    fss = params.get('four_step_system', {})
    print(f'four_step_system.enabled: {fss.get(\"enabled\")}')
    print(f'fusion_mode.enabled: {fss.get(\"fusion_mode\", {}).get(\"enabled\")}')
"

# 6. 重启服务器
./setup.sh
```

---

## 📊 验证v7.4正常运行

### 1. 运行诊断脚本

```bash
cd ~/cryptosignal
./diagnose_server_version.sh
```

**预期输出**：
```
✅ 本地代码与远程同步
✅ four_step_system.enabled: True
✅ fusion_mode.enabled: True
✅ 所有四步系统模块存在
✅ 扫描器进程正在运行
✅ 日志确认v7.4四步系统正在运行
```

---

### 2. 检查日志输出

```bash
# 查看最新日志
tail -f ~/cryptosignal_*.log
```

**v7.4正确运行的日志标识**：

```
✅ 🚀 v7.4: 启动四步系统 - BTCUSDT (融合模式)
✅ 📍 Step1: 方向确认...
✅ ✅ BTCUSDT - Step1通过: 方向=67.1, 置信度=0.98, BTC对齐=0.98
✅ ⏰ Step2: 时机判断...
✅ Enhanced_F = XX.X (flow_momentum vs price_momentum)
✅ 💰 入场价: 50,000
✅ 🛡️  止损: 49,500
✅ 🎯 止盈: 51,500
✅ 📈 盈亏比: 1:3.00
```

---

### 3. 确认配置正确

```bash
cd ~/cryptosignal
python3 -c "
import json
with open('config/params.json') as f:
    params = json.load(f)
    fss = params.get('four_step_system', {})
    print('=== v7.4配置检查 ===')
    print(f'四步系统启用: {fss.get(\"enabled\")}')
    print(f'融合模式启用: {fss.get(\"fusion_mode\", {}).get(\"enabled\")}')
    print(f'止损模式: {fss.get(\"step3_risk\", {}).get(\"stop_loss\", {}).get(\"mode\")}')
"
```

**预期输出**：
```
=== v7.4配置检查 ===
四步系统启用: True
融合模式启用: True
止损模式: structure_above_or_below
```

---

## ⚠️ 常见问题

### Q1: 脚本执行后日志仍显示v7.3

**原因**：需要等待下一次扫描周期（默认5分钟）

**解决**：
```bash
# 查看实时日志，等待下一次扫描
tail -f ~/cryptosignal_*.log
```

---

### Q2: Python缓存清理后仍有问题

**原因**：可能存在.pyc文件残留

**解决**：
```bash
cd ~/cryptosignal
# 彻底清理
find . -type f -name "*.pyc" -delete
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
# 重启
./setup.sh
```

---

### Q3: 配置显示enabled: false

**原因**：配置未正确更新

**解决**：
```bash
cd ~/cryptosignal
# 检查Git状态
git log -1 --oneline
# 应该看到：ff96266 feat(P0): 启用v7.4四步系统 - Enhanced F v2正式上线

# 如果没有，拉取最新代码
git pull --rebase origin $(git branch --show-current)
```

---

### Q4: 四步系统模块缺失

**原因**：代码未完全拉取

**解决**：
```bash
cd ~/cryptosignal
# 强制同步到远程最新版本
git fetch origin
git reset --hard origin/$(git branch --show-current)
# 重启
./setup.sh
```

---

## 📞 技术支持

如以上方法仍无法解决问题，请提供：

1. 诊断脚本输出：
   ```bash
   ./diagnose_server_version.sh > diagnosis_report.txt
   ```

2. 最新日志：
   ```bash
   tail -100 ~/cryptosignal_*.log > recent_logs.txt
   ```

3. Git状态：
   ```bash
   git log -5 --oneline > git_history.txt
   git status > git_status.txt
   ```

---

## 📚 相关文档

- v7.4系统文档：`docs/FOUR_STEP_IMPLEMENTATION_GUIDE.md`
- 会话状态：`SESSION_STATE.md`
- 系统标准：`standards/SYSTEM_ENHANCEMENT_STANDARD.md`
