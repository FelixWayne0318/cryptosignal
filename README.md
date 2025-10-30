# CryptoSignal v6.0

> **加密货币信号分析系统 - 10+1维因子体系**

---

## 🚀 快速开始

### 新用户/新对话框必读

**请先阅读规范文档**（5-10分钟快速了解整个系统）：

1. **[规范/SYSTEM_OVERVIEW.md](./规范/SYSTEM_OVERVIEW.md)** ⭐ 必读
   - 系统总览和核心功能
   - 主文件入口和运行方式
   - 目录结构和关键文件
   - 10+1维因子系统介绍

2. **[规范/MODIFICATION_RULES.md](./规范/MODIFICATION_RULES.md)**
   - 代码修改规范
   - 什么场景修改哪个文件
   - 禁止修改的文件列表

3. **[规范/CONFIGURATION_GUIDE.md](./规范/CONFIGURATION_GUIDE.md)**
   - 配置参数详解
   - 所有参数的含义和调整建议

4. **[规范/ARCHITECTURE.md](./规范/ARCHITECTURE.md)**
   - 系统架构详解
   - 数据流和核心模块

**完整文档索引**: [规范/README.md](./规范/README.md)

---

## 📦 项目结构

```
cryptosignal/
│
├── 规范/                              # ⭐ 系统规范文档（新对话框必读）
│   ├── README.md                      # 文档索引
│   ├── SYSTEM_OVERVIEW.md             # 系统总览
│   ├── MODIFICATION_RULES.md          # 修改规范
│   ├── CONFIGURATION_GUIDE.md         # 配置参数详解
│   └── ARCHITECTURE.md                # 技术架构
│
├── scripts/
│   └── realtime_signal_scanner.py     # ⭐ 主文件（唯一运行入口）
│
├── config/
│   ├── params.json                    # ⭐ 核心参数配置
│   └── telegram.json                  # Telegram配置
│
├── ats_core/                          # 核心代码库
│   ├── pipeline/                      # 分析管道
│   ├── features/                      # 基础因子（T/M/C/S/V/O/F）
│   ├── factors_v2/                    # 新增因子（L/B/Q/I）
│   ├── scoring/                       # 评分系统
│   ├── sources/                       # 数据源
│   ├── outputs/                       # 输出模块
│   └── ...
│
├── docs/                              # 历史文档
├── tests/                             # 单元测试
└── tools/                             # 辅助工具
```

---

## 🎯 主要功能

- **10+1维因子分析系统**（T/M/C/S/V/O/L/B/Q/I + F调节器）
- **WebSocket优化**（0次API调用，12-15秒/200币种）
- **自适应权重系统**（根据市场状态动态调整）
- **Prime信号判定**（v6.0权重百分比系统，阈值35分）
- **Telegram自动推送**（格式化信号消息）

---

## 🏃 运行方式

### 主文件（唯一入口）

```bash
# 单次扫描
python3 scripts/realtime_signal_scanner.py --once

# 持续扫描（每5分钟）
python3 scripts/realtime_signal_scanner.py --interval 300

# 测试模式（只扫描20个币种）
python3 scripts/realtime_signal_scanner.py --max-symbols 20 --once
```

### 服务器部署

```bash
# 拉取最新代码
cd ~/cryptosignal
git pull origin <branch>

# 清除缓存
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null

# 后台运行
nohup python3 scripts/realtime_signal_scanner.py --interval 300 > scanner.log 2>&1 &

# 查看日志
tail -f scanner.log
```

---

## ⚙️ 配置

### 修改权重

编辑 `config/params.json` → `weights` 字段

**要求**: 总权重必须=100%

```json
{
  "weights": {
    "T": 13.9,  "M": 8.3,  "C": 11.1,  "S": 5.6,
    "V": 8.3,   "O": 11.1, "L": 11.1,  "B": 8.3,
    "Q": 5.6,   "I": 6.7,  "E": 0,     "F": 10.0
  }
}
```

详见: [规范/CONFIGURATION_GUIDE.md](./规范/CONFIGURATION_GUIDE.md)

### 修改Prime阈值

编辑 `config/params.json` → `publish` 字段

```json
{
  "publish": {
    "prime_prob_min": 0.62,     // 降低→信号更多
    "prime_dims_ok_min": 4,
    "prime_dim_threshold": 65
  }
}
```

详见: [规范/MODIFICATION_RULES.md § 2](./规范/MODIFICATION_RULES.md#2-调整prime阈值)

---

## 📊 系统版本

- **当前版本**: v6.0（权重百分比系统）
- **升级时间**: 2025-10
- **主要变更**:
  - 180分制 → 100%百分比系统
  - F因子参与评分（权重10.0%）
  - Prime阈值从65分调整为35分

---

## 🔗 重要链接

- **规范文档**: [规范/README.md](./规范/README.md)
- **主文件**: [scripts/realtime_signal_scanner.py](./scripts/realtime_signal_scanner.py)
- **配置文件**: [config/params.json](./config/params.json)

---

## 📝 开发规范

### 修改代码前必读

1. 查看 [规范/MODIFICATION_RULES.md](./规范/MODIFICATION_RULES.md) 确定修改哪个文件
2. 查看 [规范/CONFIGURATION_GUIDE.md](./规范/CONFIGURATION_GUIDE.md) 了解参数含义
3. 修改后清除缓存并测试

### 禁止修改的文件

以下文件包含核心逻辑，除非完全理解系统架构，否则禁止修改：
- `ats_core/pipeline/batch_scan_optimized.py`
- `ats_core/data/realtime_kline_cache.py`
- `ats_core/sources/binance.py`
- `ats_core/cfg.py`

详见: [规范/MODIFICATION_RULES.md § 禁止修改的文件](./规范/MODIFICATION_RULES.md#-禁止修改的文件)

---

## 🎓 学习路径

### 初级用户（使用系统）
1. 阅读 [规范/SYSTEM_OVERVIEW.md](./规范/SYSTEM_OVERVIEW.md)
2. 运行测试
3. 调整Telegram配置

### 中级用户（调整参数）
1. 阅读 [规范/CONFIGURATION_GUIDE.md](./规范/CONFIGURATION_GUIDE.md)
2. 调整权重或阈值
3. 观察效果

### 高级用户（修改代码）
1. 阅读 [规范/ARCHITECTURE.md](./规范/ARCHITECTURE.md)
2. 理解核心模块
3. 按规范修改

---

## ⚠️ 注意事项

1. **所有修改必须符合规范**（参考 `规范/` 文件夹）
2. **主文件**: 只有 `scripts/realtime_signal_scanner.py`
3. **权重总和**: 必须=100%
4. **修改后**: 清除缓存并测试

---

## 📞 支持

- 遇到问题: 先查看 [规范/README.md § 常见问题速查](./规范/README.md#-常见问题速查)
- 新对话框: 先阅读 [规范/SYSTEM_OVERVIEW.md](./规范/SYSTEM_OVERVIEW.md)

---

**版本**: v6.0
**最后更新**: 2025-10-30
