# CryptoSignal 版本历史

> ⚠️ **重要**：本文档已纳入标准化部署规范体系
> 标准规范：[standards/DEPLOYMENT_STANDARD.md](standards/DEPLOYMENT_STANDARD.md)
> 快速参考：[QUICK_DEPLOY.md](QUICK_DEPLOY.md)

---

## 📋 版本更新 (v6.1 → v6.2) - 2025-11-02

### 🐛 Critical Bug修复

#### Bug 1: I因子双重归一化
- **问题**: `calculate_independence()`已通过StandardizationChain返回±100分数，但analyze_symbol.py又做了一次0-100到-100的映射，导致I值可达-300到+100
- **影响**: 大量币种显示I≤-150，严重偏离±100标准化范围
- **修复**: 移除二次映射，直接使用`calculate_independence()`的返回值
- **文件**: `ats_core/pipeline/analyze_symbol.py:328-340`
- **参考**: 与L因子修复相同（同类型的双重归一化bug）

#### Bug 2: 币龄计算错误
- **问题**: 使用K线数量(`len(k1h)`)作为币龄，导致缓存限制导致BTC/ETH等成熟币被误判为"新币B(300小时)"
- **影响**:
  - 成熟币触发新币模板的流动性惩罚
  - 错误的数据完整性要求
  - 分类显示错误
- **修复**: 使用K线时间戳差值计算真实币龄
  ```python
  coin_age_ms = latest_kline_ts - first_kline_ts
  coin_age_hours = coin_age_ms / (1000 * 3600)
  ```
- **文件**:
  - `ats_core/pipeline/analyze_symbol.py:150-161`
  - `ats_core/pipeline/batch_scan_optimized.py:465-474`

#### Bug 3: 四门系统缺失
- **问题**: batch_scan_optimized.py尝试读取`result.get('gates', {})`但analyze_symbol.py返回结果中没有'gates'键
- **影响**: 四门调节全部显示0.00，无法评估信号质量
- **修复**: 添加简化版四门系统到analyze_symbol返回结果
  - DataQual: 基于K线完整性
  - EV: 基于概率的简化估算
  - Execution: 基于流动性L因子
  - Probability: 基于P_chosen归一化
- **文件**: `ats_core/pipeline/analyze_symbol.py:731-748`
- **备注**: 当前为简化版，完整版需集成`integrated_gates.py`的FourGatesChecker

#### Bug 4: min_score参数未使用
- **问题**: batch_scan_optimized.py的scan()方法声明了min_score参数但未在过滤逻辑中使用
- **影响**: 无法通过min_score参数控制信号质量阈值
- **修复**: 添加过滤条件 `if is_prime and prime_strength >= min_score`
- **文件**: `ats_core/pipeline/batch_scan_optimized.py:585-588`

### 📊 修复效果预期

**修复前**:
- I因子: -300 到 +100（严重超出范围）
- 币龄: BTC/ETH显示为"新币B(300小时)"
- 四门: 全部显示0.00（失效）
- confidence: 5-20（极低，受I因子异常影响）
- prime_strength: base 3-12（无法达到阈值）

**修复后**:
- I因子: -100 到 +100（标准化范围）
- 币龄: 基于真实时间戳，BTC/ETH正确识别为成熟币
- 四门: 显示有意义的数值（0-1范围）
- confidence: 预期提升到正常范围（30-80）
- prime_strength: 预期提升，可能出现Prime信号

---

## 📋 版本更新 (v6.0 → v6.1)

### 🔧 关键修复

#### P0: I因子架构修正
- **问题**: I因子错误地放在A层参与评分，违反规范
- **修复**: 将I因子从A层移至B层（调制器层）
- **影响**:
  - A层从10因子减少到9因子
  - I的8%权重重新分配：T+2%, M+3%, S+4%, C+6%, L+4%, 其他rebalance
  - F和I权重设为0（不参与评分）

