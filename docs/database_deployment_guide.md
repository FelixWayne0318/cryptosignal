# 数据库部署指南

## 📋 快速回答您的问题

### ❓ 问题1: 现在运行这些代码就行了吗？

**✅ 是的！** 您提供的代码完全正确，可以直接运行：

```bash
cd ~/cryptosignal

# 1. 拉取远程分支信息
git fetch origin claude/reorganize-repo-structure-011CUrZaXUMTBXApc3jvsqTh

# 2. 切换到指定分支
git checkout claude/reorganize-repo-structure-011CUrZaXUMTBXApc3jvsqTh

# 3. 拉取该分支的最新代码
git pull origin claude/reorganize-repo-structure-011CUrZaXUMTBXApc3jvsqTh

# 4. 清理Python缓存（重要！确保新代码生效）
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true

# 5. 部署（setup.sh会自动检测当前分支并调用deploy_and_run.sh）
./setup.sh
```

**setup.sh 现在会自动：**
- ✅ 初始化 TradeRecorder 数据库（data/trade_history.db）
- ✅ 初始化 AnalysisDB 数据库（data/analysis.db）
- ✅ 创建所有表结构（6个专业表，125个字段）
- ✅ 验证数据库是否正常工作

---

### ❓ 问题2: 数据库是不是已经在服务器建好了？

**情况1: 如果服务器之前运行过v7.2分支**
- ⚠️ **可能没有**，因为之前的代码有bug
- ✅ 运行 `./setup.sh` 会自动重建或修复数据库

**情况2: 如果是全新部署**
- ❌ **肯定没有**，需要首次创建
- ✅ 运行 `./setup.sh` 会自动创建数据库

**验证数据库是否存在：**
```bash
cd ~/cryptosignal

# 检查数据库文件
ls -lh data/*.db
# 应该看到:
# data/analysis.db       - AnalysisDB (完善的分析数据库)
# data/trade_history.db  - TradeRecorder (简单的信号记录)

# 测试数据库
python3 scripts/init_databases.py
# 应该显示: ✅ 所有数据库初始化成功！
```

---

### ❓ 问题3: 如果更换分支或者服务器，需不需要重新安装数据库？

#### 🔄 更换分支（同一服务器）

**SQLite数据库文件不受分支切换影响：**
- ✅ 数据库文件（`data/*.db`）保存在本地磁盘
- ✅ 已加入 `.gitignore`，不会被git追踪
- ✅ 切换分支时数据库文件保留
- ✅ **不需要重新安装**，数据会保留

**示例：**
```bash
# 当前在 v7.2 分支
cd ~/cryptosignal
ls data/analysis.db  # ✅ 存在，有100个信号

# 切换到其他分支
git checkout main
ls data/analysis.db  # ✅ 仍然存在，数据未丢失

# 切换回 v7.2
git checkout claude/reorganize-repo-structure-011CUrZaXUMTBXApc3jvsqTh
ls data/analysis.db  # ✅ 仍然存在，数据仍然是100个信号
```

**注意事项：**
- ⚠️ 不同分支可能有不同的表结构
- ⚠️ 如果表结构冲突，可能需要删除旧数据库
- ✅ setup.sh 会自动处理（如果表不存在会创建）

#### 🖥️ 更换服务器

**数据库文件不会自动迁移：**
- ❌ 新服务器上没有数据库文件
- ✅ **需要重新创建**，但会自动完成
- ✅ 运行 `./setup.sh` 即可自动创建

**迁移数据（可选）：**
```bash
# 在旧服务器上备份
cd ~/cryptosignal
tar -czf cryptosignal_data_backup.tar.gz data/*.db

# 传输到新服务器
scp cryptosignal_data_backup.tar.gz user@new-server:~/

# 在新服务器上恢复
cd ~/cryptosignal
tar -xzf ~/cryptosignal_data_backup.tar.gz
```

---

### ❓ 问题4: 要不要写入仓库的部署文件，然后实现自动安装服务器？

**✅ 已经实现！** 刚刚更新的文件：

#### 1. 数据库初始化脚本（新增）
**文件**: `scripts/init_databases.py`

**功能**:
- 自动创建 TradeRecorder 数据库
- 自动创建 AnalysisDB 数据库（6个表）
- 验证表结构是否正确
- 显示初始化状态

**使用**:
```bash
# 手动运行
python3 scripts/init_databases.py

# 输出示例：
# ✅ trade_history.db 初始化成功
# ✅ analysis.db 初始化成功
#    - 表结构: 6个专业表
#    - 已记录信号: 0个
```

#### 2. 部署脚本更新（已更新）
**文件**: `setup.sh`

**新增步骤**:
```bash
# 初始化数据库（新增）
echo "🗄️  初始化数据库..."
python3 scripts/init_databases.py || {
    echo "❌ 数据库初始化失败"
    echo "这不会影响系统运行，数据库会在首次使用时自动创建"
}
```

