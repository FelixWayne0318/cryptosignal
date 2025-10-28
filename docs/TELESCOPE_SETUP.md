# 链上望远镜 - Telegram信号配置指南

> 专用脚本已创建，配置好Token后即可使用

---

## ⚠️ 当前状态

**Bot Token验证失败（HTTP 403）**

这说明提供的Token可能：
1. ✅ 格式正确（`7545580872:AAF7HzkHA4...`）
2. ❌ Token已过期或被撤销
3. ❌ Bot已被删除

---

## 🔧 解决方案（3个步骤）

### 步骤1: 获取有效的Bot Token

**方法A: 重新生成Token（如果Bot还在）**
1. 在Telegram中找 **@BotFather**
2. 发送 `/mybots`
3. 选择 **量灵通** (@analysis_token_bot)
4. 点击 **API Token**
5. 点击 **Revoke current token** (撤销当前)
6. 点击 **Generate new token** (生成新的)
7. 复制新Token

**方法B: 重新创建Bot（如果找不到）**
1. 在Telegram中找 **@BotFather**
2. 发送 `/newbot`
3. 输入Bot名称：`量灵通`
4. 输入用户名：`analysis_token_bot`（如果被占用，换一个）
5. 获取新Token
6. 将Bot添加到 **链上望远镜** 群组（-1003142003085）

### 步骤2: 验证Token是否有效

**使用浏览器测试**：
```
https://api.telegram.org/bot<你的Token>/getMe
```

**正确的Token会显示**：
```json
{
  "ok": true,
  "result": {
    "id": 7545580872,
    "is_bot": true,
    "first_name": "量灵通",
    "username": "analysis_token_bot"
  }
}
```

**错误的Token会显示**：
```
Access denied
```
或
```
Unauthorized
```

### 步骤3: 更新配置文件

编辑 `.env.telegram` 文件：
```bash
nano .env.telegram
```

更新Token：
```bash
export TELEGRAM_BOT_TOKEN="<新的有效Token>"
export TELEGRAM_CHAT_ID="-1003142003085"
```

保存并加载：
```bash
source .env.telegram
```

---

## 🚀 使用方法（Token配置好后）

### 快速测试

```bash
# 1. 加载配置
source .env.telegram

# 2. 发送单个币种分析（使用v2系统，无需API）
python3 tools/send_signal_to_telescope.py BTCUSDT
```

### 批量扫描 + 自动发送

```bash
# 分析前20个高流动性币种，自动发送到链上望远镜
python3 tools/send_signal_to_telescope.py --batch --max 20
```

### 使用v3系统（需要Binance API密钥）

```bash
# 单个币种（v3）
python3 tools/send_signal_to_telescope.py BTCUSDT --v3

# 批量扫描（v3）
python3 tools/send_signal_to_telescope.py --batch --max 20 --v3
```

---

## 📊 消息样式

**所有消息使用 `telegram_fmt.py` 标准样式**：

```
🔹 BTCUSDT · 现价 68,500
🟩 做多 概率72% · 有效期8h

📍 入场区间: 68,000 - 69,000
🛑 止损: 66,500
🎯 止盈1: 71,000
🎯 止盈2: 73,500

七维分析
• 趋势 🟢 +65 —— 温和上行
• 动量 🟡 +55 —— 温和上行加速
• 资金 🟢 +70 —— 偏强资金流入 (CVD+2.3%, 持续✓)
• 结构 🟡 +50 —— 结构尚可/回踩确认
• 成交 🟢 +60 —— 放量明显/跟随积极
• 持仓 🟡 +45 —— 持仓温和上升/活跃 (OI+8.5%)
• 震荡 🟡 +40 —— 偏趋势/空间尚可

⚡ 资金动量 ✅ 资金领先价格 (F+15)
   └─ 概率调整 ×1.00

#trade #BTCUSDT
```

---

## 📁 相关文件

| 文件 | 说明 |
|------|------|
| `.env.telegram` | Telegram配置文件（需更新有效Token） |
| `tools/send_signal_to_telescope.py` | 专用发送脚本（已配置好群组ID） |
| `ats_core/outputs/telegram_fmt.py` | 消息格式模板（七维分析样式） |
| `ats_core/outputs/publisher.py` | Telegram发送核心功能 |

---

## 🔍 问题诊断

### 问题1: Token验证失败（403）
✅ **已发现** - 当前Token无效

**原因**：
- Token已过期
- Token被撤销
- Bot被删除

**解决**：参考上方"获取有效的Bot Token"

### 问题2: Chat ID错误
✅ **已确认正确** - Chat ID: `-1003142003085`

### 问题3: 消息格式
✅ **已配置** - 使用 `telegram_fmt.py` 标准样式

---

## ✅ 配置检查清单

Token配置好后，确认以下项目：

- [ ] Token验证成功（浏览器测试返回Bot信息）
- [ ] Bot已添加到链上望远镜群组
- [ ] Bot有发送消息权限
- [ ] `.env.telegram` 文件已更新
- [ ] `source .env.telegram` 已执行
- [ ] 测试发送成功

---

## 🆘 获取新Token的详细步骤

### 与BotFather对话示例

```
你: /mybots

BotFather: 请选择一个机器人
[量灵通 @analysis_token_bot]

你: (点击量灵通)

BotFather:
量灵通 @analysis_token_bot
你想做什么？
[Edit Bot] [API Token] [Delete Bot] ...

你: (点击 API Token)

BotFather:
你可以使用这个token来访问HTTP API:
7545580872:AAF7HzkHA4LRQUiOZngUgL39epuGVeEta70

请妥善保管！任何拥有该token的人都可以控制你的机器人。

[Revoke current token]

你: (如果需要新Token，点击 Revoke current token)

BotFather:
Token已撤销。新的token:
7545580872:BBG8i1lIB5SmPoYpahUgM40fqvFfUcb81

请更新你的应用使用新token。
```

---

## 📞 下一步

1. 获取有效的Bot Token
2. 更新 `.env.telegram` 文件
3. 运行测试：
   ```bash
   source .env.telegram
   python3 tools/send_signal_to_telescope.py BTCUSDT
   ```
4. 查看链上望远镜群组，确认消息收到

配置成功后，系统即可自动发送信号到您的Telegram群组！🚀

---

**群组**: 链上望远镜
**Chat ID**: -1003142003085
**Bot**: @analysis_token_bot
**样式**: telegram_fmt.py 标准模板
