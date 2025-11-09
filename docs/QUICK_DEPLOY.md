# 🚀 v7.2 快速部署指南

**版本**: v7.2
**分支**: `claude/reorganize-repo-structure-011CUwp5f5x9B31K29qAb5w3`
**最后更新**: 2025-11-08

---

## ⚡ 一键部署（推荐）

服务器上执行以下命令即可完成所有操作：

```bash
cd ~/cryptosignal
./setup.sh
```

**就这么简单！** setup.sh 会自动完成以下所有步骤：

---

## 📋 setup.sh 自动执行的操作

### 第0步：代码更新
1. ✅ 保存本地修改（如果有）
2. ✅ 拉取最新代码（git fetch + pull）
3. ✅ 清理Python缓存（__pycache__ 和 *.pyc）
4. ✅ 验证v7.2目录结构

### 第1步：环境检测
5. ✅ 检测Python3
6. ✅ 检测pip3
7. ✅ 安装依赖包

### 第2步：配置检查
8. ✅ 检查Binance配置
9. ✅ 检查Telegram配置
10. ✅ 配置定时任务（crontab）

### 第3步：系统准备
11. ✅ 初始化数据库
12. ✅ 添加执行权限

### 第4步：启动服务
13. ✅ 停止旧进程
14. ✅ 启动v7.2扫描器
15. ✅ 显示实时日志

---

## 🎯 首次部署

如果是**第一次部署**，只需要克隆仓库，然后运行 setup.sh：

```bash
# 1. 克隆仓库
git clone https://github.com/FelixWayne0318/cryptosignal.git
cd cryptosignal

# 2. 切换到v7.2分支
git checkout claude/reorganize-repo-structure-011CUwp5f5x9B31K29qAb5w3

# 3. 配置API密钥
# 编辑 config/binance_credentials.json
# 编辑 config/telegram.json

# 4. 一键部署
./setup.sh
```

---

## 🔄 更新部署（已有部署的情况）

如果服务器上已经有代码，想更新到最新版本：

```bash
cd ~/cryptosignal
./setup.sh  # 就这一条命令！
```

setup.sh 会自动：
- 拉取最新代码
- 清理缓存
- 重启服务

---

## ⚙️ v7.2 新特性

### 1. 环境变量控制自动提交

**服务器自动运行**（默认）：
```bash
./setup.sh  # 自动提交启用
```

**手动测试**（禁用提交）：
```bash
export AUTO_COMMIT_REPORTS=false
./setup.sh  # 自动提交禁用
```

### 2. 重组后的目录结构

```
cryptosignal/
├── setup.sh ⭐              # 唯一入口
├── tests/                  # 测试文件
├── diagnose/               # 诊断文件
├── docs/                   # 文档文件
├── standards/              # 规范文档（v7.2）
└── ats_core/               # 核心代码
```

---

## 📋 常用命令

### 查看运行状态
```bash
~/cryptosignal/check_v72_status.sh
```

### 重启系统
```bash
~/cryptosignal/auto_restart.sh
```

### 停止系统
```bash
pkill -f realtime_signal_scanner_v72.py
```

### 查看日志
```bash
tail -f ~/cryptosignal_*.log
```

---

## ❓ 常见问题

### Q1: 如何确认使用的是v7.2版本？

**A**: 运行 setup.sh 后会显示目录结构验证：
```
✅ v7.2目录结构正确
   - tests/: 9 个测试文件
   - diagnose/: 2 个诊断文件
   - docs/: 5 个文档文件
```

### Q2: 如何禁用自动提交报告？

**A**: 设置环境变量：
```bash
export AUTO_COMMIT_REPORTS=false
```

### Q3: setup.sh 和 deploy_and_run.sh 有什么区别？

**A**: 没有区别了！所有功能已统一到 setup.sh，deploy_and_run.sh 可能是旧版本。

### Q4: 拉取代码时有冲突怎么办？

**A**: setup.sh 会自动保存本地修改到 git stash，可以用以下命令恢复：
```bash
git stash list    # 查看备份
git stash pop     # 恢复最近的备份
```

---

## 📚 详细文档

- **重组总结**: `REORGANIZATION_SUMMARY.md`
- **分支信息**: `BRANCH_INFO.md`
- **规范索引**: `standards/00_INDEX.md`
- **系统概览**: `standards/01_SYSTEM_OVERVIEW.md`

---

## 🎉 总结

**记住一条命令**：

```bash
cd ~/cryptosignal && ./setup.sh
```

这就是v7.2部署的**全部**！

---

**维护者**: Claude AI Assistant
**生效日期**: 2025-11-08
