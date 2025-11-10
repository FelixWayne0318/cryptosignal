# Vultr服务器完整部署指南

## 📋 文件说明

- **`vultr_deploy_complete.sh`** - 完整部署脚本（包含所有私有信息）
- 本文件 - 使用说明

---

## ⚠️ 安全警告

**此脚本包含以下敏感信息，严禁提交到Git：**

- GitHub Personal Access Token
- Binance API Key & Secret
- Telegram Bot Token & Chat ID

**使用建议：**
1. ✅ 保存在本地电脑（安全）
2. ✅ 需要时复制到服务器
3. ✅ 使用后立即删除
4. ❌ 不要提交到Git
5. ❌ 不要发送给他人
6. ❌ 不要保存在云盘

---

## 🚀 快速部署（3步）

### 方法1: 复制粘贴（推荐）

```bash
# 1. 在本地电脑复制脚本内容
# 2. SSH登录到Vultr服务器
ssh root@你的服务器IP

# 3. 创建并粘贴脚本
cat > deploy.sh
# 粘贴脚本内容（Ctrl+V 或 右键粘贴）
# 按 Ctrl+D 保存

# 4. 执行部署
chmod +x deploy.sh
./deploy.sh

# 5. 部署完成后删除脚本
rm deploy.sh
```

### 方法2: SCP上传

```bash
# 在本地电脑执行
scp vultr_deploy_complete.sh root@你的服务器IP:~/deploy.sh

# SSH登录服务器
ssh root@你的服务器IP

# 执行部署
chmod +x deploy.sh
./deploy.sh

# 部署完成后删除
rm deploy.sh
```

### 方法3: 下载并编辑（如果你把脚本放在安全的云存储）

```bash
# SSH登录服务器
ssh root@你的服务器IP

# 下载脚本（从你的私有云存储）
wget https://你的私有链接/deploy.sh
# 或
curl -O https://你的私有链接/deploy.sh

# 执行部署
chmod +x deploy.sh
./deploy.sh

# 部署完成后删除
rm deploy.sh
```

---

## 📊 部署过程说明

脚本会自动完成以下10个步骤：

| 步骤 | 说明 | 预计时间 |
|------|------|----------|
| 0️⃣ | 环境检查（Python, pip, git） | 30秒 |
| 1️⃣ | 停止旧进程 | 10秒 |
| 2️⃣ | 备份旧配置和数据 | 20秒 |
| 3️⃣ | 克隆GitHub仓库 | 1-2分钟 |
| 4️⃣ | 切换到目标分支 | 10秒 |
| 5️⃣ | 配置GitHub访问权限 | 5秒 |
| 6️⃣ | 配置Binance API | 5秒 |
| 7️⃣ | 配置Telegram通知 | 5秒 |
| 8️⃣ | 创建自动重启脚本 | 5秒 |
| 9️⃣ | 配置定时任务 | 10秒 |
| 🔟 | 验证配置完整性 | 20秒 |

**总计：约3-5分钟**

---

## ✅ 部署后验证

部署完成后，系统会显示验证结果。确保以下项目全部通过：

### 1. 配置文件检查
```
✅ GitHub配置
✅ Binance配置
✅ Telegram配置
✅ 重启脚本
✅ 启动脚本
```

### 2. 文件权限检查
```
✅ .cryptosignal-github.env: 600 ✓
✅ binance_credentials.json: 600 ✓
✅ telegram.json: 600 ✓
```

### 3. Git配置检查
```
✅ user.name: FelixWayne0318
✅ user.email: felixwayne0318@gmail.com
```

### 4. 定时任务检查
```
✅ 自动重启任务已配置
✅ 日志清理任务已配置
```

### 5. 代码版本检查
```
✅ 分支: claude/system-refactor-v7.2-011CUyBts14z3AdVhv9BSubr
✅ 最新提交: 4e088b4 feat: 完成P1.2回测验证基础设施与文档
```

### 6. 系统文件检查
```
✅ scripts/realtime_signal_scanner.py
✅ ats_core/pipeline/analyze_symbol_v72.py
✅ ats_core/outputs/telegram_fmt.py
✅ setup.sh
```

