# 服务器一键配置指南

## 🚀 快速开始（新服务器）

### 完整一键配置命令

**保存到您的密码管理器或本地笔记**（不要提交到Git）：

```bash
# ==========================================
# CryptoSignal 服务器完整配置
# ==========================================

# 1. GitHub访问权限
cat > ~/.cryptosignal-github.env <<'EOF'
GIT_USER_NAME="FelixWayne0318"
GIT_USER_EMAIL="felixwayne0318@gmail.com"
GITHUB_TOKEN="YOUR_GITHUB_TOKEN_HERE"
EOF
chmod 600 ~/.cryptosignal-github.env

# 注：请将 YOUR_GITHUB_TOKEN_HERE 替换为您的真实Token
# Token格式：ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# 2. Binance API凭证
cat > ~/cryptosignal/config/binance_credentials.json <<'EOF'
{
  "_comment": "Binance Futures API凭证配置",
  "binance": {
    "api_key": "YOUR_BINANCE_API_KEY_HERE",
    "api_secret": "YOUR_SECRET_KEY_HERE",
    "testnet": false,
    "_security": "只读权限API Key"
  }
}
EOF
chmod 600 ~/cryptosignal/config/binance_credentials.json

# 3. Telegram通知配置（可选）
cat > ~/cryptosignal/config/telegram.json <<'EOF'
{
  "enabled": true,
  "bot_token": "7545580872:AAF7HzkHA4LRQUiOZngUgL39epuGVeEta70",
  "chat_id": "-1003142003085",
  "_comment": "量灵通@analysis_token_bot",
  "_channel": "链上望远镜"
}
EOF
chmod 600 ~/cryptosignal/config/telegram.json

# 4. 配置定时任务（每2小时重启）
(crontab -l 2>/dev/null; echo ""; echo "# CryptoSignal自动重启"; echo "0 */2 * * * ~/cryptosignal/auto_restart.sh"; echo "0 1 * * * find ~ -name 'cryptosignal_*.log' -mtime +7 -delete") | crontab -

echo "✅ 配置完成！现在运行: cd ~/cryptosignal && bash setup.sh"
```

---

## 📋 需要配置的内容清单

| 配置项 | 文件位置 | 是否在仓库 | 说明 |
|--------|---------|-----------|------|
| **GitHub访问** | `~/.cryptosignal-github.env` | ❌ 不在 | 自动推送报告到GitHub |
| **Binance API** | `config/binance_credentials.json` | ❌ 不在 | 获取币安行情数据（只读权限） |
| **Telegram通知** | `config/telegram.json` | ⚠️ **在仓库中** | 发送交易信号通知 |
| **定时任务** | `crontab` | ❌ 不在 | 每2小时自动重启 |

---

## ⚠️ 安全警告

### Telegram配置已暴露

**问题**：`config/telegram.json` 包含真实凭证且已提交到Git仓库
**风险**：Bot Token和Chat ID已公开可见
**状态**：Bot Token: `7545580872:AAF7HzkHA4LRQUiOZngUgL39epuGVeEta70`

**建议操作**：

1. **立即撤销旧Token**（推荐）⭐
   ```
   1. 与@BotFather对话
   2. 发送 /revoke
   3. 选择对应的Bot
   4. 生成新Token
   5. 更新配置文件
   ```

2. **限制Bot权限**
   - 确保Bot只能向特定群组/频道发送消息
   - 不要给Bot管理员权限

3. **从仓库中移除**（可选，但无法撤回历史）
   ```bash
   git rm config/telegram.json
   git commit -m "security: 移除telegram配置"
   git push
   ```

---

## 🔑 如何获取各项凭证

### 1. GitHub Personal Access Token

**步骤**：
1. 访问 https://github.com/settings/tokens
2. 点击 **Generate new token (classic)**
3. 设置Token名称：`Vultr Server - CryptoSignal`
4. 勾选权限：`repo`（完整仓库权限）
5. 设置过期时间：90天或更长
6. 点击 **Generate token**
7. **立即复制token**（关闭页面后无法再次查看！）

**示例格式**：`ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

---

### 2. Binance API凭证

**步骤**：
1. 登录 Binance，访问 https://www.binance.com/en/my/settings/api-management
2. 点击 **Create API**
3. 设置API名称：`CryptoSignal - Read Only`
4. 完成安全验证
5. **权限设置**（重要）：
   - ✅ 勾选 **Enable Reading**（读取）
   - ❌ 不要勾选 **Enable Trading**（交易）
   - ❌ 不要勾选 **Enable Withdrawals**（提现）
6. 复制 **API Key** 和 **Secret Key**

**示例格式**：
- API Key: `abcdefghijklmnopqrstuvwxyz1234567890`
- Secret: `xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

**安全提示**：
- ✅ 只需只读权限，不需要交易权限
- ✅ 建议添加IP白名单（仅允许Vultr服务器IP访问）
- ✅ 定期轮换API Key（建议每3个月）

---

### 3. Telegram Bot配置

**步骤**：
1. **创建Bot**
   - 与 @BotFather 对话
   - 发送 `/newbot`
   - 设置Bot名称和用户名
   - 复制Bot Token

2. **获取Chat ID**
   - 将Bot添加到群组/频道
   - 发送一条测试消息
   - 访问：`https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
   - 在JSON响应中找到 `"chat":{"id": YOUR_CHAT_ID}`

**示例格式**：
- Bot Token: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`
- Chat ID: `-1001234567890`（群组）或 `1234567890`（个人）

---

## 📝 配置步骤详解

### 方式1：交互式配置（推荐）

```bash
cd ~/cryptosignal
bash scripts/setup_server_config.sh
```

