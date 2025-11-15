# CryptoSignal 测试目录

## 📋 目录说明

> **v7.2.44状态**: 预留目录（Placeholder）

本目录是v7.2版本仓库结构重组的一部分，用于存放单元测试、集成测试等测试文件。

### 当前状态

- **v7.2.43清理**: 测试文件已被清理，只保留README.md作为占位符
- **原因**: 系统已稳定运行，临时测试文件已不需要
- **测试方式**: 通过 `./setup.sh` 和实际运行来验证系统功能

### 如需添加测试

如果需要添加新的测试文件，请遵循以下模板：

#### 测试文件命名规范
- 单元测试: `test_<module_name>.py`
- 集成测试: `test_<feature>_integration.py`
- 性能测试: `test_<module>_performance.py`

---

## 📝 测试模板

**v7.2测试模板**:
```python
#!/usr/bin/env python3
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from ats_core.pipeline.analyze_symbol import analyze_symbol
from ats_core.outputs.telegram_fmt import render_trade_v72

# 测试单个币种
result = analyze_symbol('BTCUSDT')

if result:
    print(render_trade_v72(result))
else:
    print("分析失败")
```

---

## 🚀 快速开始

**运行v7.2集成测试**:
```bash
# 完整集成测试
python3 tests/test_v72_integration.py

# 测试单个币种
python3 tests/test_single_symbol.py ETHUSDT
```

---

## 📞 问题反馈

如发现测试问题或需要新测试，请提交issue到项目仓库。

---

**说明**: v7.2.43仓库清理后，仅保留核心测试文件。历史测试文件已归档到Git历史记录中。
