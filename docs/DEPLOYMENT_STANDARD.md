# CryptoSignal 服务器部署标准规范

> ⚠️ **重要提示**
>
> 本文档已整合到标准化规范体系中。
>
> **权威规范文档**：[standards/DEPLOYMENT.md](../standards/DEPLOYMENT.md)
>
> 本文档为快速参考版本，完整规范请查阅上述文档。

---

## 📋 文档版本

- **版本**: v1.1（引用规范版）
- **更新日期**: 2025-11-01
- **适用系统**: CryptoSignal v6.1+
- **维护状态**: 引用 standards/DEPLOYMENT.md

---

## 🎯 规范目的

本规范定义 CryptoSignal 系统在生产服务器上的标准部署流程。

**完整规范见**：[standards/DEPLOYMENT.md](../standards/DEPLOYMENT.md)

---

## 📐 标准部署流程

### 流程总览

```
┌─────────────────────────────────────────────────────────┐
│  第1步: 拉取代码  →  第2步: 配置凭证  →  第3步: 部署   │
└─────────────────────────────────────────────────────────┘
                            ↓
              ┌─────────────────────────┐
              │  第4步: 验证 + 启动      │
              └─────────────────────────┘
```

### 标准命令序列

所有服务器部署必须按照以下顺序执行：

```bash
# ============================================================================
# 标准部署流程 (CryptoSignal v6.1+)
# ============================================================================

# 第 1 步：进入项目目录并拉取代码
cd ~/cryptosignal
git fetch origin <BRANCH_NAME>
git checkout <BRANCH_NAME>
git pull origin <BRANCH_NAME>

# 第 2 步：配置 Binance API 凭证（如未配置）
# 见下文 "凭证配置规范"

# 第 3 步：运行部署脚本
./deploy_v6.1.sh

# 第 4 步：启动生产环境
./start_production.sh  # 或使用 Screen/nohup
```

---

## 🔑 凭证配置规范

### 配置文件位置

```
~/cryptosignal/config/
├── binance_credentials.json  ⬅️ Binance API 凭证（必需）
├── telegram.json             ⬅️ Telegram 通知（可选）
└── params.json               ⬅️ 系统参数（版本控制）
```

### Binance API 凭证配置

**标准配置命令**：

```bash
cd ~/cryptosignal

cat > config/binance_credentials.json <<'EOF'
{
  "_comment": "Binance Futures API凭证配置",
  "binance": {
    "api_key": "您的API_KEY",
    "api_secret": "您的SECRET_KEY",
    "testnet": false,
    "_security": "只读权限API Key，不具备交易功能"
  }
}
EOF
```

**验证命令**：

```bash
python3 -c "
import json
with open('config/binance_credentials.json') as f:
    bn = json.load(f)['binance']
    if bn['api_key'] != '您的API_KEY':
        print('✅ Binance API配置已填写')
    else:
        print('❌ 请先填写API凭证')
"
```

### Telegram 配置（可选）

**标准配置命令**：

```bash
cd ~/cryptosignal

cat > config/telegram.json <<'EOF'
{
  "bot_token": "您的BOT_TOKEN",
  "chat_id": "您的CHAT_ID",
  "_comment": "Telegram通知配置"
}
EOF
```

---

## 🔄 分支管理规范

### 分支命名规则

| 分支类型 | 命名格式 | 示例 | 用途 |
|---------|---------|------|------|
| **功能分支** | `claude/<feature>-<session-id>` | `claude/review-system-overview-011CUhLQ` | Claude 开发的功能 |
| **主分支** | `main` 或 `master` | `main` | 生产稳定版本 |
| **发布分支** | `release/v<version>` | `release/v6.1` | 版本发布 |
| **修复分支** | `hotfix/<issue>` | `hotfix/signal-scarcity` | 紧急修复 |

### 当前活跃分支

```bash
# v6.1 修复分支（当前使用）
claude/review-system-overview-011CUhLQjByWuXC1bySJCHKQ
```

**关键提交**：
- `6ee6bbe` - fix: 改进部署脚本中的Binance API配置提示
- `55ba9d2` - fix: 修复系统审查发现的关键问题（合规度70%→90%+）

---

## 🛠️ 部署脚本规范

### deploy_v6.1.sh 使用规范

**脚本功能**：
1. 停止旧进程并备份配置
2. 拉取最新代码（已在之前手动完成）
3. 验证代码修复（权重、阈值、防抖动）
4. 验证配置文件（Binance、Telegram）
5. 清理 Python 缓存
6. 快速测试运行（10秒验证）
7. 显示启动命令

**标准调用**：

```bash
cd ~/cryptosignal
./deploy_v6.1.sh
```

**脚本输出**：