**优点**：
- ✅ 交互式向导，逐步提示
- ✅ 自动检测已有配置
- ✅ 自动设置文件权限
- ✅ 一次配置，永久有效

### 方式2：一键配置（快速）

复制上面的"完整一键配置命令"，替换YOUR_BINANCE_API_KEY等占位符，直接在服务器上执行。

---

## 🔄 分支切换配置说明

### 不需要重新配置的情况

| 操作 | 是否需要重新配置 | 原因 |
|------|----------------|------|
| **切换分支** | ❌ 不需要 | 配置文件在Home目录，独立于分支 |
| **更新代码** | ❌ 不需要 | 配置文件不在仓库中 |
| **git pull** | ❌ 不需要 | 配置文件已被.gitignore排除 |

### 需要重新配置的情况

| 操作 | 是否需要重新配置 | 原因 |
|------|----------------|------|
| **换服务器** | ✅ 需要 | 配置文件在本地，不跟随代码 |
| **删除配置文件** | ✅ 需要 | 误删需要恢复 |
| **Token过期** | ✅ 需要 | 更新过期的凭证 |

---

## 🔍 验证配置

### 检查所有配置文件

```bash
# 1. 检查GitHub配置
cat ~/.cryptosignal-github.env

# 2. 检查Binance配置（显示脱敏）
cat ~/cryptosignal/config/binance_credentials.json | grep api_key | head -c 50

# 3. 检查Telegram配置
cat ~/cryptosignal/config/telegram.json

# 4. 检查定时任务
crontab -l | grep cryptosignal
```

### 测试GitHub访问

```bash
cd ~/cryptosignal
bash test_github_access.sh
```

### 测试Binance API

```bash
cd ~/cryptosignal
python3 -c "
from ats_core.data.fetcher import BinanceFuturesDataFetcher
import json

with open('config/binance_credentials.json') as f:
    config = json.load(f)
    api_key = config['binance']['api_key']
    api_secret = config['binance']['api_secret']

fetcher = BinanceFuturesDataFetcher(api_key, api_secret)
print('✅ Binance API连接成功')
"
```

---

## 🛠️ 故障排查

### 问题1：GitHub推送失败

**错误**：`Authentication failed`

**解决**：
```bash
# 检查Token是否正确
cat ~/.cryptosignal-github.env | grep GITHUB_TOKEN

# 重新配置
bash scripts/setup_server_config.sh
```

### 问题2：Binance API错误

**错误**：`Invalid API Key`

**解决**：
```bash
# 检查API Key
cat ~/cryptosignal/config/binance_credentials.json

# 确认API Key权限（读取权限）
# 检查IP白名单（如果设置了）
```

### 问题3：Telegram发送失败

**错误**：`Unauthorized`

**解决**：
```bash
# 测试Bot Token
curl "https://api.telegram.org/bot<YOUR_TOKEN>/getMe"

# 如果Token无效，重新生成
# 与@BotFather对话，发送 /revoke 撤销旧Token
```

### 问题4：定时任务未执行

**解决**：
```bash
# 检查crontab配置
crontab -l

# 查看cron日志
grep CRON /var/log/syslog | tail -20

# 手动测试脚本
cd ~/cryptosignal
bash auto_restart.sh
```

---

## 📊 配置文件权限

**安全配置**（自动设置）：

```bash
chmod 600 ~/.cryptosignal-github.env
chmod 600 ~/cryptosignal/config/binance_credentials.json
chmod 600 ~/cryptosignal/config/telegram.json
```

**说明**：`600` = 只有当前用户可读写，其他用户无权限

---

## 💡 最佳实践

### 1. 密码管理

✅ **推荐**：
- 使用密码管理器（1Password, LastPass等）保存配置命令
- 本地笔记加密保存
- 团队协作使用共享保险库

❌ **不推荐**：
- 提交到Git仓库
- 发送到Telegram/微信等聊天工具
- 保存在云端文档（Google Docs等）

### 2. 凭证轮换

定期更新凭证：
- **GitHub Token**：每90天
- **Binance API**：每3个月
- **Telegram Bot**：发现泄露时立即撤销

### 3. 多服务器部署

如果有多台服务器，每台都需要配置：

```bash
# 服务器A
ssh server-a
# 执行配置命令

# 服务器B
ssh server-b
# 执行相同配置命令
```

**提示**：所有服务器可以共用相同的配置（GitHub Token、Binance API等）

---

## 🚀 完整部署流程

### 新服务器从零开始

```bash
# 1. 克隆仓库
cd ~
git clone https://github.com/FelixWayne0318/cryptosignal.git
cd cryptosignal

# 2. 切换到指定分支（如果需要）
git checkout claude/reorganize-repo-structure-011CUrZaXUMTBXApc3jvsqTh

# 3. 执行一键配置（复制您保存的配置命令）
cat > ~/.cryptosignal-github.env <<'EOF'
...
EOF
# ... 其他配置 ...

# 4. 运行部署脚本
bash setup.sh
```

### 已有服务器更新分支

```bash
# 1. 停止旧服务
pkill -f "python.*cryptosignal"

# 2. 拉取新分支
cd ~/cryptosignal
git fetch origin
git checkout <new-branch>
git pull origin <new-branch>

# 3. 不需要重新配置（配置文件独立于分支）

# 4. 重新部署
bash deploy_and_run.sh
```

---

## 📚 相关文档

- **GitHub配置详解**：`docs/VULTR_GITHUB_SETUP.md`
- **快速开始指南**：`docs/VULTR_QUICK_START.md`
- **自动提交策略**：`docs/AUTO_COMMIT_STRATEGY.md`
- **交互式配置向导**：`scripts/setup_server_config.sh`
