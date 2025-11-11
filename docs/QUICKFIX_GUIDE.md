# 🚀 CryptoSignal v7.2 快速修复指南

**适用场景**: "还是有很多问题"、"无法运行"、"没有收到信号"
**预计时间**: 5-10分钟
**最后更新**: 2025-11-10

---

## 📋 问题自检清单

运行系统前，请按顺序检查：

- [ ] 1. Python依赖已安装
- [ ] 2. Binance API已配置
- [ ] 3. 配置文件完整性
- [ ] 4. 首次测试运行成功
- [ ] 5. 参数调优（可选）

---

## ✅ Step 1: 安装Python依赖（2分钟）

### 问题症状
```
ModuleNotFoundError: No module named 'aiohttp'
ModuleNotFoundError: No module named 'websockets'
```

### 解决方案
```bash
# 进入项目目录
cd ~/cryptosignal

# 安装所有依赖
pip3 install -r requirements.txt

# 验证安装
python3 -c "import aiohttp, websockets, pandas, numpy; print('✅ 依赖安装成功')"
```

### 预期输出
```
✅ 依赖安装成功
```

---

## ✅ Step 2: 配置Binance API（3分钟）

### 问题症状
```
FileNotFoundError: [Errno 2] No such file or directory: 'config/binance_credentials.json'
```

### 解决方案

#### 2.1 获取Binance API Key

1. 登录Binance Futures: https://www.binance.com/en/futures
2. 进入API管理: https://www.binance.com/en/my/settings/api-management
3. 创建新的API Key
4. **权限设置**: ✅ 只勾选"读取"(Read)，❌ 不要勾选"交易"和"提现"
5. 复制API Key和Secret Key

#### 2.2 创建配置文件

```bash
# 复制示例文件
cp config/binance_credentials.json.example config/binance_credentials.json

# 编辑配置文件
nano config/binance_credentials.json
# 或使用 vi/vim
```

#### 2.3 填入真实凭证

```json
{
  "binance": {
    "api_key": "粘贴你的API_KEY",
    "api_secret": "粘贴你的SECRET",
    "testnet": false
  }
}
```

#### 2.4 验证配置

```bash
python3 -c "
from ats_core.execution.binance_futures_client import get_binance_client
import asyncio
async def test():
    client = get_binance_client()
    await client.initialize()
    print('✅ Binance连接成功')
asyncio.run(test())
"
```

### 预期输出
```
✅ Binance连接成功
```

---

## ✅ Step 3: 验证配置完整性（1分钟）

### 检查信号阈值配置

```bash
python3 -c "
from ats_core.config.threshold_config import get_thresholds
config = get_thresholds()
print('✅ 配置加载成功')
print(f'v72增强参数: {config.config.get(\"v72增强参数\")}')
"
```

### 预期输出
```
✅ 配置加载成功
v72增强参数: {'description': '...', 'min_klines_for_v72': 100, 'min_cvd_points': 10, ...}
```

### 检查Telegram配置（可选）

```bash
cat config/telegram.json
```

如果要启用Telegram通知：
```json
{
  "enabled": true,
  "bot_token": "你的Telegram Bot Token",
  "chat_id": "你的Chat ID"
}
```

如果暂时禁用（推荐初次测试）：
```json
{
  "enabled": false,
  "bot_token": "",
  "chat_id": ""
}
```

---

## ✅ Step 4: 首次测试运行（3分钟）

### 小规模测试（3个币种，不发Telegram）

```bash
python3 scripts/realtime_signal_scanner.py --max-symbols 3 --no-telegram
```

### 预期输出（关键日志）
```
============================================================
🚀 初始化实时信号扫描器（v7.2增强版）
============================================================
✅ K线缓存管理器初始化完成
✅ 优化批量扫描器创建成功

============================================================
🚀 初始化优化批量扫描器...
============================================================
1️⃣  初始化Binance客户端...
2️⃣  获取币安USDT合约币种（全市场扫描）...
   总计: 200+ 个USDT永续合约
3️⃣  批量初始化K线缓存...
4️⃣  ✅ WebSocket已禁用（推荐模式）
5️⃣  预加载10维因子系统数据...
✅ 优化批量扫描器初始化完成！

🔍 开始批量扫描（WebSocket缓存加速）
...
📊 扫描统计:
   总币种数: 3
   v7.2增强: X
   Prime信号: Y
```

### 如果初始化失败

**症状1: 网络超时**
```
ConnectionError: Cannot connect to Binance
```
**解决**: 检查网络连接，或使用代理

**症状2: API权限错误**
```
API-key format invalid
```
**解决**: 重新检查config/binance_credentials.json中的凭证

---

## ⚠️ Step 5: 参数调优（可选，需要数据支持）