```
============================================
🚀 CryptoSignal v6.1 部署脚本
============================================

📍 第 1 步：停止当前运行的扫描器
✅ 已停止运行中的扫描器

📍 第 2 步：备份当前配置
✅ 配置文件已备份到 *.bak.20251101_123456

📍 第 3 步：查看当前代码版本
...

📍 第 8 步：生产环境启动指南
✅ v6.1 部署验证完成！
```

### 错误处理规范

**场景 1: Binance API 配置缺失**

脚本会输出：
```
❌ config/binance_credentials.json 不存在

请先创建 Binance API 配置文件：
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
cat > config/binance_credentials.json <<'EOF'
{...配置模板...}
EOF
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

配置完成后重新运行: ./deploy_v6.1.sh
```

**标准处理流程**：
1. 复制脚本输出的配置命令
2. 替换 API 凭证为真实值
3. 重新执行 `./deploy_v6.1.sh`

---

## 🚀 启动方式规范

### 方式 1：Screen 会话（推荐）

**适用场景**：长期运行、需要随时查看日志

```bash
cd ~/cryptosignal

# 创建 screen 会话
screen -S cryptosignal

# 启动系统
python3 scripts/realtime_signal_scanner.py --interval 300

# 分离会话：按 Ctrl+A 然后 D

# 重连会话
screen -r cryptosignal

# 终止会话：在会话中按 Ctrl+C，然后 exit
```

### 方式 2：快速启动脚本

**适用场景**：交互式选择启动方式

```bash
cd ~/cryptosignal
./start_production.sh

# 选择启动方式：
#   1) Screen 会话（推荐）
#   2) 后台运行（nohup）
#   3) 前台运行（测试用）
```

### 方式 3：后台运行（nohup）

**适用场景**：无 Screen、需要后台运行

```bash
cd ~/cryptosignal
mkdir -p logs

nohup python3 scripts/realtime_signal_scanner.py --interval 300 \
  > logs/scanner_$(date +%Y%m%d_%H%M%S).log 2>&1 &

# 记录 PID
echo $! > logs/scanner.pid

# 查看日志
tail -f logs/scanner_*.log

# 停止进程
kill $(cat logs/scanner.pid)
```

---

## 📊 验证与监控规范

### 部署后验证清单

部署完成后，必须验证以下项目：

- [ ] 进程正常运行
- [ ] WebSocket 连接成功
- [ ] Binance API 连接正常
- [ ] 能够扫描币种
- [ ] 信号检测正常
- [ ] Telegram 通知发送成功（如配置）

**标准验证命令**：

```bash
# 1. 检查进程
ps aux | grep realtime_signal_scanner

# 2. 查看日志（最近50行）
tail -50 logs/scanner_*.log  # 或 screen -r cryptosignal

# 3. 验证初始化成功
grep "✅" logs/scanner_*.log | tail -10

# 应该看到：
# ✅ 币安合约客户端初始化完成
# ✅ 客户端初始化完成，服务器时间已同步
# ✅ 四门系统组件初始化完成
# ✅ 防抖动系统初始化完成
```

### 运行监控规范

**每日检查**（推荐）：

```bash
cd ~/cryptosignal

# 1. 检查进程状态
ps aux | grep realtime_signal_scanner

# 2. 统计今日信号数量
grep -c "🔔 Prime信号" logs/scanner_*.log

# 3. 查看最近10个信号
grep "🔔 Prime信号" logs/scanner_*.log | tail -10

# 4. 检查错误日志
grep -i "error\|exception" logs/scanner_*.log | tail -20
```

**每周统计**（推荐）：

```bash
# 统计一周信号数量
find logs -name "scanner_*.log" -mtime -7 \
  -exec grep -h "🔔 Prime信号" {} \; | wc -l

# 统计各币种信号分布
find logs -name "scanner_*.log" -mtime -7 \
  -exec grep -h "🔔 Prime信号" {} \; | \
  awk '{print $NF}' | sort | uniq -c | sort -rn
```

---

## 🔙 回滚规范

### 场景 1：代码回滚

如果新版本出现问题，回滚到上一个稳定版本：

```bash
cd ~/cryptosignal

# 1. 停止当前运行
ps aux | grep realtime_signal_scanner | grep -v grep | \
  awk '{print $2}' | xargs kill

# 2. 查看提交历史
git log --oneline -10

# 3. 回滚到指定提交
git checkout <STABLE_COMMIT_HASH>

# 4. 验证代码版本
git log --oneline -3

# 5. 重新部署
./deploy_v6.1.sh
```

### 场景 2：配置回滚

如果配置修改导致问题，恢复备份配置：

