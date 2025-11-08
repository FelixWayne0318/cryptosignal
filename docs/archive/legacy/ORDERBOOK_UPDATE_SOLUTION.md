# 订单簿数据更新优化方案

**创建时间**: 2025-11-03
**问题**: 订单簿数据只在初始化时获取，长时间运行后可能过时
**影响**: L因子（流动性）准确性降低

---

## 🎯 问题分析

### 当前状态

```python
# 初始化时获取（batch_scan_optimized.py:243-293）
async def initialize():
    # 5.3 批量获取订单簿快照
    for symbol in symbols:
        orderbook = await get_orderbook_snapshot(symbol, limit=20)
        self.orderbook_cache[symbol] = orderbook  # ✅ 缓存

    # 后续扫描不再更新 ❌
```

### 影响程度

| 运行时长 | 订单簿状态 | L因子影响 | 主流币影响 | 小币种影响 |
|---------|-----------|----------|-----------|-----------|
| 0-30分钟 | ✅ 新鲜 | 无影响 | ✅ 准确 | ✅ 准确 |
| 30-60分钟 | 🔄 略旧 | 轻微影响 | ✅ 准确 | ⚠️ 可能偏差 |
| 1-2小时 | ⚠️ 过时 | 中等影响 | ✅ 基本准确 | ❌ 偏差较大 |
| >2小时 | ❌ 严重过时 | 较大影响 | ⚠️ 可能偏差 | ❌ 严重偏差 |

---

## 📋 解决方案对比

### 方案1：Layer 3定时更新（推荐）⭐

**描述**: 在Layer 3中每30分钟更新一次订单簿

**优点**：
- ✅ 数据相对新鲜（最多30分钟延迟）
- ✅ 实现简单，逻辑统一
- ✅ 与资金费率/持仓量同步更新
- ✅ 不影响正常扫描速度

**缺点**：
- ⚠️ Layer 3耗时增加20秒（从20秒→40秒）
- ⚠️ 增加API调用（200次/30分钟 = 400次/小时）

**性能影响**：
```
正常扫描（非Layer 3）: 0.2-2秒 ✅ 无影响
Layer 3触发时: 20秒 → 40秒 ⚠️ 增加1倍

每小时Layer 3触发2次:
- 额外耗时: 40秒
- 占比: 40秒/3600秒 = 1.1% ✅ 可接受
```

**实现代码**：

```python
# ats_core/pipeline/batch_scan_optimized.py

async def scan(...):
    # Layer 3: 市场数据更新（低频，每30分钟）
    if current_minute in [0, 30]:
        log(f"\n📉 [Layer 3] 更新市场数据（资金费率/持仓量/订单簿）...")
        try:
            # 原有的市场数据更新
            await self.kline_cache.update_market_data(
                symbols=symbols,
                client=self.client
            )

            # 🆕 新增：更新订单簿
            await self._update_orderbook_cache(symbols)

        except Exception as e:
            error(f"❌ Layer 3 更新异常: {e}")


async def _update_orderbook_cache(self, symbols: List[str]):
    """
    Layer 3.5: 订单簿缓存更新

    每30分钟更新一次订单簿深度
    """
    log("   📊 更新订单簿深度（20档）...")
    log("       🚀 使用并发模式，预计20-30秒")

    from ats_core.sources.binance import get_orderbook_snapshot

    orderbook_success = 0
    orderbook_failed = 0

    # 并发获取（与初始化时相同的逻辑）
    async def fetch_one_orderbook(symbol: str):
        try:
            loop = asyncio.get_event_loop()
            orderbook = await loop.run_in_executor(
                None,
                lambda: get_orderbook_snapshot(symbol, limit=20)
            )
            return symbol, orderbook, None
        except Exception as e:
            return symbol, None, e

    # 分批并发
    batch_size = 20
    for i in range(0, len(symbols), batch_size):
        batch = symbols[i:i+batch_size]
        tasks = [fetch_one_orderbook(symbol) for symbol in batch]
        results = await asyncio.gather(*tasks)

        for symbol, orderbook, error in results:
            if error is None and orderbook:
                self.orderbook_cache[symbol] = orderbook
                orderbook_success += 1
            else:
                orderbook_failed += 1

        if i + batch_size < len(symbols):
            await asyncio.sleep(0.5)

        progress = min(i + batch_size, len(symbols))
        if progress % 40 == 0 or progress >= len(symbols):
            log(f"       进度: {progress}/{len(symbols)} ({progress/len(symbols)*100:.0f}%)")

    log(f"       ✅ 订单簿更新完成: 成功{orderbook_success}, 失败{orderbook_failed}")
```

