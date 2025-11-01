# 部署规范 (Deployment Standards)

> **服务器部署标准流程与规范**
> 遵循本规范确保部署一致性、可追溯性和可回滚性

---

## 📋 文档版本

- **版本**: v1.0
- **更新日期**: 2025-11-01
- **适用系统**: CryptoSignal v6.1+
- **规范状态**: 生效中

---

## 🎯 规范目的

本规范定义 CryptoSignal 系统在生产服务器上的标准部署流程，确保：

1. **一致性** - 所有部署遵循统一流程
2. **可追溯** - 每次部署有明确版本记录
3. **可回滚** - 出现问题可快速回退
4. **安全性** - 敏感配置不泄露到代码仓库

---

## 📐 标准部署流程

### 流程图

```
┌──────────────────────────────────────────────────────┐
│  第1步: 拉取代码 → 第2步: 配置凭证 → 第3步: 部署   │
└──────────────────────────────────────────────────────┘
                         ↓
           ┌──────────────────────────┐
           │  第4步: 验证 + 启动       │
           └──────────────────────────┘
```

### 标准命令序列

```bash
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 标准部署流程（4步）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# 第 1 步：进入项目目录并拉取代码
cd ~/cryptosignal
git fetch origin <BRANCH_NAME>
git checkout <BRANCH_NAME>
git pull origin <BRANCH_NAME>

# 第 2 步：配置凭证（如未配置）
# 见 § 凭证配置规范

# 第 3 步：运行部署脚本
./deploy_v6.1.sh

# 第 4 步：验证并启动
# 脚本会自动询问是否启动（推荐选择 y）
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
        print('✅ 配置已填写')
    else:
        print('❌ 请填写API凭证')
"
```

---

## 🔄 分支管理规范

### 分支命名规则

| 分支类型 | 命名格式 | 示例 |
|---------|---------|------|
| **功能分支** | `claude/<feature>-<session-id>` | `claude/review-system-overview-011CUhLQ` |
| **主分支** | `main` 或 `master` | `main` |
| **发布分支** | `release/v<version>` | `release/v6.1` |
| **修复分支** | `hotfix/<issue>` | `hotfix/signal-scarcity` |

### 当前活跃分支

```bash
# v6.1 修复分支（当前）
claude/review-system-overview-011CUhLQjByWuXC1bySJCHKQ
```

---

## 🛠️ 部署脚本规范

### deploy_v6.1.sh 标准流程

脚本自动完成以下 9 步：

1. 停止旧进程并备份配置
2. 查看当前代码版本
3. ~~拉取最新代码~~（已在第1步手动完成）
4. 验证代码修复（权重、阈值、防抖动）
5. 验证 Telegram 配置
6. 验证 Binance API 配置
7. 清理 Python 缓存
8. 快速测试运行（10秒验证）
9. 显示启动命令
10. **询问是否立即启动**（新增）

### Screen 启动说明

选择 `y` 启动后：

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
使用 Screen 会话启动（推荐）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 Screen 工作原理：
  1. 启动后您会看到实时日志（类似前台运行）
  2. 按 Ctrl+A 然后按 D 键分离会话
  3. 分离后程序继续在后台运行
  4. ✅ 退出 Termius 不影响程序运行
  5. 随时可以重连查看日志

🔧 常用命令：
  重连会话: screen -r cryptosignal
  查看所有: screen -ls
  停止程序: 在会话中按 Ctrl+C
```

**重要**：Screen 会话分离后，程序在后台运行，关闭终端不影响！

---

## 🚀 启动方式规范

### 方式 1：deploy_v6.1.sh 自动启动（推荐）

```bash
./deploy_v6.1.sh
# 选择 y 自动启动
```

### 方式 2：手动 Screen 启动

```bash
screen -S cryptosignal
python3 scripts/realtime_signal_scanner.py --interval 300
# 按 Ctrl+A 然后 D 分离
```

### 方式 3：快速启动脚本

```bash
./start_production.sh
# 选择 1（Screen 会话）
```

### 方式 4：nohup 后台（无 Screen 时）

```bash
mkdir -p logs
nohup python3 scripts/realtime_signal_scanner.py --interval 300 \
  > logs/scanner_$(date +%Y%m%d_%H%M%S).log 2>&1 &
```

---

## 📊 验证与监控规范

### 部署后验证清单

- [ ] 进程正常运行
- [ ] WebSocket 连接成功
- [ ] Binance API 连接正常
- [ ] 能够扫描币种
- [ ] 信号检测正常
- [ ] Telegram 通知发送成功（如配置）

### 验证命令

```bash
# 1. 检查进程
ps aux | grep realtime_signal_scanner

# 2. 重连 Screen 查看日志
screen -r cryptosignal

# 3. 验证初始化成功（应该看到这些）
grep "✅" logs/scanner_*.log | tail -10
```

---

## 🔙 回滚规范

### 代码回滚

```bash
cd ~/cryptosignal

# 1. 停止进程
ps aux | grep realtime_signal_scanner | grep -v grep | \
  awk '{print $2}' | xargs kill

# 2. 回滚到指定提交
git log --oneline -10
git checkout <STABLE_COMMIT>

# 3. 重新部署
./deploy_v6.1.sh
```

### 配置回滚

```bash
# 查看备份
ls -lht config/*.bak.* | head -5

# 恢复备份
cp config/params.json.bak.YYYYMMDD_HHMMSS config/params.json
```

---

## 📝 变更记录规范

### 变更记录模板

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

---

## 🔐 安全规范

### 凭证管理

**必须遵守**：

1. ✅ 禁止将凭证提交到 Git
2. ✅ 使用只读权限 API Key
3. ✅ 启用 IP 白名单
4. ✅ 定期轮换凭证（30-90天）

### 服务器访问

1. 使用 SSH 密钥认证
2. 配置防火墙
3. 定期更新系统
4. 使用非 root 用户运行

---

## 🆘 故障处理规范

### 常见问题

| 问题 | 解决方案 |
|------|---------|
| **依赖缺失** | `pip3 install -r requirements.txt` |
| **API连接失败** | 检查 `config/binance_credentials.json` |
| **进程异常退出** | 查看日志 `tail -100 logs/scanner_*.log` |
| **配置错误** | 运行 `./deploy_v6.1.sh` 重新验证 |

---

## 📚 相关文档

| 文档 | 用途 |
|------|------|
| **[QUICK_REFERENCE.md](./QUICK_REFERENCE.md)** | 快速参考 |
| **[MODIFICATION_RULES.md](./MODIFICATION_RULES.md)** | 修改规则 |
| **[CONFIGURATION_GUIDE.md](./CONFIGURATION_GUIDE.md)** | 配置指南 |
| **[DEVELOPMENT_WORKFLOW.md](./DEVELOPMENT_WORKFLOW.md)** | 开发工作流 |

---

## ✅ 合规检查清单

部署前必须确认：

- [ ] 已拉取最新代码并验证提交历史
- [ ] Binance API 凭证已配置（只读权限）
- [ ] Telegram 配置已完成（如需通知）
- [ ] 配置文件未提交到 Git
- [ ] 运行 `./deploy_v6.1.sh` 所有验证通过
- [ ] 系统成功启动并初始化
- [ ] 进程正常运行并能扫描币种
- [ ] 已记录部署变更信息

---

**文档状态**: ✅ 生效中
**下次审核**: 2025-12-01
**维护者**: CryptoSignal Team
**最后更新**: 2025-11-01