---

## 🎯 启动系统

部署完成后，启动系统：

```bash
cd ~/cryptosignal
./setup.sh
```

**首次启动会：**
1. 安装Python依赖包（约3-5分钟）
2. 初始化数据库
3. 连接Binance WebSocket
4. 开始实时扫描
5. 发送Telegram启动通知

---

## 📊 监控系统运行

### 查看实时日志

```bash
# 实时跟踪日志
tail -f ~/cryptosignal/cryptosignal.log

# 查看最近100行
tail -n 100 ~/cryptosignal/cryptosignal.log

# 搜索错误
grep -i error ~/cryptosignal/cryptosignal.log
```

### 查看进程状态

```bash
# 查看Python进程
ps aux | grep python | grep cryptosignal

# 查看进程详情
ps aux | grep realtime_signal_scanner
```

### 查看定时任务

```bash
# 查看所有定时任务
crontab -l

# 查看自动重启日志
tail -f ~/cryptosignal/auto_restart.log
```

### 手动重启系统

```bash
# 方法1: 使用重启脚本
~/cryptosignal/auto_restart.sh

# 方法2: 手动停止再启动
pkill -f "python.*cryptosignal"
cd ~/cryptosignal && ./setup.sh
```

---

## 🔧 常见问题处理

### 问题1: Binance API返回403 Forbidden

**原因：** 服务器IP未在Binance API白名单中

**解决：**
```bash
# 1. 查看当前服务器IP
curl ifconfig.me

# 2. 登录Binance账户
# 访问: https://www.binance.com/en/my/settings/api-management

# 3. 编辑API Key，添加当前IP到白名单
```

### 问题2: Git拉取代码失败

**原因：** GitHub token过期或网络问题

**解决：**
```bash
# 测试GitHub连接
git ls-remote https://github.com/FelixWayne0318/cryptosignal.git

# 如果失败，更新token
vim ~/.cryptosignal-github.env
# 修改GITHUB_TOKEN

# 重新配置Git凭证
source ~/.cryptosignal-github.env
echo "https://$GIT_USER_NAME:$GITHUB_TOKEN@github.com" > ~/.git-credentials
```

### 问题3: Telegram通知未收到

**原因：** Bot token错误或Chat ID错误

**解决：**
```bash
# 测试Telegram Bot
curl -X POST "https://api.telegram.org/bot你的BOT_TOKEN/sendMessage" \
  -d "chat_id=你的CHAT_ID" \
  -d "text=测试消息"

# 如果失败，检查配置
cat ~/cryptosignal/config/telegram.json

# 修改配置
vim ~/cryptosignal/config/telegram.json
```

### 问题4: Python依赖安装失败

**原因：** 网络问题或依赖冲突

**解决：**
```bash
# 使用国内镜像源
pip3 install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 升级pip
pip3 install --upgrade pip

# 清除缓存重试
pip3 cache purge
pip3 install -r requirements.txt
```

### 问题5: 定时任务未执行

**原因：** cron服务未运行或脚本权限问题

**解决：**
```bash
# 检查cron服务
sudo service cron status

# 如果未运行，启动cron
sudo service cron start

# 检查脚本权限
ls -la ~/cryptosignal/auto_restart.sh

# 修复权限
chmod +x ~/cryptosignal/auto_restart.sh

# 手动测试定时任务
~/cryptosignal/auto_restart.sh
```

---

## 📁 重要文件位置

| 文件/目录 | 路径 | 说明 |
|----------|------|------|
| **主目录** | `~/cryptosignal/` | 系统根目录 |
| **启动脚本** | `~/cryptosignal/setup.sh` | 系统启动入口 |
| **配置文件** | `~/cryptosignal/config/` | 所有配置文件 |
| **数据库** | `~/cryptosignal/data/` | SQLite数据库 |
| **日志文件** | `~/cryptosignal/cryptosignal.log` | 系统运行日志 |
| **GitHub配置** | `~/.cryptosignal-github.env` | GitHub访问配置 |
| **重启脚本** | `~/cryptosignal/auto_restart.sh` | 自动重启脚本 |
| **重启日志** | `~/cryptosignal/auto_restart.log` | 重启日志 |