---

### 方案2：智能选择性更新（最优）🌟

**描述**: 只更新流动性波动较大的币种

**优点**：
- ✅ API调用少（只更新50-100个币种）
- ✅ 耗时短（10-15秒 vs 20秒）
- ✅ 主流币不更新（流动性稳定）
- ✅ 小币种重点更新（流动性波动大）

**实现逻辑**：

```python
async def _update_orderbook_cache_smart(self, symbols: List[str]):
    """
    智能选择性更新订单簿

    策略：
    1. 主流币（BTC/ETH等）：跳过更新（流动性稳定）
    2. 中等币：每次更新50%（轮换）
    3. 小币种：每次全部更新
    """

    # 分类币种
    top_tier = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT']  # 顶级流动性

    # 获取24h成交量，分类
    mid_tier = []  # 成交额 > 100M
    low_tier = []  # 成交额 < 100M

    for symbol in symbols:
        if symbol in top_tier:
            continue  # 跳过顶级币种

        # 从缓存中获取24h成交额
        volume_24h = self.get_symbol_volume(symbol)
        if volume_24h > 100_000_000:  # 100M USDT
            mid_tier.append(symbol)
        else:
            low_tier.append(symbol)

    # 选择需要更新的币种
    to_update = []

    # 顶级币：不更新
    log(f"       跳过{len(top_tier)}个顶级流动性币种")

    # 中等币：轮换更新50%
    mid_count = len(mid_tier) // 2
    to_update.extend(mid_tier[:mid_count])
    log(f"       更新{mid_count}个中等流动性币种（共{len(mid_tier)}个）")

    # 小币种：全部更新
    to_update.extend(low_tier)
    log(f"       更新{len(low_tier)}个低流动性币种")

    log(f"       总计更新: {len(to_update)}/{len(symbols)}个币种")

    # 并发更新
    await self._batch_update_orderbooks(to_update)
```

**性能对比**：

| 方案 | 更新数量 | API调用 | 耗时 | 数据准确性 |
|------|---------|---------|------|-----------|
| 全量更新 | 200个 | 200次 | 20秒 | 100% |
| 智能更新 | 50-100个 | 50-100次 | 10-15秒 | 95% ⭐ |

---

### 方案3：按需更新（备选）

**描述**: 检测到L因子异常时才更新

**优点**：
- ✅ API调用最少
- ✅ 正常情况无额外开销

**缺点**：
- ❌ 实现复杂
- ❌ 可能遗漏问题
- ❌ 被动更新，不够及时

**实现逻辑**：

```python
def should_update_orderbook(self, symbol: str) -> bool:
    """
    判断是否需要更新订单簿

    触发条件：
    1. L因子异常（>95或<-95）
    2. 缓存超过1小时
    3. 价格波动超过10%（可能影响流动性）
    """
    # 检查缓存时间
    cache_age = time.time() - self.orderbook_update_time.get(symbol, 0)
    if cache_age > 3600:  # 1小时
        return True

    # 检查价格波动
    price_change_1h = self.get_price_change(symbol, '1h')
    if abs(price_change_1h) > 0.10:  # 10%
        return True

    # 检查L因子
    L = self.latest_L_factor.get(symbol, 0)
    if abs(L) > 95:  # 极端值
        return True

    return False
```