#### P1: 降低阈值以增加信号量
- **Prime强度阈值**: 35分 → 25分
- **概率阈值**: 0.62 → 0.58
- **维度达标数**: 4 → 3
- **维度阈值**: 35 → 30

#### P2: 放宽防抖动机制
- **入场阈值**: 0.80 → 0.65
- **确认K线**: 2/3 → 1/2（响应速度提升33%）
- **冷却时间**: 90秒 → 60秒

### 📊 预期效果

**修复前 (v6.0)**:
- 扫描140个币种：2-3个信号
- 通过四门：0-1个
- Prime信号：极少或无

**修复后 (v6.1)**:
- 扫描140个币种：8-15个信号
- 通过四门：5-10个
- Prime信号：3-7个/小时

---

## 🚀 快速部署（标准流程）

### 方式 1: 标准部署流程（推荐）

在服务器上执行以下命令：

```bash
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 标准部署流程（遵循 standards/DEPLOYMENT_STANDARD.md）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# 第 1 步：拉取最新代码
cd ~/cryptosignal
git fetch origin claude/review-system-overview-011CUhLQjByWuXC1bySJCHKQ
git checkout claude/review-system-overview-011CUhLQjByWuXC1bySJCHKQ
git pull origin claude/review-system-overview-011CUhLQjByWuXC1bySJCHKQ

# 第 2 步：配置 Binance API（首次部署必需）
# 见下文 "Binance API 凭证配置"

# 第 3 步：运行部署脚本（自动验证 + 可选启动）
./deploy.sh

# 脚本会自动完成 8 步验证，最后询问是否立即启动（每5分钟扫描）
# 选择 y：自动启动生产环境 ⬅️ 推荐
# 选择 N：稍后手动启动
```

部署脚本会自动完成：
1. ✅ 停止旧进程
2. ✅ 备份配置文件
3. ✅ 拉取最新代码
4. ✅ 验证所有修复（权重、阈值、防抖动）
5. ✅ 清理Python缓存
6. ✅ 快速测试运行
7. ✅ 显示启动命令

### 方式 2: 快速启动（已部署完成后）

```bash
cd ~/cryptosignal
./start_production.sh
```

会提供三种启动方式供选择：
1. **Screen会话**（推荐）- 可分离后台运行
2. **nohup后台** - 传统后台运行
3. **前台运行** - 测试用

---

## 📝 手动部署步骤

如果需要手动执行，请按以下步骤操作：

### 第 1 步：停止旧进程

```bash
cd ~/cryptosignal

# 停止所有扫描器进程
ps aux | grep realtime_signal_scanner | grep -v grep | awk '{print $2}' | xargs kill 2>/dev/null

# 确认已停止
ps aux | grep realtime_signal_scanner | grep -v grep || echo "✅ 已停止"
```

### 第 2 步：备份配置

```bash
cd ~/cryptosignal

# 备份配置文件
BACKUP_TIME=$(date +%Y%m%d_%H%M%S)
cp config/params.json config/params.json.bak.$BACKUP_TIME
cp config/telegram.json config/telegram.json.bak.$BACKUP_TIME
cp config/binance_credentials.json config/binance_credentials.json.bak.$BACKUP_TIME

echo "✅ 配置已备份"
```

### 第 3 步：拉取v6.1代码

```bash
cd ~/cryptosignal

# 切换到v6.1分支
git fetch origin claude/review-system-overview-011CUhLQjByWuXC1bySJCHKQ
git checkout claude/review-system-overview-011CUhLQjByWuXC1bySJCHKQ
git pull origin claude/review-system-overview-011CUhLQjByWuXC1bySJCHKQ

# 查看最新提交
git log --oneline -5
```

应该看到以下提交：
- `669f403` - chore: 添加Binance凭证文件到.gitignore
- `55ba9d2` - fix: 修复系统审查发现的关键问题（合规度70%→90%+）

### 第 4 步：验证修复