---

## 🔄 更新系统代码

如果需要更新到最新代码：

```bash
cd ~/cryptosignal

# 停止系统
pkill -f "python.*cryptosignal"

# 拉取最新代码
git pull origin claude/system-refactor-v7.2-011CUyBts14z3AdVhv9BSubr

# 重新启动
./setup.sh
```

---

## 🗑️ 完全卸载

如果需要完全删除系统：

```bash
# 1. 停止所有进程
pkill -f "python.*cryptosignal"

# 2. 删除定时任务
crontab -l | grep -v "cryptosignal" | crontab -

# 3. 删除系统文件
rm -rf ~/cryptosignal
rm ~/.cryptosignal-github.env
rm ~/.git-credentials

# 4. 清理Git配置（如果不需要Git）
git config --global --unset user.name
git config --global --unset user.email
git config --global --unset credential.helper
```

---

## 📞 获取帮助

如果遇到问题，请检查：

1. **系统日志**
   ```bash
   tail -f ~/cryptosignal/cryptosignal.log
   ```

2. **自动重启日志**
   ```bash
   tail -f ~/cryptosignal/auto_restart.log
   ```

3. **系统状态**
   ```bash
   ps aux | grep python | grep cryptosignal
   ```

4. **配置文件**
   ```bash
   cat ~/cryptosignal/config/binance_credentials.json
   cat ~/cryptosignal/config/telegram.json
   ```

---

## 🎯 系统功能特性

部署完成后，系统将提供：

### 自动化功能
- ✅ 实时扫描10个主流币种
- ✅ 每5分钟生成交易信号
- ✅ Telegram实时推送通知
- ✅ 每2小时自动重启（确保稳定）
- ✅ 自动日志清理（保留7天）

### 信号质量
- ✅ 10因子综合评分
- ✅ 5道闸门质量控制
- ✅ 概率校准（真实胜率预测）
- ✅ 止损止盈自动计算
- ✅ 蓄势待发特别标记

### 数据持久化
- ✅ SQLite数据库存储所有信号
- ✅ 支持历史回测（需6个月数据）
- ✅ 完整的信号追踪系统
- ✅ 自动备份机制

---

## 📈 预期运行效果

**启动后1分钟：**
- ✅ 收到Telegram启动通知
- ✅ WebSocket连接建立
- ✅ 开始接收实时行情

**启动后5分钟：**
- ✅ 完成第一轮扫描
- ✅ 如有信号，推送到Telegram
- ✅ 信号存入数据库

**长期运行：**
- ✅ 每5分钟扫描一次
- ✅ 每2小时自动重启
- ✅ 每天清理旧日志
- ✅ 持续积累历史数据

---

## 🔐 安全最佳实践

1. **定期更换API密钥**
   - Binance API: 每3个月轮换一次
   - GitHub Token: 设置90天过期

2. **监控异常活动**
   - 定期检查Binance API使用记录
   - 监控Telegram Bot活动

3. **备份重要数据**
   ```bash
   # 备份数据库
   cp -r ~/cryptosignal/data ~/cryptosignal_backup_$(date +%Y%m%d)
   ```

4. **限制服务器访问**
   - 使用SSH密钥认证
   - 禁用root密码登录
   - 配置防火墙规则

---

## ✅ 部署清单

部署完成后，确认以下项目：

- [ ] 脚本执行无错误
- [ ] 所有验证项通过
- [ ] 系统成功启动
- [ ] 收到Telegram启动通知
- [ ] 日志文件正常生成
- [ ] 定时任务已配置
- [ ] 部署脚本已删除（安全）
- [ ] IP白名单已更新（如需要）

---

**部署脚本版本：** v7.2
**最后更新：** 2025-11-10
**维护者：** Claude AI

**祝部署顺利！** 🚀
