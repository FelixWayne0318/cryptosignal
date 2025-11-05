# 诊断系统

本目录包含系统诊断工具和诊断报告。

## 📁 目录结构

### 诊断脚本
- `diagnostic_scan.py` - 诊断扫描器（命令行输出）
- `diagnostic_with_telegram.py` - 诊断扫描器（含Telegram通知）
- `run_diagnostic.sh` - 快速诊断脚本
- `run_diagnostic_telegram.sh` - 带Telegram的诊断脚本

### 诊断文档
- `DIAGNOSTIC_GUIDE.md` - 诊断指南
- `DIAGNOSTIC_README.md` - 诊断系统说明
- `CRITICAL_DIAGNOSIS_REPORT.md` - 关键诊断报告

## 🔧 使用方法

### 快速诊断（无Telegram）
```bash
cd ~/cryptosignal
./diagnose/run_diagnostic.sh
```

### 诊断并发送到Telegram
```bash
cd ~/cryptosignal
./diagnose/run_diagnostic_telegram.sh
```

### Python直接调用
```bash
cd ~/cryptosignal
python3 diagnose/diagnostic_scan.py --max-symbols 20
```

## 📊 诊断内容

诊断系统会检查：
- ✅ 数据获取（K线、订单簿、持仓等）
- ✅ 因子计算（T/M/C/V/O/B + L/S/F/I）
- ✅ 门控系统（DataQual/EV/Execution/Probability）
- ✅ Prime评分和发布机制
- ✅ Telegram消息格式

## 🎯 适用场景

- 🔍 系统异常排查
- 📈 性能分析
- ✅ 功能验证
- 🧪 版本升级后测试
