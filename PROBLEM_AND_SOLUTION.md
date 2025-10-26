# 🔴 服务器问题诊断和解决方案

## 📋 诊断摘要

### 问题
**服务已停止运行超过24小时，没有新信号产生**

### 根本原因
**Binance API访问被拒绝（HTTP 403 Forbidden）**

---

## 🔍 详细诊断结果

### 1. 服务状态
- ✅ 数据库正常（80条历史信号）
- ❌ 没有运行中的进程
- ❌ 没有定时任务（crontab）
- ❌ 最后更新: 2025-10-25 13:40:47（已停止24小时+）

### 2. 网络问题
```
测试1: 使用系统代理访问Binance
  → ❌ HTTP 403 Forbidden（代理IP被Binance封禁）

测试2: 不使用代理访问Binance
  → ❌ DNS解析失败（容器必须使用代理访问外网）
```

### 3. 环境分析
```
代理配置:
  HTTP_PROXY = http://container...@21.0.0.197:15002
  NO_PROXY = localhost, *.google.com, ...（不包括binance.com）

问题:
  - 容器环境必须通过代理访问外网
  - 代理IP被Binance封禁（返回403）
  - binance.com不在NO_PROXY白名单中
  - 无法绕过代理直接访问
```

---

## ✅ 解决方案

### 方案1: 修改NO_PROXY环境变量（推荐）⭐

将Binance域名添加到NO_PROXY列表，让对Binance的请求绕过代理。

**操作步骤**：

1. 编辑环境配置（根据您的容器配置方式）：
```bash
# 方式A: 修改容器启动配置
# 在docker-compose.yml或容器启动命令中添加：
environment:
  - NO_PROXY=localhost,127.0.0.1,*.binance.com,binance.com,*.bnbstatic.com

# 方式B: 临时设置（测试用）
export NO_PROXY="$NO_PROXY,*.binance.com,binance.com"
export no_proxy="$no_proxy,*.binance.com,binance.com"
```

2. 重启服务或重新运行程序

**注意**: 这个方案要求容器能够直接访问Binance（不经过代理）

---

### 方案2: 在代码中强制禁用代理

修改 `ats_core/sources/binance.py`，对Binance请求强制不使用代理。

**代码修改**：

```python
# 在 ats_core/sources/binance.py 的 _get 函数中

def _get(
    path_or_url: str,
    params: Optional[Dict[str, Any]] = None,
    *,
    timeout: float = 8.0,
    retries: int = 2,
) -> Any:
    """统一 GET 请求"""
    if path_or_url.startswith("http"):
        url = path_or_url
    else:
        url = BASE + path_or_url
    q = urllib.parse.urlencode({k: v for k, v in (params or {}).items() if v is not None})
    full = f"{url}?{q}" if q else url

    last_err: Optional[Exception] = None
    for i in range(retries + 1):
        try:
            # ========== 新增：对Binance请求禁用代理 ==========
            if 'binance.com' in full:
                proxy_handler = urllib.request.ProxyHandler({})
                opener = urllib.request.build_opener(proxy_handler)
                urllib.request.install_opener(opener)
            # ================================================

            req = urllib.request.Request(full, headers={"User-Agent": "ats-analyzer/1.0"})
            with urllib.request.urlopen(req, timeout=float(timeout)) as r:
                data = r.read()
                return json.loads(data)
        except Exception as e:
            last_err = e
            sleep_retry(i)
    if last_err:
        raise last_err
    raise RuntimeError("unknown http error")
```

**问题**: 根据测试，不使用代理会导致DNS解析失败，所以这个方案在当前环境可能不可行。

---

### 方案3: 更换代理服务器

如果代理IP被Binance永久封禁，需要更换代理。

**操作**：
1. 配置新的代理服务器
2. 更新HTTP_PROXY和HTTPS_PROXY环境变量
3. 测试新代理是否能访问Binance

---

### 方案4: 使用Binance API Key（长期方案）

使用API Key可以提高访问频率限制，降低被封禁风险。

**步骤**：
1. 在Binance创建API Key（只读权限即可）
2. 修改代码添加API Key认证
3. 在请求头中添加签名

**代码示例**：
```python
# 在配置中添加API Key
BINANCE_API_KEY = os.environ.get("BINANCE_API_KEY", "")
BINANCE_API_SECRET = os.environ.get("BINANCE_API_SECRET", "")

# 在请求中添加认证
headers = {
    "User-Agent": "ats-analyzer/1.0",
    "X-MBX-APIKEY": BINANCE_API_KEY
}
```

---

### 方案5: 使用备用数据源

如果Binance访问持续受限，考虑使用其他数据源：
- OKX API
- Bybit API
- CoinGecko API
- CryptoCompare API

---

## 🚀 快速修复测试

### 步骤1: 测试当前代理状态
```bash
# 检查代理是否能访问Binance
curl -x $HTTP_PROXY "https://fapi.binance.com/fapi/v1/ping"
```

### 步骤2: 测试绕过代理（如果可行）
```bash
# 尝试将Binance添加到NO_PROXY
export NO_PROXY="$NO_PROXY,*.binance.com,binance.com"
python3 -m ats_core.pipeline.main
```

### 步骤3: 如果方案2可行，手动运行一次扫描
```bash
# 确保代码修改后，运行一次完整扫描
python3 -m ats_core.pipeline.main
```

---

## 📊 预期结果

修复成功后，您应该看到：
1. ✅ 程序能成功访问Binance API
2. ✅ 开始扫描币对并分析
3. ✅ 生成新的信号并存入数据库
4. ✅ 发送Telegram消息

---

## 🔧 长期建议

### 1. 设置定时任务
```bash
# 创建cron任务，每小时扫描一次
crontab -e

# 添加：
0 * * * * cd /home/user/cryptosignal && python3 -m ats_core.pipeline.main >> /var/log/cryptosignal.log 2>&1
```

### 2. 配置系统服务
创建systemd服务文件（如果系统支持）

### 3. 添加监控
- 监控进程是否运行
- 监控API访问是否正常
- 监控信号生成频率
- 设置告警通知

### 4. 日志管理
- 记录每次运行的日志
- 定期清理旧日志
- 监控错误频率

---

## 📝 下一步操作

**立即执行**：
1. 确定使用哪个方案（推荐方案1或方案4）
2. 实施修复
3. 测试API访问
4. 运行一次完整扫描
5. 设置定时任务

**需要您提供的信息**：
- 是否可以修改容器的NO_PROXY配置？
- 是否有Binance API Key？
- 是否可以更换代理服务器？

根据您的答案，我可以提供更具体的实施步骤。
