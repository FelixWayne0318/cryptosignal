# Vultr服务器部署指南

## 🚀 快速部署

### 完整的一键配置命令已提供给您

**上面的输出包含完整的配置脚本和命令，请保存到您的密码管理器或本地笔记。**

配置包含：
- ✅ GitHub访问权限（自动推送报告）
- ✅ Binance API凭证（只读，IP白名单139.180.157.15）
- ✅ Telegram通知配置
- ✅ 定时任务（每2小时重启）

---

## 📋 部署流程

### 场景1：全新服务器部署

```bash
# 步骤1：克隆仓库
cd ~
git clone https://github.com/FelixWayne0318/cryptosignal.git
cd cryptosignal

# 步骤2：切换到指定分支
git checkout claude/reorganize-repo-structure-011CUrZaXUMTBXApc3jvsqTh

# 步骤3：运行配置（使用上面提供的配置命令）
# 复制保存的配置命令并执行

# 步骤4：启动系统
bash setup.sh
```

---

### 场景2：现有服务器更换分支

```bash
# 停止服务
pkill -f "python.*cryptosignal"

# 拉取代码
cd ~/cryptosignal
git fetch origin
git checkout <新分支>
git pull origin <新分支>

# 配置已存在，直接部署
bash deploy_and_run.sh
```

---

### 场景3：更换服务器

```bash
# 在新服务器上：
cd ~
git clone https://github.com/FelixWayne0318/cryptosignal.git
cd cryptosignal
git checkout claude/reorganize-repo-structure-011CUrZaXUMTBXApc3jvsqTh

# 重新运行配置命令（使用保存的配置）
# 然后：
bash setup.sh
```

---

## 🔍 验证部署

### 1. 检查进程
```bash
ps aux | grep python | grep cryptosignal
```

### 2. 查看日志
```bash
tail -f ~/cryptosignal/logs/scanner_*.log
```

### 3. 验证GitHub访问
```bash
cd ~/cryptosignal
bash test_github_access.sh
```

### 4. 检查定时任务
```bash
crontab -l | grep cryptosignal
```

---

## 🔄 常见操作

### 重启服务
```bash
cd ~/cryptosignal
bash auto_restart.sh
```

### 查看Screen会话
```bash
screen -ls
screen -r cryptosignal
```

### 更新代码
```bash
cd ~/cryptosignal
git pull origin <branch>
bash deploy_and_run.sh
```

---

## 📊 系统运行状态

系统启动后：
- ✅ 每5分钟扫描405个币种
- ✅ 生成报告写入 `reports/latest/`
- ✅ 有信号立即推送到GitHub ⚡
- ✅ 无信号每小时推送一次
- ✅ 每2小时自动重启（cron任务）

---

## 🛠️ 故障排查

### Binance API错误
```bash
# 检查服务器IP
curl ifconfig.me
# 应该输出: 139.180.157.15

# 如果IP不匹配，更新币安API白名单
# 访问: https://www.binance.com/en/my/settings/api-management
```

### GitHub推送失败
```bash
# 检查配置
cat ~/.cryptosignal-github.env

# 重新运行配置命令
```

### 扫描未启动
```bash
# 查看日志
tail -100 ~/cryptosignal/logs/scanner_*.log

# 手动启动
cd ~/cryptosignal
bash deploy_and_run.sh
```

---

## 📚 相关文档

- **GitHub配置**：`docs/VULTR_GITHUB_SETUP.md`
- **完整配置指南**：`docs/SERVER_ONE_CLICK_SETUP.md`
- **自动提交策略**：`docs/AUTO_COMMIT_STRATEGY.md`

---

## ⚠️ 重要提示

1. **配置命令包含敏感信息**
   - 请保存到密码管理器
   - 不要分享给他人
   - 不要提交到Git仓库

2. **IP白名单**
   - Binance API限制IP: 139.180.157.15
   - 如服务器IP变更，需更新白名单

3. **定期维护**
   - 每90天更新GitHub Token
   - 每3个月轮换Binance API
   - 监控API使用情况

---

## ✅ 配置清单

部署完成后，确认：
- [ ] 服务器IP: 139.180.157.15
- [ ] Git配置正确
- [ ] GitHub推送成功
- [ ] Binance API连接正常
- [ ] Python进程运行中
- [ ] 日志正常输出
- [ ] 定时任务已配置
- [ ] 配置文件权限600

---

## 🎯 总结

✅ **完整配置命令已提供**（包含所有真实凭证）
✅ **3条命令完成部署**（克隆→配置→启动）
✅ **换服务器**：重新运行配置命令
✅ **换分支**：配置保留，直接部署
✅ **自动化**：定时重启+自动推送报告
✅ **安全**：所有凭证本地存储，不在仓库中

现在您可以在Vultr服务器上快速部署CryptoSignal系统！
