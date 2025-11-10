# CryptoSignal 服务器部署指南

**版本**: v2.0（灵活分支版）
**日期**: 2025-11-09
**适用系统**: Ubuntu/Debian

---

## 📋 主要改进

### v2.0 vs v1.0

| 特性 | v1.0（旧版） | v2.0（新版） |
|------|------------|------------|
| 分支选择 | ❌ 硬编码特定分支 | ✅ 支持任意分支或默认分支 |
| 灵活性 | ❌ 每次切换分支需修改脚本 | ✅ 通过参数指定，无需修改脚本 |
| 向后兼容 | ❌ 只能使用特定分支 | ✅ 自动使用仓库默认分支 |
| 维护成本 | ❌ 高（需频繁更新脚本） | ✅ 低（脚本长期有效） |

---

## 🚀 快速开始

### 方法1: 使用默认分支（推荐）

```bash
# 下载脚本
wget https://raw.githubusercontent.com/FelixWayne0318/cryptosignal/main/server_deploy.sh

# 添加执行权限
chmod +x server_deploy.sh

# 运行（使用仓库默认分支）
./server_deploy.sh
```

### 方法2: 指定分支

```bash
# 使用main分支
./server_deploy.sh main

# 使用特定功能分支
./server_deploy.sh claude/system-refactor-v7.2-011CUyBts14z3AdVhv9BSubr

# 使用任何有效分支
./server_deploy.sh <分支名>
```

---

## 📖 详细说明

### 脚本功能

**server_deploy.sh** 会自动完成以下步骤：

1. **环境检查**: 验证Python3、pip3、git
2. **清理旧部署**: 停止进程、备份配置、删除旧代码
3. **克隆仓库**: 从GitHub拉取代码
4. **拉取最新代码**: 确保使用最新版本
5. **配置GitHub**: 设置Git凭证（支持自动推送报告）
6. **配置Binance API**: 设置API密钥
7. **配置Telegram**: 设置机器人通知
8. **配置定时任务**: 每2小时自动重启
9. **验证配置**: 7项验证确保部署成功

---

## 🔧 使用场景

### 场景1: 首次部署（使用默认分支）

```bash
# 在Vultr服务器上运行
ssh root@139.180.157.152
cd ~
wget https://raw.githubusercontent.com/FelixWayne0318/cryptosignal/main/server_deploy.sh
chmod +x server_deploy.sh
./server_deploy.sh
```

**优点**:
- ✅ 自动使用仓库的稳定版本（通常是main或master）
- ✅ 无需关心具体分支名
- ✅ 脚本长期有效，无需更新

---

### 场景2: 使用开发分支测试新功能

```bash
# 切换到最新开发分支
./server_deploy.sh claude/system-refactor-v7.2-011CUyBts14z3AdVhv9BSubr

# 或者使用其他功能分支
./server_deploy.sh feature/new-factor
```

**优点**:
- ✅ 可以测试最新功能
- ✅ 灵活切换不同分支
- ✅ 脚本无需修改

---

### 场景3: 生产环境（使用稳定分支）

```bash
# 使用经过验证的稳定分支
./server_deploy.sh main

# 或使用发布标签
./server_deploy.sh v7.2.0
```

**优点**:
- ✅ 使用稳定版本
- ✅ 避免未经测试的代码
- ✅ 可追溯版本历史

---

## 📝 分支管理建议

### 推荐的分支策略

```
main/master         ← 稳定版本（生产环境）
  ├── develop       ← 开发版本（测试环境）
  └── feature/*     ← 功能分支（本地测试）
```

### 部署建议

| 环境 | 推荐分支 | 部署命令 |
|------|---------|---------|
| 生产环境 | main | `./server_deploy.sh main` |
| 测试环境 | develop | `./server_deploy.sh develop` |
| 功能测试 | feature/* | `./server_deploy.sh feature/xxx` |
| 默认部署 | 仓库默认 | `./server_deploy.sh` |

---

## 🔒 安全配置

### 敏感信息管理

脚本会创建以下配置文件（包含敏感信息）：

```
~/.cryptosignal-github.env         # GitHub凭证（权限600）
~/cryptosignal/config/binance_credentials.json  # Binance API（权限600）
~/cryptosignal/config/telegram.json             # Telegram Bot（权限600）
~/.git-credentials                  # Git凭证（权限600）
```

**安全措施**:
1. ✅ 所有敏感文件权限设置为 `600`（仅所有者可读写）
2. ✅ 配置文件自动添加到 `.gitignore`
3. ✅ 旧配置自动备份到 `~/cryptosignal_backup_<日期>/`

---

## 🛠️ 故障排查

### 问题1: 克隆失败

**症状**: `❌ 仓库克隆失败，请检查网络连接`

**解决方案**:
```bash
# 检查网络连接
ping github.com

# 检查DNS
nslookup github.com

# 尝试使用代理（如果需要）
export https_proxy=http://proxy:port
./server_deploy.sh
```

---

### 问题2: 分支不存在

**症状**: `❌ 分支 xxx 不存在或克隆失败`

**解决方案**:
```bash
# 查看所有可用分支
git clone https://github.com/FelixWayne0318/cryptosignal.git
cd cryptosignal
git branch -a

# 使用正确的分支名
./server_deploy.sh <正确的分支名>
```

---

### 问题3: IP白名单不匹配

**症状**: `⚠️ 服务器IP: xxx.xxx.xxx.xxx (预期IP: 139.180.157.152)`

**解决方案**:
1. 访问 https://www.binance.com/en/my/settings/api-management
2. 编辑API Key
3. 添加新IP到白名单
4. 或修改脚本中的IP地址

---

### 问题4: Python依赖安装失败

**症状**: `setup.sh` 运行时依赖安装失败

**解决方案**:
```bash
# 手动安装依赖
cd ~/cryptosignal
pip3 install -r requirements.txt

# 如果仍失败，升级pip
pip3 install --upgrade pip
pip3 install -r requirements.txt
```

---

## 📊 验证清单

部署完成后，脚本会自动执行7项验证：

- [ ] ✅ 验证1: 检查配置文件（GitHub、Binance、Telegram）
- [ ] ✅ 验证2: 检查文件权限（所有敏感文件权限=600）
- [ ] ✅ 验证3: 检查Git配置（user.name、user.email）
- [ ] ✅ 验证4: 检查定时任务（crontab配置）
- [ ] ✅ 验证5: 检查代码版本（分支、提交）
- [ ] ✅ 验证6: 检查服务器IP（Binance白名单）
- [ ] ✅ 验证7: 检查关键文件（setup.sh、扫描器等）

**所有验证通过**后，会显示绿色的 `✅ 配置完成！`

---

## 🚀 启动系统

部署完成后，按照提示启动系统：

```bash
cd ~/cryptosignal
./setup.sh
```

**首次启动**会：
1. 安装Python依赖（3-5分钟）
2. 初始化数据库
3. 连接WebSocket
4. 发送Telegram启动通知
5. 开始扫描信号

---

## 📌 定时任务

脚本会自动配置以下定时任务：

```cron
# 每2小时自动重启（确保系统稳定）
0 */2 * * * ~/cryptosignal/auto_restart.sh

