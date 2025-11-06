# CryptoSignal v6.6 完整部署流程

**创建时间**: 2025-11-03
**目的**: 从零开始部署CryptoSignal v6.6，配置自动重启，实现7x24小时自动运行

---

## 📋 部署流程总览

```
步骤1: 停止所有旧进程
步骤2: 备份并清理旧的定时任务
步骤3: 拉取最新代码
步骤4: 配置新的定时任务
步骤5: 首次启动系统
步骤6: 验证运行状态
```

---

## 🚀 开始部署

### 步骤1: 停止所有旧进程和清理旧会话

**说明**: 确保没有旧版本在运行，避免冲突

#### 1.1 停止Python进程

```bash
# 停止所有cryptosignal相关进程
pkill -f "python.*cryptosignal"
pkill -f "deploy_and_run"
pkill -f "full_run_v2"
pkill -f "auto_scan_prime"

# 等待2秒确保进程完全停止
sleep 2

# 验证是否停止成功
ps aux | grep -E "python.*cryptosignal|deploy_and_run|full_run|auto_scan" | grep -v grep

# 如果没有输出 → 停止成功 ✅
# 如果有输出 → 还有进程在运行，重复上面的pkill命令
```

#### 1.2 清理旧的Screen会话

```bash
# 查看所有cryptosignal相关的screen会话
screen -ls | grep cryptosignal

# 批量清理所有旧的cryptosignal screen会话
screen -ls | grep cryptosignal | cut -d. -f1 | awk '{print $1}' | xargs -I {} screen -S {} -X quit 2>/dev/null || true

# 验证清理结果
screen -ls

# 应该看不到cryptosignal会话了 ✅
```

---

### 步骤2: 备份并清理旧的定时任务

**说明**: 备份现有crontab，然后清理旧任务

#### 2.1 备份当前crontab

```bash
# 备份到home目录，文件名包含日期
crontab -l > ~/crontab_backup_$(date +%Y%m%d_%H%M%S).txt

# 查看备份文件
ls -lh ~/crontab_backup_*.txt

# 显示备份内容（确认已备份）
cat ~/crontab_backup_*.txt
```

#### 2.2 清理crontab

```bash
# 编辑crontab
crontab -e
```

**在编辑器中**：
1. 按 `Ctrl+K` 多次，删除所有行（或者手动删除全部内容）
2. 复制粘贴以下内容：

```bash
# ==========================================
# CryptoSignal v6.6 自动化配置
# ==========================================

# 每2小时自动重启系统（保持数据新鲜）
# 重启时间：00:00, 02:00, 04:00, 06:00, 08:00, 10:00, 12:00, 14:00, 16:00, 18:00, 20:00, 22:00
0 */2 * * * ~/cryptosignal/auto_restart.sh

# 每天凌晨1点清理7天前的日志（节省磁盘空间）
0 1 * * * find ~ -name "cryptosignal_*.log" -mtime +7 -delete
```

3. 保存并退出：
   - 按 `Ctrl+X`
   - 按 `Y` 确认保存
   - 按 `Enter` 确认文件名

#### 2.3 验证crontab配置

```bash
# 查看当前crontab
crontab -l

# 应该只看到上面的2行任务 ✅
```

**预期输出**：
```
# ==========================================
# CryptoSignal v6.6 自动化配置
# ==========================================

# 每2小时自动重启系统（保持数据新鲜）
0 */2 * * * ~/cryptosignal/auto_restart.sh

# 每天凌晨1点清理7天前的日志
0 1 * * * find ~ -name "cryptosignal_*.log" -mtime +7 -delete
```

---

### 步骤3: 拉取最新代码

**说明**: 获取包含所有修复的最新代码

```bash
# 切换到项目目录
cd ~/cryptosignal

# 拉取最新代码
git fetch origin claude/audit-system-compliance-011CUkshDA3WNmJWFjbAEEn8
git checkout claude/audit-system-compliance-011CUkshDA3WNmJWFjbAEEn8
git pull origin claude/audit-system-compliance-011CUkshDA3WNmJWFjbAEEn8

# 验证代码已更新
git log --oneline -5
```

**预期输出**（应该看到最新的提交）：
```
bb14bd5 feat: 添加自动重启脚本
84998c7 docs: 添加订单簿数据更新优化方案文档
4bfdaca docs: 添加完整数据更新时间表文档
...
```

