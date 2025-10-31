# 代码修改规范

> **本文档定义了不同修改场景下应该操作的文件，避免修改混乱**

---

## 📋 修改场景导航

| 修改需求 | 修改文件 | 难度 |
|---------|---------|------|
| [调整因子权重](#1-调整因子权重) | `config/params.json` | ⭐ 简单 |
| [调整Prime阈值](#2-调整prime阈值) | `config/params.json` | ⭐ 简单 |
| [修改Telegram配置](#3-修改telegram配置) | `config/telegram.json` | ⭐ 简单 |
| [调整扫描参数](#4-调整扫描参数) | `scripts/realtime_signal_scanner.py` | ⭐⭐ 中等 |
| [修改因子计算逻辑](#5-修改因子计算逻辑) | `ats_core/features/*` 或 `ats_core/factors_v2/*` | ⭐⭐⭐ 困难 |
| [修改评分公式](#6-修改评分公式) | `ats_core/scoring/scorecard.py` | ⭐⭐⭐ 困难 |
| [修改Telegram消息格式](#7-修改telegram消息格式) | `ats_core/outputs/telegram_fmt.py` | ⭐⭐ 中等 |
| [添加新因子](#8-添加新因子) | 多个文件 | ⭐⭐⭐⭐ 非常困难 |

---

## 1. 调整因子权重

### 📍 修改文件
```
config/params.json
```

### 🎯 修改位置
```json
{
  "weights": {
    "T": 13.9,  // 趋势权重
    "M": 8.3,   // 动量权重
    "C": 11.1,  // 资金流权重
    "S": 5.6,   // 结构权重
    "V": 8.3,   // 量能权重
    "O": 11.1,  // 持仓权重
    "L": 11.1,  // 流动性权重
    "B": 8.3,   // 基差权重
    "Q": 5.6,   // 清算权重
    "I": 6.7,   // 独立性权重
    "E": 0,     // 废弃
    "F": 10.0   // 资金领先权重
  }
}
```

### ✅ 注意事项
1. **总权重必须=100%**
2. **F因子权重不能为0**（v6.0升级后F参与评分）
3. **E因子已废弃**（权重保持0）
4. 修改后清除Python缓存：
   ```bash
   find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
   ```

### 📝 修改示例

**场景：加强趋势因子的影响**
```json
{
  "weights": {
    "T": 18.0,  // 13.9 → 18.0 (+4.1)
    "M": 8.3,
    "C": 11.1,
    "S": 5.6,
    "V": 8.3,
    "O": 11.1,
    "L": 9.0,   // 11.1 → 9.0 (-2.1, 平衡总权重)
    "B": 6.3,   // 8.3 → 6.3 (-2.0, 平衡总权重)
    "Q": 5.6,
    "I": 6.7,
    "E": 0,
    "F": 10.0
  }
  // 总权重：18.0+8.3+11.1+5.6+8.3+11.1+9.0+6.3+5.6+6.7+0+10.0 = 100.0 ✅
}
```

---

## 2. 调整Prime阈值

### 📍 修改文件
```
config/params.json
```

### 🎯 修改位置
```json
{
  "publish": {
    "prime_prob_min": 0.62,        // Prime最低概率阈值（调整此处）
    "prime_dims_ok_min": 4,        // Prime最低达标维度数
    "prime_dim_threshold": 65,     // 单维度达标阈值
    "watch_prob_min": 0.58,
    "watch_prob_max": 0.61
  }
}
```

### ✅ 注意事项
1. **概率范围**: 0.0 - 1.0（例如0.62 = 62%）
2. **降低阈值** → 信号更多（但质量可能下降）
3. **提高阈值** → 信号更少（但质量更高）

### 📝 修改示例

**场景A：提高Prime信号质量（减少信号数量）**
```json
{
  "publish": {
    "prime_prob_min": 0.68,  // 0.62 → 0.68（提高6%）
    "prime_dims_ok_min": 5,  // 4 → 5（提高达标维度要求）
    "prime_dim_threshold": 65
  }
}
```

**场景B：增加Prime信号数量（降低门槛）**
```json
{
  "publish": {
    "prime_prob_min": 0.58,  // 0.62 → 0.58（降低4%）
    "prime_dims_ok_min": 3,  // 4 → 3（降低达标维度要求）
    "prime_dim_threshold": 60 // 65 → 60（降低单维度阈值）
  }
}
```

---

## 3. 修改Telegram配置

### 📍 修改文件
```
config/telegram.json
```

### 🎯 修改位置
```json
{
  "bot_token": "YOUR_BOT_TOKEN",     // Telegram Bot Token
  "chat_id": "YOUR_CHAT_ID",         // Telegram Chat ID
  "enabled": true                     // 是否启用Telegram通知
}
```

### ✅ 注意事项
1. **bot_token**: 从 @BotFather 获取
2. **chat_id**: 群组ID（以`-`开头）或个人ID
3. **enabled**: 设置为`false`可临时禁用通知

### 📝 获取配置信息

**获取Bot Token**:
1. 在Telegram搜索 @BotFather
2. 发送 `/newbot` 创建新bot
3. 复制提供的Token

**获取Chat ID**:
```bash
# 方法1：通过API查询
curl https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates

# 方法2：使用Python脚本
python3 -c "import requests; print(requests.get('https://api.telegram.org/bot<TOKEN>/getUpdates').json())"
```

---

## 4. 调整扫描参数

### 📍 修改文件
```
scripts/realtime_signal_scanner.py
```

### 🎯 修改位置

**A. 修改默认扫描间隔**
```python
# Line ~128
def __init__(self, min_score: int = 50, send_telegram: bool = True):
    """
    初始化扫描器

    Args:
        min_score: 最低信号分数（默认50，可调整：40-70）
                   ↑ 修改此处的默认值
    """
```

**B. 修改默认命令行参数**
```python
# Line ~342-352
parser.add_argument(
    '--interval',
    type=int,
    default=0,           # ← 修改默认扫描间隔（秒）
    help='扫描间隔（秒），0=单次扫描，300=每5分钟'
)
parser.add_argument(
    '--min-score',
    type=int,
    default=70,          # ← 修改默认最低分数
    help='最低信号分数（默认70）'
)
```

### 📝 修改示例

**场景：修改默认扫描间隔为10分钟**
```python
parser.add_argument(
    '--interval',
    type=int,
    default=600,  # 0 → 600（10分钟）
    help='扫描间隔（秒），0=单次扫描，600=每10分钟'
)
```

---

## 5. 修改因子计算逻辑

### 📍 修改文件

**基础6维因子**：
```
ats_core/features/
├── trend.py          # T因子（趋势）
├── momentum.py       # M因子（动量）
├── cvd.py            # C因子（资金流）
├── structure_sq.py   # S因子（结构）
├── volume.py         # V因子（量能）
├── open_interest.py  # O因子（持仓）
└── fund_leading.py   # F因子（资金领先）
```

**新增4维因子**：
```
ats_core/factors_v2/
├── liquidity.py      # L因子（流动性）
├── basis_funding.py  # B因子（基差+资金费）
├── liquidation.py    # Q因子（清算密度）
└── independence.py   # I因子（独立性）
```

### ⚠️ 修改建议
1. **不要随意修改因子逻辑**（除非完全理解算法）
2. **修改前做好备份**
3. **修改后测试**：
   ```bash
   python3 scripts/realtime_signal_scanner.py --max-symbols 10 --once
   ```

### 📝 修改示例

**场景：调整趋势因子的ATR周期**

**修改文件**: `ats_core/features/trend.py`

**原代码**:
```python
def score_trend(klines, params):
    cfg = params.get("trend", {})
    atr_period = cfg.get("atr_period", 14)  # ← 默认14周期
    # ...
```

**修改为**:
```python
def score_trend(klines, params):
    cfg = params.get("trend", {})
    atr_period = cfg.get("atr_period", 20)  # 14 → 20（更平滑）
    # ...
```

**或者在config/params.json中修改**（推荐）:
```json
{
  "trend": {
    "atr_period": 20  // 14 → 20
  }
}
```

---

## 6. 修改评分公式

### 📍 修改文件
```
ats_core/scoring/scorecard.py
```

### 🎯 修改位置

**加权评分公式**（Line ~1-56）:
```python
def scorecard(scores, weights):
    """
    v6.0评分系统：加权平均（权重百分比系统）

    核心逻辑：
    - 因子输出: -100到+100
    - 权重百分比: 权重直接表示百分比（如 T=13.9%）
    - 加权平均: Σ(score × weight) / Σ(weight)
    - 总分范围: -100到+100
    """
    total = 0.0
    weight_sum = 0.0

    for dim, score in scores.items():
        if dim in weights:
            total += score * weights[dim]  # ← 加权求和
            weight_sum += weights[dim]

    # 归一化到 -100 到 +100
    if weight_sum > 0:
        weighted_score = total / weight_sum  # ← 平均
    else:
        weighted_score = 0.0

    # ... 省略
```

### ⚠️ 警告
**修改评分公式会影响整个系统的判断逻辑！**
- 只有在完全理解评分逻辑后才修改
- 修改后需要重新校准Prime阈值

---

## 7. 修改Telegram消息格式

### 📍 修改文件
```
ats_core/outputs/telegram_fmt.py
```

### 🎯 修改位置

**主要函数**:
```python
def render_signal(r: Dict[str, Any], is_watch: bool = False) -> str:
    """Unified template for both watch and trade (v4.0: 10-dimension system)."""
    l1, l2 = _header_lines(r, is_watch)      # 头部信息
    ten = _six_block(r)                      # 10维因子显示
    pricing = _pricing_block(r)              # 价格信息

    # 组合消息（可修改格式）
    body = f"{l1}\n{l2}\n{pricing}\n\n━━━━━ 10维因子分析 ━━━━━\n{ten}\n\n{_note_and_tags(r, is_watch)}"
    return body
```

### 📝 修改示例

**场景：在消息底部添加免责声明**

```python
def render_signal(r: Dict[str, Any], is_watch: bool = False) -> str:
    l1, l2 = _header_lines(r, is_watch)
    ten = _six_block(r)
    pricing = _pricing_block(r)

    # 原有格式
    body = f"{l1}\n{l2}\n{pricing}\n\n━━━━━ 10维因子分析 ━━━━━\n{ten}\n\n{_note_and_tags(r, is_watch)}"

    # 添加免责声明
    disclaimer = "\n\n⚠️ <i>本信号仅供参考，不构成投资建议。请自行判断风险。</i>"
    return body + disclaimer
```

---

## 8. 添加新因子

### ⚠️ 复杂度：非常高

添加新因子需要修改多个文件，建议由熟悉系统架构的开发者操作。

### 📍 需要修改的文件

1. **创建因子计算文件**
   ```
   ats_core/factors_v2/new_factor.py  # 或 ats_core/features/new_factor.py
   ```

2. **在analyze_symbol.py中集成**
   ```
   ats_core/pipeline/analyze_symbol.py
   - 导入新因子计算函数
   - 在scores字典中添加新因子
   - 在meta字典中添加元数据
   ```

3. **在params.json中添加权重**
   ```json
   {
     "weights": {
       "T": 13.9,
       // ... 其他因子
       "NEW": 5.0  // 新因子权重（需调整其他权重保持总和=100）
     },
     "new_factor": {
       "param1": 10,
       "param2": 20
     }
   }
   ```

4. **在adaptive_weights.py中添加**
   ```python
   # 所有regime权重配置中添加新因子
   def get_regime_weights(market_regime: int, volatility: float):
       if abs(market_regime) > 60:
           return {
               "T": 19.4,
               // ... 其他因子
               "NEW": 5.0  // 添加新因子
           }
       # ... 其他regime配置
   ```

5. **在telegram_fmt.py中添加显示**
   ```python
   # 在_six_block函数中添加新因子的显示逻辑
   ```

### 🔴 注意事项
- 新因子必须返回-100到+100的分数
- 总权重必须保持=100%
- 需要在所有regime权重配置中添加
- 建议先在独立文件中测试因子计算逻辑

---

## ❌ 禁止修改的文件

以下文件包含核心逻辑，**除非完全理解系统架构，否则禁止修改**：

1. `ats_core/pipeline/batch_scan_optimized.py` - WebSocket批量扫描核心
2. `ats_core/data/realtime_kline_cache.py` - K线缓存管理
3. `ats_core/sources/binance.py` - 币安API封装
4. `ats_core/cfg.py` - 配置加载器
5. `ats_core/logging.py` - 日志系统
6. `ats_core/backoff.py` - 重试机制

---

## ✅ 修改后的验证流程

### 1. 清除缓存
```bash
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -type f -name "*.pyc" -delete 2>/dev/null
```

### 2. 测试扫描（小规模）
```bash
python3 scripts/realtime_signal_scanner.py --max-symbols 10 --once --verbose
```

### 3. 检查输出
- 是否有Python错误？
- Prime信号数量是否合理？
- Telegram消息格式是否正确？

### 4. 完整测试
```bash
python3 scripts/realtime_signal_scanner.py --once --verbose
```

### 5. 生产部署
```bash
cd ~/cryptosignal
git pull origin <branch>
nohup python3 scripts/realtime_signal_scanner.py --interval 300 > scanner.log 2>&1 &
```

---

## 📊 修改频率建议

| 文件 | 修改频率 | 备注 |
|------|---------|------|
| `config/params.json` | 中等 | 调整权重、阈值 |
| `config/telegram.json` | 低 | 初始配置后很少改动 |
| `scripts/realtime_signal_scanner.py` | 低 | 除非需要新功能 |
| `ats_core/features/*` | 低 | 因子逻辑稳定后不常改 |
| `ats_core/scoring/*` | 极低 | 核心评分逻辑 |
| `ats_core/outputs/telegram_fmt.py` | 中等 | 可能调整消息格式 |

---

## 🔗 相关文档

- [SYSTEM_OVERVIEW.md](./SYSTEM_OVERVIEW.md) - 系统总览
- [CONFIGURATION_GUIDE.md](./CONFIGURATION_GUIDE.md) - 配置参数详解
- [ARCHITECTURE.md](./ARCHITECTURE.md) - 技术架构

---

**最后更新**: 2025-10-30