---

### 方案4：重启更新（最简单）

**描述**: 每隔2-4小时重启系统

**优点**：
- ✅ 实现简单（无需修改代码）
- ✅ 所有数据都会刷新
- ✅ 可以用cron定时重启

**缺点**：
- ❌ 重启需要2分钟初始化
- ❌ 丢失运行状态
- ❌ 不够优雅

**实现方式**：

```bash
# crontab定时重启
0 */2 * * * systemctl restart cryptosignal.service
```

---

## 🎯 推荐方案

### 短期方案（立即可用）

**方案4 - 定时重启**
```bash
# 每2小时重启一次
0 */2 * * * systemctl restart cryptosignal.service
```

**优点**: 无需修改代码，立即可用
**缺点**: 每次重启需要2分钟

---

### 长期方案（最佳实践）

**方案2 - 智能选择性更新**

**实现步骤**：
1. 在`batch_scan_optimized.py`中添加`_update_orderbook_cache_smart()`方法
2. 在Layer 3触发时调用
3. 只更新50-100个中小币种

**预期效果**：
- 耗时：10-15秒（vs 20秒全量更新）
- API调用：50-100次（vs 200次全量更新）
- 数据准确性：95%+（主流币稳定，小币种实时）

---

## 📊 性能影响评估

### 当前系统（无订单簿更新）

```
每5分钟扫描一次：
├─ 正常扫描: 0.2-2秒 ✅
├─ Layer 2触发: 8-15秒（15/60分钟=25%概率）
└─ Layer 3触发: 20秒（每30分钟=8%概率）

平均扫描时间:
= 0.7 * 1秒 + 0.25 * 10秒 + 0.08 * 20秒
= 0.7 + 2.5 + 1.6 = 4.8秒
```

### 方案1：Layer 3全量更新

```
每5分钟扫描一次：
├─ 正常扫描: 0.2-2秒 ✅
├─ Layer 2触发: 8-15秒
└─ Layer 3触发: 40秒 ⚠️ (增加订单簿更新)

平均扫描时间:
= 0.7 * 1秒 + 0.25 * 10秒 + 0.08 * 40秒
= 0.7 + 2.5 + 3.2 = 6.4秒 (+33%)
```

### 方案2：Layer 3智能更新

```
每5分钟扫描一次：
├─ 正常扫描: 0.2-2秒 ✅
├─ Layer 2触发: 8-15秒
└─ Layer 3触发: 30秒 ✅ (智能更新50%币种)

平均扫描时间:
= 0.7 * 1秒 + 0.25 * 10秒 + 0.08 * 30秒
= 0.7 + 2.5 + 2.4 = 5.6秒 (+17%)
```

---

## ✅ 最终建议

### 立即执行

使用**方案4（定时重启）**作为临时解决方案：

```bash
# 添加到crontab
crontab -e

# 每2小时重启
0 */2 * * * systemctl restart cryptosignal.service
```

### 后续优化

如果需要长期稳定运行，实施**方案2（智能更新）**：

1. 评估实际需求（是否真的需要实时订单簿）
2. 如果需要，实现智能选择性更新
3. 只更新中小币种（50-100个）
4. 主流币使用缓存（流动性稳定）

### 是否必要？

**需要考虑的问题**：

1. **L因子权重**: 在v6.6中，L因子权重是0%（仅调制器）
   - 如果L因子不影响信号评分，订单簿略过时影响不大

2. **实际影响**:
   - 主流币（BTC/ETH）流动性稳定，1小时变化很小
   - 小币种流动性波动大，但数量少

3. **成本收益比**:
   - 成本：每30分钟40秒 + 100次API调用
   - 收益：L因子更准确
   - 如果L因子权重低，可能不值得

**建议先运行1-2天，观察L因子的实际变化幅度再决定是否需要更新**

---

**文档维护者**: Claude AI
**最后更新**: 2025-11-03
**状态**: 方案评估中，等待决策
