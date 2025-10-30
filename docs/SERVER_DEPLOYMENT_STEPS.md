# 服务器部署和测试步骤

**目标**: 在服务器上部署最新代码并测试统一数据管理器

**部署时间**: 约10-15分钟
**测试时间**: 约5-10分钟
**更新日期**: 2025-10-29

---

## 📋 前置检查

### 1. 确认服务器信息

```bash
# SSH连接到服务器
ssh user@your-server-ip

# 确认Python版本（需要3.11+）
python3 --version

# 确认Git已安装
git --version

# 确认当前工作目录
pwd
```

---

## 🧹 第一步：清理服务器缓存

### 1.1 停止所有运行中的CryptoSignal进程

```bash
# 查找运行中的进程
ps aux | grep -E "realtime_signal_scanner|auto_trader|cryptosignal"

# 如果有运行中的进程，记录PID并停止
kill -9 <PID>

# 或者使用pkill
pkill -f realtime_signal_scanner
pkill -f auto_trader
```

### 1.2 清理Python缓存

```bash
# 进入项目目录
cd ~/cryptosignal

# 清理Python缓存文件
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -type f -name "*.pyc" -delete
find . -type f -name "*.pyo" -delete

echo "✅ Python缓存已清理"
```

### 1.3 清理旧的数据缓存（可选）

```bash
# 如果有临时数据文件，可以清理
# 注意：不要删除数据库文件（*.db）

# 清理日志文件（可选）
# rm -f logs/*.log

echo "✅ 缓存清理完成"
```

---

## 📥 第二步：拉取最新代码

### 2.1 查看当前分支状态

```bash
cd ~/cryptosignal

# 查看当前分支
git branch

# 查看状态
git status

# 查看最近的提交
git log --oneline -5
```

### 2.2 拉取最新代码

```bash
# 切换到目标分支（如果不在该分支）
git checkout claude/analyze-system-functionality-011CUbfJcoGsD3prWPkay6LE

# 拉取最新代码
git pull origin claude/analyze-system-functionality-011CUbfJcoGsD3prWPkay6LE

# 确认最新提交包含统一数据管理器
git log --oneline -1
# 应该看到: d53e77f feat: 实现统一数据管理器 - WebSocket+REST有机结合
```

### 2.3 验证新文件已存在

```bash
# 检查新文件
ls -lh ats_core/data/unified_data_manager.py
ls -lh docs/UNIFIED_DATA_MANAGER_DESIGN.md

# 应该看到两个文件
# ats_core/data/unified_data_manager.py (~40KB)
# docs/UNIFIED_DATA_MANAGER_DESIGN.md (~30KB)

echo "✅ 代码拉取完成"
```

---

## 🔧 第三步：更新依赖

### 3.1 检查依赖

```bash
cd ~/cryptosignal

# 查看requirements.txt
cat requirements.txt

# 确认aiohttp、websockets等依赖已列出
```

### 3.2 安装/更新依赖

```bash
# 激活虚拟环境（如果使用）
# source venv/bin/activate

# 更新pip
pip3 install --upgrade pip

# 安装依赖
pip3 install -r requirements.txt

# 验证关键依赖
python3 -c "import aiohttp; print(f'aiohttp: {aiohttp.__version__}')"
python3 -c "import websockets; print(f'websockets: {websockets.__version__}')"
python3 -c "import pandas; print(f'pandas: {pandas.__version__}')"
python3 -c "import numpy; print(f'numpy: {numpy.__version__}')"

echo "✅ 依赖安装完成"
```

---

## ✅ 第四步：验证代码完整性

### 4.1 语法检查

```bash
cd ~/cryptosignal

# 检查新的统一数据管理器
python3 -m py_compile ats_core/data/unified_data_manager.py
echo "✅ unified_data_manager.py 语法正确"

# 检查主运行脚本
python3 -m py_compile scripts/realtime_signal_scanner.py
echo "✅ realtime_signal_scanner.py 语法正确"

# 检查核心模块
python3 -m py_compile ats_core/pipeline/batch_scan_optimized.py
echo "✅ batch_scan_optimized.py 语法正确"
```

