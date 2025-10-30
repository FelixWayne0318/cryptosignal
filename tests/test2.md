Welcome to Ubuntu 22.04.5 LTS (GNU/Linux 5.15.0-160-generic x86_64)

 * Documentation:  https://help.ubuntu.com
 * Management:     https://landscape.canonical.com
 * Support:        https://ubuntu.com/pro

 System information as of Wed Oct 29 06:09:14 PM UTC 2025

  System load:  0.02               Processes:               138
  Usage of /:   28.2% of 51.01GB   Users logged in:         0
  Memory usage: 17%                IPv4 address for enp1s0: 139.180.157.152
  Swap usage:   0%

 * Strictly confined Kubernetes makes edge and IoT secure. Learn how MicroK8s
   just raised the bar for easy, resilient and secure K8s cluster deployment.

   https://ubuntu.com/engage/secure-kubernetes-at-the-edge

Expanded Security Maintenance for Applications is not enabled.

0 updates can be applied immediately.

Enable ESM Apps to receive additional future security updates.
See https://ubuntu.com/esm or run: sudo pro status

New release '24.04.3 LTS' available.
Run 'do-release-upgrade' to upgrade to it.


Last login: Wed Oct 29 18:09:15 2025 from 157.10.251.28
cryptosignal@vultr-ats:~$ cd ~/cryptosignal
cryptosignal@vultr-ats:~/cryptosignal$ git pull origin claude/analyze-system-functionality-011CUbfJcoGsD3prWPkay6LE
remote: Enumerating objects: 6, done.
remote: Counting objects: 100% (6/6), done.
remote: Compressing objects: 100% (2/2), done.
remote: Total 4 (delta 2), reused 4 (delta 2), pack-reused 0 (from 0)
Unpacking objects: 100% (4/4), 2.64 KiB | 1.32 MiB/s, done.
From https://github.com/FelixWayne0318/cryptosignal
 * branch            claude/analyze-system-functionality-011CUbfJcoGsD3prWPkay6LE -> FETCH_HEAD
   7271fcf..277cfdd  claude/analyze-system-functionality-011CUbfJcoGsD3prWPkay6LE -> origin/claude/analyze-system-functionality-011CUbfJcoGsD3prWPkay6LE
Updating 7271fcf..277cfdd
Fast-forward
 scripts/run_full_system.sh | 173 ++++++++++++++++++++++++++++++++++++++++++++++++++++
 1 file changed, 173 insertions(+)
 create mode 100755 scripts/run_full_system.sh
cryptosignal@vultr-ats:~/cryptosignal$ 
cryptosignal@vultr-ats:~/cryptosignal$ # 验证文件是否存在
cryptosignal@vultr-ats:~/cryptosignal$ ls -lh scripts/run_full_system.sh
-rwxrwxr-x 1 cryptosignal cryptosignal 4.4K Oct 29 18:10 scripts/run_full_system.sh
cryptosignal@vultr-ats:~/cryptosignal$ 
cryptosignal@vultr-ats:~/cryptosignal$ # 查看最新提交
cryptosignal@vultr-ats:~/cryptosignal$ git log --oneline -1
277cfdd (HEAD -> claude/optimize-coin-analysis-speed-011CUYy6rjvHGXbkToyBt9ja, origin/claude/analyze-system-functionality-011CUbfJcoGsD3prWPkay6LE) feat: 添加完整系统一键运行脚本
cryptosignal@vultr-ats:~/cryptosignal$ export TELEGRAM_BOT_TOKEN="7545580872:AAF7HzkHA4LRQUiOZngUgL39epuGVeEta70"
cryptosignal@vultr-ats:~/cryptosignal$ export TELEGRAM_CHAT_ID="-1003142003085"
cryptosignal@vultr-ats:~/cryptosignal$ 
cryptosignal@vultr-ats:~/cryptosignal$ bash scripts/run_full_system.sh --test
================================================================================
  CryptoSignal 完整系统启动
================================================================================

📁 项目目录: /home/cryptosignal/cryptosignal

🔍 检查环境变量...
   ✅ TELEGRAM_BOT_TOKEN: 7545580872:AAF7HzkHA...
   ✅ TELEGRAM_CHAT_ID: -1003142003085
   ✅ BINANCE_API_KEY: cIPL0yqyYD...

🐍 检查Python环境...
Python 3.10.12

📦 检查依赖...
   ✅ 核心依赖已安装
   🧪 测试模式: 只扫描10个币种

================================================================================
  运行参数
================================================================================
   最低分数阈值: 70
   扫描模式: 单次扫描
   币种限制: 10
================================================================================

▶️  按Enter键开始运行，或Ctrl+C取消... 

📝 日志文件: logs/full_system_20251029_181054.log

================================================================================
  🚀 启动中...
================================================================================

运行命令: python3 scripts/realtime_signal_scanner.py --min-score 70 --max-symbols 10

