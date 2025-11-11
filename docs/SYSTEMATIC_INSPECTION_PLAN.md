# 系统性检索和修复方案

**生成时间**: 2025-11-10
**目标**: 从setup.sh入口点出发，系统性检索整个执行链路，找出所有问题

---

## 📊 执行链路

```
setup.sh (L184)
  → scripts/realtime_signal_scanner.py
    → ats_core/pipeline/batch_scan_optimized.py
      → ats_core/pipeline/analyze_symbol.py
    → ats_core/pipeline/analyze_symbol_v72.py
    → ats_core/outputs/telegram_fmt.py
```

---

## 🔍 检索方案（按执行顺序）

### Phase 1: 入口点检查
- [ ] setup.sh L184: 启动命令参数正确性
- [ ] scripts/realtime_signal_scanner.py 导入检查
- [ ] 配置文件加载顺序

### Phase 2: 扫描器初始化
- [ ] OptimizedBatchScanner.__init__() 初始化逻辑
- [ ] get_kline_cache() WebSocket缓存状态
- [ ] 配置文件加载（signal_thresholds.json）

### Phase 3: 批量扫描链路
- [ ] batch_scan_optimized.scan() 返回结果结构
- [ ] intermediate_data字段完整性
- [ ] klines/oi_data/cvd_series数据有效性

### Phase 4: 基础分析链路
- [ ] analyze_symbol.py 输入输出完整性
- [ ] 6+4维因子计算正确性
- [ ] intermediate_data数据保存

### Phase 5: v7.2增强链路（关键）
- [ ] _apply_v72_enhancements() 数据读取
- [ ] intermediate_data读取顺序
- [ ] analyze_with_v72_enhancements() 返回结构
- [ ] v72_enhancements字段完整性

### Phase 6: 闸门过滤链路
- [ ] _filter_prime_signals_v72() 过滤逻辑
- [ ] 五道闸门检查
- [ ] confidence阈值检查
- [ ] AntiJitter防抖动

### Phase 7: Telegram发送链路
- [ ] _send_signals_to_telegram_v72() 排序逻辑
- [ ] render_trade_v72() 类型检查
- [ ] v72_enhancements访问安全性
- [ ] telegram_send_wrapper() 调用

---

## 🎯 检查重点

### 数据流完整性
1. intermediate_data → v72_enhancements 传递
2. v72_enhancements 字段类型（必须是dict）
3. 必要字段存在性检查

### 类型安全
1. 所有dict访问使用.get()
2. 所有列表访问检查长度
3. 所有数值计算检查None

### 配置一致性
1. 所有硬编码已移除
2. 所有阈值从config读取
3. 默认值与配置文件一致

---

## 📋 问题分类

### P0 - 致命问题（阻止系统运行）
- v72_enhancements为None导致无法发送
- 数据读取错误导致增强失败
- 类型错误导致崩溃

### P1 - 严重问题（影响核心功能）
- 过滤逻辑错误导致信号丢失
- 配置读取错误导致行为异常
- 数据传递不完整

### P2 - 一般问题（影响用户体验）
- 日志不清晰
- 错误提示不准确
- 性能次优

---

## 🔧 修复原则

1. **按执行顺序修复**: 从入口点到输出，确保每个环节正确
2. **数据完整性优先**: 确保数据在链路中正确传递
3. **类型安全**: 所有访问都要防御性编程
4. **配置化**: 消除所有硬编码
5. **可追溯**: 添加关键日志点

---

## ✅ 验证方法

### 单元验证
```bash
# 1. 配置加载
python3 -c "from ats_core.config.threshold_config import get_thresholds; config = get_thresholds(); print('OK')"

# 2. 模块导入
python3 -c "from scripts.realtime_signal_scanner import OptimizedRealtimeScanner; print('OK')"

# 3. v7.2增强
python3 -c "from ats_core.pipeline.analyze_symbol_v72 import analyze_with_v72_enhancements; print('OK')"
```

### 集成验证
```bash
# 完整扫描测试（10个币种）
python3 scripts/realtime_signal_scanner.py --max-symbols 10 --no-telegram
```

---

## 📝 执行记录

检索开始时间:
预计完成时间:
实际问题数量:
修复完成数量:
