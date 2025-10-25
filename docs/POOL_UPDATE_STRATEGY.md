# 候选池更新策略

## 📋 更新频率建议

### **Base Pool（基础池）**
- **更新频率**: 每日1次
- **推荐时间**: UTC 00:00（北京时间 08:00）
- **原因**:
  - Z24波动性指标基于24小时数据，日频更新即可
  - 流动性排名变化不频繁
  - 减少API调用，避免风控

### **Overlay Pool（叠加层）**
- **更新频率**: 每小时1次
- **推荐时间**: 每小时第0分钟
- **原因**:
  - 捕捉短期异动信号（1小时价格变动）
  - CVD资金流实时性要求高
  - 量能比需要及时更新

### **实时扫描**
- **更新频率**: 按需运行（手动或每15分钟）
- **数据来源**: 读取缓存的Base + Overlay池
- **速度**: ~2分钟（仅分析候选币）

---

## 🚀 性能优化对比

| 场景 | 当前方案 | 优化方案 | 提升 |
|-----|---------|---------|-----|
| **首次运行** | 5.2分钟 | 8.2分钟 | -58% |
| **后续扫描** | 5.2分钟 | 2分钟 | +62% |
| **API调用** | 521次 | 180次 | +65% |
| **风控风险** | 中等 | 低 | ✅ |

**说明**：首次运行稍慢（需要建立Base缓存），但后续扫描速度显著提升。

---

## ⚙️ 配置Crontab定时任务

### **1. 编辑Crontab**

```bash
crontab -e
```

### **2. 添加定时任务**

```bash
# Base Pool: 每日UTC 00:00更新（北京时间08:00）
0 0 * * * cd ~/cryptosignal && python3 tools/update_pools.py --base >> logs/pool_update.log 2>&1

# Overlay Pool: 每小时更新
0 * * * * cd ~/cryptosignal && python3 tools/update_pools.py --overlay >> logs/pool_update.log 2>&1

# 实时扫描: 每15分钟运行一次（从缓存读取候选池）
*/15 * * * * cd ~/cryptosignal && python3 tools/full_run_v2_fast.py --send >> logs/scan.log 2>&1
```

### **3. 创建日志目录**

```bash
mkdir -p ~/cryptosignal/logs
```

### **4. 验证Crontab**

```bash
crontab -l  # 查看已设置的任务
```

---

## 🛠️ 手动更新命令

### **检查缓存状态**
```bash
cd ~/cryptosignal
python3 tools/update_pools.py --check
```

**输出示例**：
```
============================================================
候选池缓存状态
============================================================

📦 Base Pool:
   文件: /home/user/cryptosignal/data/base_pool.json
   更新: 2小时30分钟前
   状态: ✅ 有效 (建议每日更新)
   数量: 67 个币种

🔥 Overlay Pool:
   文件: /home/user/cryptosignal/data/overlay_pool.json
   更新: 45分钟前
   状态: ✅ 有效 (建议每小时更新)
   数量: 12 个币种

============================================================
```

### **更新Base Pool**
```bash
python3 tools/update_pools.py --base
```

### **更新Overlay Pool**
```bash
python3 tools/update_pools.py --overlay
```

### **更新全部**
```bash
python3 tools/update_pools.py --all
```

### **强制更新（忽略缓存）**
```bash
python3 tools/update_pools.py --all --force
```

---

## 📊 API调用量分析

### **Base Pool构建（每日1次）**
```
- all_24h(): 1次请求, weight=40
- klines_1h(800): 400次请求, weight=400
- 总计: 401次请求, weight=440
- 耗时: ~4分钟
```

### **Overlay Pool构建（每小时1次）**
```
- get_klines(1h, 60): 60次请求, weight=60
- get_open_interest(1h, 60): 60次请求, weight=60
- 总计: 120次请求, weight=120
- 耗时: ~72秒
```

### **实时扫描（每15分钟，读缓存）**
```
- Base/Overlay: 从文件读取, 0次API
- 分析60个候选币:
  * klines(1h,300): weight=1
  * klines(4h,200): weight=1
  * OI(1h,300): weight=1
  * 总计: 180次请求, weight=180
- 耗时: ~2分钟
```

### **风控评估**
- **币安限制**: 1200 req/min, 3000 weight/min
- **单次扫描**: 180 weight（仅6%配额）
- **结论**: ✅ 安全，不会触发风控

---

## 🎯 优化效果

### **优化前（每次都重建候选池）**
```
全市场扫描 → Base筛选 → Overlay筛选 → 分析 → 发送
    ↓           ↓           ↓           ↓
  40w        521次      5.2分钟    风控风险
```

### **优化后（缓存分离更新）**
```
[每日] Base Pool更新 → 缓存
         ↓
[每小时] Overlay Pool更新 → 缓存
         ↓
[实时] 读取缓存 → 分析 → 发送
       ↓         ↓
     0秒      180次     2分钟    ✅安全
```

---

## 🔧 配置参数说明

**config/params.json**:

```json
{
  "base": {
    "min_quote_volume": 5000000,    // 最小成交额500万USDT
    "min_z24_abs": 0.5,              // Z24波动性阈值
    "min_pool_size": 20              // 保底数量（震荡市保证至少20个）
  },

  "overlay": {
    "triple_sync": {
      "mode": "2of3",                // 三选二模式（降低严格度）
      "dP1h_abs_pct": 0.015,         // 1.5%价格变动（原2%）
      "v5_over_v20": 1.2,            // 1.2倍量能（原1.3倍）
      "cvd_mix_abs_per_h": 0.025,    // 2.5% CVD（原3%）
      "anti_chase": {
        "enabled": true,             // 启用回撤过滤
        "lookback": 72,              // 回看72小时
        "max_distance_pct": 0.05     // 距离高点/低点5%内跳过
      }
    }
  }
}
```

---

## 📝 日志监控

### **查看更新日志**
```bash
tail -f ~/cryptosignal/logs/pool_update.log
```

### **查看扫描日志**
```bash
tail -f ~/cryptosignal/logs/scan.log
```

### **日志轮转（可选）**
```bash
# 在 /etc/logrotate.d/cryptosignal
/home/user/cryptosignal/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
}
```

---

## ⚠️ 注意事项

1. **首次运行**：需要手动运行一次 `--all` 建立初始缓存
2. **网络断开**：更新失败不影响现有缓存，下次重试
3. **币安封IP**：如果遇到403，等待5分钟后重试
4. **时区设置**：Crontab默认使用系统时区，注意UTC转换
5. **SSH断开**：使用 `nohup` 或 `screen` 保持长时间运行

---

## 🚀 快速开始

```bash
# 1. 首次建立缓存
cd ~/cryptosignal
python3 tools/update_pools.py --all --force

# 2. 检查状态
python3 tools/update_pools.py --check

# 3. 运行一次扫描测试
python3 tools/full_run_v2_fast.py

# 4. 设置定时任务
crontab -e
# （粘贴上面的crontab配置）

# 5. 监控日志
tail -f logs/scan.log
```

---

## 📈 监控建议

- **每日检查**：Base Pool数量是否正常（50-80个）
- **每小时检查**：Overlay Pool是否为空（震荡市可能为0）
- **实时监控**：扫描成功率、信号数量、Telegram发送状态
- **异常告警**：API失败率 > 10%时人工介入
