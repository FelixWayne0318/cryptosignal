# Vultr服务器快速部署指南

## 🚀 首次部署（推荐流程）

### 步骤1：克隆仓库
```bash
cd ~
git clone https://github.com/FelixWayne0318/cryptosignal.git
cd cryptosignal
```

### 步骤2：配置GitHub访问权限
```bash
bash scripts/setup_github_config.sh
```

**配置向导会提示：**
- Git用户名（如：FelixWayne0318）
- Git邮箱（如：felixwayne0318@gmail.com）
- GitHub Personal Access Token（可选，用于自动推送报告）

**配置文件位置：** `~/.cryptosignal-github.env`（不会被提交到Git）

### 步骤3：运行部署脚本
```bash
bash setup.sh
```

**setup.sh会自动：**
- ✅ 应用GitHub配置（如果存在）
- ✅ 检测并安装依赖
- ✅ 验证API配置
- ✅ 启动扫描系统

---

## 🔄 已部署服务器（更新流程）

### 快速更新并重启
```bash
cd ~/cryptosignal
bash deploy_and_run.sh
```

**deploy_and_run.sh会自动：**
- ✅ 应用GitHub配置
- ✅ 同步最新代码
- ✅ 停止旧进程
- ✅ 安装依赖更新
- ✅ 启动新版本

---

## 📝 GitHub Token获取方法

### 方式1：使用浏览器获取
1. 登录GitHub，访问 https://github.com/settings/tokens
2. 点击 **Generate new token (classic)**
3. 设置Token名称：`Vultr Server - CryptoSignal`
4. 勾选权限：`repo`（完整仓库权限）
5. 设置过期时间：90天或更长
6. 点击 **Generate token**
7. **立即复制token**（关闭页面后无法再次查看！）

### 方式2：使用命令行获取
```bash
# 需要安装gh CLI
gh auth login
```

---

## 🔐 安全配置说明

### 配置文件安全性
- **配置文件位置：** `~/.cryptosignal-github.env`
- **文件权限：** 600（仅当前用户可读写）
- **Git忽略：** 已添加到.gitignore，不会被提交到仓库
- **内容：** Git用户信息 + GitHub Token

### Token权限说明
- **最小权限原则：** 只需要 `repo` 权限
- **用途：** 自动提交扫描报告到GitHub
- **不需要：** workflow, admin, delete等危险权限

### 如何查看当前配置
```bash
cat ~/.cryptosignal-github.env
```

### 如何重新配置
```bash
bash scripts/setup_github_config.sh
```

---

## 🔍 验证GitHub访问

### 测试GitHub推送权限
```bash
cd ~/cryptosignal
bash test_github_access.sh
```

**测试脚本会检查：**
- ✅ Git用户配置
- ✅ 远程仓库地址
- ✅ 认证方式（SSH/HTTPS）
- ✅ 推送权限测试

### 手动测试推送
```bash
cd ~/cryptosignal
git pull origin <branch>
# 如果成功拉取，说明访问权限正常
```

---

## 📊 自动报告功能

### 报告自动提交流程
```
扫描完成
  ↓
写入 reports/latest/
  ↓
自动 git add
  ↓
自动 git commit
  ↓
自动 git push
  ↓
Claude直接读取GitHub文件分析
```

### 报告文件位置
- **最新报告：** `reports/latest/scan_summary.json`
- **详细数据：** `reports/latest/scan_detail.json`
- **人类可读：** `reports/latest/scan_summary.md`
- **历史趋势：** `reports/trends.json`

### 查看报告
```bash
# 查看最新报告摘要
cat ~/cryptosignal/reports/latest/scan_summary.json

# 查看提交历史
cd ~/cryptosignal
git log --oneline | grep "scan:"
```

---

## 🛠️ 常见问题

### 问题1：Git push失败，提示认证错误
**原因：** Token未配置或已过期

**解决：**
```bash
bash scripts/setup_github_config.sh
```

### 问题2：提交成功但无法推送
**原因：** 网络问题或GitHub服务异常

**解决：**
```bash
# 检查网络
ping github.com

# 手动推送
cd ~/cryptosignal
git push origin <branch>
```

### 问题3：配置文件丢失
**原因：** 重装系统或清理Home目录

**解决：**
```bash
bash scripts/setup_github_config.sh
```

### 问题4：想使用SSH而不是Token
**解决：** 参考 `docs/VULTR_GITHUB_SETUP.md` 中的SSH配置方法

---

## 📚 相关文档

- **完整配置指南：** `docs/VULTR_GITHUB_SETUP.md`
- **全市场扫描说明：** `docs/FULL_MARKET_SCAN.md`
- **报告系统说明：** `reports/README.md`

---

## ⚡ 一键命令速查

```bash
# 首次部署
cd ~ && git clone https://github.com/FelixWayne0318/cryptosignal.git && cd cryptosignal && bash scripts/setup_github_config.sh && bash setup.sh

# 更新并重启
cd ~/cryptosignal && bash deploy_and_run.sh

# 查看实时日志
tail -f ~/cryptosignal/logs/scanner_*.log

# 重连screen会话
screen -r cryptosignal

# 测试GitHub访问
cd ~/cryptosignal && bash test_github_access.sh

# 查看最新报告
cat ~/cryptosignal/reports/latest/scan_summary.json | python3 -m json.tool
```

---

## 💡 专业提示

### 提示1：保护Token安全
- ❌ 不要将Token写在代码或文档中
- ❌ 不要将Token提交到Git仓库
- ✅ 使用配置文件存储（已被.gitignore排除）
- ✅ 定期更换Token（建议每90天）

### 提示2：监控自动提交
```bash
# 查看自动提交的报告
cd ~/cryptosignal
git log --oneline --grep="scan:" -10
```

### 提示3：分支切换
```bash
# 切换到其他分支
cd ~/cryptosignal
git checkout <branch-name>
bash deploy_and_run.sh
```

### 提示4：多服务器部署
每个服务器只需运行一次：
```bash
bash scripts/setup_github_config.sh
```

配置会保存在 `~/.cryptosignal-github.env`，以后每次部署自动应用。