### 4.2 导入测试

```bash
# 测试统一数据管理器导入
python3 -c "
from ats_core.data.unified_data_manager import get_data_manager
dm = get_data_manager()
print('✅ UnifiedDataManager 导入成功')
print(f'   类型: {type(dm).__name__}')
"

# 测试其他关键模块
python3 -c "
from ats_core.pipeline.batch_scan_optimized import OptimizedBatchScanner
from ats_core.outputs.publisher import telegram_send
from ats_core.logging import log
print('✅ 所有核心模块导入成功')
"
```

---

## 🧪 第五步：测试统一数据管理器

### 5.1 运行基础测试（不连接币安）

```bash
cd ~/cryptosignal

# 运行统一数据管理器的测试代码
# 注意：这会尝试连接币安API，如果没有配置API密钥可能会失败
# 但至少可以测试代码是否能运行

python3 -m ats_core.data.unified_data_manager

# 预期输出：
# ======================================================================
# 统一数据管理器测试
# ======================================================================
# 🚀 初始化统一数据管理器
# ...
```

**注意**: 如果没有配置Binance API密钥，部分功能会失败，但这是正常的。主要看代码是否能运行到初始化阶段。

### 5.2 配置环境变量

```bash
# 设置Telegram配置（必需）
export TELEGRAM_BOT_TOKEN="7545580872:AAF7HzkHA4LRQUiOZngUgL39epuGVeEta70"
export TELEGRAM_CHAT_ID="-1003142003085"

# 设置Binance API配置（可选，但建议配置）
# export BINANCE_API_KEY="your_binance_api_key"
# export BINANCE_API_SECRET="your_binance_api_secret"

# 验证环境变量
echo "Telegram Token: ${TELEGRAM_BOT_TOKEN:0:20}..."
echo "Telegram Chat ID: $TELEGRAM_CHAT_ID"
```

### 5.3 快速测试（扫描5个币种）

```bash
cd ~/cryptosignal

# 运行快速测试（只扫描5个币种，不发送Telegram）
python3 scripts/realtime_signal_scanner.py \
    --max-symbols 5 \
    --no-telegram \
    --min-score 50

# 预期输出：
# ✅ 信号扫描器创建成功
# 🚀 初始化WebSocket信号扫描器
# 1️⃣  初始化Binance客户端...
# 2️⃣  获取高流动性USDT合约币种...
# 3️⃣  批量初始化K线缓存...
# ...
# 🔍 第 1 次扫描
# 📊 扫描结果
#    总扫描: 5 个币种
#    耗时: 12.5秒
#    发现信号: 2 个
#    Prime信号: 1 个
```

**如果测试成功，继续下一步。如果失败，查看错误信息。**

---

## 🚀 第六步：运行完整系统

### 6.1 单次扫描（发送到Telegram）

```bash
cd ~/cryptosignal

# 设置环境变量
export TELEGRAM_BOT_TOKEN="7545580872:AAF7HzkHA4LRQUiOZngUgL39epuGVeEta70"
export TELEGRAM_CHAT_ID="-1003142003085"

# 单次扫描（所有币种）
python3 scripts/realtime_signal_scanner.py \
    --min-score 70

# 这会：
# 1. 初始化140个高流动性币种（约2-3分钟）
# 2. 执行一次完整扫描（约12-15秒）
# 3. 发送Prime信号到Telegram群组
```

### 6.2 定期扫描（每5分钟）

```bash
cd ~/cryptosignal

# 设置环境变量
export TELEGRAM_BOT_TOKEN="7545580872:AAF7HzkHA4LRQUiOZngUgL39epuGVeEta70"
export TELEGRAM_CHAT_ID="-1003142003085"

# 定期扫描（每5分钟）
python3 scripts/realtime_signal_scanner.py \
    --interval 300 \
    --min-score 70

# 按Ctrl+C停止
```

