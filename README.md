# CryptoSignal v6.4 Phase 2

> **加密货币信号分析系统 - 10+1维因子体系**
> v6.4 Phase 2: 新币数据流架构改造完成

---

## 🚀 快速部署

### 一键全自动部署（推荐）⭐⭐⭐

```bash
cd ~/cryptosignal
git fetch origin claude/review-system-overview-011CUhLQjByWuXC1bySJCHKQ
git checkout claude/review-system-overview-011CUhLQjByWuXC1bySJCHKQ
git pull origin claude/review-system-overview-011CUhLQjByWuXC1bySJCHKQ
./deploy_and_run.sh  # 全自动：检测环境、安装依赖、部署、启动
```

**功能**:
- ✅ 自动环境检测
- ✅ 自动依赖安装
- ✅ 首次部署引导
- ✅ 自动启动系统

详细文档见: [standards/deployment/DEPLOYMENT_GUIDE.md](standards/deployment/DEPLOYMENT_GUIDE.md)

---

## 📚 规范文档体系

> ⚠️ **重要**: 所有规范文档已重组并统一到 `standards/` 目录

### 快速导航

| 角色 | 推荐文档 | 优先级 |
|------|---------|--------|
| **新用户** | [standards/deployment/QUICK_START.md](standards/deployment/QUICK_START.md) | ⭐⭐⭐⭐⭐ |
| **运维人员** | [standards/deployment/DEPLOYMENT_GUIDE.md](standards/deployment/DEPLOYMENT_GUIDE.md) | ⭐⭐⭐⭐⭐ |
| **开发人员** | [standards/01_SYSTEM_OVERVIEW.md](standards/01_SYSTEM_OVERVIEW.md) | ⭐⭐⭐⭐⭐ |
| **量化研究** | [standards/specifications/FACTOR_SYSTEM.md](standards/specifications/FACTOR_SYSTEM.md) | ⭐⭐⭐⭐ |

### 完整索引

→ **[standards/00_INDEX.md](standards/00_INDEX.md)** - 规范文档总索引（入口）

---

## 🎯 系统版本

**当前版本**: v6.4 Phase 2
**更新日期**: 2025-11-02

### 版本历史

| 版本 | 日期 | 关键特性 | 合规度 |
|------|------|---------|--------|
| v6.0 | 2025-10-30 | 10+1维因子系统 | - |
| v6.1 | 2025-11-01 | I因子架构修正 | - |
| v6.2 | 2025-11-02 | 4个Critical Bug修复 | - |
| v6.3 | 2025-11-02 | 解决0信号困境 | - |
| v6.3.2 | 2025-11-02 | 新币逻辑冲突修复 | 12.8% |
| **v6.4** | **2025-11-02** | **新币数据流架构改造** | **40%** |

详见: [standards/03_VERSION_HISTORY.md](standards/03_VERSION_HISTORY.md)

---

## 📦 主要功能

### v6.4 Phase 2 核心改进

✅ **新币数据流分离**
- 数据获取前快速预判
- 新币使用1m/5m/15m数据（vs 成熟币1h/4h）
- AVWAP锚点计算

✅ **WebSocket实时订阅**
- kline_1m/5m/15m实时流
- 指数回退重连
- 心跳监控与DataQual降级

✅ **架构性改进**
- 解决数据获取顺序倒置问题
- 为Phase 3新币专用因子做准备

详见: [standards/specifications/NEWCOIN.md](standards/specifications/NEWCOIN.md)

### 核心系统

- **10+1维因子系统** (T/M/C/S/V/O/L/B/Q/I + F调节器)
- **四门系统** (DataQual/EV/Execution/Probability)
- **防抖动机制** (入场/确认/冷却)
- **新币通道** (Phase 2已实现数据流，Phase 3-4待完成)

---

## 🏃 运行方式

### 主入口文件

```bash
# 单次扫描
python3 scripts/realtime_signal_scanner.py

# 定期扫描（每5分钟）
python3 scripts/realtime_signal_scanner.py --interval 300

# 测试模式（10个币种）
python3 scripts/realtime_signal_scanner.py --max-symbols 10
```

### 后台运行（Screen）

```bash
# 启动Screen会话
screen -S cryptosignal
python3 scripts/realtime_signal_scanner.py --interval 300

# 分离会话: Ctrl+A 然后 D
# 重连会话: screen -r cryptosignal
```

