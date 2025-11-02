━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CryptoSignal v6.2 服务器部署命令清单
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📌 快速索引：
  1. 全自动部署并运行（一键） → 见下方 ⭐⭐⭐ 【适用所有场景】
  2. 首次部署（全新服务器） → 见下方"首次部署"
  3. 更新部署（手动启动） → 见下方"更新部署（手动启动）" ⭐

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


🚀 全自动部署并运行（一键）⭐⭐⭐ - 最推荐，适用所有场景
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

适用场景：首次部署、更新部署、全新服务器、删除后重新部署

✅ 新增功能（v6.2 增强版）：
  ✓ 自动检测系统环境（Python、pip、git、screen）
  ✓ 自动安装 pip3（如未安装）
  ✓ 自动检测并安装 Python 依赖
  ✓ 首次部署引导（API 配置提示）
  ✓ 智能检测 git 仓库和配置文件
  ✓ 自动启动并发送 Telegram 信号

复制以下命令直接执行：

cd ~/cryptosignal && git fetch origin claude/review-system-overview-011CUhLQjByWuXC1bySJCHKQ && git checkout claude/review-system-overview-011CUhLQjByWuXC1bySJCHKQ && git pull origin claude/review-system-overview-011CUhLQjByWuXC1bySJCHKQ && ./deploy_and_run.sh

执行后：
  - 第 0 步：系统环境检测和依赖自动安装
  - 第 1-8 步：完整部署验证
  - 自动启动完整系统（包括 Telegram 信号发送）
  - 使用 Screen 会话（推荐）或 nohup 后台运行
  - 每 5 分钟扫描 200 个币种，自动发送 Prime 信号


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


🚀 更新部署（手动启动）⭐ - 需要确认后启动
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

适用场景：需要检查配置后再手动启动

复制以下命令直接执行：

cd ~/cryptosignal && git fetch origin claude/review-system-overview-011CUhLQjByWuXC1bySJCHKQ && git checkout claude/review-system-overview-011CUhLQjByWuXC1bySJCHKQ && git pull origin claude/review-system-overview-011CUhLQjByWuXC1bySJCHKQ && ./deploy.sh

执行后：
  - 自动完成8步验证
  - 最后询问是否启动，输入 y 启动，n 跳过


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


🔧 首次部署（全新服务器）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

适用场景：全新服务器，从未部署过


步骤 1：克隆仓库
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

cd ~
git clone <仓库地址> cryptosignal
cd cryptosignal


步骤 2：配置Binance API凭证
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

cat > config/binance_credentials.json <<'EOF'
{
  "_comment": "Binance Futures API凭证配置",
  "binance": {
    "api_key": "YOUR_API_KEY_HERE",
    "api_secret": "YOUR_SECRET_KEY_HERE",
    "testnet": false,
    "_security": "只读权限API Key"
  }
}
EOF

⚠️ 记得替换 YOUR_API_KEY_HERE 和 YOUR_SECRET_KEY_HERE 为真实值


步骤 3：安装Python依赖（如需要）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

pip3 install -r requirements.txt


步骤 4：切换到目标分支并部署
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

git fetch origin claude/review-system-overview-011CUhLQjByWuXC1bySJCHKQ
git checkout claude/review-system-overview-011CUhLQjByWuXC1bySJCHKQ
git pull origin claude/review-system-overview-011CUhLQjByWuXC1bySJCHKQ
./deploy.sh


✅ 首次部署完成后，后续更新只需使用上方"更新部署（一键）"命令


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


🔄 日常运维命令
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

查看运行状态：
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# 检查进程
ps aux | grep realtime_signal_scanner | grep -v grep

# 重连Screen会话（查看实时日志）
screen -r cryptosignal

# 查看日志文件
tail -f logs/scanner_*.log


停止系统：
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# 方式1：在Screen会话中按 Ctrl+C

# 方式2：命令行杀进程
ps aux | grep realtime_signal_scanner | grep -v grep | awk '{print $2}' | xargs kill


手动启动（如果脚本没有自动启动）：
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

cd ~/cryptosignal
./start_production.sh


监控统计：
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# 统计今日Prime信号数
grep -c "🔔 Prime信号" logs/scanner_*.log

# 查看最近10个信号
grep "🔔 Prime信号" logs/scanner_*.log | tail -10

# 查看多空分布（v6.2新增）
grep "多空分布" logs/scanner_*.log | tail -3

# 查看波动率范围（v6.2新增）
grep "波动率范围" logs/scanner_*.log | tail -3

# 检查错误
grep -i "error" logs/scanner_*.log | tail -20


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


📋 v6.2 更新内容（2025-11-01）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ 修复运行时错误：
   - UnboundLocalError: warn变量未定义
   - I因子显示错误（从scores改为modulation）

✅ 选币机制优化：
   - 多空对称：使用abs(波动率)，做多做空机会均衡（1:1）
   - 波动率优先：70%权重，优先选择高波动币种
   - 流动性保障：30%权重，避免滑点过大
   - 预期效果：做空信号增加2-3倍

✅ 扫描优化：
   - 扫描币种：140 → 200个
   - 新增监控：多空分布、波动率范围

✅ 部署流程标准化：
   - 统一使用 ./deploy.sh 一键部署
   - 自动8步验证、备份、清理、测试


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


🆘 常见问题
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Q1: 提示"Binance API配置未填写"
A1: 检查 config/binance_credentials.json 是否存在且填写了真实API
    cat config/binance_credentials.json

Q2: 提示依赖缺失（ModuleNotFoundError）
A2: 重新安装依赖
    pip3 install -r requirements.txt

Q3: 进程启动后自动退出
A3: 查看日志排查错误
    tail -100 logs/scanner_*.log

Q4: 如何查看实时运行日志？
A4: 重连Screen会话
    screen -r cryptosignal
    （按 Ctrl+A 然后 D 可分离会话）

Q5: Screen未安装怎么办？
A5: 脚本会自动使用nohup后台启动
    查看日志：tail -f logs/scanner_*.log


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


📚 详细文档
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- 快速参考：standards/QUICK_DEPLOY.md
- 部署规范：standards/DEPLOYMENT_STANDARD.md
- 版本历史：standards/VERSION_HISTORY.md
- 选币优化说明：docs/COIN_SELECTION_OPTIMIZATION.md
- 系统规范：standards/ 目录下所有文档


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


📞 当前版本
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

版本：v6.2
分支：claude/review-system-overview-011CUhLQjByWuXC1bySJCHKQ
最后更新：2025-11-01

关键提交：
  54654c6 - 选币机制优化（多空对称+波动率优先）
  9687675 - 修复运行时错误
  5987bc5 - 统一标准部署流程


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