```bash
cd ~/cryptosignal

# 验证权重配置
python3 -c "
import json
with open('config/params.json') as f:
    w = json.load(f)['weights']
    a_total = sum(w[k] for k in ['T','M','C','S','V','O','L','B','Q'])
    print(f'A层9因子总和: {a_total}%')
    print(f'F权重: {w[\"F\"]}, I权重: {w[\"I\"]}')
    assert a_total == 100.0 and w['F'] == 0 and w['I'] == 0
    print('✅ 权重配置正确')
"

# 验证Prime阈值
grep -n "is_prime = (prime_strength >=" ats_core/pipeline/analyze_symbol.py

# 验证防抖动参数
grep -A 5 "self.anti_jitter = AntiJitter" scripts/realtime_signal_scanner.py
```

### 第 5 步：清理缓存

```bash
cd ~/cryptosignal

# 清理Python缓存
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -name "*.pyc" -delete 2>/dev/null

echo "✅ 缓存已清理"
```

### 第 6 步：测试运行

```bash
cd ~/cryptosignal

# 快速测试（10秒）
timeout 10 python3 scripts/realtime_signal_scanner.py --max-symbols 10 --no-telegram || echo "✅ 测试完成"
```

### 第 7 步：生产启动

#### 选项 A: Screen会话（推荐）

```bash
cd ~/cryptosignal

# 创建screen会话
screen -S cryptosignal

# 在screen中运行（完整扫描140币种 + Telegram通知）
python3 scripts/realtime_signal_scanner.py --interval 300

# 初始化完成后，按 Ctrl+A 然后 D 分离会话

# 重新连接
screen -r cryptosignal
```

#### 选项 B: 后台运行

```bash
cd ~/cryptosignal
mkdir -p logs

# 后台启动
nohup python3 scripts/realtime_signal_scanner.py --interval 300 > logs/scanner_$(date +%Y%m%d_%H%M%S).log 2>&1 &

# 查看PID
echo $!

# 查看日志
tail -f logs/scanner_*.log
```

#### 选项 C: 前台运行（测试用）

```bash
cd ~/cryptosignal

# 前台运行（Ctrl+C停止）
python3 scripts/realtime_signal_scanner.py --interval 300
```

---

## ✅ 验证清单

部署完成后，请确认以下项目：

### 配置文件验证
- [ ] `config/params.json` 存在且有效
- [ ] `config/binance_credentials.json` 存在且已填写真实API
- [ ] `config/telegram.json` 存在且已配置（可选）

### 代码修复验证
- [ ] A层9因子权重总和 = 100.0%
- [ ] F和I权重 = 0（B层调制器）
- [ ] Prime阈值 = 25分
- [ ] 概率阈值 = 0.58
- [ ] 防抖动阈值 = 0.65
- [ ] 确认K线 = 1/2
- [ ] 冷却时间 = 60秒

### 系统运行验证
- [ ] 系统成功初始化
- [ ] 没有导入错误
- [ ] 能够连接Binance API
- [ ] WebSocket连接正常
- [ ] 能够扫描币种并生成信号

### 监控验证（运行后）
- [ ] 查看日志输出正常
- [ ] Telegram通知能够发送
- [ ] 进程在后台稳定运行
- [ ] 每5分钟扫描一次（间隔300秒）

---

## 📊 监控与调优

### 实时监控

```bash
# 查看运行状态
ps aux | grep realtime_signal_scanner

# 查看日志（如果使用nohup）
tail -f logs/scanner_*.log

# 查看Screen会话
screen -ls
screen -r cryptosignal

# 统计信号数量（假设日志在logs目录）
grep -c "🔔 Prime信号" logs/scanner_*.log
```

### 24小时后统计

```bash
cd ~/cryptosignal

# 统计信号数量
echo "=== 信号统计 ==="
grep "🔔 Prime信号" logs/scanner_*.log | wc -l
grep "⚠️ Watch信号" logs/scanner_*.log | wc -l

# 统计四门通过率
echo "=== 四门统计 ==="
grep "DataQual门" logs/scanner_*.log | wc -l
grep "EV门" logs/scanner_*.log | wc -l
grep "Execution门" logs/scanner_*.log | wc -l
grep "Probability门" logs/scanner_*.log | wc -l
```