---

## ⚙️ 配置文件

### 核心配置

- **`config/params.json`** - 权重、阈值、发布参数
- **`config/telegram.json`** - Telegram通知配置
- **`config/binance_credentials.json`** - Binance API凭证

### 修改权重

```json
{
  "weights": {
    "T": 13.9, "M": 8.3, "C": 11.1, "S": 5.6,
    "V": 8.3, "O": 11.1, "L": 11.1, "B": 8.3,
    "Q": 5.6, "F": 0.0, "I": 0.0
  }
}
```

**要求**: A层9因子总和必须=100%，B层调制器(F/I)=0

详见: [standards/configuration/PARAMS_SPEC.md](standards/configuration/PARAMS_SPEC.md)

---

## 📊 项目结构

```
cryptosignal/
├── standards/                    # ⭐ 规范文档（统一入口）
│   ├── 00_INDEX.md              # 总索引
│   ├── 01_SYSTEM_OVERVIEW.md    # 系统概览
│   ├── 03_VERSION_HISTORY.md    # 版本历史
│   ├── specifications/          # 规范子系统
│   ├── deployment/              # 部署运维
│   ├── configuration/           # 配置管理
│   └── development/             # 开发指南
│
├── scripts/
│   └── realtime_signal_scanner.py   # ⭐ 主入口
│
├── ats_core/                    # 核心代码
│   ├── pipeline/                # 分析流水线
│   ├── factors_v2/              # 因子计算
│   ├── gates/                   # 四门系统
│   ├── publishing/              # 发布系统
│   └── data_feeds/              # 数据获取（Phase 2新增）
│
├── config/                      # 配置文件
│   ├── params.json
│   ├── telegram.json
│   └── binance_credentials.json
│
├── deploy_and_run.sh            # ⭐ 一键部署脚本
└── test_phase2.py               # Phase 2测试脚本
```

---

## 🔬 测试

### Phase 2测试

```bash
# 测试新币数据获取
python3 test_phase2.py BTCUSDT

# 测试新币vs成熟币
python3 test_phase2.py BTCUSDT ETHUSDT
```

---

## 🎓 学习路径

### 新用户

1. 阅读: [01_SYSTEM_OVERVIEW.md](standards/01_SYSTEM_OVERVIEW.md)
2. 部署: `./deploy_and_run.sh`
3. 配置: [deployment/TELEGRAM_SETUP.md](standards/deployment/TELEGRAM_SETUP.md)

### 开发人员

1. 系统概览: [01_SYSTEM_OVERVIEW.md](standards/01_SYSTEM_OVERVIEW.md)
2. 架构设计: [02_ARCHITECTURE.md](standards/02_ARCHITECTURE.md)
3. 因子规范: [specifications/FACTOR_SYSTEM.md](standards/specifications/FACTOR_SYSTEM.md)
4. 新币规范: [specifications/NEWCOIN.md](standards/specifications/NEWCOIN.md)
5. 开发流程: [development/WORKFLOW.md](standards/development/WORKFLOW.md)

---

## 📈 下一步计划

### Phase 3: 新币专用因子与模型（v6.5）

**目标**: 合规度40% → 65%

**待实现**:
- T_new/M_new/S_new因子（基于ZLEMA_1m/5m）
- 点火-成势-衰竭模型
- 新币专用权重配置

**工作量**: 4-6天

详见: [specifications/NEWCOIN.md § 9](standards/specifications/NEWCOIN.md#9-实施进度phase-2-phase-4)

---

## ⚠️ 注意事项

1. **规范文档**：所有规范已统一到 `standards/` 目录
2. **版本**: 当前为v6.4 Phase 2，合规度40%
3. **主入口**: `scripts/realtime_signal_scanner.py`
4. **部署脚本**: `deploy_and_run.sh`
5. **配置**: 修改 `config/params.json` 后需清除缓存

---

## 📞 支持

- **规范文档**: [standards/00_INDEX.md](standards/00_INDEX.md)
- **快速参考**: [standards/reference/QUICK_REFERENCE.md](standards/reference/QUICK_REFERENCE.md)
- **问题反馈**: GitHub Issues

---

**版本**: v6.4 Phase 2
**最后更新**: 2025-11-02
**分支**: claude/review-system-overview-011CUhLQjByWuXC1bySJCHKQ