---

### 步骤4: 给脚本添加执行权限

**说明**: 确保自动重启脚本和部署脚本可执行

```bash
# 添加执行权限
chmod +x ~/cryptosignal/auto_restart.sh
chmod +x ~/cryptosignal/deploy_and_run.sh

# 验证权限
ls -lh ~/cryptosignal/*.sh
```

**预期输出**（应该看到 -rwxr-xr-x）：
```
-rwxr-xr-x 1 cryptosignal cryptosignal  1.2K Nov  3 23:50 auto_restart.sh
-rwxr-xr-x 1 cryptosignal cryptosignal 18.3K Nov  3 12:31 deploy_and_run.sh
```

---

### 步骤5: 首次启动系统

**说明**: 使用自动重启脚本启动系统，系统将在后台运行

#### 方式1: 使用auto_restart.sh（推荐）

```bash
# 执行自动重启脚本
~/cryptosignal/auto_restart.sh
```

**预期输出**：
```
==========================================
🔄 CryptoSignal 自动重启
时间: Mon Nov  3 23:55:00 UTC 2025
==========================================
📍 步骤1: 停止旧进程...
   没有运行中的进程
📍 步骤2: 拉取最新代码...
Already up to date.
📍 步骤3: 重新启动系统...
==========================================

✅ 重启完成！进程ID: 12345
📋 查看日志: tail -f ~/cryptosignal_20251103_235500.log
```

#### 方式2: 直接使用deploy_and_run.sh

```bash
# 如果您想直接运行部署脚本（不推荐，因为不会后台运行）
cd ~/cryptosignal
nohup ./deploy_and_run.sh > ~/cryptosignal_$(date +%Y%m%d_%H%M%S).log 2>&1 &

# 记录进程ID
echo "进程ID: $!"
```

---

### 步骤6: 验证运行状态

**说明**: 确认系统正在运行

#### 6.1 检查进程

```bash
# 查看cryptosignal进程
ps aux | grep python | grep cryptosignal | grep -v grep

# 如果看到类似以下输出 → 运行成功 ✅
# cryptosignal  12345  5.0  2.1 456789 123456 ?  S  23:55  0:15 python3 ...
```

#### 6.2 查看实时日志

```bash
# 查看最新的日志文件
ls -lt ~/cryptosignal_*.log | head -1

# 实时查看日志（按Ctrl+C停止）
tail -f ~/cryptosignal_$(date +%Y%m%d)_*.log

# 或者查看最新的一个
tail -f $(ls -t ~/cryptosignal_*.log | head -1)
```

**预期日志内容**（应该看到初始化过程）：
```
==========================================
🚀 CryptoSignal v6.6 全自动部署并运行
==========================================
...
🚀 初始化优化批量扫描器...
1️⃣  初始化Binance客户端...
✅ 客户端初始化完成
2️⃣  获取高流动性USDT合约币种...
✅ 筛选出 200 个高波动币种
3️⃣  批量初始化K线缓存...
...
✅ 优化批量扫描器初始化完成！
🔍 开始批量扫描...
```

#### 6.3 检查系统是否在扫描

```bash
# 等待2-3分钟后，再次查看日志
tail -100 $(ls -t ~/cryptosignal_*.log | head -1)

# 应该看到扫描输出
# 🔍 开始批量扫描...
# 📈 [Layer 1] 更新实时价格...
# ✅ [Layer 1] 价格更新完成: 12个K线缓存已更新
# ...
```

---

### 步骤7: 测试自动重启功能（可选）

**说明**: 验证定时任务是否正确配置

```bash
# 查看crontab配置
crontab -l

# 查看cron服务状态
systemctl status cron

# 或者（某些系统）
service cron status

# 手动触发一次自动重启（测试用）
~/cryptosignal/auto_restart.sh
```

---

## ✅ 部署完成检查清单

完成以上步骤后，确认以下内容：

```bash
# 1. 检查进程运行
ps aux | grep cryptosignal | grep -v grep
# ✅ 应该有输出

# 2. 检查日志文件
ls -lh ~/cryptosignal_*.log
# ✅ 应该有日志文件

# 3. 检查日志内容
tail -50 $(ls -t ~/cryptosignal_*.log | head -1)
# ✅ 应该看到扫描输出

# 4. 检查crontab
crontab -l
# ✅ 应该只有2行任务

# 5. 检查定时任务
grep CRON /var/log/syslog | tail -5
# ✅ 应该看到cron执行记录（如果已经触发过）
```