### 调优建议

如果运行24小时后：

**信号仍然太少**（< 2个Prime/小时）:
```json
// 进一步降低阈值 (config/params.json)
{
  "publish": {
    "prime_prob_min": 0.55,  // 0.58 → 0.55
    "prime_dims_ok_min": 2,  // 3 → 2
    "prime_dim_threshold": 25 // 30 → 25
  }
}
```

**假信号过多**（胜率 < 50%）:
```json
// 适当提高阈值 (config/params.json)
{
  "publish": {
    "prime_prob_min": 0.60,  // 0.58 → 0.60
    "prime_dims_ok_min": 4,  // 3 → 4
  }
}
```

**修改后重启**:
```bash
# 停止旧进程
ps aux | grep realtime_signal_scanner | grep -v grep | awk '{print $2}' | xargs kill

# 清理缓存
find ~/cryptosignal -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null

# 重新启动
cd ~/cryptosignal
./start_production.sh
```

---

## 🔧 故障排查

### 问题 1: 无法启动

**错误**: `ModuleNotFoundError: No module named 'aiohttp'`

**解决**:
```bash
cd ~/cryptosignal
pip3 install -r requirements.txt
```

### 问题 2: Binance API错误

**错误**: `FileNotFoundError: config/binance_credentials.json`

**解决**:
```bash
# 确保配置文件存在
ls -l config/binance_credentials.json

# 验证内容有效
python3 -c "
import json
with open('config/binance_credentials.json') as f:
    config = json.load(f)
    assert config['binance']['api_key'] != 'YOUR_BINANCE_API_KEY_HERE'
    print('✅ 配置有效')
"
```

### 问题 3: Telegram无法发送

**错误**: Telegram通知未收到

**解决**:
```bash
# 检查配置
cat config/telegram.json

# 测试Telegram连接
python3 -c "
import requests
import json

with open('config/telegram.json') as f:
    tg = json.load(f)

url = f\"https://api.telegram.org/bot{tg['bot_token']}/sendMessage\"
data = {
    'chat_id': tg['chat_id'],
    'text': '✅ CryptoSignal v6.1 测试消息'
}

resp = requests.post(url, json=data)
if resp.status_code == 200:
    print('✅ Telegram连接正常')
else:
    print(f'❌ 错误: {resp.text}')
"
```

### 问题 4: 进程异常退出

**现象**: 进程启动后自动退出

**排查步骤**:
```bash
# 1. 查看完整日志
tail -100 logs/scanner_*.log

# 2. 前台运行查看错误
cd ~/cryptosignal
python3 scripts/realtime_signal_scanner.py --interval 300

# 3. 检查权限
ls -l scripts/realtime_signal_scanner.py

# 4. 检查Python版本（需要3.8+）
python3 --version
```

---

## 📚 相关文档

- **修复方案**: `SYSTEM_FIX_PLAN.md`
- **系统概览**: `docs/SYSTEM_REVIEW_2025-11.md`
- **规范文档**:
  - `newstandards/STANDARDS.md` - 总规范
  - `newstandards/MODULATORS.md` - B层调制器规范
  - `newstandards/PUBLISHING.md` - 发布规范
- **快速参考**: `standards/QUICK_REFERENCE.md`

---

## 📞 支持

如遇到问题，请提供以下信息：

1. **Git版本**: `git log --oneline -3`
2. **配置验证**: 运行 `./deploy.sh` 的输出
3. **错误日志**: 最近50行日志
4. **系统信息**: Python版本、操作系统

---

**版本**: v6.1
**更新日期**: 2025-11-01
**分支**: `claude/review-system-overview-011CUhLQjByWuXC1bySJCHKQ`
**关键提交**: `55ba9d2`, `669f403`