```bash
cd ~/cryptosignal

# 1. 查看备份文件
ls -lht config/*.bak.* | head -5

# 2. 恢复备份
cp config/params.json.bak.YYYYMMDD_HHMMSS config/params.json

# 3. 验证配置
python3 -c "
import json
with open('config/params.json') as f:
    config = json.load(f)
    print('✅ 配置已恢复')
"

# 4. 重启系统
./start_production.sh
```

---

## 📝 变更记录规范

### 部署变更记录模板

每次部署后应记录变更信息：

```
日期：YYYY-MM-DD HH:MM
操作人：<操作人员>
分支：<分支名称>
提交：<commit hash>
变更内容：
  - <变更1>
  - <变更2>
验证结果：✅ 通过 / ❌ 失败
备注：<其他说明>
```

**示例**：

```
日期：2025-11-01 20:45
操作人：系统管理员
分支：claude/review-system-overview-011CUhLQjByWuXC1bySJCHKQ
提交：6ee6bbe
变更内容：
  - I因子架构修正（A层→B层）
  - Prime阈值降低（35→25分）
  - 防抖动机制放宽（1/2确认，60秒冷却）
验证结果：✅ 通过
备注：信号量明显增加，预期3-7个/小时
```

---

## 🔐 安全规范

### 凭证管理

**必须遵守**：

1. ✅ **禁止将凭证提交到 Git**
   - `config/binance_credentials.json` 已在 `.gitignore`
   - `config/telegram.json` 已在 `.gitignore`

2. ✅ **使用只读权限 API**
   - Binance API Key 必须仅启用"读取"权限
   - 禁止启用"交易"、"提现"权限

3. ✅ **启用 IP 白名单**
   - 在 Binance 后台限制 API Key 只能从服务器 IP 访问

4. ✅ **定期轮换凭证**
   - 建议每 30-90 天更换一次 API Key

### 服务器访问

**推荐配置**：

1. 使用 SSH 密钥认证（禁用密码登录）
2. 配置防火墙只开放必要端口
3. 定期更新系统安全补丁
4. 使用非 root 用户运行系统

---

## 📚 相关文档

| 文档 | 路径 | 用途 |
|------|------|------|
| **部署规范** | `docs/DEPLOYMENT_STANDARD.md` | 标准部署流程（本文档） |
| **快速部署** | `QUICK_DEPLOY.md` | 一页纸快速参考 |
| **详细指南** | `DEPLOYMENT_v6.1.md` | 完整部署文档 |
| **服务器命令** | `SERVER_DEPLOY.txt` | 可复制的命令清单 |
| **部署脚本** | `deploy_v6.1.sh` | 自动化部署脚本 |
| **启动脚本** | `start_production.sh` | 生产环境启动脚本 |

---

## 🆘 故障处理规范

### 常见问题处理流程

**问题 1：依赖缺失**

```bash
# 错误：ModuleNotFoundError: No module named 'xxx'
# 解决：
pip3 install -r requirements.txt
```

**问题 2：API 连接失败**

```bash
# 错误：Cannot connect to host fapi.binance.com
# 排查：
# 1. 检查网络连接
curl -I https://fapi.binance.com

# 2. 检查 API 凭证
cat config/binance_credentials.json

# 3. 测试 API
python3 -c "
import asyncio
from ats_core.execution.binance_futures_client import get_binance_client

async def test():
    client = get_binance_client()
    await client.initialize()
    info = await client.get_exchange_info()
    print(f'✅ API连接成功: {len(info[\"symbols\"])} 个交易对')
    await client.close()

asyncio.run(test())
"
```

**问题 3：进程异常退出**

```bash
# 排查步骤：
# 1. 查看日志
tail -100 logs/scanner_*.log

# 2. 前台运行查看错误
python3 scripts/realtime_signal_scanner.py --interval 300

# 3. 检查系统资源
free -h
df -h
```

### 紧急联系流程

1. 查看错误日志收集信息
2. 尝试标准故障处理流程
3. 如无法解决，联系技术支持并提供：
   - Git 版本（`git log --oneline -3`）
   - 错误日志（最近 100 行）
   - 系统环境（Python 版本、操作系统）

---

## ✅ 合规检查清单

部署前必须确认：

- [ ] 已拉取最新代码并验证提交历史
- [ ] Binance API 凭证已正确配置（只读权限）
- [ ] Telegram 配置已完成（如需通知）
- [ ] 配置文件未提交到 Git
- [ ] 运行 `./deploy_v6.1.sh` 所有验证通过
- [ ] 系统成功启动并初始化
- [ ] 进程正常运行并能够扫描币种
- [ ] 已记录部署变更信息

---

## 📞 支持与反馈

- **文档问题**：提交 Issue 到代码仓库
- **技术支持**：联系开发团队
- **规范更新**：由技术负责人审核批准

---

**文档状态**：✅ 生效中
**下次审核**：2025-12-01
**维护人员**：CryptoSignal 开发团队