# 每天清理7天前的日志
0 1 * * * find ~ -name 'cryptosignal_*.log' -mtime +7 -delete
```

**查看定时任务**:
```bash
crontab -l
```

**编辑定时任务**:
```bash
crontab -e
```

---

## 🔄 更新系统

### 方法1: 重新部署（推荐）

```bash
# 重新运行部署脚本（会自动备份旧配置）
./server_deploy.sh

# 或指定新分支
./server_deploy.sh <新分支名>
```

**优点**:
- ✅ 自动备份旧配置
- ✅ 确保环境干净
- ✅ 所有验证重新执行

---

### 方法2: 手动更新（快速）

```bash
cd ~/cryptosignal
git pull origin <分支名>
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
./auto_restart.sh
```

**优点**:
- ✅ 更快（不重新克隆）
- ✅ 保留旧配置

**缺点**:
- ⚠️ 可能有残留文件
- ⚠️ 需要手动清理缓存

---

## 📞 技术支持

### 获取帮助

1. 查看日志文件:
   ```bash
   ls -lh ~/cryptosignal_*.log
   tail -100 ~/cryptosignal_<最新日期>.log
   ```

2. 检查系统状态:
   ```bash
   cd ~/cryptosignal
   ./check_status.sh
   ```

3. 查看进程状态:
   ```bash
   ps aux | grep python
   ```

---

## 🆕 版本历史

### v2.0（2025-11-09）

**改进**:
- ✅ 移除硬编码的分支名
- ✅ 支持通过参数指定任意分支
- ✅ 默认使用仓库的默认分支
- ✅ 自动拉取最新代码
- ✅ 清理Python缓存
- ✅ 改进验证流程

**向后兼容**: ✅ 完全兼容v1.0的所有功能

---

### v1.0（2025-11-08）

**初始版本**:
- ✅ 自动配置服务器环境
- ✅ 配置Git、Binance、Telegram
- ✅ 配置定时任务
- ✅ 7项验证清单

---

## 📝 常见问题

### Q1: 脚本会删除我的旧配置吗？

**A**: 不会。脚本会自动备份旧配置到 `~/cryptosignal_backup_<日期>/`，然后创建新配置。

---

### Q2: 可以在本地测试吗？

**A**: 可以，但需要修改IP白名单。建议在Vultr服务器上运行。

---

### Q3: 如何回滚到旧版本？

**A**:
```bash
# 方法1: 使用备份
cp ~/cryptosignal_backup_<日期>/* ~/cryptosignal/config/

# 方法2: 切换到旧分支
./server_deploy.sh <旧分支名>

# 方法3: 使用Git回滚
cd ~/cryptosignal
git reset --hard <旧提交ID>
```

---

### Q4: 脚本支持哪些操作系统？

**A**:
- ✅ Ubuntu 18.04+
- ✅ Debian 10+
- ✅ 其他基于Debian的系统

不支持：
- ❌ CentOS/RHEL（命令差异）
- ❌ macOS（命令差异）
- ❌ Windows（需WSL或Docker）

---

## 🎯 最佳实践

### 1. 定期更新

```bash
# 每周更新一次
./server_deploy.sh
```

### 2. 监控日志

```bash
# 设置日志监控
watch -n 60 "tail -20 ~/cryptosignal_$(ls -t ~/cryptosignal_*.log | head -1)"
```

### 3. 备份配置

```bash
# 手动备份
cp ~/.cryptosignal-github.env ~/backup/
cp ~/cryptosignal/config/*.json ~/backup/
```

### 4. 测试新功能前先备份

```bash
# 先部署到测试服务器
./server_deploy.sh feature/new-feature

# 验证功能正常后再部署到生产
./server_deploy.sh main
```

---

**文档结束**

如有问题，请查看：
- 系统审查报告: `docs/SYSTEM_REFACTOR_V72_AUDIT.md`
- 部署标准: `standards/DEPLOYMENT_STANDARD.md`
- GitHub Issues: https://github.com/FelixWayne0318/cryptosignal/issues
