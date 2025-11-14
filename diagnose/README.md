# 🔍 系统诊断工具使用说明

## 📋 目录说明

> **v7.2.44状态**: 预留目录（Placeholder）

本目录是v7.2版本仓库结构重组的一部分，用于存放系统诊断、配置验证等工具文件。

### 当前状态

- **v7.2.43清理**: 诊断文件已被清理，只保留README.md作为占位符
- **原因**: 诊断功能已集成到主程序的日志输出中
- **诊断方式**:
  - 查看扫描器日志: `tail -f ~/cryptosignal_*.log`
  - 验证配置: `python3 -c "from ats_core.config.threshold_config import get_thresholds; print(get_thresholds().config)"`
  - 测试导入: `python3 -c "from ats_core.pipeline.analyze_symbol_v72 import analyze_with_v72_enhancements"`

---

## 🎯 诊断场景

### 场景1: 验证阈值是否生效

**问题**: 修改了配置文件，但系统行为未改变

**解决**:
```bash
# 1. 验证配置
python3 diagnose/verify_config.py

# 2. 清理Python缓存（重要！）
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -name "*.pyc" -delete

# 3. 重新启动系统
./setup.sh
```

### 场景2: 测试单个币种

**问题**: 想快速验证某个币种的分析结果

**解决**:
```bash
python3 tests/test_single_symbol.py BTCUSDT
```

### 场景3: 完整系统测试

**问题**: 验证v7.2增强功能是否正常工作

**解决**:
```bash
python3 tests/test_v72_integration.py
```

---

## 🔧 常见问题

### Q1: 配置修改后未生效

**原因**: Python缓存了旧的配置

**解决**:
```bash
# 清理缓存
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -name "*.pyc" -delete

# 重启系统
pkill -f realtime_signal_scanner
./setup.sh
```

### Q2: 如何查看当前阈值

**解决**:
```bash
python3 diagnose/verify_config.py
```

### Q3: 数据库初始化失败

**解决**:
```bash
python3 scripts/init_databases.py
```

---

## 📚 相关文档

- **系统配置**: [standards/02_ARCHITECTURE.md](../standards/02_ARCHITECTURE.md)
- **部署指南**: [standards/deployment/DEPLOYMENT_GUIDE.md](../standards/deployment/DEPLOYMENT_GUIDE.md)
- **测试说明**: [tests/README.md](../tests/README.md)

---

**说明**: v7.2.43仓库清理后，诊断工具精简为核心配置验证。复杂诊断功能已集成到主程序的日志输出中。