### 6.3 后台运行（推荐）

```bash
cd ~/cryptosignal

# 使用nohup后台运行
nohup python3 scripts/realtime_signal_scanner.py \
    --interval 300 \
    --min-score 70 \
    > logs/scanner.log 2>&1 &

# 记录进程ID
echo $! > scanner.pid

# 查看日志
tail -f logs/scanner.log

# 停止后台进程
kill $(cat scanner.pid)
```

---

## 📊 第七步：监控和验证

### 7.1 查看日志

```bash
# 实时查看日志
tail -f logs/scanner.log

# 查看最近100行
tail -100 logs/scanner.log

# 搜索错误
grep -i error logs/scanner.log
grep -i "❌" logs/scanner.log
```

### 7.2 检查Telegram群组

- 打开Telegram群组："链上望远镜"
- 确认收到启动通知
- 确认收到Prime信号（如果有）

### 7.3 检查进程状态

```bash
# 查看运行中的进程
ps aux | grep realtime_signal_scanner

# 查看资源占用
top -p $(cat scanner.pid)
```

---

## 🔍 故障排查

### 问题1: 导入错误 (ModuleNotFoundError)

```bash
# 解决方案：重新安装依赖
pip3 install -r requirements.txt

# 确认Python路径
which python3
python3 -c "import sys; print(sys.path)"
```

### 问题2: Telegram发送失败

```bash
# 检查环境变量
echo $TELEGRAM_BOT_TOKEN
echo $TELEGRAM_CHAT_ID

# 测试Telegram连接
python3 -c "
from ats_core.outputs.publisher import telegram_send
telegram_send('测试消息')
print('✅ Telegram发送成功')
"
```

### 问题3: Binance API错误

```bash
# 检查API密钥配置
echo $BINANCE_API_KEY
echo $BINANCE_API_SECRET

# 测试API连接
python3 -c "
from ats_core.sources.binance import get_klines
klines = get_klines('BTCUSDT', '1h', 10)
print(f'✅ 获取到 {len(klines)} 根K线')
"
```

### 问题4: 内存不足

```bash
# 检查内存使用
free -h

# 如果内存不足，减少扫描币种数
python3 scripts/realtime_signal_scanner.py \
    --max-symbols 50 \
    --interval 300
```

---

## 🧹 清理和重置

### 重置系统

```bash
# 停止所有进程
pkill -f realtime_signal_scanner

# 清理缓存
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null

# 重新拉取代码
git reset --hard
git pull origin claude/analyze-system-functionality-011CUbfJcoGsD3prWPkay6LE

# 重新安装依赖
pip3 install -r requirements.txt
```

---

## ✅ 验证清单

部署完成后，确认以下项目：

- [ ] 代码已拉取到最新版本 (commit d53e77f)
- [ ] 依赖已安装（aiohttp, websockets等）
- [ ] 语法检查通过
- [ ] 导入测试通过
- [ ] 环境变量已配置
- [ ] 快速测试成功（5个币种）
- [ ] Telegram通知收到
- [ ] 完整扫描成功
- [ ] 日志正常输出
- [ ] 进程稳定运行

---

## 📝 下一步建议

1. **监控24小时**：确保系统稳定运行
2. **优化参数**：根据信号质量调整 `--min-score`
3. **实现WebSocket**：进一步优化性能（可选）
4. **数据库持久化**：保存信号历史
5. **性能分析**：对比新旧架构性能

---

## 🆘 需要帮助？

如果遇到问题，提供以下信息：

1. 错误日志（最后100行）
2. Python版本
3. 依赖版本（`pip3 list`）
4. 系统信息（`uname -a`）
5. 内存使用（`free -h`）

---

**文档版本**: v1.0
**更新日期**: 2025-10-29
**适用分支**: claude/analyze-system-functionality-011CUbfJcoGsD3prWPkay6LE