**完整流程**:
1. ✅ 检查Python环境
2. ✅ 安装依赖
3. ✅ 检查配置文件
4. ✅ 配置定时任务
5. ✅ **初始化数据库**（新增！）
6. ✅ 启动系统

#### 3. .gitignore 更新（已更新）
**文件**: `.gitignore`

**新增规则**:
```
# 数据库文件不提交到git
data/*.db
data/*.db-journal
data/*.db-wal
data/*.db-shm
```

**原因**:
- 数据库文件太大（可能几百MB）
- 包含服务器特定数据
- 频繁变化，会产生大量git提交
- 每个服务器应该有独立的数据

---

## 🚀 完整部署流程

### 首次部署（全新服务器）

```bash
# 1. 克隆仓库
cd ~
git clone https://github.com/FelixWayne0318/cryptosignal.git
cd cryptosignal

# 2. 切换到v7.2分支
git checkout claude/reorganize-repo-structure-011CUrZaXUMTBXApc3jvsqTh

# 3. 配置Binance凭证
# 创建 config/binance_credentials.json（参考.example文件）

# 4. 一键部署（自动初始化数据库）
./setup.sh

# 完成！数据库已自动创建
```

### 更新部署（已有仓库）

```bash
cd ~/cryptosignal

# 1. 拉取最新代码
git fetch origin claude/reorganize-repo-structure-011CUrZaXUMTBXApc3jvsqTh
git checkout claude/reorganize-repo-structure-011CUrZaXUMTBXApc3jvsqTh
git pull origin claude/reorganize-repo-structure-011CUrZaXUMTBXApc3jvsqTh

# 2. 清理缓存
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true

# 3. 重新部署（会自动检查/创建数据库）
./setup.sh

# 完成！
```

---

## 📊 数据库文件说明

### 文件位置和大小

| 文件 | 用途 | 初始大小 | 增长速度 |
|------|------|----------|----------|
| `data/trade_history.db` | TradeRecorder | ~20KB | ~100KB/天 |
| `data/analysis.db` | AnalysisDB | ~60KB | ~500KB/天 |

### 数据保留策略

**默认**: 永久保留所有数据

**清理旧数据**（可选）:
```bash
# 备份数据库
cp data/analysis.db data/analysis_backup_$(date +%Y%m%d).db

# 删除数据库（下次运行会重新创建）
rm data/analysis.db data/trade_history.db

# 重新运行会自动创建空数据库
./setup.sh
```

---

## 🔧 故障排查

### 问题1: 数据库初始化失败

```bash
# 检查错误信息
python3 scripts/init_databases.py

# 常见原因：
# 1. 权限问题
chmod -R 755 data/
mkdir -p data

# 2. 依赖问题
pip3 install -r requirements.txt

# 3. Python版本问题
python3 --version  # 需要 ≥ 3.8
```

### 问题2: 表结构错误

```bash
# 删除旧数据库，重新创建
rm data/*.db
python3 scripts/init_databases.py
```

### 问题3: 数据库损坏

```bash
# 备份
cp data/analysis.db data/analysis_corrupted.db

# 尝试修复（SQLite自带）
sqlite3 data/analysis.db "PRAGMA integrity_check;"

# 如果无法修复，删除重建
rm data/analysis.db
python3 scripts/init_databases.py
```

---

## ✅ 总结

### 回答您的所有问题：

1. ✅ **可以直接运行您提供的代码**
2. ✅ **setup.sh 会自动初始化数据库**
3. ✅ **更换分支不需要重新安装**（数据保留）
4. ✅ **更换服务器需要重新创建**（自动完成）
5. ✅ **已写入部署文件**（setup.sh + scripts/init_databases.py）
6. ✅ **已实现自动安装**（运行setup.sh即可）

### 关键文件：

| 文件 | 用途 | 状态 |
|------|------|------|
| `scripts/init_databases.py` | 数据库初始化脚本 | ✅ 新增 |
| `setup.sh` | 部署脚本 | ✅ 已更新 |
| `.gitignore` | Git忽略规则 | ✅ 已更新 |
| `docs/database_deployment_guide.md` | 本文档 | ✅ 新增 |

### 下一步：

```bash
cd ~/cryptosignal

# 按照您提供的命令执行即可
git fetch origin claude/reorganize-repo-structure-011CUrZaXUMTBXApc3jvsqTh
git checkout claude/reorganize-repo-structure-011CUrZaXUMTBXApc3jvsqTh
git pull origin claude/reorganize-repo-structure-011CUrZaXUMTBXApc3jvsqTh
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
./setup.sh

# 数据库会自动初始化，开始采集数据！
```

🎉 **完成！一切都已自动化！**
