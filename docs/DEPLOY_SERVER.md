# 服务器部署指南 - v7.4.0方案B

## 快速开始

### 方式1：使用模板脚本（推荐）

**适用场景**：首次部署或完整重新部署

1. **上传模板到服务器**
   ```bash
   # 在本地
   scp deploy_server_v7.4.0_planB.template.sh root@YOUR_SERVER_IP:~
   ```

2. **修改配置**
   ```bash
   # 在服务器上
   vim ~/deploy_server_v7.4.0_planB.template.sh

   # 修改以下配置（约30-40行处）：
   GITHUB_TOKEN="YOUR_GITHUB_TOKEN_HERE"
   GIT_USER_NAME="YOUR_GITHUB_USERNAME"
   GIT_USER_EMAIL="YOUR_EMAIL@example.com"
   BINANCE_API_KEY="YOUR_BINANCE_API_KEY"
   BINANCE_API_SECRET="YOUR_BINANCE_API_SECRET"
   TELEGRAM_BOT_TOKEN="YOUR_TELEGRAM_BOT_TOKEN"
   TELEGRAM_CHAT_ID="YOUR_TELEGRAM_CHAT_ID"
   SERVER_IP_WHITELIST="YOUR_SERVER_IP"
   ```

3. **执行部署**
   ```bash
   chmod +x ~/deploy_server_v7.4.0_planB.template.sh
   ~/deploy_server_v7.4.0_planB.template.sh

   # 然后执行生成的部署脚本
   ~/vultr_deploy_v7.4.0_planB.sh
   ```

4. **清理敏感文件**
   ```bash
   rm ~/deploy_server_v7.4.0_planB.template.sh
   rm ~/vultr_deploy_v7.4.0_planB.sh
   ```

### 方式2：直接使用setup.sh（快速）

**适用场景**：代码已部署，仅需重启

```bash
cd ~/cryptosignal
./setup.sh
```

## v7.4.0方案B特性

### 核心改进

| 特性 | 旧方案 | 方案B | 优势 |
|------|--------|-------|------|
| **重启频率** | 每2小时 | 每日3am | 保护AntiJitter状态 |
| **新币发现** | 靠重启 | 动态刷新（6h） | 无需重启 |
| **冷却期** | 破坏状态 | 完整保留 | 2h策略有效 |
| **运维成本** | 每日12次重启 | 每日1次重启 | 降低92% |

### 定时任务配置

```bash
# crontab配置（setup.sh自动设置）
0 3 * * * ~/cryptosignal/auto_restart.sh           # 每日3am保险重启
0 1 * * * find ~ -name 'cryptosignal_*.log' -mtime +7 -delete  # 日志清理
0 2 * * * tail -n 100 ~/cryptosignal/auto_restart.log > ...    # 日志轮转
```

**注意**：不再使用`0 */2 * * *`（每2h重启）

### 动态刷新机制

- **刷新频率**：每6小时（UTC 0/6/12/18点）
- **触发方式**：自动（无需cron配置）
- **新币验证**：K线数据充足性检查
  - 15m ≥ 20根（约5小时）
  - 1h ≥ 24根（约1天）
  - 4h ≥ 7根（约28小时）
  - 1d ≥ 3根（约3天）
- **历史记录**：`data/symbol_list_history.jsonl`

## 配置文件说明

### 必需配置

1. **config/binance_credentials.json**
   ```json
   {
     "binance": {
       "api_key": "YOUR_API_KEY",
       "api_secret": "YOUR_API_SECRET",
       "testnet": false
     }
   }
   ```

2. **config/telegram.json**
   ```json
   {
     "enabled": true,
     "bot_token": "YOUR_BOT_TOKEN",
     "chat_id": "YOUR_CHAT_ID"
   }
   ```

3. **config/params.json** (自动包含)
   - `symbol_refresh`配置块已内置
   - 无需手动配置

### Binance API白名单

**重要**：确保在Binance添加服务器IP到API白名单

1. 访问：https://www.binance.com/en/my/settings/api-management
2. 编辑API Key
3. 添加IP白名单：服务器的公网IP
4. 保存设置