[2025-10-29 18:10:54Z] ✅ K线缓存管理器初始化完成
[2025-10-29 18:10:54Z] ✅ 优化批量扫描器创建成功
[2025-10-29 18:10:54Z] ✅ 信号扫描器创建成功
[2025-10-29 18:10:54Z] 
============================================================
[2025-10-29 18:10:54Z] 🚀 初始化WebSocket信号扫描器
[2025-10-29 18:10:54Z] ============================================================
[2025-10-29 18:10:55Z] 
============================================================
[2025-10-29 18:10:55Z] 🚀 初始化优化批量扫描器...
[2025-10-29 18:10:55Z] ============================================================
[2025-10-29 18:10:55Z] 
1️⃣  初始化Binance客户端...
[2025-10-29 18:10:55Z] ✅ 币安合约客户端初始化完成 (testnet=False)
[2025-10-29 18:10:55Z] ⏰ 服务器时间同步完成，偏移: -25ms
[2025-10-29 18:10:55Z] ✅ 客户端初始化完成，服务器时间已同步
[2025-10-29 18:10:55Z] 
2️⃣  获取高流动性USDT合约币种...
[2025-10-29 18:10:55Z]    总计: 530 个USDT永续合约
[2025-10-29 18:10:55Z]    获取24h行情数据...
[2025-10-29 18:10:56Z]    ✅ 筛选出 140 个高流动性币种（24h成交额>3M USDT）
[2025-10-29 18:10:56Z]    TOP 5: ETHUSDT, BTCUSDT, SOLUSDT, XRPUSDT, BNBUSDT
[2025-10-29 18:10:56Z]    成交额范围: 16576.2M ~ 25.5M USDT
[2025-10-29 18:10:56Z] 
3️⃣  批量初始化K线缓存（这是一次性操作）...
[2025-10-29 18:10:56Z] ============================================================
[2025-10-29 18:10:56Z] 🔧 批量初始化K线缓存...
[2025-10-29 18:10:56Z] ============================================================
[2025-10-29 18:10:56Z]    币种数: 140
[2025-10-29 18:10:56Z]    周期: 1h, 4h, 15m, 1d
[2025-10-29 18:10:56Z]    K线数/周期: 300
[2025-10-29 18:10:56Z]    预计总调用: 560次
[2025-10-29 18:10:56Z]    预计耗时: 1.9分钟
[2025-10-29 18:10:56Z] ============================================================
[2025-10-29 18:11:06Z]    进度: 20/140 (14%), 速度: 1.9 币种/秒, 已用: 10s, 剩余: 62s
[2025-10-29 18:11:06Z]    进度: 20/140 (14%), 速度: 1.9 币种/秒, 已用: 10s, 剩余: 63s
[2025-10-29 18:11:06Z]    进度: 20/140 (14%), 速度: 1.9 币种/秒, 已用: 11s, 剩余: 63s
[2025-10-29 18:11:06Z]    进度: 20/140 (14%), 速度: 1.9 币种/秒, 已用: 11s, 剩余: 64s
[2025-10-29 18:11:17Z]    进度: 40/140 (29%), 速度: 1.9 币种/秒, 已用: 21s, 剩余: 52s
[2025-10-29 18:11:17Z]    进度: 40/140 (29%), 速度: 1.9 币种/秒, 已用: 21s, 剩余: 53s
[2025-10-29 18:11:17Z]    进度: 40/140 (29%), 速度: 1.9 币种/秒, 已用: 21s, 剩余: 53s
[2025-10-29 18:11:17Z]    进度: 40/140 (29%), 速度: 1.9 币种/秒, 已用: 21s, 剩余: 53s
[2025-10-29 18:11:27Z]    进度: 60/140 (43%), 速度: 1.9 币种/秒, 已用: 32s, 剩余: 42s
[2025-10-29 18:11:27Z]    进度: 60/140 (43%), 速度: 1.9 币种/秒, 已用: 32s, 剩余: 42s
[2025-10-29 18:11:27Z]    进度: 60/140 (43%), 速度: 1.9 币种/秒, 已用: 32s, 剩余: 42s
[2025-10-29 18:11:28Z]    进度: 60/140 (43%), 速度: 1.9 币种/秒, 已用: 32s, 剩余: 43s
[2025-10-29 18:11:37Z]    进度: 80/140 (57%), 速度: 1.9 币种/秒, 已用: 42s, 剩余: 31s
[2025-10-29 18:11:38Z]    进度: 80/140 (57%), 速度: 1.9 币种/秒, 已用: 42s, 剩余: 32s
[2025-10-29 18:11:38Z]    进度: 80/140 (57%), 速度: 1.9 币种/秒, 已用: 42s, 剩余: 32s
[2025-10-29 18:11:38Z]    进度: 80/140 (57%), 速度: 1.9 币种/秒, 已用: 42s, 剩余: 32s
[2025-10-29 18:11:48Z]    进度: 100/140 (71%), 速度: 1.9 币种/秒, 已用: 52s, 剩余: 21s
[2025-10-29 18:11:48Z]    进度: 100/140 (71%), 速度: 1.9 币种/秒, 已用: 53s, 剩余: 21s
[2025-10-29 18:11:48Z]    进度: 100/140 (71%), 速度: 1.9 币种/秒, 已用: 53s, 剩余: 21s
[2025-10-29 18:11:48Z]    进度: 100/140 (71%), 速度: 1.9 币种/秒, 已用: 53s, 剩余: 21s
[2025-10-29 18:11:58Z]    进度: 120/140 (86%), 速度: 1.9 币种/秒, 已用: 63s, 剩余: 10s
[2025-10-29 18:11:58Z]    进度: 120/140 (86%), 速度: 1.9 币种/秒, 已用: 63s, 剩余: 10s
[2025-10-29 18:11:59Z]    进度: 120/140 (86%), 速度: 1.9 币种/秒, 已用: 63s, 剩余: 10s
[2025-10-29 18:11:59Z]    进度: 120/140 (86%), 速度: 1.9 币种/秒, 已用: 63s, 剩余: 11s
[2025-10-29 18:12:09Z]    进度: 140/140 (100%), 速度: 1.9 币种/秒, 已用: 73s, 剩余: 0s
[2025-10-29 18:12:09Z]    进度: 140/140 (100%), 速度: 1.9 币种/秒, 已用: 73s, 剩余: 0s
[2025-10-29 18:12:09Z]    进度: 140/140 (100%), 速度: 1.9 币种/秒, 已用: 73s, 剩余: 0s
[2025-10-29 18:12:09Z]    进度: 140/140 (100%), 速度: 1.9 币种/秒, 已用: 73s, 剩余: 0s
[2025-10-29 18:12:09Z] ============================================================
[2025-10-29 18:12:09Z] ✅ 批量初始化完成
[2025-10-29 18:12:09Z] ============================================================
[2025-10-29 18:12:09Z]    成功: 560/560 次调用
[2025-10-29 18:12:09Z]    失败: 0 次
[2025-10-29 18:12:09Z]    总耗时: 74秒 (1.2分钟)
[2025-10-29 18:12:09Z]    平均速度: 1.9 币种/秒
[2025-10-29 18:12:09Z]    内存占用: 27.9MB
[2025-10-29 18:12:09Z] ============================================================
[2025-10-29 18:12:09Z] 
4️⃣  启动WebSocket实时更新...
[2025-10-29 18:12:09Z]    策略: 仅订阅关键周期（1h, 4h）以避免连接数超限
[2025-10-29 18:12:09Z]    连接数: 140币种 × 2周期 = 280 < 300限制 ✅
[2025-10-29 18:12:09Z] ============================================================
[2025-10-29 18:12:09Z] 🚀 批量启动WebSocket K线流...
[2025-10-29 18:12:09Z] ============================================================
[2025-10-29 18:12:09Z]    币种数: 140
[2025-10-29 18:12:09Z]    周期: 1h, 4h
[2025-10-29 18:12:09Z]    WebSocket连接数: 280/280
[2025-10-29 18:12:09Z] ============================================================
[2025-10-29 18:12:09Z] ✅ 已订阅数据流: ethusdt@kline_1h
[2025-10-29 18:12:09Z] 🔌 连接WebSocket: ethusdt@kline_1h
[2025-10-29 18:12:09Z] ✅ 已订阅数据流: ethusdt@kline_4h
[2025-10-29 18:12:09Z] 🔌 连接WebSocket: ethusdt@kline_4h
[2025-10-29 18:12:09Z] ✅ 已订阅数据流: btcusdt@kline_1h
[2025-10-29 18:12:09Z] 🔌 连接WebSocket: btcusdt@kline_1h
[2025-10-29 18:12:09Z] ✅ 已订阅数据流: btcusdt@kline_4h
[2025-10-29 18:12:09Z] 🔌 连接WebSocket: btcusdt@kline_4h
[2025-10-29 18:12:09Z] ✅ 已订阅数据流: solusdt@kline_1h
[2025-10-29 18:12:09Z] 🔌 连接WebSocket: solusdt@kline_1h
[2025-10-29 18:12:09Z] ✅ 已订阅数据流: solusdt@kline_4h
[2025-10-29 18:12:09Z] 🔌 连接WebSocket: solusdt@kline_4h
[2025-10-29 18:12:09Z] ✅ 已订阅数据流: xrpusdt@kline_1h
[2025-10-29 18:12:09Z] 🔌 连接WebSocket: xrpusdt@kline_1h
[2025-10-29 18:12:09Z] ✅ 已订阅数据流: xrpusdt@kline_4h
[2025-10-29 18:12:09Z] 🔌 连接WebSocket: xrpusdt@kline_4h
[2025-10-29 18:12:09Z] ✅ 已订阅数据流: bnbusdt@kline_1h
[2025-10-29 18:12:09Z] 🔌 连接WebSocket: bnbusdt@kline_1h
[2025-10-29 18:12:09Z] ✅ 已订阅数据流: bnbusdt@kline_4h
[2025-10-29 18:12:09Z] 🔌 连接WebSocket: bnbusdt@kline_4h
[2025-10-29 18:12:09Z] ✅ 已订阅数据流: trumpusdt@kline_1h
[2025-10-29 18:12:09Z] 🔌 连接WebSocket: trumpusdt@kline_1h
[2025-10-29 18:12:09Z] ✅ 已订阅数据流: trumpusdt@kline_4h
[2025-10-29 18:12:09Z] 🔌 连接WebSocket: trumpusdt@kline_4h
[2025-10-29 18:12:09Z] ✅ 已订阅数据流: dogeusdt@kline_1h
[2025-10-29 18:12:09Z] 🔌 连接WebSocket: dogeusdt@kline_1h
[2025-10-29 18:12:09Z] ✅ 已订阅数据流: dogeusdt@kline_4h
[2025-10-29 18:12:09Z] 🔌 连接WebSocket: dogeusdt@kline_4h
[2025-10-29 18:12:09Z] ✅ 已订阅数据流: zecusdt@kline_1h
[2025-10-29 18:12:09Z] 🔌 连接WebSocket: zecusdt@kline_1h
[2025-10-29 18:12:09Z] ✅ 已订阅数据流: zecusdt@kline_4h
[2025-10-29 18:12:09Z] 🔌 连接WebSocket: zecusdt@kline_4h
[2025-10-29 18:12:09Z] ✅ 已订阅数据流: hypeusdt@kline_1h
[2025-10-29 18:12:09Z] 🔌 连接WebSocket: hypeusdt@kline_1h
[2025-10-29 18:12:09Z] ✅ 已订阅数据流: hypeusdt@kline_4h
[2025-10-29 18:12:09Z] 🔌 连接WebSocket: hypeusdt@kline_4h
[2025-10-29 18:12:09Z] ✅ 已订阅数据流: asterusdt@kline_1h
[2025-10-29 18:12:09Z] 🔌 连接WebSocket: asterusdt@kline_1h
[2025-10-29 18:12:09Z] ✅ 已订阅数据流: asterusdt@kline_4h
[2025-10-29 18:12:09Z] 🔌 连接WebSocket: asterusdt@kline_4h
[2025-10-29 18:12:09Z] ✅ 已订阅数据流: ensousdt@kline_1h
[2025-10-29 18:12:09Z] 🔌 连接WebSocket: ensousdt@kline_1h
[2025-10-29 18:12:09Z] ✅ WebSocket连接成功: ethusdt@kline_4h
[2025-10-29 18:12:09Z] ✅ WebSocket连接成功: ethusdt@kline_1h
[2025-10-29 18:12:09Z] ✅ WebSocket连接成功: btcusdt@kline_1h
[2025-10-29 18:12:09Z] ✅ 已订阅数据流: ensousdt@kline_4h
[2025-10-29 18:12:09Z] 🔌 WebSocket已关闭: ensousdt@kline_4h
[2025-10-29 18:12:09Z] ✅ WebSocket连接成功: btcusdt@kline_4h
[2025-10-29 18:12:09Z] ✅ WebSocket连接成功: solusdt@kline_1h
[2025-10-29 18:12:09Z] ✅ 已订阅数据流: suiusdt@kline_1h
[2025-10-29 18:12:09Z] 🔌 WebSocket已关闭: suiusdt@kline_1h
[2025-10-29 18:12:09Z] ✅ WebSocket连接成功: solusdt@kline_4h
[2025-10-29 18:12:09Z] ✅ 已订阅数据流: suiusdt@kline_4h
[2025-10-29 18:12:09Z] 🔌 WebSocket已关闭: suiusdt@kline_4h
[2025-10-29 18:12:09Z] ✅ WebSocket连接成功: xrpusdt@kline_1h
[2025-10-29 18:12:09Z] ✅ 已订阅数据流: pumpusdt@kline_1h
[2025-10-29 18:12:09Z] 🔌 WebSocket已关闭: pumpusdt@kline_1h
[2025-10-29 18:12:09Z] ✅ WebSocket连接成功: xrpusdt@kline_4h
[2025-10-29 18:12:09Z] ✅ 已订阅数据流: pumpusdt@kline_4h
[2025-10-29 18:12:09Z] 🔌 WebSocket已关闭: pumpusdt@kline_4h
[2025-10-29 18:12:09Z] ✅ WebSocket连接成功: bnbusdt@kline_1h
[2025-10-29 18:12:09Z] ✅ 已订阅数据流: coaiusdt@kline_1h
[2025-10-29 18:12:09Z] 🔌 WebSocket已关闭: coaiusdt@kline_1h
[2025-10-29 18:12:09Z] ✅ WebSocket连接成功: bnbusdt@kline_4h
[2025-10-29 18:12:09Z] ✅ WebSocket连接成功: trumpusdt@kline_1h
[2025-10-29 18:12:09Z] ✅ 已订阅数据流: coaiusdt@kline_4h
[2025-10-29 18:12:09Z] 🔌 WebSocket已关闭: coaiusdt@kline_4h
[2025-10-29 18:12:09Z] ✅ WebSocket连接成功: trumpusdt@kline_4h
[2025-10-29 18:12:09Z] ✅ 已订阅数据流: linkusdt@kline_1h
[2025-10-29 18:12:09Z] 🔌 WebSocket已关闭: linkusdt@kline_1h
[2025-10-29 18:12:09Z] ✅ WebSocket连接成功: dogeusdt@kline_1h
[2025-10-29 18:12:09Z] ✅ 已订阅数据流: linkusdt@kline_4h
[2025-10-29 18:12:09Z] 🔌 WebSocket已关闭: linkusdt@kline_4h
[2025-10-29 18:12:09Z] ✅ WebSocket连接成功: dogeusdt@kline_4h
[2025-10-29 18:12:09Z] ✅ 已订阅数据流: taousdt@kline_1h
[2025-10-29 18:12:09Z] 🔌 WebSocket已关闭: taousdt@kline_1h
[2025-10-29 18:12:09Z] ✅ 已订阅数据流: taousdt@kline_4h
[2025-10-29 18:12:09Z] 🔌 WebSocket已关闭: taousdt@kline_4h
[2025-10-29 18:12:09Z] ✅ WebSocket连接成功: zecusdt@kline_1h
[2025-10-29 18:12:09Z] ✅ 已订阅数据流: adausdt@kline_1h
[2025-10-29 18:12:09Z] 🔌 WebSocket已关闭: adausdt@kline_1h
[2025-10-29 18:12:09Z] ✅ WebSocket连接成功: zecusdt@kline_4h
[2025-10-29 18:12:09Z] ✅ 已订阅数据流: adausdt@kline_4h
[2025-10-29 18:12:09Z] 🔌 WebSocket已关闭: adausdt@kline_4h
[2025-10-29 18:12:10Z] ✅ WebSocket连接成功: hypeusdt@kline_1h
[2025-10-29 18:12:10Z] ✅ WebSocket连接成功: hypeusdt@kline_4h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: olusdt@kline_1h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: olusdt@kline_1h
[2025-10-29 18:12:10Z] ✅ WebSocket连接成功: asterusdt@kline_1h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: olusdt@kline_4h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: olusdt@kline_4h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: enausdt@kline_1h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: enausdt@kline_1h
[2025-10-29 18:12:10Z] ✅ WebSocket连接成功: asterusdt@kline_4h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: enausdt@kline_4h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: enausdt@kline_4h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: 1000pepeusdt@kline_1h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: 1000pepeusdt@kline_1h
[2025-10-29 18:12:10Z] ✅ WebSocket连接成功: ensousdt@kline_1h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: 1000pepeusdt@kline_4h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: 1000pepeusdt@kline_4h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: evaausdt@kline_1h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: evaausdt@kline_1h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: evaausdt@kline_4h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: evaausdt@kline_4h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: virtualusdt@kline_1h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: virtualusdt@kline_1h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: virtualusdt@kline_4h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: virtualusdt@kline_4h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: giggleusdt@kline_1h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: giggleusdt@kline_1h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: giggleusdt@kline_4h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: giggleusdt@kline_4h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: ltcusdt@kline_1h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: ltcusdt@kline_1h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: ltcusdt@kline_4h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: ltcusdt@kline_4h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: avaxusdt@kline_1h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: avaxusdt@kline_1h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: avaxusdt@kline_4h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: avaxusdt@kline_4h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: phbusdt@kline_1h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: phbusdt@kline_1h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: phbusdt@kline_4h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: phbusdt@kline_4h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: kiteusdt@kline_1h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: kiteusdt@kline_1h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: kiteusdt@kline_4h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: kiteusdt@kline_4h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: paxgusdt@kline_1h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: paxgusdt@kline_1h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: paxgusdt@kline_4h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: paxgusdt@kline_4h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: hbarusdt@kline_1h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: hbarusdt@kline_1h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: hbarusdt@kline_4h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: hbarusdt@kline_4h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: wlfiusdt@kline_1h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: wlfiusdt@kline_1h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: wlfiusdt@kline_4h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: wlfiusdt@kline_4h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: maviausdt@kline_1h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: maviausdt@kline_1h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: maviausdt@kline_4h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: maviausdt@kline_4h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: xplusdt@kline_1h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: xplusdt@kline_1h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: xplusdt@kline_4h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: xplusdt@kline_4h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: bchusdt@kline_1h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: bchusdt@kline_1h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: bchusdt@kline_4h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: bchusdt@kline_4h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: fartcoinusdt@kline_1h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: fartcoinusdt@kline_1h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: fartcoinusdt@kline_4h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: fartcoinusdt@kline_4h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: sapienusdt@kline_1h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: sapienusdt@kline_1h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: sapienusdt@kline_4h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: sapienusdt@kline_4h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: wifusdt@kline_1h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: wifusdt@kline_1h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: wifusdt@kline_4h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: wifusdt@kline_4h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: flmusdt@kline_1h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: flmusdt@kline_1h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: flmusdt@kline_4h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: flmusdt@kline_4h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: ybusdt@kline_1h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: ybusdt@kline_1h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: ybusdt@kline_4h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: ybusdt@kline_4h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: nearusdt@kline_1h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: nearusdt@kline_1h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: nearusdt@kline_4h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: nearusdt@kline_4h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: penguusdt@kline_1h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: penguusdt@kline_1h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: penguusdt@kline_4h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: penguusdt@kline_4h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: commonusdt@kline_1h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: commonusdt@kline_1h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: commonusdt@kline_4h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: commonusdt@kline_4h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: dotusdt@kline_1h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: dotusdt@kline_1h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: dotusdt@kline_4h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: dotusdt@kline_4h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: aaveusdt@kline_1h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: aaveusdt@kline_1h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: aaveusdt@kline_4h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: aaveusdt@kline_4h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: filusdt@kline_1h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: filusdt@kline_1h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: filusdt@kline_4h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: filusdt@kline_4h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: b2usdt@kline_1h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: b2usdt@kline_1h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: b2usdt@kline_4h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: b2usdt@kline_4h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: aprusdt@kline_1h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: aprusdt@kline_1h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: aprusdt@kline_4h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: aprusdt@kline_4h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: wldusdt@kline_1h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: wldusdt@kline_1h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: wldusdt@kline_4h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: wldusdt@kline_4h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: 币安人生usdt@kline_1h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: 币安人生usdt@kline_1h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: 币安人生usdt@kline_4h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: 币安人生usdt@kline_4h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: arbusdt@kline_1h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: arbusdt@kline_1h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: arbusdt@kline_4h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: arbusdt@kline_4h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: 1000bonkusdt@kline_1h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: 1000bonkusdt@kline_1h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: 1000bonkusdt@kline_4h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: 1000bonkusdt@kline_4h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: kgenusdt@kline_1h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: kgenusdt@kline_1h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: kgenusdt@kline_4h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: kgenusdt@kline_4h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: trxusdt@kline_1h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: trxusdt@kline_1h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: trxusdt@kline_4h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: trxusdt@kline_4h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: kdausdt@kline_1h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: kdausdt@kline_1h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: kdausdt@kline_4h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: kdausdt@kline_4h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: pufferusdt@kline_1h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: pufferusdt@kline_1h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: pufferusdt@kline_4h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: pufferusdt@kline_4h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: husdt@kline_1h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: husdt@kline_1h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: husdt@kline_4h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: husdt@kline_4h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: tonusdt@kline_1h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: tonusdt@kline_1h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: tonusdt@kline_4h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: tonusdt@kline_4h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: aptusdt@kline_1h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: aptusdt@kline_1h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: aptusdt@kline_4h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: aptusdt@kline_4h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: 1000shibusdt@kline_1h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: 1000shibusdt@kline_1h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: 1000shibusdt@kline_4h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: 1000shibusdt@kline_4h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: aiausdt@kline_1h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: aiausdt@kline_1h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: aiausdt@kline_4h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: aiausdt@kline_4h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: avntusdt@kline_1h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: avntusdt@kline_1h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: avntusdt@kline_4h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: avntusdt@kline_4h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: ffusdt@kline_1h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: ffusdt@kline_1h
[2025-10-29 18:12:10Z] ✅ 已订阅数据流: ffusdt@kline_4h
[2025-10-29 18:12:10Z] 🔌 WebSocket已关闭: ffusdt@kline_4h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: ondousdt@kline_1h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: ondousdt@kline_1h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: ondousdt@kline_4h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: ondousdt@kline_4h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: 4usdt@kline_1h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: 4usdt@kline_1h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: 4usdt@kline_4h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: 4usdt@kline_4h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: tiausdt@kline_1h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: tiausdt@kline_1h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: tiausdt@kline_4h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: tiausdt@kline_4h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: xlmusdt@kline_1h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: xlmusdt@kline_1h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: xlmusdt@kline_4h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: xlmusdt@kline_4h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: merlusdt@kline_1h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: merlusdt@kline_1h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: merlusdt@kline_4h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: merlusdt@kline_4h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: atusdt@kline_1h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: atusdt@kline_1h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: atusdt@kline_4h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: atusdt@kline_4h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: uniusdt@kline_1h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: uniusdt@kline_1h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: uniusdt@kline_4h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: uniusdt@kline_4h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: ubusdt@kline_1h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: ubusdt@kline_1h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: ubusdt@kline_4h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: ubusdt@kline_4h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: ethfiusdt@kline_1h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: ethfiusdt@kline_1h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: ethfiusdt@kline_4h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: ethfiusdt@kline_4h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: crvusdt@kline_1h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: crvusdt@kline_1h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: crvusdt@kline_4h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: crvusdt@kline_4h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: treeusdt@kline_1h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: treeusdt@kline_1h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: treeusdt@kline_4h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: treeusdt@kline_4h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: melaniausdt@kline_1h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: melaniausdt@kline_1h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: melaniausdt@kline_4h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: melaniausdt@kline_4h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: opusdt@kline_1h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: opusdt@kline_1h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: opusdt@kline_4h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: opusdt@kline_4h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: 42usdt@kline_1h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: 42usdt@kline_1h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: 42usdt@kline_4h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: 42usdt@kline_4h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: recallusdt@kline_1h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: recallusdt@kline_1h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: recallusdt@kline_4h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: recallusdt@kline_4h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: eigenusdt@kline_1h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: eigenusdt@kline_1h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: eigenusdt@kline_4h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: eigenusdt@kline_4h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: xpinusdt@kline_1h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: xpinusdt@kline_1h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: xpinusdt@kline_4h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: xpinusdt@kline_4h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: ldousdt@kline_1h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: ldousdt@kline_1h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: ldousdt@kline_4h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: ldousdt@kline_4h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: etcusdt@kline_1h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: etcusdt@kline_1h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: etcusdt@kline_4h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: etcusdt@kline_4h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: shellusdt@kline_1h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: shellusdt@kline_1h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: shellusdt@kline_4h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: shellusdt@kline_4h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: riverusdt@kline_1h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: riverusdt@kline_1h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: riverusdt@kline_4h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: riverusdt@kline_4h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: biousdt@kline_1h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: biousdt@kline_1h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: biousdt@kline_4h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: biousdt@kline_4h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: bluaiusdt@kline_1h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: bluaiusdt@kline_1h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: bluaiusdt@kline_4h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: bluaiusdt@kline_4h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: eulusdt@kline_1h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: eulusdt@kline_1h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: eulusdt@kline_4h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: eulusdt@kline_4h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: turtleusdt@kline_1h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: turtleusdt@kline_1h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: turtleusdt@kline_4h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: turtleusdt@kline_4h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: fusdt@kline_1h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: fusdt@kline_1h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: fusdt@kline_4h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: fusdt@kline_4h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: diausdt@kline_1h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: diausdt@kline_1h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: diausdt@kline_4h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: diausdt@kline_4h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: zenusdt@kline_1h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: zenusdt@kline_1h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: zenusdt@kline_4h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: zenusdt@kline_4h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: kernelusdt@kline_1h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: kernelusdt@kline_1h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: kernelusdt@kline_4h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: kernelusdt@kline_4h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: zbtusdt@kline_1h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: zbtusdt@kline_1h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: zbtusdt@kline_4h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: zbtusdt@kline_4h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: aixbtusdt@kline_1h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: aixbtusdt@kline_1h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: aixbtusdt@kline_4h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: aixbtusdt@kline_4h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: aiotusdt@kline_1h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: aiotusdt@kline_1h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: aiotusdt@kline_4h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: aiotusdt@kline_4h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: avausdt@kline_1h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: avausdt@kline_1h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: avausdt@kline_4h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: avausdt@kline_4h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: injusdt@kline_1h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: injusdt@kline_1h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: injusdt@kline_4h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: injusdt@kline_4h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: meusdt@kline_1h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: meusdt@kline_1h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: meusdt@kline_4h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: meusdt@kline_4h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: seiusdt@kline_1h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: seiusdt@kline_1h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: seiusdt@kline_4h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: seiusdt@kline_4h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: fetusdt@kline_1h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: fetusdt@kline_1h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: fetusdt@kline_4h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: fetusdt@kline_4h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: dashusdt@kline_1h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: dashusdt@kline_1h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: dashusdt@kline_4h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: dashusdt@kline_4h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: cakeusdt@kline_1h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: cakeusdt@kline_1h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: cakeusdt@kline_4h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: cakeusdt@kline_4h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: jellyjellyusdt@kline_1h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: jellyjellyusdt@kline_1h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: jellyjellyusdt@kline_4h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: jellyjellyusdt@kline_4h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: ogusdt@kline_1h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: ogusdt@kline_1h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: ogusdt@kline_4h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: ogusdt@kline_4h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: stblusdt@kline_1h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: stblusdt@kline_1h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: stblusdt@kline_4h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: stblusdt@kline_4h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: snxusdt@kline_1h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: snxusdt@kline_1h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: snxusdt@kline_4h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: snxusdt@kline_4h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: berausdt@kline_1h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: berausdt@kline_1h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: berausdt@kline_4h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: berausdt@kline_4h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: clousdt@kline_1h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: clousdt@kline_1h
[2025-10-29 18:12:11Z] ✅ 已订阅数据流: clousdt@kline_4h
[2025-10-29 18:12:11Z] 🔌 WebSocket已关闭: clousdt@kline_4h
[2025-10-29 18:12:12Z] ✅ 已订阅数据流: dydxusdt@kline_1h
[2025-10-29 18:12:12Z] 🔌 WebSocket已关闭: dydxusdt@kline_1h
[2025-10-29 18:12:12Z] ✅ 已订阅数据流: dydxusdt@kline_4h
[2025-10-29 18:12:12Z] 🔌 WebSocket已关闭: dydxusdt@kline_4h
[2025-10-29 18:12:12Z] ✅ 已订阅数据流: galausdt@kline_1h
[2025-10-29 18:12:12Z] 🔌 WebSocket已关闭: galausdt@kline_1h
[2025-10-29 18:12:12Z] ✅ 已订阅数据流: galausdt@kline_4h
[2025-10-29 18:12:12Z] 🔌 WebSocket已关闭: galausdt@kline_4h
[2025-10-29 18:12:12Z] ✅ 已订阅数据流: atomusdt@kline_1h
[2025-10-29 18:12:12Z] 🔌 WebSocket已关闭: atomusdt@kline_1h
[2025-10-29 18:12:12Z] ✅ 已订阅数据流: atomusdt@kline_4h
[2025-10-29 18:12:12Z] 🔌 WebSocket已关闭: atomusdt@kline_4h
[2025-10-29 18:12:12Z] ✅ 已订阅数据流: onusdt@kline_1h
[2025-10-29 18:12:12Z] 🔌 WebSocket已关闭: onusdt@kline_1h
[2025-10-29 18:12:12Z] ✅ 已订阅数据流: onusdt@kline_4h
[2025-10-29 18:12:12Z] 🔌 WebSocket已关闭: onusdt@kline_4h
[2025-10-29 18:12:12Z] ✅ 已订阅数据流: ipusdt@kline_1h
[2025-10-29 18:12:12Z] 🔌 WebSocket已关闭: ipusdt@kline_1h
[2025-10-29 18:12:12Z] ✅ 已订阅数据流: ipusdt@kline_4h
[2025-10-29 18:12:12Z] 🔌 WebSocket已关闭: ipusdt@kline_4h
[2025-10-29 18:12:12Z] ✅ 已订阅数据流: pnutusdt@kline_1h
[2025-10-29 18:12:12Z] 🔌 WebSocket已关闭: pnutusdt@kline_1h
[2025-10-29 18:12:12Z] ✅ 已订阅数据流: pnutusdt@kline_4h
[2025-10-29 18:12:12Z] 🔌 WebSocket已关闭: pnutusdt@kline_4h
[2025-10-29 18:12:12Z] ✅ 已订阅数据流: neirousdt@kline_1h
[2025-10-29 18:12:12Z] 🔌 WebSocket已关闭: neirousdt@kline_1h
[2025-10-29 18:12:12Z] ✅ 已订阅数据流: neirousdt@kline_4h
[2025-10-29 18:12:12Z] 🔌 WebSocket已关闭: neirousdt@kline_4h
[2025-10-29 18:12:12Z] ✅ 已订阅数据流: 1000flokiusdt@kline_1h
[2025-10-29 18:12:12Z] 🔌 WebSocket已关闭: 1000flokiusdt@kline_1h
[2025-10-29 18:12:12Z] ✅ 已订阅数据流: 1000flokiusdt@kline_4h
[2025-10-29 18:12:12Z] 🔌 WebSocket已关闭: 1000flokiusdt@kline_4h
[2025-10-29 18:12:12Z] ✅ 已订阅数据流: spxusdt@kline_1h
[2025-10-29 18:12:12Z] 🔌 WebSocket已关闭: spxusdt@kline_1h
[2025-10-29 18:12:12Z] ✅ 已订阅数据流: spxusdt@kline_4h
[2025-10-29 18:12:12Z] 🔌 WebSocket已关闭: spxusdt@kline_4h
[2025-10-29 18:12:12Z] ✅ 已订阅数据流: degousdt@kline_1h
[2025-10-29 18:12:12Z] 🔌 WebSocket已关闭: degousdt@kline_1h
[2025-10-29 18:12:12Z] ✅ 已订阅数据流: degousdt@kline_4h
[2025-10-29 18:12:12Z] 🔌 WebSocket已关闭: degousdt@kline_4h
[2025-10-29 18:12:12Z] ✅ 已订阅数据流: edenusdt@kline_1h
[2025-10-29 18:12:12Z] 🔌 WebSocket已关闭: edenusdt@kline_1h
[2025-10-29 18:12:12Z] ✅ 已订阅数据流: edenusdt@kline_4h
[2025-10-29 18:12:12Z] 🔌 WebSocket已关闭: edenusdt@kline_4h
[2025-10-29 18:12:12Z] ✅ 已订阅数据流: ai16zusdt@kline_1h
[2025-10-29 18:12:12Z] 🔌 WebSocket已关闭: ai16zusdt@kline_1h
[2025-10-29 18:12:12Z] ✅ 已订阅数据流: ai16zusdt@kline_4h
[2025-10-29 18:12:12Z] 🔌 WebSocket已关闭: ai16zusdt@kline_4h
[2025-10-29 18:12:12Z] ✅ 已订阅数据流: formusdt@kline_1h
[2025-10-29 18:12:12Z] 🔌 WebSocket已关闭: formusdt@kline_1h
[2025-10-29 18:12:12Z] ✅ 已订阅数据流: formusdt@kline_4h
[2025-10-29 18:12:12Z] 🔌 WebSocket已关闭: formusdt@kline_4h
[2025-10-29 18:12:12Z] ✅ 已订阅数据流: metusdt@kline_1h
[2025-10-29 18:12:12Z] 🔌 WebSocket已关闭: metusdt@kline_1h
[2025-10-29 18:12:12Z] ✅ 已订阅数据流: metusdt@kline_4h
[2025-10-29 18:12:12Z] 🔌 WebSocket已关闭: metusdt@kline_4h
[2025-10-29 18:12:12Z] ✅ 已订阅数据流: blessusdt@kline_1h
[2025-10-29 18:12:12Z] 🔌 WebSocket已关闭: blessusdt@kline_1h
[2025-10-29 18:12:12Z] ✅ 已订阅数据流: blessusdt@kline_4h
[2025-10-29 18:12:12Z] 🔌 WebSocket已关闭: blessusdt@kline_4h
[2025-10-29 18:12:12Z] ✅ 已订阅数据流: algousdt@kline_1h
[2025-10-29 18:12:12Z] 🔌 WebSocket已关闭: algousdt@kline_1h
[2025-10-29 18:12:12Z] ✅ 已订阅数据流: algousdt@kline_4h
[2025-10-29 18:12:12Z] 🔌 WebSocket已关闭: algousdt@kline_4h
[2025-10-29 18:12:12Z] ✅ 已订阅数据流: lineausdt@kline_1h
[2025-10-29 18:12:12Z] 🔌 WebSocket已关闭: lineausdt@kline_1h
[2025-10-29 18:12:12Z] ✅ 已订阅数据流: lineausdt@kline_4h
[2025-10-29 18:12:12Z] 🔌 WebSocket已关闭: lineausdt@kline_4h
[2025-10-29 18:12:12Z] ✅ 已订阅数据流: zorausdt@kline_1h
[2025-10-29 18:12:12Z] 🔌 WebSocket已关闭: zorausdt@kline_1h
[2025-10-29 18:12:12Z] ✅ 已订阅数据流: zorausdt@kline_4h
[2025-10-29 18:12:12Z] 🔌 WebSocket已关闭: zorausdt@kline_4h
[2025-10-29 18:12:12Z] ✅ 已订阅数据流: jupusdt@kline_1h
[2025-10-29 18:12:12Z] 🔌 WebSocket已关闭: jupusdt@kline_1h
[2025-10-29 18:12:12Z] ✅ 已订阅数据流: jupusdt@kline_4h
[2025-10-29 18:12:12Z] 🔌 WebSocket已关闭: jupusdt@kline_4h
[2025-10-29 18:12:12Z] ✅ 已订阅数据流: uselessusdt@kline_1h
[2025-10-29 18:12:12Z] 🔌 WebSocket已关闭: uselessusdt@kline_1h
[2025-10-29 18:12:12Z] ✅ 已订阅数据流: uselessusdt@kline_4h
[2025-10-29 18:12:12Z] 🔌 WebSocket已关闭: uselessusdt@kline_4h
[2025-10-29 18:12:12Z] ✅ 已订阅数据流: flowusdt@kline_1h
[2025-10-29 18:12:12Z] 🔌 WebSocket已关闭: flowusdt@kline_1h
[2025-10-29 18:12:12Z] ✅ 已订阅数据流: flowusdt@kline_4h
[2025-10-29 18:12:12Z] 🔌 WebSocket已关闭: flowusdt@kline_4h
[2025-10-29 18:12:12Z] ✅ 已订阅数据流: 0gusdt@kline_1h
[2025-10-29 18:12:12Z] 🔌 WebSocket已关闭: 0gusdt@kline_1h
[2025-10-29 18:12:12Z] ✅ 已订阅数据流: 0gusdt@kline_4h
[2025-10-29 18:12:12Z] 🔌 WebSocket已关闭: 0gusdt@kline_4h
[2025-10-29 18:12:12Z] ✅ 已订阅数据流: aerousdt@kline_1h
[2025-10-29 18:12:12Z] 🔌 WebSocket已关闭: aerousdt@kline_1h
[2025-10-29 18:12:12Z] ✅ 已订阅数据流: aerousdt@kline_4h
[2025-10-29 18:12:12Z] 🔌 WebSocket已关闭: aerousdt@kline_4h
[2025-10-29 18:12:12Z] ✅ 已订阅数据流: kaitousdt@kline_1h
[2025-10-29 18:12:12Z] 🔌 WebSocket已关闭: kaitousdt@kline_1h
[2025-10-29 18:12:12Z] ✅ 已订阅数据流: kaitousdt@kline_4h
[2025-10-29 18:12:12Z] 🔌 WebSocket已关闭: kaitousdt@kline_4h
[2025-10-29 18:12:12Z] ✅ 已订阅数据流: openusdt@kline_1h
[2025-10-29 18:12:12Z] 🔌 WebSocket已关闭: openusdt@kline_1h
[2025-10-29 18:12:12Z] ✅ 已订阅数据流: openusdt@kline_4h
[2025-10-29 18:12:12Z] 🔌 WebSocket已关闭: openusdt@kline_4h
[2025-10-29 18:12:12Z] ✅ 已订阅数据流: pendleusdt@kline_1h
[2025-10-29 18:12:12Z] 🔌 WebSocket已关闭: pendleusdt@kline_1h
[2025-10-29 18:12:12Z] ✅ 已订阅数据流: pendleusdt@kline_4h
[2025-10-29 18:12:12Z] 🔌 WebSocket已关闭: pendleusdt@kline_4h
[2025-10-29 18:12:12Z] ✅ 已订阅数据流: doodusdt@kline_1h
[2025-10-29 18:12:12Z] 🔌 WebSocket已关闭: doodusdt@kline_1h
[2025-10-29 18:12:12Z] ✅ 已订阅数据流: doodusdt@kline_4h
[2025-10-29 18:12:12Z] 🔌 WebSocket已关闭: doodusdt@kline_4h
[2025-10-29 18:12:12Z] ✅ 已订阅数据流: renderusdt@kline_1h
[2025-10-29 18:12:12Z] 🔌 WebSocket已关闭: renderusdt@kline_1h
[2025-10-29 18:12:12Z] ✅ 已订阅数据流: renderusdt@kline_4h
[2025-10-29 18:12:12Z] 🔌 WebSocket已关闭: renderusdt@kline_4h
[2025-10-29 18:12:12Z] ✅ 已订阅数据流: pippinusdt@kline_1h
[2025-10-29 18:12:12Z] 🔌 WebSocket已关闭: pippinusdt@kline_1h
[2025-10-29 18:12:12Z] ✅ 已订阅数据流: pippinusdt@kline_4h
[2025-10-29 18:12:12Z] 🔌 WebSocket已关闭: pippinusdt@kline_4h
[2025-10-29 18:12:12Z] ✅ 已订阅数据流: rvvusdt@kline_1h
[2025-10-29 18:12:12Z] 🔌 WebSocket已关闭: rvvusdt@kline_1h
[2025-10-29 18:12:12Z] ✅ 已订阅数据流: rvvusdt@kline_4h
[2025-10-29 18:12:12Z] 🔌 WebSocket已关闭: rvvusdt@kline_4h
[2025-10-29 18:12:12Z] ✅ 已订阅数据流: myxusdt@kline_1h
[2025-10-29 18:12:12Z] 🔌 WebSocket已关闭: myxusdt@kline_1h
[2025-10-29 18:12:12Z] ✅ 已订阅数据流: myxusdt@kline_4h
[2025-10-29 18:12:12Z] 🔌 WebSocket已关闭: myxusdt@kline_4h
[2025-10-29 18:12:12Z] ✅ 已订阅数据流: ordiusdt@kline_1h
[2025-10-29 18:12:12Z] 🔌 WebSocket已关闭: ordiusdt@kline_1h
[2025-10-29 18:12:12Z] ✅ 已订阅数据流: ordiusdt@kline_4h
[2025-10-29 18:12:12Z] 🔌 WebSocket已关闭: ordiusdt@kline_4h
[2025-10-29 18:12:12Z] ✅ 已订阅数据流: 2zusdt@kline_1h
[2025-10-29 18:12:12Z] 🔌 WebSocket已关闭: 2zusdt@kline_1h
[2025-10-29 18:12:12Z] ✅ 已订阅数据流: 2zusdt@kline_4h
[2025-10-29 18:12:12Z] 🔌 WebSocket已关闭: 2zusdt@kline_4h
[2025-10-29 18:12:12Z] ✅ 已订阅数据流: icpusdt@kline_1h
[2025-10-29 18:12:12Z] 🔌 WebSocket已关闭: icpusdt@kline_1h
[2025-10-29 18:12:12Z] ✅ 已订阅数据流: icpusdt@kline_4h
[2025-10-29 18:12:12Z] 🔌 WebSocket已关闭: icpusdt@kline_4h
[2025-10-29 18:12:12Z] ============================================================
[2025-10-29 18:12:12Z] ✅ WebSocket K线流已启动
[2025-10-29 18:12:12Z] ============================================================
[2025-10-29 18:12:12Z]    成功: 280 个连接
[2025-10-29 18:12:12Z]    失败: 0 个
[2025-10-29 18:12:12Z] ============================================================
[2025-10-29 18:12:12Z]    15m和1d周期: 使用REST API数据（更新频率低，无需实时订阅）
[2025-10-29 18:12:12Z] 
5️⃣  预加载10维因子系统数据（订单簿、资金费率、现货价格）...
[2025-10-29 18:12:12Z]    5.1 批量获取现货价格...
[2025-10-29 18:12:12Z]        ✅ 获取 93/140 个币种的现货价格
[2025-10-29 18:12:12Z]    5.2 批量获取标记价格和资金费率...
[2025-10-29 18:12:13Z]        ✅ 获取 140 个币种的标记价格和资金费率
[2025-10-29 18:12:13Z]    5.3 批量获取订单簿深度（20档）...
[2025-10-29 18:12:13Z]        注意：此步骤需要~140次API调用，预计15-20秒
[2025-10-29 18:14:40Z]        进度: 60/140 (43%)
[2025-10-29 18:16:48Z]        进度: 120/140 (86%)
[2025-10-29 18:18:19Z]        进度: 140/140 (100%)
[2025-10-29 18:18:19Z]        ✅ 成功: 140, 失败: 0
[2025-10-29 18:18:19Z] 
   [DEBUG] 缓存验证:
