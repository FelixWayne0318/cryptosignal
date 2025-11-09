# v7.2数据持久化问题修复总结

## ✅ 已修复

### 问题根源
v7.2第二阶段数据库和报告使用**相对路径**，导致在工作目录不正确时写入失败。

### 修复内容
1. **trade_recorder.py**: 改用绝对路径 `/home/user/cryptosignal/data/trade_history.db`
2. **analysis_db.py**: 改用绝对路径 `/home/user/cryptosignal/data/analysis.db`

## 🔧 如何使用

### 方式1：自动修复（推荐）
```bash
cd ~/cryptosignal
git pull  # 获取最新修复
bash setup.sh  # 自动重启
```

### 方式2：手动运行修复脚本
```bash
cd ~/cryptosignal
python3 fix_v72_paths.py  # 修复路径配置
pkill -f realtime_signal_scanner  # 停止旧进程
bash setup.sh  # 重新启动
```

### 方式3：诊断检查
```bash
cd ~/cryptosignal
python3 diagnose_v72_issue.py  # 检查当前配置
```

## 📊 验证修复成功

运行扫描后检查：

### 1. 数据库写入
```bash
python3 << 'EOF'
import sys
sys.path.insert(0, '/home/user/cryptosignal')
from ats_core.data.trade_recorder import get_recorder

recorder = get_recorder()
stats = recorder.get_statistics()
print(f"信号总数: {stats['total_signals']}")
print(f"通过闸门: {stats['gates_passed']}")
EOF
```

### 2. 报告文件更新
```bash
ls -lht ~/cryptosignal/reports/latest/
# 查看文件时间是否是最新的
```

### 3. Git自动提交
```bash
cd ~/cryptosignal
git log --oneline -5 | grep "scan:"
# 应该看到最新的扫描提交
```

## 📝 修复前后对比

### 修复前
```python
# ❌ 相对路径（依赖工作目录）
db_path = "data/trade_history.db"

# 工作目录错误时写入位置错误
# 例如：/home/cryptosignal/cryptosignal/data/trade_history.db (错误路径)
```

### 修复后
```python
# ✅ 绝对路径（不受工作目录影响）
db_path = "/home/user/cryptosignal/data/trade_history.db"

# 始终写入正确位置
```

## 🎯 预期效果

修复后，每次扫描将：
1. ✅ 写入信号快照到数据库 (`data/trade_history.db`)
2. ✅ 写入分析数据到数据库 (`data/analysis.db`)
3. ✅ 更新统计报告文件 (`reports/latest/`)
4. ✅ 自动提交报告到Git

## ❓ 常见问题

### Q: 修复后还是没有数据？
A: 检查进程是否重启：
```bash
ps aux | grep realtime_signal_scanner
# 如果没有运行，执行: bash setup.sh
```

### Q: 如何查看历史数据？
A:
```bash
# 查看数据库
python3 -c "from ats_core.data.trade_recorder import get_recorder; print(get_recorder().get_statistics())"

# 查看报告历史
ls -lht ~/cryptosignal/reports/history/
```

### Q: 如何手动触发扫描？
A:
```bash
cd ~/cryptosignal
python3 scripts/realtime_signal_scanner_v72.py --max-symbols 20 --no-telegram
```

## 📂 相关文件

- 修复脚本: `fix_v72_paths.py`
- 诊断脚本: `diagnose_v72_issue.py`
- 详细分析: `docs/v72_path_fix_analysis.md`
- 原始设计: `docs/v72_data_storage_design.md`

## ✅ 下一步

1. 拉取最新代码: `cd ~/cryptosignal && git pull`
2. 重启服务: `bash setup.sh`
3. 等待下次扫描（每5分钟）
4. 验证数据正确写入

---

**修复时间**: 2025-11-08
**状态**: ✅ 已修复并推送
