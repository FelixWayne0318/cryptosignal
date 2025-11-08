# v7.2 服务器测试指南

## 在你的Vultr服务器上运行测试

### 方法1: 使用测试脚本（推荐）

#### 1. 通过Termius连接到服务器
```bash
ssh user@your-server-ip
```

#### 2. 进入项目目录
```bash
cd /path/to/cryptosignal
```

#### 3. 拉取最新代码
```bash
git fetch origin
git checkout claude/reorganize-repo-structure-011CUrZaXUMTBXApc3jvsqTh
git pull origin claude/reorganize-repo-structure-011CUrZaXUMTBXApc3jvsqTh
```

#### 4. 给测试脚本添加执行权限
```bash
chmod +x run_server_tests.sh
```

#### 5. 运行测试脚本
```bash
./run_server_tests.sh
```

### 预期输出

如果一切正常，你应该看到：

```
======================================
v7.2 Stage 1 服务器测试
======================================

检查Python版本...
Python 3.x.x
✅ Python版本检查通过

当前目录: /path/to/cryptosignal
✅ 目录检查通过

======================================
测试1: v7.2核心功能
======================================
============================================================
测试1: F因子v2
============================================================
...
✅ F因子v2测试通过: F=94 (资金领先价格)
...
============================================================
✅ v7.2 Stage 1 所有测试通过!
============================================================
✅ v7.2核心功能测试通过

======================================
测试2: Telegram消息格式
======================================
...
✅ 所有测试完成！
✅ Telegram消息格式测试通过

======================================
测试3: 模块导入检查
======================================
✅ fund_leading模块加载成功
✅ factor_groups模块加载成功
✅ calibration模块加载成功
✅ gates模块加载成功
✅ analyze_symbol_v72模块加载成功
✅ telegram_fmt模块加载成功
✅ 所有模块导入测试通过

======================================
测试4: 文件完整性检查
======================================
✅ ats_core/features/fund_leading.py
✅ ats_core/scoring/factor_groups.py
✅ ats_core/calibration/empirical_calibration.py
✅ ats_core/pipeline/gates.py
✅ ats_core/pipeline/analyze_symbol_v72.py
✅ ats_core/outputs/telegram_fmt.py
✅ test_v72_stage1.py
✅ test_telegram_v72.py
✅ 所有文件完整性检查通过

======================================
测试总结
======================================
✅ v7.2核心功能测试: 通过
✅ Telegram消息格式测试: 通过
✅ 模块导入测试: 通过
✅ 文件完整性测试: 通过

🎉 v7.2 Stage 1 服务器测试全部通过！
💡 系统已准备好部署到生产环境
```

---

### 方法2: 手动运行单个测试

如果你想单独运行测试：

#### 测试v7.2核心功能
```bash
cd /path/to/cryptosignal
python3 test_v72_stage1.py
```

#### 测试Telegram消息格式
```bash
cd /path/to/cryptosignal
python3 test_telegram_v72.py
```

#### 测试模块导入
```bash
# 测试所有v7.2模块是否可以正常导入
python3 -c "
from ats_core.features.fund_leading import score_fund_leading_v2
from ats_core.scoring.factor_groups import calculate_grouped_score
from ats_core.calibration.empirical_calibration import EmpiricalCalibrator
from ats_core.pipeline.gates import FourGatesFilter
from ats_core.pipeline.analyze_symbol_v72 import analyze_with_v72_enhancements
from ats_core.outputs.telegram_fmt import render_signal_v72, render_watch_v72, render_trade_v72
print('✅ 所有模块导入成功')
"
```

---

### 方法3: 快速检查（只验证基本功能）

```bash
cd /path/to/cryptosignal

# 1行命令运行所有测试
python3 test_v72_stage1.py && python3 test_telegram_v72.py && echo "✅ 所有测试通过"
```

---

## 故障排查

### 问题1: Permission denied
```bash
# 解决方案
chmod +x run_server_tests.sh
```

### 问题2: Python3 not found
```bash
# 检查Python版本
python --version
# 或
python3 --version

# 如果没有python3，创建软链接
sudo ln -s /usr/bin/python /usr/bin/python3
```

### 问题3: Module not found
```bash
# 确保在正确的目录
pwd  # 应该显示 /path/to/cryptosignal

# 检查PYTHONPATH
export PYTHONPATH=/path/to/cryptosignal:$PYTHONPATH

# 重新运行测试
python3 test_v72_stage1.py
```

### 问题4: Git分支不存在
```bash
# 刷新远程分支列表
git fetch origin

# 查看所有分支
git branch -a

# 切换到正确的分支
git checkout claude/reorganize-repo-structure-011CUrZaXUMTBXApc3jvsqTh
```

---

## 测试后续步骤

### 如果所有测试通过 ✅

1. **查看测试报告**（可选）
   ```bash
   cat SERVER_TEST_REPORT_v72.md
   ```

2. **准备部署到生产环境**
   - v7.2 Stage 1已准备就绪
   - 可以开始小规模测试（10-20个币种）

3. **下一步集成工作**
   - 修改主扫描脚本使用v7.2
   - 更新Telegram publisher配置
   - 开始收集真实交易数据

### 如果测试失败 ❌

1. **查看错误信息**
   - 仔细阅读错误输出
   - 确定是哪个测试失败

2. **检查依赖**
   ```bash
   pip3 list | grep -E "numpy|pandas|requests"
   ```

3. **检查文件权限**
   ```bash
   ls -la ats_core/features/fund_leading.py
   ls -la test_v72_stage1.py
   ```

4. **联系支持**
   - 复制完整的错误信息
   - 提供系统信息（Python版本、OS版本）

---

## 性能基准

在Vultr 50GB VPS上的预期性能：

| 测试 | 预期时间 | 预期内存 |
|------|----------|----------|
| test_v72_stage1.py | < 1秒 | < 50MB |
| test_telegram_v72.py | < 1秒 | < 50MB |
| 总测试时间 | < 5秒 | < 100MB |

如果测试时间显著超过这些值，可能存在性能问题。

---

## 自动化测试（可选）

如果你想定期运行测试，可以设置cron任务：

```bash
# 编辑crontab
crontab -e

# 添加每天早上8点运行测试
0 8 * * * cd /path/to/cryptosignal && ./run_server_tests.sh >> /var/log/v72_tests.log 2>&1

# 查看测试日志
tail -f /var/log/v72_tests.log
```

---

## 测试文件说明

| 文件 | 用途 | 运行时间 |
|------|------|----------|
| `run_server_tests.sh` | 一键运行所有测试 | ~5秒 |
| `test_v72_stage1.py` | v7.2核心功能测试 | ~1秒 |
| `test_telegram_v72.py` | Telegram消息格式测试 | ~1秒 |
| `SERVER_TEST_REPORT_v72.md` | 详细测试报告（参考） | N/A |
| `SERVER_TEST_INSTRUCTIONS.md` | 本文档 | N/A |

---

## 快速命令参考

```bash
# 最小测试（只测试核心功能）
python3 test_v72_stage1.py

# 完整测试（包括Telegram）
python3 test_v72_stage1.py && python3 test_telegram_v72.py

# 自动化测试（使用脚本）
./run_server_tests.sh

# 模块导入快速测试
python3 -c "from ats_core.pipeline.analyze_symbol_v72 import *; print('OK')"

# 查看系统资源
free -h && df -h
```

---

## 需要帮助？

如果遇到问题：
1. 检查Python版本（需要Python 3.6+）
2. 确保在正确的分支上
3. 验证所有文件都已正确拉取
4. 查看详细错误信息
5. 参考故障排查部分

---

**测试愉快！** 🚀
