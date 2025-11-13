# CryptoSignal 测试目录

## v7.2 当前测试

### ✅ 活跃测试

#### `test_v72_integration.py` - v7.2集成测试
**用途**: 测试v7.2集成和数据采集功能

**测试内容**:
- TradeRecorder数据库创建
- v7.2扫描器（不发送Telegram）
- 数据记录验证
- 统计信息显示

**运行方法**:
```bash
cd /home/user/cryptosignal
python3 tests/test_v72_integration.py
```

---

#### `test_single_symbol.py` - 单币种快速测试
**用途**: 分析单个币种并输出详细格式，验证分析流程

**测试内容**:
- 单个币种完整分析
- 因子计算验证
- 详细输出格式
- 门控系统验证

**运行方法**:
```bash
cd /home/user/cryptosignal
python3 tests/test_single_symbol.py BTCUSDT
```

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