如果首次测试成功运行，但出现以下情况：

### 情况A: v7.2增强数据生成率很低（<30%）

**症状**: 扫描统计显示 `v7.2增强: 1` （只有1个或很少）

**原因**: min_klines_for_v72阈值过高

**解决**: 编辑config/signal_thresholds.json
```json
"v72增强参数": {
  "min_klines_for_v72": 50,  // 从100降到50
  "min_cvd_points": 5         // 从10降到5
}
```

### 情况B: Prime信号数量为0

**症状**: 扫描统计显示 `Prime信号: 0`

**原因**: 五道闸门过严

**诊断步骤**:
1. 运行一次大规模扫描并保存结果
   ```bash
   python3 scripts/realtime_signal_scanner.py --max-symbols 100 --no-telegram > scan_log.txt
   ```

2. 检查scan_detail.json
   ```bash
   cat reports/latest/scan_detail.json | grep -o '"pass_all": false' | wc -l
   # 查看有多少信号被闸门拒绝
   ```

3. 分析具体哪个闸门拒绝最多（需要手动查看scan_detail.json中的gate_results）

**常见调整**:

```json
// 如果Gate2（F因子）拒绝太多
"gate2_fund_support": {
  "F_min": -20  // 从-50放宽到-20
}

// 如果Gate4（概率）拒绝太多
"gate4_probability": {
  "P_min": 0.35  // 从0.40降到0.35
}
```

### 情况C: Prime信号数量太多（>50个）

**原因**: 闸门太松

**解决**: 收紧阈值
```json
"gate2_fund_support": {
  "F_min": 0  // 只允许资金支撑的信号
},
"gate4_probability": {
  "P_min": 0.50  // 提高概率要求
}
```

---

## 🎯 成功验证标准

系统正常运行的标志：

✅ **初始化阶段**:
- Binance客户端连接成功
- K线缓存初始化完成（200+ 币种）
- 市场数据预加载成功

✅ **扫描阶段**:
- 至少有1个币种成功分析
- v7.2增强数据生成率 > 30%
- 无严重错误（ERROR日志）

✅ **输出阶段**:
- reports/latest/scan_detail.json 存在且有效
- 如果有Prime信号，scan_summary.json显示

---

## 🔧 常见问题排查

### Q1: 扫描很慢（>5分钟）

**原因**: 首次运行需要初始化K线缓存
**解决**:
- 首次初始化需要3-5分钟，这是正常的
- 后续扫描会很快（~10秒）

### Q2: 日志显示 "数据不足"

**原因**: 币种上市时间太短或数据未同步
**解决**: 正常现象，系统会自动跳过这些币种

### Q3: Telegram不发送消息

**检查**:
1. config/telegram.json中enabled=true
2. bot_token和chat_id正确
3. 有Prime信号产生（不是0个）
4. AntiJitter防抖动未拦截

### Q4: v72_enhancements全是None

**症状**: scan_detail.json中所有币种的v72_enhancements都是{}
**原因**: intermediate_data中的数据不足
**解决**:
1. 检查klines/oi_data/cvd_series长度
2. 降低min_klines_for_v72阈值（Step 5）

---

## 📞 获取帮助

### 1. 查看详细检索报告
```bash
cat docs/PHASE2_INSPECTION_RESULTS.md
cat docs/PHASE3_PROBLEM_SUMMARY.md
```

### 2. 提交Issue
包含以下信息：
- 错误信息（完整的traceback）
- scan_log.txt
- config/signal_thresholds.json（隐藏敏感信息）
- 系统环境（Python版本、OS）

### 3. 查看历史修复记录
```bash
cat docs/P0_HARDCODE_CLEANUP_v7.2.10.md
```

---

## 🎓 进阶配置

### 启用定期扫描（每5分钟）

```bash
# 测试模式（前台运行，Ctrl+C停止）
python3 scripts/realtime_signal_scanner.py --interval 300

# 生产模式（后台运行）
nohup python3 scripts/realtime_signal_scanner.py --interval 300 > cryptosignal.log 2>&1 &

# 查看日志
tail -f cryptosignal.log
```

### 启用Telegram通知

1. 配置config/telegram.json（enabled=true）
2. 移除--no-telegram参数
3. 重启扫描器

### 使用setup.sh一键启动

```bash
./setup.sh
# 这会自动完成所有步骤并启动后台扫描
```

---

## ✅ 检查清单总结

运行前确认：
- [x] Python依赖已安装（Step 1）
- [x] Binance API已配置（Step 2）
- [x] 配置文件验证通过（Step 3）
- [x] 首次测试成功运行（Step 4）
- [ ] 参数已调优（Step 5，可选）

全部完成后，系统应该能正常运行！