---

## 🎯 系统运行机制说明

### 正常运行流程

```
初始启动：
├─ 执行 auto_restart.sh
├─ 系统在后台运行
└─ 持续扫描（每次<1秒）

自动重启：
├─ 每2小时（00:00, 02:00, ...）
├─ cron触发 auto_restart.sh
├─ 停止旧进程
├─ 拉取最新代码
├─ 重新启动
└─ 继续运行
```

### 数据更新机制

```
每次扫描：
├─ Layer 1: 更新价格（0.2秒）
├─ CVD: 实时计算
└─ 现货价格: 实时获取

智能触发：
├─ Layer 2: K线更新（02/17/32/47分，05/07分）
└─ Layer 3: 市场数据更新（00/30分）

定时重启：
└─ 每2小时刷新所有数据（包括订单簿）
```

---

## 🔧 常用维护命令

### 查看系统状态

```bash
# 查看进程
ps aux | grep cryptosignal

# 查看最新日志
tail -f $(ls -t ~/cryptosignal_*.log | head -1)

# 查看所有日志文件
ls -lh ~/cryptosignal_*.log
```

### 手动重启系统

```bash
# 方式1: 使用自动重启脚本
~/cryptosignal/auto_restart.sh

# 方式2: 手动操作
pkill -f "python.*cryptosignal"
cd ~/cryptosignal
git pull origin claude/audit-system-compliance-011CUkshDA3WNmJWFjbAEEn8
nohup ./deploy_and_run.sh > ~/cryptosignal_$(date +%Y%m%d_%H%M%S).log 2>&1 &
```

### 停止系统

```bash
# 停止所有进程
pkill -f "python.*cryptosignal"
pkill -f "deploy_and_run"

# 验证已停止
ps aux | grep cryptosignal
```

### 清理日志

```bash
# 查看日志占用空间
du -sh ~/cryptosignal_*.log

# 删除7天前的日志
find ~ -name "cryptosignal_*.log" -mtime +7 -delete

# 删除所有日志（慎用）
rm -f ~/cryptosignal_*.log
```

---

## ⚠️ 故障排查

### 问题1: 进程没有启动

```bash
# 检查脚本权限
ls -lh ~/cryptosignal/*.sh

# 如果没有x权限，添加
chmod +x ~/cryptosignal/auto_restart.sh
chmod +x ~/cryptosignal/deploy_and_run.sh

# 手动运行查看错误
~/cryptosignal/auto_restart.sh
```

### 问题2: crontab没有执行

```bash
# 检查cron服务
systemctl status cron

# 如果未运行，启动
sudo systemctl start cron

# 查看cron日志
grep CRON /var/log/syslog | tail -20
```

### 问题3: 日志中有错误

```bash
# 查看错误信息
tail -100 $(ls -t ~/cryptosignal_*.log | head -1) | grep -i error

# 常见错误解决：
# - "No module named xxx" → pip3 install -r requirements.txt
# - "Permission denied" → chmod +x 脚本名
# - "Connection refused" → 检查网络连接
```

---

## 📊 监控指标

### 每日检查（可选）

```bash
# 查看今天的重启次数
grep "🔄 CryptoSignal 自动重启" ~/cryptosignal_$(date +%Y%m%d)*.log | wc -l
# 应该是：(当前小时/2) 次

# 查看扫描成功率
grep "✅ 批量扫描完成" ~/cryptosignal_$(date +%Y%m%d)*.log | wc -l

# 查看发现的信号数
grep "发现信号:" ~/cryptosignal_$(date +%Y%m%d)*.log
```

---

## 🎉 部署成功！

如果以上所有步骤都正常，您的系统现在：

✅ 在后台持续运行
✅ 每次扫描 <1秒
✅ 每2小时自动重启
✅ 自动拉取最新代码
✅ 自动清理旧日志
✅ 数据保持新鲜（订单簿最多2小时）
✅ 7×24小时无人值守运行

**您可以放心关闭SSH连接了！**

---

**文档维护者**: Claude AI
**最后更新**: 2025-11-03
**适用版本**: CryptoSignal v6.6