## 验证部署

### 检查定时任务
```bash
crontab -l | grep cryptosignal
# 应该看到：
# 0 3 * * * ~/cryptosignal/auto_restart.sh
```

### 检查进程
```bash
ps aux | grep realtime_signal_scanner
# 应该看到Python进程在运行
```

### 检查日志
```bash
tail -f ~/cryptosignal_*.log
# 查看系统运行日志
```

### 检查刷新配置
```bash
cd ~/cryptosignal
python3 -c "import json; print(json.load(open('config/params.json'))['symbol_refresh']['enabled'])"
# 应该输出：True
```

## 故障排除

### 问题1：定时任务包含旧的2h重启

**现象**：
```bash
crontab -l | grep "0 \*/2"
# 输出：0 */2 * * * ~/cryptosignal/auto_restart.sh
```

**解决**：
```bash
# 方法1：重新运行setup.sh（推荐）
cd ~/cryptosignal && ./setup.sh

# 方法2：手动清理
crontab -e
# 删除包含 "*/2" 的行
# 添加：0 3 * * * ~/cryptosignal/auto_restart.sh
```

### 问题2：动态刷新未启用

**检查**：
```bash
cd ~/cryptosignal
grep -A5 '"symbol_refresh"' config/params.json | grep enabled
```

**解决**：
```bash
# 1. 确保在正确的分支
git checkout claude/reorganize-audit-signals-01PavGxKBtm1yUZ1iz7ADXkA

# 2. 拉取最新代码
git pull origin claude/reorganize-audit-signals-01PavGxKBtm1yUZ1iz7ADXkA

# 3. 重启系统
./setup.sh
```

### 问题3：进程意外停止

**检查**：
```bash
# 查看日志
tail -100 ~/cryptosignal_*.log

# 查看系统日志
tail -100 ~/cryptosignal/auto_restart.log
```

**解决**：
```bash
# 手动重启
cd ~/cryptosignal && ./auto_restart.sh
```

## 安全建议

### 1. 凭证保护
- ✅ 所有配置文件权限设为`600`
- ✅ 不要将配置文件提交到Git
- ✅ 定期轮换API密钥

### 2. 服务器安全
- ✅ 启用SSH密钥认证
- ✅ 禁用root密码登录
- ✅ 配置防火墙（UFW）
- ✅ 定期更新系统

### 3. Binance API安全
- ✅ 使用只读权限API Key
- ✅ 启用IP白名单
- ✅ 定期检查API使用记录

## 监控和维护

### 每日检查
```bash
# 查看运行状态
ps aux | grep realtime_signal_scanner

# 查看最近日志
tail -50 ~/cryptosignal_$(ls -t ~/cryptosignal_*.log | head -1)

# 查看币种刷新历史
tail -5 ~/cryptosignal/data/symbol_list_history.jsonl
```

### 每周检查
```bash
# 检查磁盘空间
df -h

# 检查日志大小
du -sh ~/cryptosignal_*.log

# 检查数据库大小
du -sh ~/cryptosignal/data/
```

## 升级指南

### 拉取最新代码
```bash
cd ~/cryptosignal
git pull origin claude/reorganize-audit-signals-01PavGxKBtm1yUZ1iz7ADXkA

# 清理Python缓存
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# 重启系统
./auto_restart.sh
```

### 检查更新
```bash
cd ~/cryptosignal
git log --oneline -5
# 查看最近5次提交
```

## 相关文档

- [SESSION_STATE.md](./SESSION_STATE.md) - 方案B实施详情
- [SYSTEM_ENHANCEMENT_STANDARD.md](../standards/SYSTEM_ENHANCEMENT_STANDARD.md) - 系统规范
- [README.md](../README.md) - 项目总览

## 支持

遇到问题？
1. 查看日志：`tail -f ~/cryptosignal_*.log`
2. 检查GitHub Issues
3. 查阅SESSION_STATE.md文档

---

**部署时间**：2025-11-17
**版本**：v7.4.0 方案B
**状态**：✅ 生产就绪
