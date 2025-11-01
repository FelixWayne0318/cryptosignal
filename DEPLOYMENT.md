# CryptoSignal v6.0 部署和运行指南

## 📋 目录

1. [系统要求](#系统要求)
2. [首次部署](#首次部署)
3. [配置Telegram](#配置telegram)
4. [运行方式](#运行方式)
5. [更新代码](#更新代码)
6. [常见问题](#常见问题)

---

## 系统要求

- **操作系统**: Linux (Ubuntu 18.04+)
- **Python**: 3.8+
- **依赖包**: numpy, pandas, websockets, aiohttp
- **网络**: 稳定的互联网连接（访问Binance API和Telegram）

---

## 首次部署

### 步骤1: 克隆代码（如果还没有）

```bash
cd /home/user
git clone <your-repo-url> cryptosignal
cd cryptosignal
```

### 步骤2: 检查分支

```bash
# 查看当前分支
git branch

# 如果在claude分支上，拉取最新代码
git pull origin claude/review-system-overview-011CUfa54C3QqQuZNhcVBDgA

# 或者切换到main分支
# git checkout main
# git pull origin main
```

### 步骤3: 安装依赖

```bash
pip3 install numpy pandas websockets aiohttp scipy
```

### 步骤4: 赋予脚本执行权限

```bash
chmod +x deploy_and_run.sh
chmod +x start.sh
chmod +x test_scan.sh
```

---

## 配置Telegram

### 方法1: 使用配置文件（推荐）

创建配置文件：

```bash
mkdir -p config
nano config/telegram.json
```

填写以下内容：

```json
{
  "bot_token": "YOUR_BOT_TOKEN_HERE",
  "chat_id": "YOUR_CHAT_ID_HERE"
}
```

**获取Bot Token和Chat ID的方法**：

1. **创建Bot**：
   - 在Telegram中搜索 @BotFather
   - 发送 `/newbot` 创建新机器人
   - 按提示设置机器人名称和用户名
   - 获得Bot Token（形如：`123456789:ABCdefGHIjklMNOpqrsTUVwxyz`）

2. **获取Chat ID**：
   - 在Telegram中搜索你刚创建的机器人
   - 向机器人发送任意消息（如 `/start`）
   - 访问：`https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
   - 在返回的JSON中找到 `"chat":{"id":123456789}`
   - 这个id就是你的Chat ID

3. **填写配置**：
   ```json
   {
     "bot_token": "123456789:ABCdefGHIjklMNOpqrsTUVwxyz",
     "chat_id": "123456789"
   }
   ```

### 方法2: 使用环境变量

```bash
export TELEGRAM_BOT_TOKEN="your_bot_token_here"
export TELEGRAM_CHAT_ID="your_chat_id_here"
```

或添加到 `~/.bashrc`：

```bash
echo 'export TELEGRAM_BOT_TOKEN="your_bot_token_here"' >> ~/.bashrc
echo 'export TELEGRAM_CHAT_ID="your_chat_id_here"' >> ~/.bashrc
source ~/.bashrc
```

---

## 运行方式

### 方式1: 使用完整部署脚本（推荐）

```bash
./deploy_and_run.sh
```

**功能**：
- ✅ 自动拉取最新代码
- ✅ 检查Python环境和依赖
- ✅ 验证Telegram配置
- ✅ 提供5种运行模式选择

**运行模式**：
1. 测试模式（20个币种，约3分钟）
2. 完整模式（200个币种，约15分钟）
3. 定期扫描（每5分钟）
4. 定期扫描（每15分钟）
5. 自定义参数

---

### 方式2: 快速启动（定期扫描）

```bash
./start.sh
```

**功能**：
- 自动拉取最新代码
- 每5分钟扫描一次
- 最低分数70分

---

### 方式3: 测试扫描

```bash
./test_scan.sh
```

**功能**：
- 仅扫描20个币种（快速测试）
- 验证系统是否正常运行

---

### 方式4: 直接运行Python脚本

#### 单次扫描（测试）

```bash
python3 scripts/realtime_signal_scanner.py --max-symbols 20
```

#### 单次扫描（完整）

```bash
python3 scripts/realtime_signal_scanner.py
```

#### 定期扫描（每5分钟）

```bash
python3 scripts/realtime_signal_scanner.py --interval 300
```

#### 定期扫描（每15分钟）

```bash
python3 scripts/realtime_signal_scanner.py --interval 900
```

#### 自定义参数

```bash
python3 scripts/realtime_signal_scanner.py \
  --interval 600 \          # 每10分钟扫描
  --min-score 60 \          # 最低分数60
  --max-symbols 100         # 最多扫描100个币种（测试用）
```

#### 不发送Telegram（仅测试）

```bash
python3 scripts/realtime_signal_scanner.py --no-telegram
```

---

## 更新代码

### 方法1: 使用部署脚本（推荐）

```bash
./deploy_and_run.sh
```

脚本会自动拉取最新代码。

### 方法2: 手动更新

```bash
cd /home/user/cryptosignal

# 查看当前分支
git branch

# 拉取最新代码
git pull origin <your-branch-name>

# 或者拉取所有分支
git fetch --all
```

---

## 运行参数说明

### 完整参数列表

```bash
python3 scripts/realtime_signal_scanner.py [选项]
```

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `--interval` | int | 0 | 扫描间隔（秒），0=单次扫描 |
| `--min-score` | int | 70 | 最低信号分数（40-90） |
| `--max-symbols` | int | 200 | 最大扫描币种数（测试用） |
| `--no-telegram` | flag | False | 不发送Telegram通知 |

### 推荐配置

**生产环境**（长期运行）：
```bash
python3 scripts/realtime_signal_scanner.py --interval 300 --min-score 70
```

**测试环境**（验证系统）：
```bash
python3 scripts/realtime_signal_scanner.py --max-symbols 20 --min-score 60
```

**高频扫描**（捕捉更多信号）：
```bash
python3 scripts/realtime_signal_scanner.py --interval 180 --min-score 65
```

**严格筛选**（仅高质量信号）：
```bash
python3 scripts/realtime_signal_scanner.py --interval 600 --min-score 80
```

---

## 系统性能

### 初始化阶段

- **首次运行**: 3-4分钟（构建WebSocket缓存）
- **后续启动**: 3-4分钟（重建缓存）
- **内存占用**: 约200-300MB

### 扫描阶段

- **20个币种**: 约1-2秒
- **200个币种**: 约12-15秒
- **API调用**: 0次（使用WebSocket缓存）
- **网络流量**: 极低（仅WebSocket连接）

---

## 后台运行

### 使用nohup

```bash
nohup ./start.sh > logs/scanner.log 2>&1 &
```

### 使用screen

```bash
# 创建新会话
screen -S cryptosignal

# 运行扫描器
./start.sh

# 按Ctrl+A然后按D分离会话
# 重新连接：screen -r cryptosignal
```

### 使用tmux

```bash
# 创建新会话
tmux new -s cryptosignal

# 运行扫描器
./start.sh

# 按Ctrl+B然后按D分离会话
# 重新连接：tmux attach -t cryptosignal
```

### 使用systemd（推荐）

创建服务文件：

```bash
sudo nano /etc/systemd/system/cryptosignal.service
```

填写以下内容：

```ini
[Unit]
Description=CryptoSignal v6.0 Real-time Scanner
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/home/user/cryptosignal
ExecStart=/usr/bin/python3 /home/user/cryptosignal/scripts/realtime_signal_scanner.py --interval 300 --min-score 70
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable cryptosignal
sudo systemctl start cryptosignal

# 查看状态
sudo systemctl status cryptosignal

# 查看日志
sudo journalctl -u cryptosignal -f
```

---

## 常见问题

### Q1: Telegram配置错误

**错误**：`Telegram配置未找到`

**解决**：
1. 确认 `config/telegram.json` 文件存在
2. 确认文件内容格式正确（JSON格式）
3. 确认bot_token和chat_id已填写

### Q2: WebSocket连接失败

**错误**：`WebSocket连接超时`

**解决**：
1. 检查网络连接
2. 确认能访问Binance API（`curl https://fapi.binance.com/fapi/v1/ping`）
3. 检查防火墙设置

### Q3: 初始化时间过长

**现象**：初始化超过10分钟

**解决**：
1. 正常情况3-4分钟，超过10分钟说明网络慢
2. 可以使用 `--max-symbols 20` 测试（约30秒初始化）
3. 检查网络质量

### Q4: 没有收到信号

**可能原因**：
1. 当前市场没有符合条件的信号（正常现象）
2. `--min-score` 设置过高（降低到60试试）
3. Telegram配置错误（检查bot是否能发消息）

**验证**：
```bash
# 使用测试模式，降低分数
python3 scripts/realtime_signal_scanner.py --max-symbols 20 --min-score 40
```

### Q5: 多空对称性问题

**现状**：V和O因子存在多空不对称问题

**解决方案**：
1. 短期：已记录问题，暂无影响实际使用
2. 长期：需要修改volume.py和open_interest.py代码
3. 详见：`docs/archive/SYMMETRY_ANALYSIS_REPORT.md`

---

## 监控和日志

### 查看实时日志

```bash
# 如果使用systemd
sudo journalctl -u cryptosignal -f

# 如果使用nohup
tail -f logs/scanner.log

# 如果使用screen/tmux
# 重新连接到会话即可查看
```

### 日志位置

- **控制台输出**: 标准输出（stdout）
- **Telegram通知**: 自动发送到配置的Chat
- **系统日志**: 如果使用systemd，在journalctl中

---

## 系统架构

### 核心组件

- **batch_scan_optimized.py**: WebSocket批量扫描引擎（0 API调用）
- **realtime_signal_scanner.py**: 实时信号扫描器（主程序）
- **telegram_fmt.py**: Telegram消息格式化
- **四门系统**: DataQual/EV/执行/概率验证

### 信号流程

```
1. WebSocket缓存 (200个币种，实时更新)
   ↓
2. 批量分析 (analyze_symbol，12-15秒)
   ↓
3. 四门验证 (DataQual/EV/执行/概率)
   ↓
4. Prime信号过滤 (min_score筛选)
   ↓
5. Telegram发送 (render_trade格式化)
```

---

## 版本信息

- **系统版本**: v6.0 newstandards整合版
- **分支**: `claude/review-system-overview-011CUfa54C3QqQuZNhcVBDgA`
- **核心特性**:
  - 9因子方向评分（T/M/C/S/V/O/L/B/Q/I）
  - F/I调制器（不参与评分）
  - 四门验证系统
  - WebSocket零API调用
  - 增强型监控输出（可选）

---

## 下一步

1. **测试系统**: `./test_scan.sh`
2. **验证配置**: 检查是否收到Telegram通知
3. **正式运行**: `./start.sh` 或使用systemd
4. **监控日志**: 观察扫描结果和信号质量

如有问题，请查看 `docs/` 目录中的详细文档。