[2025-10-29 18:18:19Z]        - orderbook_cache: 140 条目
[2025-10-29 18:18:19Z]        - mark_price_cache: 140 条目
[2025-10-29 18:18:19Z]        - funding_rate_cache: 140 条目
[2025-10-29 18:18:19Z]        - spot_price_cache: 140 条目
[2025-10-29 18:18:19Z]        - BTCUSDT订单簿样本: bids=20, asks=20
[2025-10-29 18:18:19Z]        - BTCUSDT标记价格: 111452.70621739
[2025-10-29 18:18:19Z]        - BTCUSDT资金费率: 3.263e-05
[2025-10-29 18:18:19Z]        - BTCUSDT现货价格: 111501.5
[2025-10-29 18:18:19Z]    5.4 批量获取聚合成交数据（Q因子）...
[2025-10-29 18:21:11Z]        ✅ 成功: 140, 失败: 0
[2025-10-29 18:21:11Z]    5.5 获取BTC和ETH K线数据（I因子）...
[2025-10-29 18:21:11Z]        ✅ 获取BTC K线: 48根
[2025-10-29 18:21:16Z]        ✅ 获取ETH K线: 48根
[2025-10-29 18:21:16Z]    数据预加载完成，耗时: 544.1秒
[2025-10-29 18:21:16Z] 
============================================================
[2025-10-29 18:21:16Z] ✅ 优化批量扫描器初始化完成！
[2025-10-29 18:21:16Z] ============================================================
[2025-10-29 18:21:16Z]    总耗时: 621秒 (10.4分钟)
[2025-10-29 18:21:16Z]    后续扫描将极快（约5秒）
[2025-10-29 18:21:16Z] ============================================================
[2025-10-29 18:21:18Z] 
============================================================
[2025-10-29 18:21:18Z] ✅ 初始化完成！开始扫描...
[2025-10-29 18:21:18Z] ============================================================
[2025-10-29 18:21:18Z] 
============================================================
[2025-10-29 18:21:18Z] 🔍 第 1 次扫描
[2025-10-29 18:21:18Z] ============================================================
[2025-10-29 18:21:18Z] 
============================================================
[2025-10-29 18:21:18Z] 🔍 开始批量扫描（WebSocket缓存加速）
[2025-10-29 18:21:18Z] ============================================================
[2025-10-29 18:21:18Z]    扫描币种: 10 个高流动性币种
[2025-10-29 18:21:18Z]    最低分数: 70
[2025-10-29 18:21:18Z] ============================================================
[2025-10-29 18:21:18Z] 
开始扫描 10 个币种...
[2025-10-29 18:21:18Z] [1/10] 正在分析 ETHUSDT...
[2025-10-29 18:21:18Z]   └─ K线数据: 1h=300根, 4h=200根, 15m=200根, 1d=100根
[2025-10-29 18:21:18Z]   └─ 币种类型：新币B（300小时）
[2025-10-29 18:21:18Z]   └─ 开始因子分析...
[2025-10-29 18:21:18Z]   [DEBUG] ETHUSDT 数据传递:
[2025-10-29 18:21:18Z]       orderbook: 存在 (bids=20 asks=20)
[2025-10-29 18:21:18Z]       mark_price: 3994.36739922
[2025-10-29 18:21:18Z]       funding_rate: 6.248e-05
[2025-10-29 18:21:18Z]       spot_price: 3995.78
[2025-10-29 18:21:18Z]       agg_trades: 500笔（Q因子）
[2025-10-29 18:21:18Z]       btc_klines: 48根
[2025-10-29 18:21:18Z]       eth_klines: 48根
[2025-10-29 18:21:18Z]   [DEBUG] _analyze_symbol_core收到 ETHUSDT:
[2025-10-29 18:21:18Z]       orderbook: 存在 (bids=20 asks=20)
[2025-10-29 18:21:18Z]       mark_price: 3994.36739922
[2025-10-29 18:21:18Z]       funding_rate: 6.248e-05
[2025-10-29 18:21:18Z]       spot_price: 3995.78
[2025-10-29 18:21:18Z]       liquidations: 0条
[2025-10-29 18:21:18Z]       btc_klines: 48根
[2025-10-29 18:21:18Z]       eth_klines: 48根
[2025-10-29 18:21:23Z]   └─ 分析完成（耗时4.4秒）
[2025-10-29 18:21:23Z] [2/10] 正在分析 BTCUSDT...
[2025-10-29 18:21:23Z]   └─ K线数据: 1h=300根, 4h=200根, 15m=200根, 1d=100根
[2025-10-29 18:21:23Z]   └─ 币种类型：新币B（300小时）
[2025-10-29 18:21:23Z]   └─ 开始因子分析...
[2025-10-29 18:21:23Z]   [DEBUG] BTCUSDT 数据传递:
[2025-10-29 18:21:23Z]       orderbook: 存在 (bids=20 asks=20)
[2025-10-29 18:21:23Z]       mark_price: 111452.70621739
[2025-10-29 18:21:23Z]       funding_rate: 3.263e-05
[2025-10-29 18:21:23Z]       spot_price: 111501.5
[2025-10-29 18:21:23Z]       agg_trades: 500笔（Q因子）
[2025-10-29 18:21:23Z]       btc_klines: 48根
[2025-10-29 18:21:23Z]       eth_klines: 48根
[2025-10-29 18:21:23Z]   [DEBUG] _analyze_symbol_core收到 BTCUSDT:
[2025-10-29 18:21:23Z]       orderbook: 存在 (bids=20 asks=20)
[2025-10-29 18:21:23Z]       mark_price: 111452.70621739
[2025-10-29 18:21:23Z]       funding_rate: 3.263e-05
[2025-10-29 18:21:23Z]       spot_price: 111501.5
[2025-10-29 18:21:23Z]       liquidations: 0条
[2025-10-29 18:21:23Z]       btc_klines: 48根
[2025-10-29 18:21:23Z]       eth_klines: 48根
[2025-10-29 18:21:23Z]   └─ 分析完成（耗时0.6秒）
[2025-10-29 18:21:23Z] [3/10] 正在分析 SOLUSDT...
[2025-10-29 18:21:23Z]   └─ K线数据: 1h=300根, 4h=200根, 15m=200根, 1d=100根
[2025-10-29 18:21:23Z]   └─ 币种类型：新币B（300小时）
[2025-10-29 18:21:23Z]   └─ 开始因子分析...
[2025-10-29 18:21:23Z]   [DEBUG] SOLUSDT 数据传递:
[2025-10-29 18:21:23Z]       orderbook: 存在 (bids=20 asks=20)
[2025-10-29 18:21:23Z]       mark_price: 196.58
[2025-10-29 18:21:23Z]       funding_rate: -9.51e-06
[2025-10-29 18:21:23Z]       spot_price: 196.72
[2025-10-29 18:21:23Z]       agg_trades: 500笔（Q因子）
[2025-10-29 18:21:23Z]       btc_klines: 48根
[2025-10-29 18:21:23Z]       eth_klines: 48根
[2025-10-29 18:21:23Z]   [DEBUG] _analyze_symbol_core收到 SOLUSDT:
[2025-10-29 18:21:23Z]       orderbook: 存在 (bids=20 asks=20)
[2025-10-29 18:21:23Z]       mark_price: 196.58
[2025-10-29 18:21:23Z]       funding_rate: -9.51e-06
[2025-10-29 18:21:23Z]       spot_price: 196.72
[2025-10-29 18:21:23Z]       liquidations: 0条
[2025-10-29 18:21:23Z]       btc_klines: 48根
[2025-10-29 18:21:23Z]       eth_klines: 48根
[2025-10-29 18:21:24Z]   └─ 分析完成（耗时0.6秒）
[2025-10-29 18:21:24Z] [4/10] 正在分析 XRPUSDT...
[2025-10-29 18:21:24Z]   └─ K线数据: 1h=300根, 4h=200根, 15m=200根, 1d=100根
[2025-10-29 18:21:24Z]   └─ 币种类型：新币B（300小时）
[2025-10-29 18:21:24Z]   └─ 开始因子分析...
[2025-10-29 18:21:25Z]   └─ 分析完成（耗时0.6秒）
[2025-10-29 18:21:25Z] [5/10] 正在分析 BNBUSDT...
[2025-10-29 18:21:25Z]   └─ K线数据: 1h=300根, 4h=200根, 15m=200根, 1d=100根
[2025-10-29 18:21:25Z]   └─ 币种类型：新币B（300小时）
[2025-10-29 18:21:25Z]   └─ 开始因子分析...
[2025-10-29 18:21:25Z]   └─ 分析完成（耗时0.6秒）
[2025-10-29 18:21:25Z] [6/10] 正在分析 TRUMPUSDT...
[2025-10-29 18:21:25Z]   └─ K线数据: 1h=300根, 4h=200根, 15m=200根, 1d=100根
[2025-10-29 18:21:25Z]   └─ 币种类型：新币B（300小时）
[2025-10-29 18:21:25Z]   └─ 开始因子分析...
[2025-10-29 18:21:26Z]   └─ 分析完成（耗时0.6秒）
[2025-10-29 18:21:26Z] [7/10] 正在分析 DOGEUSDT...
[2025-10-29 18:21:26Z]   └─ K线数据: 1h=300根, 4h=200根, 15m=200根, 1d=100根
[2025-10-29 18:21:26Z]   └─ 币种类型：新币B（300小时）
[2025-10-29 18:21:26Z]   └─ 开始因子分析...
[2025-10-29 18:21:36Z]   └─ ⚠️  分析耗时较长: 10.6秒
[2025-10-29 18:21:36Z]       慢速步骤:
[2025-10-29 18:21:36Z]       - O持仓: 5.3秒
[2025-10-29 18:21:36Z]   └─ 分析完成（耗时10.6秒）
[2025-10-29 18:21:36Z] [8/10] 正在分析 ZECUSDT...
[2025-10-29 18:21:36Z]   └─ K线数据: 1h=300根, 4h=200根, 15m=200根, 1d=100根
[2025-10-29 18:21:36Z]   └─ 币种类型：新币B（300小时）
[2025-10-29 18:21:36Z]   └─ 开始因子分析...
[2025-10-29 18:21:41Z]   └─ 分析完成（耗时4.9秒）
[2025-10-29 18:21:41Z] [9/10] 正在分析 HYPEUSDT...
[2025-10-29 18:21:41Z]   └─ K线数据: 1h=300根, 4h=200根, 15m=200根, 1d=100根
[2025-10-29 18:21:41Z]   └─ 币种类型：新币B（300小时）
[2025-10-29 18:21:41Z]   └─ 开始因子分析...
[2025-10-29 18:21:41Z]   └─ 分析完成（耗时0.2秒）
[2025-10-29 18:21:41Z] [10/10] 正在分析 ASTERUSDT...
[2025-10-29 18:21:41Z]   └─ K线数据: 1h=300根, 4h=200根, 15m=200根, 1d=41根
[2025-10-29 18:21:41Z]   └─ 币种类型：新币B（300小时）
[2025-10-29 18:21:41Z]   └─ 开始因子分析...
[2025-10-29 18:21:42Z]   └─ 分析完成（耗时0.2秒）
[2025-10-29 18:21:42Z] 
============================================================
[2025-10-29 18:21:42Z] ✅ 批量扫描完成
[2025-10-29 18:21:42Z] ============================================================
[2025-10-29 18:21:42Z]    总币种: 10
[2025-10-29 18:21:42Z]    高质量信号: 0
[2025-10-29 18:21:42Z]    跳过: 0（数据不足）
[2025-10-29 18:21:42Z]    错误: 0
[2025-10-29 18:21:42Z]    耗时: 23.3秒
[2025-10-29 18:21:42Z]    速度: 0.4 币种/秒 🚀
[2025-10-29 18:21:42Z]    API调用: 0次 ✅
[2025-10-29 18:21:42Z]    缓存命中率: 100.0%
[2025-10-29 18:21:42Z]    内存占用: 27.9MB
[2025-10-29 18:21:42Z] ============================================================
[2025-10-29 18:21:42Z] 
============================================================
[2025-10-29 18:21:42Z] 📊 扫描结果
[2025-10-29 18:21:42Z] ============================================================
[2025-10-29 18:21:42Z]    总扫描: 0 个币种
[2025-10-29 18:21:42Z]    耗时: 0.0秒
[2025-10-29 18:21:42Z]    发现信号: 0 个
[2025-10-29 18:21:42Z]    Prime信号: 0 个
[2025-10-29 18:21:42Z] ============================================================
[2025-10-29 18:21:49Z] 🔌 WebSocket已关闭: ethusdt@kline_4h
[2025-10-29 18:21:55Z] 🔌 WebSocket已关闭: ethusdt@kline_1h
[2025-10-29 18:22:04Z] 🔌 WebSocket已关闭: btcusdt@kline_1h
[2025-10-29 18:22:11Z] 🔌 WebSocket已关闭: btcusdt@kline_4h
[2025-10-29 18:22:19Z] 🔌 WebSocket已关闭: solusdt@kline_1h
[2025-10-29 18:22:27Z] 🔌 WebSocket已关闭: solusdt@kline_4h
[2025-10-29 18:22:37Z] 🔌 WebSocket已关闭: xrpusdt@kline_1h
[2025-10-29 18:22:46Z] 🔌 WebSocket已关闭: xrpusdt@kline_4h
[2025-10-29 18:22:54Z] 🔌 WebSocket已关闭: bnbusdt@kline_1h
[2025-10-29 18:23:03Z] 🔌 WebSocket已关闭: bnbusdt@kline_4h
[2025-10-29 18:23:10Z] 🔌 WebSocket已关闭: trumpusdt@kline_1h
[2025-10-29 18:23:17Z] 🔌 WebSocket已关闭: trumpusdt@kline_4h
[2025-10-29 18:23:27Z] 🔌 WebSocket已关闭: dogeusdt@kline_1h
[2025-10-29 18:23:34Z] 🔌 WebSocket已关闭: dogeusdt@kline_4h
[2025-10-29 18:23:42Z] 🔌 WebSocket已关闭: zecusdt@kline_1h
[2025-10-29 18:23:51Z] 🔌 WebSocket已关闭: zecusdt@kline_4h
[2025-10-29 18:23:59Z] 🔌 WebSocket已关闭: hypeusdt@kline_1h
[2025-10-29 18:24:08Z] 🔌 WebSocket已关闭: hypeusdt@kline_4h
[2025-10-29 18:24:15Z] 🔌 WebSocket已关闭: asterusdt@kline_1h
[2025-10-29 18:24:25Z] 🔌 WebSocket已关闭: asterusdt@kline_4h
[2025-10-29 18:24:32Z] 🔌 连接WebSocket: ensousdt@kline_1h
[2025-10-29 18:24:32Z] ✅ 客户端已关闭
[2025-10-29 18:24:32Z] ✅ 优化批量扫描器已关闭
[2025-10-29 18:24:32Z] ✅ 扫描器已关闭

================================================================================
  ✅ 系统正常退出
================================================================================

📝 完整日志已保存到: logs/full_system_20251029_181054.log

cryptosignal@vultr-ats:~/cryptosignal$

